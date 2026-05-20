/**
 * ESP32 MQTT Simple - LED + Buzzer Only
 * 
 * Chỉ có:
 *   - LED (GPIO19)
 *   - Buzzer (GPIO18)
 *   - WiFi + MQTT
 * 
 * Topics Subscribe:
 *   - home/alarm/siren         {"action":"alarm","duration":60}
 *   - home/light/living_room   {"power":"on"} hoặc {"power":"off"}
 * 
 * Hardware:
 *   - ESP32
 *   - LED + 220Ω trở (GPIO19)
 *   - Buzzer 5V (GPIO18)
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ═══════════════════════════════════════════════════════════════════════════
// ⚙️ CONFIG - EDIT THESE
// ═══════════════════════════════════════════════════════════════════════════

// WiFi
const char* WIFI_SSID = "your_wifi_ssid";
const char* WIFI_PASSWORD = "your_wifi_password";

// MQTT
const char* MQTT_BROKER = "192.168.1.100";    // Backend IP
const int MQTT_PORT = 1883;
const char* MQTT_USER = "mqtt_user";
const char* MQTT_PASS = "mqtt_pass";

// GPIO
const int LED_PIN = 19;
const int BUZZER_PIN = 18;

// ═══════════════════════════════════════════════════════════════════════════
// Global Variables
// ═══════════════════════════════════════════════════════════════════════════

WiFiClient espClient;
PubSubClient client(espClient);

bool ledState = false;
bool buzzerActive = false;
unsigned long buzzerStartTime = 0;
unsigned long buzzerDuration = 0;

// ═══════════════════════════════════════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n╔════════════════════════════════════════╗");
  Serial.println("║     ESP32 LED + Buzzer (Simple)        ║");
  Serial.println("╚════════════════════════════════════════╝\n");
  
  // Init GPIO
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  Serial.println("[✓] GPIO initialized");
  
  // Connect WiFi
  connectWiFi();
  
  // Setup MQTT
  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setCallback(mqttCallback);
  Serial.println("[✓] MQTT configured\n");
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN LOOP
// ═══════════════════════════════════════════════════════════════════════════

void loop() {
  // Check WiFi
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[!] WiFi lost, reconnecting...");
    connectWiFi();
  }
  
  // Check MQTT
  if (!client.connected()) {
    connectMQTT();
  }
  
  // Process messages
  client.loop();
  
  // Handle buzzer timer
  if (buzzerActive) {
    unsigned long elapsed = millis() - buzzerStartTime;
    if (elapsed >= buzzerDuration) {
      buzzerActive = false;
      digitalWrite(BUZZER_PIN, LOW);
      Serial.println("[✓] Buzzer stopped (timer expired)");
    }
  }
  
  delay(10);
}

// ═══════════════════════════════════════════════════════════════════════════
// WiFi
// ═══════════════════════════════════════════════════════════════════════════

void connectWiFi() {
  Serial.print("[*] Connecting WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[✓] WiFi connected!");
    Serial.print("    IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[✗] WiFi failed");
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// MQTT
// ═══════════════════════════════════════════════════════════════════════════

void connectMQTT() {
  int attempts = 0;
  
  while (!client.connected() && attempts < 10) {
    Serial.print("[*] Connecting MQTT: ");
    Serial.println(MQTT_BROKER);
    
    if (client.connect("esp32_led_buzzer", MQTT_USER, MQTT_PASS)) {
      Serial.println("[✓] MQTT connected!");
      
      // Subscribe
      client.subscribe("home/alarm/siren");
      client.subscribe("home/light/living_room");
      Serial.println("    [✓] Subscribed: home/alarm/siren");
      Serial.println("    [✓] Subscribed: home/light/living_room\n");
      
      return;
    } else {
      Serial.print("[✗] Failed (rc=");
      Serial.print(client.state());
      Serial.println(")");
      delay(1000);
      attempts++;
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// MQTT Callback - Xử lý message
// ═══════════════════════════════════════════════════════════════════════════

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("[📨] Topic: ");
  Serial.println(topic);
  Serial.print("    Payload: ");
  Serial.println(message);
  
  // Parse JSON
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.println("[✗] JSON parse error");
    return;
  }
  
  // Route
  if (strcmp(topic, "home/alarm/siren") == 0) {
    handleBuzzer(doc);
  } 
  else if (strcmp(topic, "home/light/living_room") == 0) {
    handleLED(doc);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Command Handlers
// ═══════════════════════════════════════════════════════════════════════════

void handleBuzzer(JsonDocument& doc) {
  const char* action = doc["action"] | "unknown";
  int duration = doc["duration"] | 10;  // Default 10 seconds
  
  Serial.print("[🔔] Buzzer command: ");
  Serial.println(action);
  
  if (strcmp(action, "alarm") == 0) {
    // Start buzzer
    buzzerActive = true;
    buzzerStartTime = millis();
    buzzerDuration = duration * 1000;  // ms
    
    digitalWrite(BUZZER_PIN, HIGH);
    Serial.print("    [✓] BUZZER ON for ");
    Serial.print(duration);
    Serial.println("s");
    
  } else if (strcmp(action, "stop") == 0) {
    // Stop buzzer
    buzzerActive = false;
    digitalWrite(BUZZER_PIN, LOW);
    Serial.println("    [✓] BUZZER OFF");
  }
}

void handleLED(JsonDocument& doc) {
  const char* power = doc["power"] | "off";
  
  Serial.print("[💡] LED command: ");
  Serial.println(power);
  
  if (strcmp(power, "on") == 0) {
    digitalWrite(LED_PIN, HIGH);
    ledState = true;
    Serial.println("    [✓] LED ON");
  } else {
    digitalWrite(LED_PIN, LOW);
    ledState = false;
    Serial.println("    [✓] LED OFF");
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// END
// ═══════════════════════════════════════════════════════════════════════════
