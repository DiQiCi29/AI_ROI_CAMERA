import os
import threading
import torch
import numpy as np
import json
import logging
from datetime import datetime
from typing import Optional
from ultralytics import YOLO
from shapely.geometry import Point, Polygon

logger = logging.getLogger(__name__)

# Đường dẫn mặc định: cùng thư mục với file detector.py
DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolov8s.pt")


class IntrusionDetector:
    """
    Module AI phát hiện người xâm nhập vào vùng cấm (ROI).
    Hỗ trợ MQTT publish alerts tới Backend.

    Cách dùng:
        # Khởi tạo 1 lần duy nhất khi server start
        detector = IntrusionDetector(mqtt_client=mqtt_client, camera_id=1)

        # Cập nhật ROI từ App bất cứ lúc nào (thread-safe)
        detector.update_roi([(x1,y1), (x2,y2), (x3,y3), ...])

        # Gọi mỗi frame camera gửi vào
        output = detector.process_frame(frame)
        # output = {
        #     "alert"    : True/False,
        #     "intruders": [{"bbox": [x1,y1,x2,y2], "confidence": 0.91}, ...],
        #     "timestamp": "2026-05-11T14:00:00.123456"
        # }
    """

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        confidence: float = 0.5,
        mqtt_client: Optional[object] = None,
        camera_id: int = 1
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(model_path).to(self.device)
        self.confidence = confidence
        
        # Đổi thành lưu mảng tọa độ chuẩn hóa thay vì Polygon cứng
        self.roi_normalized = None 
        self._lock = threading.Lock()
        
        self.mqtt_client = mqtt_client
        self.camera_id = camera_id
        self.last_alert_time = None
        self.alert_cooldown = 2
        self.latest_frame = None

        print(f"[Detector] Running on : {self.device}")
        

    def update_roi(self, roi_points_norm: list) -> bool:
        """
        Cập nhật vùng cấm ROI (Tọa độ chuẩn hóa 0.0 - 1.0)
        Ví dụ: [(0.1, 0.2), (0.9, 0.2), (0.9, 0.8), (0.1, 0.8)]
        """
        if len(roi_points_norm) < 3:
            return False

        with self._lock:
            self.roi_normalized = roi_points_norm

        print(f"[Detector] ROI Normalized updated: {roi_points_norm}")
        return True

    def _check_intrusion(self, bbox: list) -> bool:
        """
        Kiểm tra điểm chân người có nằm trong ROI không.

        Args:
            bbox: [x1, y1, x2, y2]

        Returns:
            True nếu chân người nằm trong ROI.
        """
        with self._lock:
            if self.roi_polygon is None:
                return False
            roi = self.roi_polygon

        x1, y1, x2, y2 = bbox
        foot_point = Point((x1 + x2) / 2, y2)  # bottom-center
        return roi.contains(foot_point)

    def process_frame(self, frame: np.ndarray) -> dict:
        """Xử lý frame và trả về BBox chuẩn hóa"""
        height, width = frame.shape[:2]
        self.latest_frame = frame.copy()
        # 1. Tạo Polygon theo kích thước pixel thực tế của frame hiện tại
        with self._lock:
            if self.roi_normalized:
                pixel_points = [(int(p[0] * width), int(p[1] * height)) for p in self.roi_normalized]
                self.roi_polygon = Polygon(pixel_points)
            else:
                self.roi_polygon = None

        # 2. Nhận diện (Để tránh lỗi méo ảnh, ta nhận diện toàn khung hình)
        results = self.model(
            frame,
            classes=[0],        # Chỉ nhận diện người (Class 0)
            conf=self.confidence,
            device=self.device,
            verbose=False
        )

        intruders = []
        total_people_found = 0 # Biến đếm debug

        for result in results:
            for box in result.boxes:
                total_people_found += 1 # Cộng dồn số người YOLO thấy được
                bbox = box.xyxy[0].tolist()  
                conf = float(box.conf[0])

                if self._check_intrusion(bbox):
                    # 3. CHUẨN HÓA BBOX TRƯỚC KHI GỬI VỀ APP
                    bbox_norm = [
                        round(bbox[0] / width, 4),
                        round(bbox[1] / height, 4),
                        round(bbox[2] / width, 4),
                        round(bbox[3] / height, 4)
                    ]
                    intruders.append({
                        "bbox": bbox_norm,
                        "confidence": round(conf, 2)
                    })

        # --- THÊM DÒNG LOG NÀY ĐỂ DEBUG ---
        # print(f"[Detector] Frame size: {width}x{height} | YOLO found total: {total_people_found} people | Inside ROI: {len(intruders)}")

        output = {
            "alert"    : len(intruders) > 0,
            "intruders": intruders,
            "timestamp": datetime.now().isoformat()
        }
        
        if output["alert"] and self.mqtt_client:
            self._publish_alert_mqtt(output)
        
        return output
    
    def _publish_alert_mqtt(self, output: dict):
        """
        Publish intrusion alert tới MQTT broker
        Topic: alerts/camera_{id}/intrusion
        
        Args:
            output: Dict output từ process_frame()
        """
        try:
            import time
            now = time.time()
            
            # Cooldown để tránh spam (chỉ publish mỗi 2 giây)
            if self.last_alert_time and (now - self.last_alert_time) < self.alert_cooldown:
                return
            
            self.last_alert_time = now
            
            # Prepare MQTT payload
            payload = {
                "camera_id": self.camera_id,
                "detected_at": output["timestamp"],
                "intruder_count": len(output["intruders"]),
                "intruders": output["intruders"]
            }
            
            # Publish to MQTT
            topic = f"alerts/camera_{self.camera_id}/intrusion"
            success = self.mqtt_client.publish(topic, payload, qos=1)
            
            if success:
                print(f"[Detector] 📤 MQTT Alert published: {topic} (count: {len(output['intruders'])})")
            else:
                print(f"[Detector] ⚠️  MQTT publish failed for {topic}")
                
        except Exception as e:
            print(f"[Detector] ✗ Error publishing MQTT alert: {str(e)}")

    def draw_frame(self, frame: np.ndarray, output: dict) -> np.ndarray:
        """
        Vẽ annotation lên frame để gửi về Mobile App.
        - Bình thường : chỉ vẽ ROI (xanh lá)
        - Có intruder : vẽ ROI + bbox người xâm nhập (đỏ) + alert banner

        Args:
            frame : numpy array ảnh gốc (BGR)
            output: dict trả về từ process_frame()

        Returns:
            numpy array ảnh đã vẽ annotation (BGR)
        """
        import cv2
        frame = frame.copy()

        # ── Vẽ ROI ──────────────────────────────────────────────────────
        with self._lock:
            roi = self.roi_polygon

        if roi is not None:
            roi_pts = np.array(list(roi.exterior.coords[:-1]), np.int32)

            overlay = frame.copy()
            cv2.fillPoly(overlay, [roi_pts], (0, 255, 0))
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)

            cv2.polylines(frame, [roi_pts], isClosed=True,
                          color=(0, 255, 0), thickness=2)

            cx = int(np.mean([p[0] for p in roi_pts]))
            cy = int(np.mean([p[1] for p in roi_pts]))
            cv2.putText(frame, "ROI", (cx - 15, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # ── Vẽ intruders (chỉ khi có alert) ─────────────────────────────
        if output["alert"]:
            for intruder in output["intruders"]:
                x1, y1, x2, y2 = map(int, intruder["bbox"])
                conf = intruder["confidence"]
                r = 12

                # Bounding box bo góc màu đỏ
                cv2.line(frame, (x1+r, y1), (x2-r, y1), (0,0,220), 2)
                cv2.line(frame, (x1+r, y2), (x2-r, y2), (0,0,220), 2)
                cv2.line(frame, (x1, y1+r), (x1, y2-r), (0,0,220), 2)
                cv2.line(frame, (x2, y1+r), (x2, y2-r), (0,0,220), 2)
                cv2.ellipse(frame, (x1+r, y1+r), (r,r), 180, 0, 90, (0,0,220), 2)
                cv2.ellipse(frame, (x2-r, y1+r), (r,r), 270, 0, 90, (0,0,220), 2)
                cv2.ellipse(frame, (x1+r, y2-r), (r,r),  90, 0, 90, (0,0,220), 2)
                cv2.ellipse(frame, (x2-r, y2-r), (r,r),   0, 0, 90, (0,0,220), 2)

                # Label có nền
                label = f"INTRUDER {conf}"
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                cv2.rectangle(frame, (x1, y1-h-6), (x1+w+6, y1+2), (0,0,220), -1)
                cv2.putText(frame, label, (x1+3, y1-3),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1)

                # Foot point
                cv2.circle(frame, ((x1+x2)//2, y2), 5, (0,0,220), -1)

            # Alert banner
            fh, fw = frame.shape[:2]
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (fw, 50), (0,0,180), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            cv2.putText(frame, "!  INTRUSION DETECTED", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)

        return frame