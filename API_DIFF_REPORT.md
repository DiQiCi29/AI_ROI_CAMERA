# 📝 Báo Cáo So Sánh: Thực Tế Code vs. Thiết Kế (API_DESIGN.md)

Bản báo cáo này liệt kê các điểm sai lệch, thiếu sót hoặc các điểm cần lưu ý giữa mã nguồn Flutter hiện tại và tài liệu thiết kế API.

---

## 1. Dịch Vụ API (`ApiService.dart`)

| Chức năng | Trong Thiết Kế (API_DESIGN.md) | Trạng thái trong Code | Ghi chú |
| :--- | :--- | :--- | :--- |
| **Lấy lịch sử Log** | `GET /logs` | ❌ **Thiếu** | Mới chỉ có hàm `getStats()`, chưa có hàm lấy danh sách logs phân trang. |
| **Chi tiết Zone** | `GET /zones/{id}` | ❌ **Thiếu** | Chưa cài đặt hàm lấy thông tin chi tiết của một vùng cụ thể. |
| **Cập nhật Zone** | `PUT /zones/{id}` | ❌ **Thiếu** | Chưa có hàm để chỉnh sửa tọa độ hoặc tên vùng đã có. |
| **Xóa Media** | `DELETE /media/alerts/{id}` | ❌ **Thiếu** | Chưa có hàm hỗ trợ xóa ảnh/video cảnh báo từ app. |
| **Đăng ký FCM** | `POST /auth/register-fcm-token` | ✅ Khớp | Đã cài đặt đúng. |
| **Thống kê Dashboard** | `GET /logs/stats` | ✅ Khớp | Đã cài đặt hàm `getStats()`. |

---

## 2. Models Dữ Liệu (`models/`)

### ZoneModel:
*   **Thiếu trường:** `updated_at`. Trong thiết kế yêu cầu cả `created_at` và `updated_at`.
*   **Thừa trường:** Hiện tại code đang xử lý khá tốt, bám sát các trường tọa độ `%`.

### AlertModel:
*   **Khớp:** Đã có đầy đủ `thumbnail_url`, `video_url`, `bounding_boxes`, `object_count` và `confidence`.

---

## 3. WebSocket (`WebSocketService.dart`)

*   **Sự kiện kết nối:** Thiết kế có sự kiện `{"event": "connected", ...}` gửi từ server khi vừa connect thành công. Code hiện tại đang bỏ qua (không xử lý) sự kiện này.
*   **Keep-alive:** Đã cài đặt đúng cơ chế `ping`/`pong` mỗi 30 giây.
*   **Xử lý sự kiện:** Đã khớp các tên sự kiện chính: `intrusion_detected`, `intrusion_ended`, `camera_status_changed`.

---

## 4. Cấu Hình & Môi Trường (`AppConfig.dart`)

*   **Đường dẫn WebSocket:** Trong thiết kế là `ws://<ip>:<port>/ws?token=...`. Trong code đang dùng `$wsUrl?token=$token`. Cần đảm bảo `wsUrl` trong `AppConfig` không bao gồm `/api/v1` nếu backend tách riêng route WS.
*   **HTTP vs HTTPS:** Code đang dùng `http`. Cần đảm bảo `android:usesCleartextTraffic="true"` luôn tồn tại trong `AndroidManifest.xml` (đã được cập nhật).

---

## 5. Các vấn đề kỹ thuật khác (Android)

*   **Package Name Mismatch:** 
    *   Thiết kế/Config: `com.example.zone_monitor_app` (chữ **o**).
    *   Thực tế thư mục code cũ: `com.example.zone_moniter_app` (chữ **e**).
    *   *Trạng thái:* Đã được chỉnh sửa thủ công để đồng bộ, nhưng cần cẩn thận khi chạy `flutter pub get` hoặc build bản release.

---

## 💡 Đề Xuất Cần Làm Ngay:
1.  Bổ sung hàm `getLogs()` vào `ApiService.dart` để hiển thị lịch sử xâm nhập.
2.  Bổ sung hàm `updateZone()` để người dùng có thể chỉnh sửa vùng cấm sau khi vẽ.
3.  Cập nhật `ZoneModel` thêm trường `updatedAt` để đồng bộ dữ liệu.
4.  Kiểm tra lại URL `videoStream` trong `AppConfig.dart` xem có cần header `Authorization` không (vì thiết kế yêu cầu Bearer token cho MJPEG stream).
