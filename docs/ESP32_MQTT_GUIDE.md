# 🔌 Hướng dẫn kết nối ESP32 với Server qua MQTT

## 🎯 Tổng quan

Tài liệu này hướng dẫn cách **nạp code cho ESP32** để giao tiếp với server AI_ROI_CAMERA qua giao thức MQTT.

### Luồng giao tiếp:

```
┌─────────────────────────────────────────────────────────────┐
│                        SERVER                               │
│  (FastAPI :8000 + MQTT Service :1883)                      │
│                                                              │
│  ┌──────────────────────┐    ┌────────────────────────┐    │
│  │  MQTTService          │    │  Device API            │    │
│  │  (mqtt_service.py)    │    │  (/api/v1/devices/)    │    │
│  └──────┬───────────────┘    └────────────────────────┘    │
│         │                                                   │
│         │ MQTT Protocol (:1883)                             │
│         │                                                   │
└─────────┼───────────────────────────────────────────────────┘
          │
          │                        ┌─────────────────────┐
          ├── devices/siren_01/command ──►  │                     │
          │   {"command":"on",           │   ESP32              │
          │    "duration":30}            │   (Arduino code)     │
          │                              │                      │
          │ ◄── devices/siren_01/status ──┤                      │
          │        {"power":"on"}         │                      │
          │                              └─────────────────────┘
```

---

## 📋 MQTT Topics Convention

| Topic | Hướng | Mô tả |
|-------|-------|-------|
| `devices/{name}/command` | Server → ESP | Server gửi lệnh điều khiển |
| `devices/{name}/status` | ESP → Server | ESP gửi trạng thái hiện tại |

### Format Command (Server → ESP):
```json
// Bật thiết bị
{"command": "on"}

// Tắt thiết bị
{"command": "off"}

// Chuyển đổi on/off
{"command": "toggle"}

// Bật còi 30 giây (sẽ tự tắt sau 30s)
{"command": "on", "duration": 30}

// Yêu cầu gửi lại trạng thái
{"command": "status"}
```

### Format Status (ESP → Server):
```json
// Trạng thái cơ bản
{"power": "on"}

// Trạng thái với cảm biến
{"power": "on", "temperature": 30.5, "humidity": 65.2}

// Trạng thái với cảnh báo
{"power": "off", "motion_detected": true}
```

---

## 🚀 Code mẫu cho ESP32

### 1. Siren / Còi báo động (ESP32_Siren)

File: `arduino/ESP32_Siren/ESP32_Siren.ino`

```cpp
/*
 * ESP32 Siren (Còi báo động)
 * ==========================
 * Kết nối: 
 *   - Relay/Transistor -> GPIO 13 (điều khiển còi)
 *   - Nút nhấn test    -> GPIO 0 (BOOT button on ESP32 dev board)
 * 
 * MQTT Topic:
 *   - Command: devices/siren_01/command (nhận lệnh từ server)
 *   - Status:  devices/siren_01/status  (gửi trạng thái lên server)
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ═══════════════════════════════════════════════════════════════
// ✅ CẤU HÌNH - SỬA CÁC GIÁ TRỊ NÀY CHO PHÙ HỢP
// ═══════════════════════════════════════════════════════════════
const char* WIFI_SSID     = "WIFI_TEN_MANG";       // ← Sửa tên WiFi
const char* WIFI_PASSWORD = "WIFI_MAT_KHAU";       // ← Sửa mật khẩu WiFi
const char* MQTT_SERVER   = "192.168.1.100";       // ← Sửa IP của laptop chạy server
const int   MQTT_PORT     = 1883;
const char* DEVICE_NAME   = "siren_01";            // ← Tên thiết bị (khớp với database)
// ═══════════════════════════════════════════════════════════════

// GPIO
const int SIREN_PIN = 13;     // Chân điều khiển còi (qua relay)
const int TEST_BTN  = 0;      // Nút test (BOOT button)

// MQTT Topics
String command_topic = String("devices/") + DEVICE_NAME + "/command";
String status_topic  = String("devices/") + DEVICE_NAME + "/status";

// State
bool siren_on = false;
unsigned long siren_off_time = 0;  // Thời điểm tự động tắt còi

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

void setup() {
  Serial.begin(115200);
  Serial.println("\n========================================");
  Serial.println("ESP32 Siren starting...");
  Serial.println("========================================");
  
  pinMode(SIREN_PIN, OUTPUT);
  digitalWrite(SIREN_PIN, LOW);  // Tắt còi ban đầu
  
  pinMode(TEST_BTN, INPUT_PULLUP);
  
  connectWiFi();
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  // Giữ kết nối MQTT
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();
  
  // Kiểm tra tự động tắt còi theo thời gian
  if (siren_on && siren_off_time > 0 && millis() >= siren_off_time) {
    Serial.println("[Siren] ⏰ Auto turn OFF after duration");
    setSiren(false);
  }
  
  // Kiểm tra nút nhấn test (BOOT button)
  if (digitalRead(TEST_BTN) == LOW) {
    delay(200);  // Debounce
    if (digitalRead(TEST_BTN) == LOW) {
      Serial.println("[Siren] 🔘 Test button pressed");
      setSiren(!siren_on);
      publishStatus();
      
      // Đợi nhả nút
      while (digitalRead(TEST_BTN) == LOW) {
        delay(50);
      }
    }
  }
}

// ─── WiFi ─────────────────────────────────────────────────────
void connectWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.print(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] ✅ Connected!");
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WiFi] ❌ Failed to connect!");
  }
}

// ─── MQTT ─────────────────────────────────────────────────────
void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Connecting to ");
    Serial.print(MQTT_SERVER);
    Serial.print(":");
    Serial.print(MQTT_PORT);
    Serial.print("...");
    
    if (mqttClient.connect(DEVICE_NAME)) {
      Serial.println(" ✅ Connected!");
      
      // Subscribe nhận lệnh từ server
      mqttClient.subscribe(command_topic.c_str());
      Serial.print("[MQTT] Subscribed to: ");
      Serial.println(command_topic);
      
      // Gửi trạng thái ban đầu
      publishStatus();
      
    } else {
      Serial.print(" ❌ Failed (rc=");
      Serial.print(mqttClient.state());
      Serial.println(") retrying in 5s...");
      delay(5000);
    }
  }
}

// ─── MQTT Callback (nhận lệnh từ server) ─────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Chuyển payload thành String
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("[MQTT] 📩 Received: ");
  Serial.print(topic);
  Serial.print(" -> ");
  Serial.println(message);
  
  // Parse JSON
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.print("[MQTT] ❌ JSON parse error: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Lấy command
  const char* command = doc["command"];
  int duration = doc["duration"] | 0;
  
  if (!command) {
    Serial.println("[MQTT] ❌ No 'command' field in payload");
    return;
  }
  
  Serial.print("[Siren] Command: ");
  Serial.println(command);
  
  // Xử lý lệnh
  if (strcmp(command, "on") == 0) {
    setSiren(true);
    
    // Nếu có duration, tự động tắt sau duration giây
    if (duration > 0) {
      siren_off_time = millis() + (duration * 1000UL);
      Serial.print("[Siren] ⏰ Will auto-off in ");
      Serial.print(duration);
      Serial.println(" seconds");
    } else {
      siren_off_time = 0;  // Không tự tắt
    }
    
  } else if (strcmp(command, "off") == 0) {
    setSiren(false);
    siren_off_time = 0;
    
  } else if (strcmp(command, "toggle") == 0) {
    setSiren(!siren_on);
    siren_off_time = 0;
    
  } else if (strcmp(command, "status") == 0) {
    // Chỉ gửi lại trạng thái
    publishStatus();
    
  } else {
    Serial.print("[Siren] ❌ Unknown command: ");
    Serial.println(command);
  }
  
  // Gửi trạng thái lên server
  publishStatus();
}

// ─── Điều khiển còi ──────────────────────────────────────────
void setSiren(bool state) {
  siren_on = state;
  digitalWrite(SIREN_PIN, state ? HIGH : LOW);
  Serial.print("[Siren] ");
  Serial.println(state ? "🔔 ON" : "🔕 OFF");
}

// ─── Gửi trạng thái lên server ───────────────────────────────
void publishStatus() {
  StaticJsonDocument<100> doc;
  doc["power"] = siren_on ? "on" : "off";
  
  char buffer[100];
  serializeJson(doc, buffer);
  
  if (mqttClient.connected()) {
    mqttClient.publish(status_topic.c_str(), buffer, true);
    Serial.print("[MQTT] 📤 Published: ");
    Serial.print(status_topic);
    Serial.print(" -> ");
    Serial.println(buffer);
  }
}
```

---

### 2. Đèn cảnh báo (ESP32_Light)

File: `arduino/ESP32_Light/ESP32_Light.ino`

```cpp
/*
 * ESP32 Light (Đèn cảnh báo)
 * ==========================
 * Kết nối: Relay -> GPIO 12
 * 
 * MQTT Topic:
 *   - Command: devices/light_01/command
 *   - Status:  devices/light_01/status
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ═══════════════════════════════════════════════════════════════
// ✅ CẤU HÌNH - SỬA CHO PHÙ HỢP
// ═══════════════════════════════════════════════════════════════
const char* WIFI_SSID     = "WIFI_TEN_MANG";
const char* WIFI_PASSWORD = "WIFI_MAT_KHAU";
const char* MQTT_SERVER   = "192.168.1.100";
const int   MQTT_PORT     = 1883;
const char* DEVICE_NAME   = "light_01";
// ═══════════════════════════════════════════════════════════════

const int LIGHT_PIN = 12;
bool light_on = false;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

String command_topic = String("devices/") + DEVICE_NAME + "/command";
String status_topic  = String("devices/") + DEVICE_NAME + "/status";

void setup() {
  Serial.begin(115200);
  pinMode(LIGHT_PIN, OUTPUT);
  digitalWrite(LIGHT_PIN, LOW);
  
  connectWiFi();
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  if (!mqttClient.connected()) connectMQTT();
  mqttClient.loop();
}

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting WiFi...");
  }
  Serial.println("WiFi connected");
}

void connectMQTT() {
  while (!mqttClient.connected()) {
    if (mqttClient.connect(DEVICE_NAME)) {
      mqttClient.subscribe(command_topic.c_str());
      publishStatus();
    } else {
      delay(5000);
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (int i = 0; i < length; i++) msg += (char)payload[i];
  
  StaticJsonDocument<200> doc;
  deserializeJson(doc, msg);
  
  const char* cmd = doc["command"];
  
  if (strcmp(cmd, "on") == 0) {
    light_on = true;
    digitalWrite(LIGHT_PIN, HIGH);
  } else if (strcmp(cmd, "off") == 0) {
    light_on = false;
    digitalWrite(LIGHT_PIN, LOW);
  } else if (strcmp(cmd, "toggle") == 0) {
    light_on = !light_on;
    digitalWrite(LIGHT_PIN, light_on ? HIGH : LOW);
  }
  
  publishStatus();
}

void publishStatus() {
  StaticJsonDocument<100> doc;
  doc["power"] = light_on ? "on" : "off";
  
  char buffer[100];
  serializeJson(doc, buffer);
  mqttClient.publish(status_topic.c_str(), buffer, true);
}
```

---

### 3. Cảm biến (ESP32_Sensor)

File: `arduino/ESP32_Sensor/ESP32_Sensor.ino`

```cpp
/*
 * ESP32 Sensor (Cảm biến)
 * =======================
 * Kết nối:
 *   - PIR motion sensor -> GPIO 14
 *   - DHT22 temp/humid  -> GPIO 27 (optional)
 * 
 * MQTT Topic:
 *   - Status: devices/sensor_01/status
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID     = "WIFI_TEN_MANG";
const char* WIFI_PASSWORD = "WIFI_MAT_KHAU";
const char* MQTT_SERVER   = "192.168.1.100";
const int   MQTT_PORT     = 1883;
const char* DEVICE_NAME   = "sensor_01";

const int PIR_PIN = 14;
bool last_motion = false;
unsigned long last_publish = 0;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
String status_topic = String("devices/") + DEVICE_NAME + "/status";

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
}

void loop() {
  if (!mqttClient.connected()) {
    while (!mqttClient.connect(DEVICE_NAME)) delay(5000);
  }
  mqttClient.loop();
  
  // Đọc cảm biến mỗi 2 giây
  if (millis() - last_publish > 2000) {
    bool motion = digitalRead(PIR_PIN) == HIGH;
    
    // Chỉ gửi nếu trạng thái thay đổi
    if (motion != last_motion) {
      last_motion = motion;
      
      StaticJsonDocument<100> doc;
      doc["power"] = "on";  // Sensor luôn "on" khi hoạt động
      doc["motion_detected"] = motion;
      
      char buffer[100];
      serializeJson(doc, buffer);
      mqttClient.publish(status_topic.c_str(), buffer, true);
    }
    
    last_publish = millis();
  }
}
```

---

## 🛠️ Hướng dẫn sử dụng (Step by Step)

### Bước 1: Cài đặt Arduino IDE
1. Download và cài [Arduino IDE](https://www.arduino.cc/en/software)
2. Vào **File → Preferences**, thêm URL vào "Additional Boards Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Vào **Tools → Board → Boards Manager**, tìm "ESP32" và cài đặt

### Bước 2: Cài đặt thư viện
Vào **Sketch → Include Library → Manage Libraries**, tìm và cài:
- `PubSubClient` by Nick O'Leary
- `ArduinoJson` by Benoit Blanchon

### Bước 3: Sửa cấu hình trong code
Trong file `.ino`, sửa 3 thông số:

```cpp
const char* WIFI_SSID     = "TEN_WIFI_NHA_BAN";     // ← Tên WiFi nhà bạn
const char* WIFI_PASSWORD = "MAT_KHAU_WIFI";         // ← Mật khẩu WiFi
const char* MQTT_SERVER   = "192.168.1.100";         // ← IP laptop chạy server
```

### Bước 4: Nạp code cho ESP32
1. Kết nối ESP32 với máy tính qua USB
2. Chọn **Tools → Board → ESP32 Dev Module** (hoặc board tương ứng)
3. Chọn đúng **COM port**
4. Nhấn nút **Upload** (→) trong Arduino IDE

### Bước 5: Kiểm tra
Mở **Serial Monitor** (Tools → Serial Monitor), set baud rate `115200`.
Nếu thành công, bạn sẽ thấy:
```
========================================
ESP32 Siren starting...
========================================
[WiFi] Connecting to TEN_WIFI_NHA_BAN.....
[WiFi] ✅ Connected!
[WiFi] IP: 192.168.1.50
[MQTT] Connecting to 192.168.1.100:1883... ✅ Connected!
[MQTT] Subscribed to: devices/siren_01/command
```

### Bước 6: Thêm thiết bị vào Database (dùng Swagger)

Mở Swagger UI: `http://localhost:8000/docs`

**Endpoint**: `POST /api/v1/devices`
```json
{
  "name": "siren_01",
  "device_type": "siren",
  "mqtt_topic": "home/siren",
  "location": "Phòng khách"
}
```

### Bước 7: Kiểm tra gửi lệnh

**Endpoint**: `POST /api/v1/devices/{id}/command`
```json
{
  "command": "on",
  "duration": 10
}
```

👉 Còi sẽ bật trong 10 giây rồi tự tắt!

---

## 🔗 Kiểm tra kết nối tổng thể

### 1. Kiểm tra WiFi
```bash
# Ping ESP32 từ laptop
ping 192.168.1.50   # (IP của ESP32)
```

### 2. Kiểm tra MQTT Broker
```bash
# Kiểm tra Mosquitto có chạy không
docker ps | findstr mosquitto

# Nếu chưa chạy, start Mosquitto
docker-compose up -d mosquitto
```

### 3. Kiểm tra Server MQTT Service
Mở browser: `http://localhost:8000/docs`

Test endpoint: `POST /api/v1/devices/{id}/command`

### 4. Debug trên Serial Monitor của ESP32
Mở Serial Monitor, set 115200 baud. ESP sẽ in log:
- Kết nối WiFi ✅
- Kết nối MQTT ✅
- Nhận được lệnh 📩
- Gửi trạng thái 📤

---

## ⚠️ Troubleshooting

### ESP không kết nối được WiFi
- Kiểm tra SSID và password
- Đảm bảo WiFi ở băng tần 2.4GHz (ESP32 không hỗ trợ 5GHz)
- Khoảng cách đến router không quá xa

### ESP không kết nối được MQTT
- Kiểm tra Mosquitto đã chạy: `docker ps | findstr mosquitto`
- Kiểm tra IP server: `ipconfig` (lấy IPv4 Address)
- Firewall Windows có thể chặn port 1883 → Tạm thời tắt firewall
- Thử telnet: `telnet 192.168.1.100 1883` (từ máy khác)

### Server không nhận status từ ESP
- Đảm bảo topic đúng format: `devices/{name}/status`
- Kiểm tra Serial Monitor của ESP xem có log "Published" không
- Kiểm tra trong Swagger: `GET /api/v1/devices` xem device có `is_online: true` không

---

## 📊 Sơ đồ kết nối vật lý

### Siren (Còi báo động)
```
ESP32                Relay Module              Còi 12V
┌──────┐           ┌──────────┐             ┌────────┐
│ GPIO │──────────►│ IN       │             │        │
│  13  │           │          │             │  Còi   │
│      │           │ VCC ────► 5V           │        │
│      │           │ GND ────► GND          │        │
│      │           │ COM ──────────────────►│ (+)    │
│      │           │ NO  ────► 12V (+)      │ (-) ──► GND
└──────┘           └──────────┘             └────────┘
```

### Light (Đèn cảnh báo)
Tương tự siren nhưng dùng đèn LED hoặc đèn 220V qua relay.

### Sensor (Cảm biến PIR)
```
ESP32           PIR Sensor
┌──────┐       ┌─────────┐
│ GPIO │──────►│ OUT     │
│  14  │       │         │
│      │       │ VCC ───► 5V
│      │       │ GND ───► GND
└──────┘       └─────────┘
```

---

## ✅ Kết luận

**Điều kiện để ESP giao tiếp với server:**
1. ✅ ESP32 và laptop **cùng chung mạng WiFi**
2. ✅ Server đã chạy MQTT Service (thêm trong code mới)
3. ✅ Mosquitto broker đã chạy (docker-compose up -d mosquitto)
4. ✅ ESP32 đã nạp đúng code với IP server
5. ✅ Thiết bị đã được thêm vào database

**Công nghệ sử dụng:**
- **WiFi**: ESP32 kết nối đến router WiFi nhà bạn
- **MQTT**: Giao thức nhẹ cho IoT, chạy trên TCP port 1883
- **Mosquitto**: MQTT Broker (chạy trong Docker)
- **Server**: FastAPI Python với MQTTService