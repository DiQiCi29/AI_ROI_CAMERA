import cv2
import time
import threading
import asyncio
from app.api.v1.routes.websocket import broadcast_event

class AIWorker:
    def __init__(self, detector, rtsp_url: str, camera_id: int = 1):
        self.detector = detector
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self.running = False
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            print(f"[AI Worker] Started for Camera {self.camera_id}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            print(f"[AI Worker] Stopped for Camera {self.camera_id}")

    def _run(self):
        # Mở luồng camera ưu tiên TCP cho ổn định
        cap = cv2.VideoCapture(f"{self.rtsp_url}?transport=tcp", cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Khởi tạo event loop để gửi WebSocket trong Thread này
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        print(f"[AI Worker] Connecting to RTSP: {self.rtsp_url}")

        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("[AI Worker] Connection lost. Reconnecting in 3s...")
                time.sleep(3)
                cap = cv2.VideoCapture(f"{self.rtsp_url}?transport=tcp", cv2.CAP_FFMPEG)
                continue

            # Bỏ ảnh vào YOLO
            output = self.detector.process_frame(frame)
#log test
            print(f"[AI Worker] Frame read. Alert: {output['alert']} | Intruders: {len(output['intruders'])}")

            # Bắn WebSocket (real-time live stream tọa độ)
            if output["alert"]:
                event_data = {
                    "camera_id": str(self.camera_id),
                    "intruders": output["intruders"] # Đây là list bbox 0.0 - 1.0
                }
                # Bắn sự kiện tên là 'live_intrusion_boxes' xuống App Flutter
                loop.run_until_complete(broadcast_event("live_intrusion_boxes", event_data))

            # Giới hạn tốc độ phân tích để đỡ nóng máy (10 FPS là quá đủ cho an ninh)
            time.sleep(0.1)

        cap.release()
        loop.close()