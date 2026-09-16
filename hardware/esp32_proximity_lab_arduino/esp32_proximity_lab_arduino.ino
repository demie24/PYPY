/*
  ============================================================================
  LAB QUESTION 1 - ESP32 DUAL-INTERFACE PROXIMITY MONITORING SYSTEM
  ============================================================================
  Compatible with: Arduino IDE 1.8.x & Arduino IDE 2.x
  Board: ESP32 Dev Module / ESP32 WROOM DA (38-Pin)

  Hardware Pin Map:
  - Ultrasonic Sensor HC-SR04: Trig = GPIO 17, Echo = GPIO 23
  - Green LED  : GPIO 16 (< 20 cm)
  - Yellow LED : GPIO 18 (20 cm - 35 cm)
  - Red LED    : GPIO 19 (> 35 cm)
  ============================================================================
*/

#include <Arduino.h>
#include <WiFi.h>
#include <LittleFS.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>

// ============================================================================
// HARDWARE PIN CONFIGURATION
// ============================================================================
#define TRIG_PIN       17  // Ultrasonic Sensor Trigger Pin
#define ECHO_PIN       23  // Ultrasonic Sensor Echo Pin

#define GREEN_LED_PIN  16  // Green LED Indicator (< 20 cm)
#define YELLOW_LED_PIN 18  // Yellow LED Indicator (20 cm - 35 cm)
#define RED_LED_PIN    19  // Red LED Indicator (> 35 cm)

// ============================================================================
// WI-FI NETWORK CONFIGURATION (WIFI_AP_STA Dual Mode)
// ============================================================================
// Soft Access Point (AP Mode) - Direct Laptop Connection
const char* AP_SSID = "phone demie";
const char* AP_PASS = "asdfghjkl123";

// Station (STA Mode) - Facility Wi-Fi Router Connection for Mobile Devices
const char* STA_SSID = "phone demie";
const char* STA_PASS = "asdfghjkl123";

// Global Objects & Variables
AsyncWebServer server(80);
float currentDistance = 0.0;
String currentLEDStatus = "GREEN";
String currentHealthStatus = "NORMAL";
unsigned long lastSensorReadTime = 0;
const unsigned long SENSOR_READ_INTERVAL = 150; // Read sensor every 150 ms

// ============================================================================
// SENSOR BACAAN JARAK & LOGIK AMBANG (DISTANCE THRESHOLD LOGIC)
// ============================================================================
float measureDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Read Echo pulse width with 30ms timeout (~500 cm max range)
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) {
    return -1.0; // Out of range or sensor timeout
  }

  // Speed of sound = 343 m/s -> 0.0343 cm/us (divide by 2 for round-trip)
  float distance = (duration * 0.0343f) / 2.0f;
  return distance;
}

void evaluateThresholdsAndSetLEDs(float dist) {
  if (dist < 0.0f) {
    currentHealthStatus = "SENSOR ERROR / TIMEOUT";
    currentLEDStatus = "OFF";
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);
    return;
  }

  // Logik Ambang (Requirement 2):
  // - Distance < 20 cm: Green LED ON (Yellow & Red OFF)
  // - 20 cm <= Distance <= 35 cm: Yellow LED ON (Green & Red OFF)
  // - Distance > 35 cm: Red LED ON (Green & Yellow OFF)
  if (dist < 20.0f) {
    digitalWrite(GREEN_LED_PIN, HIGH);
    digitalWrite(YELLOW_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);
    currentLEDStatus = "GREEN";
    currentHealthStatus = "SAFE RANGE (< 20 cm)";
  } else if (dist >= 20.0f && dist <= 35.0f) {
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, HIGH);
    digitalWrite(RED_LED_PIN, LOW);
    currentLEDStatus = "YELLOW";
    currentHealthStatus = "WARNING RANGE (20 cm - 35 cm)";
  } else { // dist > 35.0f
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, HIGH);
    currentLEDStatus = "RED";
    currentHealthStatus = "CRITICAL RANGE (> 35 cm)";
  }
}

// ============================================================================
// ARDUINO SETUP FUNCTION
// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n==============================================");
  Serial.println(" ESP32 Dual-Interface Proximity Monitor (Arduino IDE) ");
  Serial.println("==============================================");

  // 1. Initialize Pin Modes
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(YELLOW_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);

  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(YELLOW_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);

  // 2. Initialize LittleFS File System
  if (!LittleFS.begin(true)) {
    Serial.println("[ERROR] LittleFS Mounting Failed!");
  } else {
    Serial.println("[OK] LittleFS File System Mounted Successfully");
  }

  // 3. Network Setup (Requirement 3: Enable WIFI_AP_STA Dual Mode)
  WiFi.mode(WIFI_AP_STA);
  Serial.println("[NET] WiFi Mode set to WIFI_AP_STA (Dual Mode)");

  // Start Soft Access Point (AP Mode for Laptop Direct Connection)
  bool apSuccess = WiFi.softAP(AP_SSID, AP_PASS);
  IPAddress apIP = WiFi.softAPIP();
  if (apSuccess) {
    Serial.print("[AP] SoftAP Started. SSID: ");
    Serial.print(AP_SSID);
    Serial.print(" | IP: ");
    Serial.println(apIP);
  } else {
    Serial.println("[AP] SoftAP Failed to Start!");
  }

  // Connect to Local Wi-Fi Router (STA Mode for Mobile Access)
  Serial.print("[STA] Connecting to Router SSID: ");
  Serial.println(STA_SSID);
  WiFi.begin(STA_SSID, STA_PASS);

  // 4. Web Server Endpoints Setup (Requirement 4)
  // Serve static index.html from LittleFS
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    if (LittleFS.exists("/index.html")) {
      request->send(LittleFS, "/index.html", "text/html");
    } else {
      request->send(404, "text/plain", "LittleFS Error: index.html not found. Please upload LittleFS file system image.");
    }
  });

  // Serve dynamic JSON data for live Web UI updates
  server.on("/api/data", HTTP_GET, [](AsyncWebServerRequest *request) {
    StaticJsonDocument<300> jsonDoc;
    jsonDoc["distance"] = (currentDistance >= 0.0) ? String(currentDistance, 1).toFloat() : -1;
    jsonDoc["active_led"] = currentLEDStatus;
    jsonDoc["health_status"] = currentHealthStatus;
    jsonDoc["ap_ssid"] = AP_SSID;
    jsonDoc["ap_ip"] = WiFi.softAPIP().toString();
    jsonDoc["sta_ip"] = (WiFi.status() == WL_CONNECTED) ? WiFi.localIP().toString() : "Connecting...";
    jsonDoc["sta_connected"] = (WiFi.status() == WL_CONNECTED);

    String jsonResponse;
    serializeJson(jsonDoc, jsonResponse);

    AsyncWebServerResponse *response = request->beginResponse(200, "application/json", jsonResponse);
    response->addHeader("Access-Control-Allow-Origin", "*");
    request->send(response);
  });

  server.begin();
  Serial.println("[WEB] Async Web Server Started on Port 80");
}

// ============================================================================
// ARDUINO LOOP FUNCTION
// ============================================================================
void loop() {
  unsigned long now = millis();

  // Read ultrasonic sensor at non-blocking interval
  if (now - lastSensorReadTime >= SENSOR_READ_INTERVAL) {
    lastSensorReadTime = now;

    currentDistance = measureDistanceCM();
    evaluateThresholdsAndSetLEDs(currentDistance);

    // Print to Serial Monitor for debugging
    Serial.print("Distance: ");
    if (currentDistance >= 0.0f) {
      Serial.print(currentDistance, 1);
      Serial.print(" cm | LED: ");
      Serial.print(currentLEDStatus);
    } else {
      Serial.print("OUT OF RANGE");
    }
    Serial.print(" | AP IP: ");
    Serial.print(WiFi.softAPIP());
    Serial.print(" | STA Status: ");
    Serial.println((WiFi.status() == WL_CONNECTED) ? WiFi.localIP().toString() : "Connecting...");
  }
}
