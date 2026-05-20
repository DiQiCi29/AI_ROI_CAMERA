/*
 * ESP32 Sensor (Cảm biến)
 * =======================
 * Kết nối:
 *   - PIR motion sensor -> GPIO 14
 *   - DHT22 temp/humid  -> GPIO 27 (optional, thêm thư viện DHT)
 * 
 * MQTT Topic:
 *   - Status: devices/sensor_01/status (gửi dữ liệu lên server)
 *   
 * ESP32 chủ động gửi dữ liệu cảm biến lên server.
 * Server tự động cập nhật database khi nhận được.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ═══════════════════════════════════════════════════════════════
// ✅ CẤU HÌNH - SỬA CHO PHÙ HỢP
// ═══════════════════════════════════════════════════════════════
const char* WIFI_SSID     = "TEN_WIFI_NHA_BAN";    // ← Sửa WiFi
const char* WIFI_PASSWORD = "MAT_KHAU_WIFI";        // ← Sửa mật khẩu
const char* MQTT_SERVER   = "192.168.1.100";        // ← Sửa IP server
const int   MQTT_PORT     = 1883;
const char* DEVICE_NAME   = "sensor_01";            // ← Tên thiết bị
// ═══════════════════════════════════════════════════════════════

// GPIO Pins
const int PIR_PIN = 14;      // PIR motion sensor
const int LED_PIN = 2;       // LED onboard (ESP32 built-in)

// State
bool current_motion = false;
bool last_motion = false;
unsigned long last_publish = 0;
const unsigned long PUBLISH_INTERVAL = 2000;  // 2 giây gửi 1 lần

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
String status_topic = String("devices/") + DEVICE_NAME + "/status";

void setup() {
  Serial.begin(115200);
  Serial.println("\n========================================");
  Serial.println("ESP32 Sensor starting...");
  Serial.println("========================================");
  
  pinMode(PIR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  connectWiFi();
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
}

void loop() {
  // Giữ kết nối MQTT
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();
  
  // Đọc cảm biến định kỳ
  unsigned long now = millis();
  if (now - last_publish >= PUBLISH_INTERVAL) {
    last_publish = now;
    readAndPublish();
  }
}

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

void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Connecting to ");
    Serial.print(MQTT_SERVER);
    Serial.print("...");
    
    if (mqttClient.connect(DEVICE_NAME)) {
      Serial.println(" ✅ Connected!");
      
      // Gửi trạng thái ngay khi kết nối
      readAndPublish();
      
    } else {
      Serial.print(" ❌ Failed (rc=");
      Serial.print(mqttClient.state());
      Serial.println("), retrying in 5s...");
      delay(5000);
    }
  }
}

void readAndPublish() {
  // Đọc PIR motion sensor
  current_motion = digitalRead(PIR_PIN) == HIGH;
  
  // Chớp LED theo chuyển động
  digitalWrite(LED_PIN, current_motion ? HIGH : LOW);
  
  // Tạo JSON payload
  StaticJsonDocument<200> doc;
  doc["power"] = "on";  // Sensor luôn "on" khi đang hoạt động
  doc["motion_detected"] = current_motion;
  doc["rssi"] = WiFi.RSSI();  // Cường độ WiFi
  
  // Chỉ log khi trạng thái thay đổi
  if (current_motion != last_motion) {
    Serial.print("[Sensor] Motion: ");
    Serial.println(current_motion ? "🚶 DETECTED!" : "❌ None");
    last_motion = current_motion;
  }
  
  // Gửi lên MQTT
  char buffer[200];
  serializeJson(doc, buffer);
  
  if (mqttClient.connected()) {
    bool success = mqttClient.publish(status_topic.c_str(), buffer, true);
    if (success) {
      Serial.print("[MQTT] 📤 Published: ");
      Serial.println(buffer);
    } else {
      Serial.println("[MQTT] ❌ Publish failed");
    }
  }
}