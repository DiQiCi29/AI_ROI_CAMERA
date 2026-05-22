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
        
        # Các biến phục vụ luồng đọc khung hình thời gian thực (Low Latency)
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.cap = None

    def start(self):
        if not self.running:
            self.running = True
            # Khởi chạy luồng chính điều phối AI
            self.thread = threading.Thread(target=self._run_ai_loop, daemon=True)
            self.thread.start()
            print(f"[AI Worker] Started for Camera {self.camera_id}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            print(f"[AI Worker] Stopped for Camera {self.camera_id}")

    def _capture_thread(self):
        """
        LUỒNG PHỤ: Chỉ làm đúng 1 nhiệm vụ duy nhất là đọc khung hình từ RTSP 
        càng nhanh càng tốt nhằm giải phóng và xóa sạch bộ đệm của OpenCV/FFmpeg.
        """
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                break
            
            # Ghi đè khung hình mới nhất vào biến dùng chung
            with self.frame_lock:
                self.latest_frame = frame
                
        print(f"[AI Worker] Capture thread stopped for Camera {self.camera_id}")

    def _run_ai_loop(self):
        """
        LUỒNG CHÍNH: Lấy khung hình mới nhất từ luồng phụ để xử lý AI (YOLO).
        Nếu AI chạy không kịp, các khung hình cũ sẽ tự động bị bỏ qua, triệt tiêu hoàn toàn độ trễ.
        """
        import os
        # Thiết lập cấu hình kết nối TCP để tránh vỡ hình, rớt gói tin
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000"
        
        while self.running:
            print(f"[AI Worker] Connecting to RTSP: {self.rtsp_url}")
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Giới hạn bộ đệm tối thiểu

            if not self.cap.isOpened():
                print(f"[AI Worker] ❌ Không thể mở luồng RTSP, thử lại sau 2 giây...")
                time.sleep(2)
                continue

            # Kích hoạt luồng phụ để đọc xả bộ đệm liên tục ngay khi kết nối thành công
            capture_worker = threading.Thread(target=self._capture_thread, daemon=True)
            capture_worker.start()

            # Vòng lặp tính toán AI
            while self.running and self.cap.isOpened():
                frame = None
                with self.frame_lock:
                    if self.latest_frame is not None:
                        # Lấy bản sao khung hình mới nhất ngoài đời ra xử lý
                        frame = self.latest_frame.copy()
                        # Xóa dấu vết để vòng lặp sau không xử lý lại khung hình cũ này
                        self.latest_frame = None 

                # Nếu luồng phụ chưa kịp đọc được khung hình nào, tạm thời nghỉ một chút rồi kiểm tra lại
                if frame is None:
                    time.sleep(0.005)
                    continue

                # Đưa khung hình thời gian thực vào mô hình YOLOv8 để tính toán ROI
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
                except Exception:
                    pass  # Bỏ qua lỗi nghẽn mạch mạng để giữ tiến trình mượt mà

                # Nghỉ cực ngắn (5ms) để nhường tài nguyên CPU cho luồng đọc, tuyệt đối không sleep 60ms như trước
                time.sleep(0.005)

            # Giải phóng tài nguyên khi luồng kết nối bị đứt để chuẩn bị cho chu kỳ kết nối lại
            if self.cap:
                self.cap.release()
            capture_worker.join(timeout=1.0)
            time.sleep(2)