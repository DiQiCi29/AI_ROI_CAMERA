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
const char* WIFI_SSID     = "TEN_WIFI_NHA_BAN";    // ← Sửa tên WiFi
const char* WIFI_PASSWORD = "MAT_KHAU_WIFI";        // ← Sửa mật khẩu WiFi
const char* MQTT_SERVER   = "192.168.1.100";        // ← Sửa IP của laptop chạy server
const int   MQTT_PORT     = 1883;
const char* DEVICE_NAME   = "siren_01";             // ← Tên thiết bị (khớp với database)
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