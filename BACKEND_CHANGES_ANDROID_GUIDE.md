# Backend Changes & Android App Sync Guide

## 1. Stream: HLS thay thế MJPEG

### Backend đã thêm
- `GET /api/v1/stream/urls?camera_id=N` → trả về HLS/WebRTC/RTSP URLs

### Android cần sửa
- **Cũ**: gọi `/stream/video?camera_id=N` (MJPEG)
- **Mới**: gọi `/stream/urls?camera_id=N` → lấy `hls` URL → dùng ExoLoader/PlayerView

**Lưu ý**: Port HLS của MediaMTX là **8888**, URL mẫu: `http://server:8888/camera_01/index.m3u8`

---

## 2. Dashboard: Camera không offline nữa

### Backend đã sửa
- `/stream/status` đã match đúng path MediaMTX (cả `camera_1` lẫn `camera_01`)
- Thêm trạng thái `"connecting"` khi camera đang chờ kết nối

### Android không cần sửa
Chỉ cần gọi `GET /stream/status?camera_id=N` như cũ, response sẽ có `status: "online"` thay vì `"offline"`.

---

## 3. Logout: Tức thì

### Backend đã thêm
- Token blacklist: khi logout, JWT bị chặn ngay

### Android cần sửa
- Khi gọi `DELETE /auth/logout`, **phải gửi kèm Header**:
  ```
  Authorization: Bearer <token>
  ```
  (đây là header chuẩn FastAPI HTTPBearer — nếu code cũ đã gửi rồi thì không cần sửa gì)

---

## 4. Đồng bộ camera mới với MediaMTX

Khi thêm camera mới từ Android vào database, chạy lệnh sau trên server:

```bash
python mediamtx/setup_camera.py
```

Script này sẽ gọi API MediaMTX để tạo path tương ứng cho camera mới.

---

## 5. Tóm tắt API endpoints thay đổi

| Endpoint | Method | Android cần sửa? | Ghi chú |
|----------|--------|------------------|---------|
| `/stream/video` | GET | ✅ **Nên thay bằng HLS** | Vẫn hoạt động, nhưng HLS mượt hơn |
| `/stream/urls` | GET **(mới)** | ✅ **Gọi để lấy HLS URL** | Trả về HLS/WebRTC/RTSP |
| `/stream/list` | GET **(mới)** | Tùy chọn | Danh sách camera + HLS URL |
| `/stream/status` | GET | ❌ Giữ nguyên | Đã sửa backend |
| `/auth/logout` | DELETE | ❌ Giữ nguyên | Đã thêm blacklist backend |