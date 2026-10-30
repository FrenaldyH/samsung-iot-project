// Libraries first: the pin #defines below are plain text substitution and must not leak into these headers
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "secrets.h"

#define Step 32
#define DIR 33
#define MQ2 12
#define PIR 0
#define Reset 2
#define Buzz 4
#define EN 25
#define MQ2_AOUT 34
int count = 0;
bool gas = 0;
bool A = 0;
bool butsig = 0;

// MQTT settings: one JSON status topic + one retained online/offline topic
const char* TOPIC_STATUS = "sic8/frenaldy-gasleak/status";
const char* TOPIC_AVAIL = "sic8/frenaldy-gasleak/availability";
const unsigned long HEARTBEAT_MS = 2000;
const unsigned long RETRY_MS = 5000;

WiFiClientSecure net;
PubSubClient mqtt(net);
char clientId[32];
bool alarmOn = false;
bool lastMotion = false;
unsigned long lastBeat = 0;
unsigned long lastRetry = 0;

// Connect to WiFi, but give up after 10 s so the local alarm still works offline
void connectWifi(){
  Serial.print("[WIFI] Menghubungkan ke ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000){
    delay(250);
  }
  if (WiFi.status() == WL_CONNECTED){
    Serial.println("[WIFI] Terhubung");
  }else{
    Serial.println("[WIFI] Gagal, sistem tetap jalan tanpa jaringan");
  }
}

// Reconnect MQTT at most every RETRY_MS so a dead network never stalls the alarm
void ensureMqtt(){
  if (mqtt.connected() || WiFi.status() != WL_CONNECTED) return;
  if (lastRetry != 0 && millis() - lastRetry < RETRY_MS) return;
  lastRetry = millis();
  // ponytail: each TLS connect attempt blocks ~1-3 s; move networking to its own FreeRTOS task if that matters
  // Last Will: the broker publishes "offline" for us if the ESP32 disappears
  // Empty credentials = anonymous login (public broker); NULL tells PubSubClient to skip them
  const char* user = strlen(MQTT_USER) ? MQTT_USER : NULL;
  const char* pass = strlen(MQTT_PASS) ? MQTT_PASS : NULL;
  if (mqtt.connect(clientId, user, pass, TOPIC_AVAIL, 1, true, "offline")){
    mqtt.publish(TOPIC_AVAIL, "online", true);
    Serial.println("[MQTT] Terhubung ke broker");
  }else{
    Serial.print("[MQTT] Gagal terhubung, kode=");
    Serial.println(mqtt.state());
  }
}

// Publish live sensor values + alarm state as JSON; skipped silently when offline
void publishStatus(const char* event){
  if (!mqtt.connected()) return;
  char payload[160];
  snprintf(payload, sizeof(payload),
           "{\"gas\":%d,\"raw\":%d,\"motion\":%d,\"alarm\":%d,\"pos\":%d,\"event\":\"%s\"}",
           digitalRead(MQ2) == LOW, analogRead(MQ2_AOUT), digitalRead(PIR) == HIGH,
           alarmOn, count, event);
  mqtt.publish(TOPIC_STATUS, payload);
}

// Keep MQTT alive and send a heartbeat; called from loop() and from inside the alarm loop
void netLoop(){
  ensureMqtt();
  mqtt.loop();
  if (millis() - lastBeat >= HEARTBEAT_MS){
    lastBeat = millis();
    publishStatus("heartbeat");
  }
}

void setup(){
  Serial.begin(115200);
  Serial.println("[BOOT] Sistem deteksi kebocoran gas");

  pinMode(Step, OUTPUT);
  pinMode(DIR, OUTPUT);
  pinMode(Buzz, OUTPUT);
  pinMode(Reset, INPUT_PULLDOWN);
  pinMode(PIR, INPUT);
  pinMode(MQ2, INPUT);
  pinMode(EN, OUTPUT);

  digitalWrite(EN,HIGH);
  digitalWrite(Buzz,LOW);

  // Network setup: TLS without certificate check (see notes/penjelasan-pengembangan.md)
  snprintf(clientId, sizeof(clientId), "sic8-gasleak-%08lX", (unsigned long)ESP.getEfuseMac());
  connectWifi();
  net.setInsecure();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  Serial.println("[SIAP] Memantau gas...");
}

void loop(){
  netLoop();
  gas = digitalRead(MQ2);
  butsig = digitalRead(Reset);
  if (gas == LOW){
    // Alarm latched: log + notify once when it starts
    alarmOn = true;
    Serial.print("[ALARM] Kebocoran gas terdeteksi, raw=");
    Serial.println(analogRead(MQ2_AOUT));
    publishStatus("alarm_start");
    while (butsig == LOW){
      netLoop();
      digitalWrite(EN,HIGH);
      butsig = digitalRead(Reset);
      A = digitalRead(PIR);
      if (A == HIGH){
        digitalWrite(Buzz, HIGH);
      }else{
        digitalWrite(Buzz,LOW);
      }
      // Report only when the PIR state changes, not every iteration
      if (A != lastMotion){
        lastMotion = A;
        Serial.println(A ? "[PIR] Ada orang, buzzer ON" : "[PIR] Tidak ada orang, buzzer OFF");
        publishStatus(A ? "motion_on" : "motion_off");
      }
      while (count != 200){
        digitalWrite(EN,LOW);
        digitalWrite(DIR, HIGH);
        for (int i = 0; i<200; i++){
          digitalWrite(Step, HIGH);
          delayMicroseconds(1000);
          digitalWrite(Step, LOW);
          delayMicroseconds(1000);
          count += 1;
        }
        // Motor reached the target position
        Serial.println("[MOTOR] Sampai posisi 200 langkah");
        publishStatus("motor_open");
      }
    }
    digitalWrite(Buzz, LOW);
    digitalWrite(EN, LOW);
    digitalWrite(DIR, LOW);
    int Hitung = count;
    for (int i = 0; i<Hitung; i++){
      digitalWrite(Step, HIGH);
      delayMicroseconds(1000);
      digitalWrite(Step, LOW);
      delayMicroseconds(1000);
      count -= 1;
    }
    digitalWrite(EN,HIGH);
    // Reset finished: clear alarm state and notify
    alarmOn = false;
    lastMotion = false;
    Serial.println("[RESET] Alarm dimatikan, motor kembali ke posisi 0");
    publishStatus("reset");
    delay (500);
  }
}
