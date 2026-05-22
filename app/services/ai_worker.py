import cv2
import time
import threading
import asyncio
from app.api.v1.routes.websocket import broadcast_event, manager

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
        import os
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000"
        
        cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        print(f"[AI Worker] Connecting to RTSP: {self.rtsp_url}")

        while self.running:
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                time.sleep(2)
                cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue

            output = self.detector.process_frame(frame)

            # Đóng gói dữ liệu gửi qua WebSocket
            event_data = {
                "camera_id": str(self.camera_id),
                "alert": output["alert"],
                "intruders": output["intruders"],
                "all_people": output.get("all_people", [])
            }
            
            try:
                try:
                    main_loop = asyncio.get_running_loop()
                    asyncio.run_coroutine_threadsafe(broadcast_event("live_intrusion_boxes", event_data), main_loop)
                except RuntimeError:
                    asyncio.run(broadcast_event("live_intrusion_boxes", event_data))
            except Exception as ws_err:
                pass  # Silent để không spam log

            time.sleep(0.06)

        cap.release()