import os
import threading
import torch
import numpy as np
from datetime import datetime
from ultralytics import YOLO
from shapely.geometry import Point, Polygon

# Đường dẫn mặc định: cùng thư mục với file detector.py
DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolov8s.pt")


class IntrusionDetector:
    """
    Module AI phát hiện người xâm nhập vào vùng cấm (ROI).

    Cách dùng:
        # Khởi tạo 1 lần duy nhất khi server start
        detector = IntrusionDetector()

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

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, confidence: float = 0.5):
        """
        Khởi tạo model - chỉ gọi 1 lần duy nhất khi server start.

        Args:
            model_path: Đường dẫn tới file weights YOLO (.pt)
                        Mặc định: cùng thư mục với detector.py
            confidence: Ngưỡng confidence để nhận diện người (0.0 - 1.0)
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(model_path).to(self.device)
        self.confidence = confidence
        self.roi_polygon = None
        self._lock = threading.Lock()  # Thread-safe khi update ROI
        print(f"[Detector] Running on : {self.device}")
        print(f"[Detector] Model path : {model_path}")
        print(f"[Detector] Confidence : {confidence}")

    def update_roi(self, roi_points: list) -> bool:
        """
        Cập nhật vùng cấm ROI - thread-safe, gọi bất cứ lúc nào.

        Args:
            roi_points: List tọa độ đa giác [(x1,y1), (x2,y2), ...]
                        Tối thiểu 3 điểm, không cần đóng lại điểm đầu.

        Returns:
            True nếu update thành công, False nếu thất bại.
        """
        if len(roi_points) < 3:
            print("[Detector] ROI cần ít nhất 3 điểm!")
            return False

        with self._lock:
            self.roi_polygon = Polygon(roi_points)

        print(f"[Detector] ROI updated: {roi_points}")
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
        """
        Xử lý 1 frame ảnh từ camera.

        Args:
            frame: numpy array ảnh (BGR format từ OpenCV)

        Returns:
            {
                "alert"    : True nếu có người xâm nhập, False nếu không,
                "intruders": [
                    {
                        "bbox"      : [x1, y1, x2, y2],
                        "confidence": 0.91
                    },
                    ...
                ],
                "timestamp": "2026-05-11T14:00:00.123456"
            }
        """
        results = self.model(
            frame,
            classes=[0],        # Class 0 = person (COCO dataset)
            conf=self.confidence,
            device=self.device,
            verbose=False
        )

        intruders = []

        for result in results:
            for box in result.boxes:
                bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                conf = float(box.conf[0])

                if self._check_intrusion(bbox):
                    intruders.append({
                        "bbox"      : bbox,
                        "confidence": round(conf, 2)
                    })

        return {
            "alert"    : len(intruders) > 0,
            "intruders": intruders,
            "timestamp": datetime.now().isoformat()
        }

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