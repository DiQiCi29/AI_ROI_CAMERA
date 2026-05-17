import os
import cv2
import time
import torch
from app.ai.detector import IntrusionDetector

# ─── Khởi tạo 1 lần duy nhất khi server start ────────────────────────────────
detector = IntrusionDetector()

# ─── Giả lập Mobile App gửi ROI lên server ───────────────────────────────────
ROI_POINTS = [
    (200, 100),
    (400, 100),
    (550, 250),
    (500, 520),
    (150, 520),
    (100, 250)
]
detector.update_roi(ROI_POINTS)

# ─── Main loop (giả lập server nhận frame từ camera) ─────────────────────────
cap = cv2.VideoCapture(0)
prev_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Bạn kia gọi đúng 2 hàm này
    output = detector.process_frame(frame)
    annotated_frame = detector.draw_frame(frame, output)

    # FPS
    curr_time = time.time()
    fps = 1.0 / (curr_time - prev_time + 1e-6)
    prev_time = curr_time
    cv2.putText(annotated_frame, f"FPS: {fps:.1f}",
                (annotated_frame.shape[1] - 100, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

    # Gửi annotated_frame về Mobile App (ở đây chỉ hiển thị)
    cv2.imshow("AI Security Camera", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()