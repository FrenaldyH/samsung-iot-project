#include <WiFi.h>
#include <PubSubClient.h>

// --- Pin Definitions ---
#define Step 32   
#define DIR 33   
#define MQ2 12   
#define PIR 0    
#define Reset 2    
#define Buzz 4    
#define EN 25

// --- Network & Broker Configuration ---
const char* ssid        = "Wokwi-GUEST";
const char* password    = "";
const char* mqtt_server = "broker.emqx.io";
const int   mqtt_port   = 1883;

// --- MQTT Topics Specification ---
const char* topic_asap   = "tsabit/wokwi/status/asap";
const char* topic_pir    = "tsabit/wokwi/status/pir";
const char* topic_buzzer = "tsabit/wokwi/status/buzzer";
const char* topic_motor  = "tsabit/wokwi/status/motor";
const char* topic_button = "tsabit/wokwi/status/button";

WiFiClient espClient;
PubSubClient client(espClient);

// --- Global Variables & State Tracking ---
int count = 0;
bool asap = HIGH;
bool lastAsap = -1;

bool pirVal = LOW;
bool lastPirVal = -1;

bool buzzVal = LOW;
bool lastBuzzVal = -1;

bool butsig = LOW;
bool lastButsig = -1;

String motorStatus = "DIAM";
String lastMotorStatus = "";

unsigned long lastMqttSend = 0;

void setup_wifi() {
  delay(10);
  Serial.println("\n[WiFi] Connecting to Wokwi-GUEST...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Connected!");
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("[MQTT] Connecting to broker.emqx.io...");
    String clientId = "ESP32-Wokwi-";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println(" CONNECTED!");
    } else {
      delay(5000);
    }
  }
}

void checkAndPublishAll() {
  // 1. Asap (MQ2)
  asap = digitalRead(MQ2);
  if (asap != lastAsap) {
    lastAsap = asap;
    client.publish(topic_asap, (asap == LOW) ? "ADA_ASAP" : "AMAN");
  }

  // 2. PIR Sensor
  pirVal = digitalRead(PIR);
  if (pirVal != lastPirVal) {
    lastPirVal = pirVal;
    client.publish(topic_pir, (pirVal == HIGH) ? "GERAKAN_DETECTED" : "NORMAL");
  }

  // 3. Buzzer
  if (buzzVal != lastBuzzVal) {
    lastBuzzVal = buzzVal;
    client.publish(topic_buzzer, (buzzVal == HIGH) ? "BUNYI" : "DIAM");
  }

  // 4. Tombol Reset
  butsig = digitalRead(Reset);
  if (butsig != lastButsig) {
    lastButsig = butsig;
    client.publish(topic_button, (butsig == HIGH) ? "PRESSED" : "RELEASED");
  }

  // 5. Motor Stepper
  if (motorStatus != lastMotorStatus) {
    lastMotorStatus = motorStatus;
    client.publish(topic_motor, motorStatus.c_str());
  }
}

void sendRutin() {
  if (millis() - lastMqttSend > 1000) {
    lastMqttSend = millis();
    client.publish(topic_asap, (asap == LOW) ? "ADA_ASAP" : "AMAN");
    client.publish(topic_pir, (pirVal == HIGH) ? "GERAKAN_DETECTED" : "NORMAL");
    client.publish(topic_buzzer, (buzzVal == HIGH) ? "BUNYI" : "DIAM");
    client.publish(topic_motor, motorStatus.c_str());
    client.publish(topic_button, (butsig == HIGH) ? "PRESSED" : "RELEASED");
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(Step, OUTPUT);
  pinMode(DIR, OUTPUT);
  pinMode(Buzz, OUTPUT);
  pinMode(Reset, INPUT_PULLDOWN);
  pinMode(PIR, INPUT);
  pinMode(MQ2, INPUT);
  pinMode(EN, OUTPUT);
  
  digitalWrite(EN, HIGH);
  digitalWrite(Buzz, LOW);

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  checkAndPublishAll();
  sendRutin();

  // --- Logika Darurat Kebocoran Gas ---
  if (asap == LOW) {
    while (butsig == LOW) {
      client.loop();
      checkAndPublishAll();
      sendRutin();

      butsig = digitalRead(Reset);

      if (pirVal == HIGH) {
        digitalWrite(Buzz, HIGH);
        buzzVal = HIGH;
      } else {
        digitalWrite(Buzz, LOW);
        buzzVal = LOW;
      }

      // Memutar Stepper Motor memutus Knob Regulator Winn Gas W-688 M (Posisi ON -> OFF)
      if (count != 200) {
        motorStatus = "BERPUTAR";
        checkAndPublishAll();

        digitalWrite(EN, LOW);
        digitalWrite(DIR, HIGH);
        for (int i = 0; i < 200; i++) {
          digitalWrite(Step, HIGH);
          delayMicroseconds(1000);
          digitalWrite(Step, LOW);
          delayMicroseconds(1000);
          count += 1;
        }
        digitalWrite(EN, HIGH);
      }
    }

    // --- Eksekusi Tombol Reset (Memutar Balik Knob Regulator OFF -> ON) ---
    motorStatus = "BERPUTAR";
    buzzVal = LOW;
    digitalWrite(Buzz, LOW);
    checkAndPublishAll();

    digitalWrite(EN, LOW);
    digitalWrite(DIR, LOW);
    
    for (int i = 0; i < 200; i++) {
      digitalWrite(Step, HIGH);
      delayMicroseconds(1000);
      digitalWrite(Step, LOW);
      delayMicroseconds(1000);
      count -= 1;
    }
    
    digitalWrite(EN, HIGH);
    motorStatus = "DIAM";
    checkAndPublishAll();
    delay(500);
  } else {
    buzzVal = LOW;
    digitalWrite(Buzz, LOW);
    motorStatus = "DIAM";
  }
}
