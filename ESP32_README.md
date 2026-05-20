# 🔔 ESP32 Simple - LED + Buzzer

## 📋 Tóm Tắt

File `esp32_simple.ino` - Firmware đơn giản:
- ✅ LED (GPIO19) - bật/tắt
- ✅ Buzzer (GPIO18) - cảnh báo với timeout
- ✅ WiFi + MQTT
- ❌ Không cảm biến DHT/PIR

---

## ⚙️ Cấu Hình

Mở `esp32_simple.ino`, edit dòng 18-32:

```cpp
const char* WIFI_SSID = "YourWiFi";        // Tên WiFi
const char* WIFI_PASSWORD = "YourPass";    // Mật khẩu
const char* MQTT_BROKER = "192.168.1.100"; // IP Backend
const char* MQTT_USER = "mqtt_user";       // Từ .env
const char* MQTT_PASS = "mqtt_pass";       // Từ .env
```

---

## 📦 Library Cần Install

**Sketch → Include Library → Manage Libraries**, search & install:
1. **PubSubClient** (Nick O'Leary)
2. **ArduinoJson** (Benoit Blanchon)

**Board:**
- Tools → Board → Boards Manager → Search "esp32" → Install

---

## 🚀 Upload

1. Connect ESP32 USB
2. Tools → Board → ESP32 Dev Module
3. Tools → Port → COM#
4. Sketch → Upload (Ctrl+U)
5. Tools → Serial Monitor (115200 baud)

**Expected:**
```
[✓] GPIO initialized
[✓] WiFi connected!
[✓] MQTT connected!
    [✓] Subscribed: home/alarm/siren
    [✓] Subscribed: home/light/living_room
```

---

## 📡 MQTT Commands

### LED On
```bash
mosquitto_pub -h 192.168.1.100 -p 1883 \
  -u mqtt_user -P mqtt_pass \
  -t "home/light/living_room" \
  -m '{"power":"on"}'
```

### LED Off
```bash
mosquitto_pub -h 192.168.1.100 -p 1883 \
  -u mqtt_user -P mqtt_pass \
  -t "home/light/living_room" \
  -m '{"power":"off"}'
```

### Buzzer On (30 seconds)
```bash
mosquitto_pub -h 192.168.1.100 -p 1883 \
  -u mqtt_user -P mqtt_pass \
  -t "home/alarm/siren" \
  -m '{"action":"alarm","duration":30}'
```

### Buzzer Stop
```bash
mosquitto_pub -h 192.168.1.100 -p 1883 \
  -u mqtt_user -P mqtt_pass \
  -t "home/alarm/siren" \
  -m '{"action":"stop"}'
```

---

## 🔌 Hardware

```
ESP32 Board
├─ GPIO18 → Buzzer (+) [- → GND]
├─ GPIO19 → LED (+) [- → GND via 220Ω resistor]
└─ GND → Ground
```

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| WiFi không connect | Check SSID, use 2.4GHz, check signal |
| MQTT không connect | Check broker IP, check credentials, firewall port 1883 |
| No serial output | Check baud (115200), check USB cable |
| Buzzer/LED không hoạt động | Check GPIO pins, check wiring |

---

## 💡 Notes

- Buzzer tự stop sau duration
- Default: 10 seconds nếu không specify
- GPIO19 = LED, GPIO18 = Buzzer
