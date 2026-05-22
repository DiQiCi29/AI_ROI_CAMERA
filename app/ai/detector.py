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
DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolov8s.pt")

class IntrusionDetector:
    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        confidence: float = 0.35,
        mqtt_client: Optional[object] = None,
        camera_id: int = 1
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(model_path).to(self.device)
        self.confidence = confidence
        
        self.multi_roi_normalized = [] 
        self.multi_roi_polygons = []   
        
        self._lock = threading.Lock()
        self.mqtt_client = mqtt_client
        self.camera_id = camera_id
        self.last_alert_time = None
        self.alert_cooldown = 2
        self.latest_frame = None
        self._last_log_count = -1  # Throttle log: chỉ in khi số người thay đổi

        print(f"[Detector] Running on : {self.device} | Nhạy: {self.confidence}")

    def update_multi_roi(self, list_of_roi_points: list) -> bool:
        with self._lock:
            self.multi_roi_normalized = []
            for roi_points_raw in list_of_roi_points:
                if len(roi_points_raw) < 3:
                    continue
                normalized_points = []
                for p in roi_points_raw:
                    x, y = float(p[0]), float(p[1])
                    if x > 1.0 or y > 1.0:
                        x, y = x / 100.0, y / 100.0
                    normalized_points.append((x, y))
                self.multi_roi_normalized.append(normalized_points)
            self.multi_roi_polygons = []
        return True

    def _check_intrusion_with_ioa(self, bbox: list) -> bool:
        """
        Thuật toán tối ưu mới: Kiểm tra phần thân dưới của người có giao thoa diện tích với ROI không.
        Chống lỗi khuất chân, rớt gói tọa độ đáy hoặc đứng quá gần camera.
        """
        with self._lock:
            if not self.multi_roi_polygons:
                return False
            polygons = self.multi_roi_polygons

        x1, y1, x2, y2 = bbox
        bbox_h = y2 - y1
        
        # Tạo đa giác hộp đại diện cho 25% phần thân dưới/chân của người
        box_bottom_y1 = y2 - (bbox_h * 0.25)
        person_base_poly = Polygon([
            (x1, box_bottom_y1),
            (x2, box_bottom_y1),
            (x2, y2),
            (x1, y2)
        ])
        
        if not person_base_poly.is_valid:
            return False

        # Kiểm tra xem phần thân dưới này có chạm trúng bất kỳ vùng cấm nào không
        for idx, poly in enumerate(polygons):
            if not poly.is_valid:
                continue
                
            # Tính diện tích phần giao nhau giữa người và vùng cấm
            intersection_area = person_base_poly.intersection(poly).area
            
            # Chỉ cần có phần giao nhau xuất hiện (Diện tích giao nhau > 0) là coi như xâm nhập
            if intersection_area > 0:
                return True
                
        return False

    def process_frame(self, frame: np.ndarray) -> dict:
        height, width = frame.shape[:2]
        
        with self._lock:
            self.latest_frame = frame.copy()
            if self.multi_roi_normalized and not self.multi_roi_polygons:
                self.multi_roi_polygons = []
                for roi_norm in self.multi_roi_normalized:
                    pixel_points = [(int(p[0] * width), int(p[1] * height)) for p in roi_norm]
                    self.multi_roi_polygons.append(Polygon(pixel_points))

        results = self.model(frame, classes=[0], conf=self.confidence, device=self.device, verbose=False)

        intruders = []
        all_people = []
        total_people_found = 0

        for result in results:
            for box in result.boxes:
                total_people_found += 1
                bbox = box.xyxy[0].tolist()  
                conf = float(box.conf[0])

                bbox_norm = [
                    round(bbox[0] / width, 4), round(bbox[1] / height, 4),
                    round(bbox[2] / width, 4), round(bbox[3] / height, 4)
                ]
                
                person = {"bbox": bbox_norm, "confidence": round(conf, 2)}
                all_people.append(person)  # Tất cả người detect được

                # Chỉ thêm vào intruders nếu TRONG ROI
                if self._check_intrusion_with_ioa(bbox):
                    intruders.append(person)

        # Chỉ log khi số người thay đổi (tránh spam)
        if total_people_found != self._last_log_count:
            self._last_log_count = total_people_found
            roi_status = f"CÓ ({len(self.multi_roi_polygons)} vùng)" if self.multi_roi_polygons else "TRỐNG"
            print(f"👀 YOLO thấy {total_people_found} người | ROI: {roi_status} | Xâm nhập: {len(intruders)} | An toàn: {len(all_people) - len(intruders)}")

        output = {
            "alert": len(intruders) > 0,
            "intruders": intruders,
            "all_people": all_people,
            "timestamp": datetime.now().isoformat()
        }
        
        # Kiểm tra trạng thái chế độ giám sát từ bộ nhớ RAM hệ thống
# Trong app/ai/detector.py (Hàm process_frame)
        from app.main import app as fastapi_app

        # Đọc trực tiếp từ bộ nhớ RAM (được Router đồng bộ từ DB liên tục)
        is_monitoring = getattr(fastapi_app.state, "monitoring_active", True)

        if output["alert"]:
            if is_monitoring:
                # Nếu ON: Gửi lệnh MQTT điều khiển còi đèn, bắn WebSocket, gửi FCM hỏa tốc...
                if self.mqtt_client:
                    self._publish_alert_mqtt(output)
                
                # Luồng đẩy FCM khẩn cấp không lưu DB (Xem tiếp ở mục dưới)
                import asyncio
                from app.services.detection_service import on_intrusion_detected_fast
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.run_coroutine_threadsafe(on_intrusion_detected_fast(self.camera_id, intruders), loop)
                except RuntimeError:
                    asyncio.run(on_intrusion_detected_fast(self.camera_id, intruders))
            else:
                # Chế độ giám sát TẮT: AI vẫn hoạt động nhưng im lặng hoàn toàn
                pass  # Silent: monitoring OFF
                
        return output
    
    def _publish_alert_mqtt(self, output: dict):
        try:
            import time
            now = time.time()
            if self.last_alert_time and (now - self.last_alert_time) < self.alert_cooldown:
                return
            self.last_alert_time = now
            payload = {
                "camera_id": self.camera_id,
                "detected_at": output["timestamp"],
                "intruder_count": len(output["intruders"]),
                "intruders": output["intruders"]
            }
            topic = f"alerts/camera_{self.camera_id}/intrusion"
            self.mqtt_client.publish(topic, payload, qos=1)
        except Exception as e:
            print(f"[Detector] ✗ Error MQTT: {str(e)}")

    def draw_frame(self, frame: np.ndarray, output: dict) -> np.ndarray:
        """
        Vẽ annotation lên frame (Dùng để lưu ảnh snapshot lúc có cảnh báo).
        ĐÃ FIX: Hỗ trợ Đa vùng cấm (Multi-Zones) và sửa lỗi tọa độ.
        """
        import cv2
        frame = frame.copy()
        fh, fw = frame.shape[:2]

        # ── Vẽ TẤT CẢ các ROI ───────────────────────────────────────────
        with self._lock:
            rois = self.multi_roi_polygons

        if rois:
            for roi in rois:
                roi_pts = np.array(list(roi.exterior.coords[:-1]), np.int32)

                overlay = frame.copy()
                cv2.fillPoly(overlay, [roi_pts], (0, 255, 0))
                cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)

                cv2.polylines(frame, [roi_pts], isClosed=True, color=(0, 255, 0), thickness=2)

                cx = int(np.mean([p[0] for p in roi_pts]))
                cy = int(np.mean([p[1] for p in roi_pts]))
                cv2.putText(frame, "ROI", (cx - 15, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # ── Vẽ intruders (chỉ khi có alert) ─────────────────────────────
        if output["alert"]:
            for intruder in output["intruders"]:
                # ĐÃ FIX: Chuyển đổi tọa độ chuẩn hóa về tọa độ pixel
                bbox_norm = intruder["bbox"]
                x1 = int(bbox_norm[0] * fw)
                y1 = int(bbox_norm[1] * fh)
                x2 = int(bbox_norm[2] * fw)
                y2 = int(bbox_norm[3] * fh)
                
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
                cv2.putText(frame, label, (x1+3, y1-3), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1)

                # Foot point (Dấu chấm ở chân)
                cv2.circle(frame, ((x1+x2)//2, y2), 5, (0,0,220), -1)

            # Alert banner
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (fw, 50), (0,0,180), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            cv2.putText(frame, "!  INTRUSION DETECTED", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)

        return frame