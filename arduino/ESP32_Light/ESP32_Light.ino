/*
 * ESP32 Light (Đèn cảnh báo)
 * ==========================
 * Kết nối: Relay -> GPIO 12
 * 
 * MQTT Topic:
 *   - Command: devices/light_01/command (nhận lệnh từ server)
 *   - Status:  devices/light_01/status  (gửi trạng thái lên server)
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
const char* DEVICE_NAME   = "light_01";             // ← Tên thiết bị
// ═══════════════════════════════════════════════════════════════

const int LIGHT_PIN = 12;
bool light_on = false;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

String command_topic = String("devices/") + DEVICE_NAME + "/command";
String status_topic  = String("devices/") + DEVICE_NAME + "/status";

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 Light starting...");
  
  pinMode(LIGHT_PIN, OUTPUT);
  digitalWrite(LIGHT_PIN, LOW);
  
  connectWiFi();
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();
}

void connectWiFi() {
  Serial.print("[WiFi] Connecting...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" ✅ Connected!");
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(" ❌ Failed!");
  }
}

void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Connecting...");
    
    if (mqttClient.connect(DEVICE_NAME)) {
      Serial.println(" ✅ Connected!");
      mqttClient.subscribe(command_topic.c_str());
      Serial.print("[MQTT] Subscribed to: ");
      Serial.println(command_topic);
      publishStatus();
    } else {
      Serial.println(" ❌ Failed, retrying...");
      delay(5000);
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (int i = 0; i < length; i++) msg += (char)payload[i];
  
  Serial.print("[MQTT] Received: ");
  Serial.println(msg);
  
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, msg);
  if (error) {
    Serial.print("JSON error: ");
    Serial.println(error.c_str());
    return;
  }
  
  const char* cmd = doc["command"];
  if (!cmd) return;
  
  if (strcmp(cmd, "on") == 0) {
    light_on = true;
    digitalWrite(LIGHT_PIN, HIGH);
    Serial.println("[Light] 💡 ON");
  } else if (strcmp(cmd, "off") == 0) {
    light_on = false;
    digitalWrite(LIGHT_PIN, LOW);
    Serial.println("[Light] 💡 OFF");
  } else if (strcmp(cmd, "toggle") == 0) {
    light_on = !light_on;
    digitalWrite(LIGHT_PIN, light_on ? HIGH : LOW);
    Serial.print("[Light] Toggle: ");
    Serial.println(light_on ? "ON" : "OFF");
  }
  
  publishStatus();
}

void publishStatus() {
  StaticJsonDocument<100> doc;
  doc["power"] = light_on ? "on" : "off";
  
  char buffer[100];
  serializeJson(doc, buffer);
  
  if (mqttClient.connected()) {
    mqttClient.publish(status_topic.c_str(), buffer, true);
    Serial.print("[MQTT] Published: ");
    Serial.println(buffer);
  }
}