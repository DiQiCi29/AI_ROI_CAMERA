# ✅ Docker Setup - Mosquitto + Backend

## 📝 Các File Đã Cập Nhật

✅ `.env` - MQTT_HOST thay từ `localhost` → `mosquitto`
✅ `docker-compose.yml` - DB name, MQTT config chuẩn
✅ `mosquitto.conf` - Config Mosquitto tạo sẵn

---

## 🚀 Cách Chạy (Trên Docker)

### **Step 1: Tạo thư mục mosquitto**

```bash
mkdir mosquitto/config
mkdir mosquitto/data
```

### **Step 2: Copy config file**

```bash
# Windows:
copy mosquitto.conf mosquitto\config\mosquitto.conf
```

### **Step 3: Chạy Docker**

```bash
docker-compose up -d
```

**Check:**
```bash
docker-compose ps
```

**Output:**
```
smart_home_mysql    Up
smart_home_mqtt     Up
```

### **Step 4: Chạy Backend**

```bash
pip install -r requirements.txt
python app/main.py
```

✅ **OK!**

---

## ✅ Verify

### **Test MQTT từ Backend**

```bash
# Terminal, project root:
mosquitto_pub -h localhost -t "test" -m "hello"
```

### **Test API**

```bash
curl -X POST http://localhost:8000/api/v1/devices/1/control \
  -H "Content-Type: application/json" \
  -d '{"action":"alarm","duration":5}'
```

---

## 📊 Giải Thích Thay Đổi

| File | Thay Đổi |
|------|---------|
| `.env` | `MQTT_HOST=localhost` → `MQTT_HOST=mosquitto` |
| `.env` | `DB_HOST=localhost` → `DB_HOST=mysql` |
| `docker-compose.yml` | `MYSQL_DATABASE: smart_home_db` → `AI_ROI_CAMERA` |
| `mosquitto.conf` | Tạo mới, listen tất cả IP (0.0.0.0) |

**Tại sao?**
- Docker containers kết nối qua service names (mosquitto, mysql)
- Không dùng localhost
- Mosquitto listen 0.0.0.0 = ESP32 + local đều kết nối được

---

## 🎯 ESP32 Config

Khi bạn merge vào nhánh main, ESP32 config vẫn:

```cpp
const char* MQTT_BROKER = "192.168.123.244";  // IP của máy chạy Docker
```

✅ **Không thay đổi!**

---

## 📋 Commit & Push

```bash
git add .env docker-compose.yml mosquitto.conf
git commit -m "Switch MQTT to Docker - use service names"
git push origin mqtt_ver_2
```

✅ **Xong!** Bạn tôi merge nhánh này vào main sẽ dễ dàng hơn.
