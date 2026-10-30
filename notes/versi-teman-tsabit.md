# Versi Proyek dari Teman (Muhammad Sayyid Tsabit)

> Disimpan 2026-10-30 untuk dibahas tim. Bagian A adalah dokumen asli dari teman, apa adanya; yang diubah hanya format agar tampil benar di Markdown (kode dibungkus blok kode, sel tabel yang terpotong baris digabung dengan " / "). Bagian B adalah catatan evaluasi.
> Belum ada keputusan versi mana yang dipakai. Lihat juga [pemahaman-proyek.md](pemahaman-proyek.md) dan [penjelasan-pengembangan.md](penjelasan-pengembangan.md).

---

# Bagian A: Dokumen Asli

MASTER DOKUMENTASI & SPESIFIKASI TEKNIS PROYEK IOT

Teks di bawah ini berisi seluruh acuan teknis, spesifikasi jaringan, skema GPIO, arsitektur data, dan source code proyek untuk menyatukan pemahaman sistem secara menyeluruh.

## 1. IDENTITAS & OVERVIEW PROYEK

- **Judul Proyek:** Smart LPG Gas Leak Detection & Automatic Regulator Safety Shut-Off System
- **Tema / Kategori:** Smart Security & Automation / Smart Home Safety (K3 Rumah Tangga)
- **Target User:** Pengguna kompor gas LPG rumah tangga/UMKM, lansia, pengelola dapur komersial, dan tim Keselamatan dan Kesehatan Kerja (K3).
- **Platform Simulasi & Tools:** Wokwi Simulator, Google Colab (Python 3), VS Code / Arduino IDE, Browser (HTML5/WebSocket).
- **Studi Kasus Hardware Fisik:** Modifikasi non-invasif pada Regulator LPG Tekanan Rendah Winn Gas W-688 M (Model konvensional ber-Manometer tanpa fitur electric auto cut-off bawaan).

## 2. PROBLEM STATEMENT, TEKNIS K3, & ANALISIS MEKANIS AKTUTATOR

### A. Problem Statement
Sembilan puluh persen rumah tangga Indonesia menggunakan regulator LPG konvensional (seperti Winn Gas W-688 M). Regulator jenis ini tidak memiliki katup pemutus elektrik otomatis (automatic electric cut-off) apabila terjadi kebocoran gas akibat selang retak, gigitan tikus, atau klem terlepas. Kebocoran gas yang tidak segera ditangani berpotensi memicu ledakan fatal.

### B. Analisis K3 & Bahaya Melepas Selang Gas
- **Kesalahan Fatal:** Melepas atau memutus selang penghubung dari regulator saat terjadi kebocoran sangat dilarang dan berbahaya. Jika selang dicabut sementara tuas regulator masih dalam posisi ON, gas LPG bertekanan tinggi dari dalam tabung justru akan menyembur bebas langsung ke udara dapur.
- **Solusi K3 Otomatisasi Tuas Regulator:** Solusi yang benar dan aman adalah memutar tuas/knob pengunci regulator dari posisi ON (180°) ke OFF (0°). Memutar tuas ke posisi OFF membebaskan pin penekan internal regulator sehingga aliran gas dari dalam tabung LPG terhenti total dari sumbernya.

### C. Analisis Transmisi Gir Reduksi (1:3)
Knob manual Winn Gas W-688 M memiliki hambatan mekanis (breakaway torque) akibat tekanan pegas internal. Memutarnya secara langsung (direct drive) menggunakan motor stepper berisiko memicu stall (motor selip/macet).
- **Pinion Gear (Gir Motor):** 15 T (dipasang pada poros Stepper Motor A4988).
- **Sector Gear (Gir Regulator):** 45 T (mencengkeram knob plastik luar Winn Gas W-688 M).
- **Rasio Reduksi Gir (1:3):** Meningkatkan torsi keluaran motor sebesar 300% (3x lipat), membuat pemutaran knob regulator dari ON ke OFF berjalan mulus, cepat, dan presisi.
- **Prinsip Non-Invasive Safety:** Pemasangan gir dilakukan sepenuhnya di luar body regulator, tanpa merusak atau membongkar ruang kedap gas internal. 100% menjaga sertifikasi keamanan pabrik.

## 3. SPESIFIKASI LENGKAP PROTOKOL & MATRIKS MQTT BROKER

### A. Network & Broker Endpoint
- **MQTT Broker Public Domain:** broker.emqx.io
- **Transport Protocol:** TCP/IP & WebSockets
- **Data Format / Payload:** Plaintext String (UTF-8)
- **QoS Level:** QoS 0
- **Retain Flag:** false
- **KeepAlive Interval:** 60 Detik
- **Client ID Pattern:**
  - ESP32 Wokwi: `ESP32-Wokwi-<HEX_RANDOM>`
  - Python Colab Subscriber: `Colab_Full_5in1_<TIMESTAMP>`
  - Web Dashboard Client: `web_dash_<HEX_RANDOM>`

### B. Daftar Port & Path

| Jenis Koneksi | Port | Path | Penggunaan / Client |
|---|---|---|---|
| MQTT Plaintext (TCP) | 1883 | / | ESP32 Wokwi (PubSubClient) & Python Google Colab (paho-mqtt) |
| MQTT TLS/SSL (Encrypted) | 8883 | / | Koneksi aman untuk Hardware ESP32 Fisik |
| MQTT WebSockets (HTTP) | 8083 | /mqtt | Web Client Browser tanpa enkripsi SSL |
| MQTT WebSockets Secure (HTTPS/WSS) | 8084 | /mqtt | Dashboard HTML Web Client (Paho.MQTT.Client via HTTPS) |

### C. Hierarki Topik MQTT, Path Sensor, & Spesifikasi Payload
- **Root Topic Path:** `tsabit/wokwi/#` (Wildcard subscription)

| Sensor / Aktuator | Topik MQTT Path | Tipe Data | Nilai Payload | Indikasi Status |
|---|---|---|---|---|
| Sensor Gas MQ-2 | tsabit/wokwi/status/asap | String | "ADA_ASAP" / "AMAN" | Terdeteksi kebocoran gas/asap (LOW) / Kondisi udara normal (HIGH) |
| Sensor PIR Motion | tsabit/wokwi/status/pir | String | "GERAKAN_DETECTED" / "NORMAL" | Terdapat pergerakan manusia (HIGH) / Area dapur sepi/kosong (LOW) |
| Piezo Buzzer Alarm | tsabit/wokwi/status/buzzer | String | "BUNYI" / "DIAM" | Alarm evakuasi aktif (Gas Bocor + Ada Orang) / Alarm mati |
| Stepper Motor (Regulator) | tsabit/wokwi/status/motor | String | "BERPUTAR" / "DIAM" | Motor sedang memutar knob Winn Gas W-688 M / Knob posisi stasioner |
| Push Button Reset | tsabit/wokwi/status/button | String | "PRESSED" / "RELEASED" | Tombol reset ditekan untuk memulihkan sistem / Tombol tidak ditekan |
| Remote Control Input | tsabit/wokwi/control | String | "RESET" / "TEST_ALARM" | Topik subskripsi ESP32 untuk perintah jarak jauh |

## 4. DEVICE DISCOVERY & ALOKASI GPIO ESP32

| Nama Perangkat | Kategori | Pin ESP32 | Mode GPIO | Spesifikasi Sinyal & Fungsi Teknis |
|---|---|---|---|---|
| ESP32 DevKit V1 | Microcontroller | - | - | Dual-Core, 2.4 GHz WiFi untuk MQTT Client. |
| MQ-2 Gas Sensor | Input / Sensing | GPIO 12 | INPUT | Digital Output pin. Logika invers (LOW saat gas/asap terdeteksi). |
| PIR Motion Sensor | Input / Sensing | GPIO 0 | INPUT | Passive Infrared. Output HIGH (3.3V) saat mendeteksi pergerakan panas. |
| Push Button Reset | Input / Control | GPIO 2 | INPUT_PULLDOWN | Tombol manual recovery. Memicu pemutaran balik knob regulator ke posisi ON. |
| A4988 Motor Driver | Actuator Driver | STEP: 32 / DIR: 33 / EN: 25 | OUTPUT | Driver Stepper Bipolar. EN Active LOW (LOW = Motor Bertenaga, HIGH = Disable). |
| Stepper Motor NEMA 17 | Output / Actuator | Dihubungkan ke A4988 | OUTPUT | Step angle 1.8° (200 step/rotasi). Memutar knob Winn Gas W-688 M via gir 1:3. |
| Piezo Buzzer | Output / Indicator | GPIO 4 | OUTPUT | Indikator audio evakuasi. Berbunyi HANYA jika Gas Bocor + Ada Pergerakan Manusia. |

## 5. SKEMA JSON SIMULASI WOKWI (diagram.json)

```json
{
  "version": 1,
  "author": "Muhammad Sayyid Tsabit",
  "editor": "wokwi",
  "parts": [
    { "type": "wokwi-esp32-devkit-v1", "id": "esp", "top": 0, "left": 0, "attrs": {} },
    { "type": "wokwi-gas-sensor", "id": "mq2", "top": -140, "left": -200, "attrs": {} },
    { "type": "wokwi-pir-motion-sensor", "id": "pir", "top": 100, "left": -200, "attrs": {} },
    { "type": "wokwi-pushbutton", "id": "btn", "top": 250, "left": -200, "attrs": { "color": "red" } },
    { "type": "wokwi-buzzer", "id": "buzz", "top": -140, "left": 220, "attrs": {} },
    { "type": "wokwi-a4988", "id": "driver", "top": 40, "left": 220, "attrs": {} },
    { "type": "wokwi-stepper-motor", "id": "stepper", "top": 180, "left": 220, "attrs": { "size": "17" } }
  ],
  "connections": [
    [ "esp:GND.1", "mq2:GND", "black", [ "v0" ] ],
    [ "esp:3V3", "mq2:VCC", "red", [ "v0" ] ],
    [ "esp:12", "mq2:A0", "green", [ "v0" ] ],

    [ "esp:GND.1", "pir:GND", "black", [ "v0" ] ],
    [ "esp:3V3", "pir:VCC", "red", [ "v0" ] ],
    [ "esp:0", "pir:OUT", "purple", [ "v0" ] ],

    [ "esp:GND.1", "btn:1.L", "black", [ "v0" ] ],
    [ "esp:2", "btn:2.R", "orange", [ "v0" ] ],

    [ "esp:GND.1", "buzz:1", "black", [ "v0" ] ],
    [ "esp:4", "buzz:2", "red", [ "v0" ] ],

    [ "esp:32", "driver:STEP", "blue", [ "v0" ] ],
    [ "esp:33", "driver:DIR", "green", [ "v0" ] ],
    [ "esp:25", "driver:ENABLE", "yellow", [ "v0" ] ],

    [ "driver:1A", "stepper:A1", "blue", [ "v0" ] ],
    [ "driver:1B", "stepper:A2", "red", [ "v0" ] ],
    [ "driver:2A", "stepper:B1", "black", [ "v0" ] ],
    [ "driver:2B", "stepper:B2", "green", [ "v0" ] ]
  ]
}
```

## 6. SOURCE CODE UTAMA SISTEM

### A. Firmware ESP32 C++ (sketch.ino)

```cpp
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
```

### B. Kode Dashboard Visualisasi Google Colab (Python 3)

```python
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
from IPython.display import clear_output
import time

time_series = []
asap_data = []
pir_data = []
buzzer_data = []
motor_data = []
button_data = []

asap_val = 0
pir_val = 0
buzzer_val = 0
motor_val = 0
button_val = 0

def on_message(client, userdata, msg):
    global asap_val, pir_val, buzzer_val, motor_val, button_val
    topic = msg.topic
    payload = msg.payload.decode('utf-8')

    if topic == "tsabit/wokwi/status/asap":
        asap_val = 1 if payload == "ADA_ASAP" else 0
    elif topic == "tsabit/wokwi/status/pir":
        pir_val = 1 if payload == "GERAKAN_DETECTED" else 0
    elif topic == "tsabit/wokwi/status/buzzer":
        buzzer_val = 1 if payload == "BUNYI" else 0
    elif topic == "tsabit/wokwi/status/motor":
        motor_val = 1 if payload == "BERPUTAR" else 0
    elif topic == "tsabit/wokwi/status/button":
        button_val = 1 if payload == "PRESSED" else 0

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION1,
    client_id="Colab_Full_5in1_" + str(int(time.time()))
)

client.on_message = on_message
client.connect("broker.emqx.io", 1883, 60)
client.subscribe("tsabit/wokwi/#")
client.loop_start()

plt.ion()
start_time = time.time()

try:
    while True:
        elapsed = round(time.time() - start_time, 1)
        time_series.append(elapsed)
        asap_data.append(asap_val)
        pir_data.append(pir_val)
        buzzer_data.append(buzzer_val)
        motor_data.append(motor_val)
        button_data.append(button_val)

        if len(time_series) > 20:
            time_series.pop(0)
            asap_data.pop(0)
            pir_data.pop(0)
            buzzer_data.pop(0)
            motor_data.pop(0)
            button_data.pop(0)

        clear_output(wait=True)
        fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(11, 10), sharex=True)

        ax1.plot(time_series, asap_data, color='crimson', marker='o')
        ax1.set_title("1. Sensor Kebocoran Gas/Asap (MQ2)")
        ax1.set_yticks([0, 1])
        ax1.set_yticklabels(["AMAN", "ADA_ASAP"])
        ax1.grid(True)

        ax2.plot(time_series, pir_data, color='royalblue', marker='s')
        ax2.set_title("2. Sensor Gerakan (PIR)")
        ax2.set_yticks([0, 1])
        ax2.set_yticklabels(["NORMAL", "GERAKAN"])
        ax2.grid(True)

        ax3.plot(time_series, buzzer_data, color='purple', marker='*')
        ax3.set_title("3. Status Buzzer (Alarm)")
        ax3.set_yticks([0, 1])
        ax3.set_yticklabels(["DIAM", "BUNYI"])
        ax3.grid(True)

        ax4.plot(time_series, motor_data, color='darkorange', marker='^')
        ax4.set_title("4. Status Stepper Motor (Regulator Winn Gas W-688 M)")
        ax4.set_yticks([0, 1])
        ax4.set_yticklabels(["DIAM", "BERPUTAR"])
        ax4.grid(True)

        ax5.plot(time_series, button_data, color='forestgreen', marker='d')
        ax5.set_title("5. Tombol Reset Manual")
        ax5.set_yticks([0, 1])
        ax5.set_yticklabels(["RELEASED", "PRESSED"])
        ax5.set_xlabel("Waktu (Detik)")
        ax5.grid(True)

        plt.tight_layout()
        plt.show()

        time.sleep(1)

except KeyboardInterrupt:
    client.loop_stop()
    print("Visualisasi dihentikan.")
```

### C. Web Dashboard Client HTML + JavaScript (dashboard.html)

```html
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>IoT LPG Safety Dashboard - Wokwi</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        h1 { margin-bottom: 20px; color: #f8fafc; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; max-width: 900px; }
        .card { padding: 20px; border-radius: 12px; text-align: center; background: #1e293b; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); }
        .card h3 { margin-top: 0; color: #94a3b8; font-size: 13px; text-transform: uppercase; }
        .status { font-size: 18px; font-weight: bold; margin-top: 10px; padding: 10px; border-radius: 8px; }
        .safe { background-color: #15803d; color: #dcfce7; }
        .danger { background-color: #b91c1c; color: #fee2e2; animation: pulse 1s infinite; }
        .active { background-color: #1d4ed8; color: #dbeafe; }
        .inactive { background-color: #334155; color: #94a3b8; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <h1>LPG Gas Leak & Safety Monitoring System</h1>
    <div class="grid">
        <div class="card"><h3>Sensor Gas (MQ2)</h3><div id="status-asap" class="status safe">AMAN</div></div>
        <div class="card"><h3>Sensor Gerakan (PIR)</h3><div id="status-pir" class="status inactive">NORMAL</div></div>
        <div class="card"><h3>Piezo Buzzer</h3><div id="status-buzzer" class="status inactive">DIAM</div></div>
        <div class="card"><h3>Motor Pemutar Regulator</h3><div id="status-motor" class="status inactive">DIAM</div></div>
        <div class="card"><h3>Tombol Reset</h3><div id="status-button" class="status inactive">RELEASED</div></div>
    </div>

    <script>
        const client = new Paho.MQTT.Client("broker.emqx.io", 8084, "/mqtt", "web_dash_" + Math.random().toString(16).substr(2, 8));
        client.onMessageArrived = function (message) {
            const topic = message.destinationName;
            const payload = message.payloadString;

            if (topic === "tsabit/wokwi/status/asap") {
                const el = document.getElementById("status-asap");
                el.innerText = (payload === "ADA_ASAP") ? "ADA GAS/ASAP!" : "AMAN";
                el.className = "status " + ((payload === "ADA_ASAP") ? "danger" : "safe");
            }
            if (topic === "tsabit/wokwi/status/pir") {
                const el = document.getElementById("status-pir");
                el.innerText = (payload === "GERAKAN_DETECTED") ? "GERAKAN!" : "NORMAL";
                el.className = "status " + ((payload === "GERAKAN_DETECTED") ? "active" : "inactive");
            }
            if (topic === "tsabit/wokwi/status/buzzer") {
                const el = document.getElementById("status-buzzer");
                el.innerText = (payload === "BUNYI") ? "BUNYI" : "DIAM";
                el.className = "status " + ((payload === "BUNYI") ? "danger" : "inactive");
            }
            if (topic === "tsabit/wokwi/status/motor") {
                const el = document.getElementById("status-motor");
                el.innerText = (payload === "BERPUTAR") ? "BERPUTAR" : "DIAM";
                el.className = "status " + ((payload === "BERPUTAR") ? "active" : "inactive");
            }
            if (topic === "tsabit/wokwi/status/button") {
                const el = document.getElementById("status-button");
                el.innerText = (payload === "PRESSED") ? "PRESSED" : "RELEASED";
                el.className = "status " + ((payload === "PRESSED") ? "active" : "inactive");
            }
        };
        client.connect({ useSSL: true, onSuccess: function () { client.subscribe("tsabit/wokwi/#"); } });
    </script>
</body>
</html>
```

## 7. MATRIX HASIL PENGUJIAN (TESTING & VALIDATION)

| No | Skenario Pengujian | Input Condition | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| 1 | Kondisi Normal (Standby) | MQ2 = HIGH (Aman) / PIR = LOW (Sepi) / Button = LOW | Motor Stepper = DIAM (Tuas Regulator ON). Buzzer = DIAM. Dashboard menampilkan status AMAN & NORMAL. | Sesuai Ekspektasi. Telemetri ter-publish rutin tiap 1 detik. | PASSED |
| 2 | Kondisi Kebocoran Gas & Ada Orang | MQ2 = LOW (Gas Bocor) / PIR = HIGH (Gerakan) | Motor Stepper berputar 200 step memutar tuas Winn Gas W-688 M ke posisi OFF. Buzzer berbunyi alarm. Dashboard menunjukkan ADA_ASAP & GERAKAN_DETECTED. | Sesuai Ekspektasi. State-change detection mem-publish alert secara instan. | PASSED |
| 3 | Pemulihan / Reset Manual | Push Button ditekan (HIGH) saat kondisi emergency | Motor Stepper berputar balik 200 step (memutar tuas regulator kembali ke ON). Buzzer mati. Dashboard menampilkan PRESSED lalu kembali normal. | Sesuai Ekspektasi. Loop emergency berhenti dan sistem siap kembali. | PASSED |

---

# Bagian B: Catatan Evaluasi (2026-10-30)

> Penanda: **[Pasti]** terlihat langsung di kode; **[Kemungkinan besar]** berdasarkan pengetahuan tentang komponen Wokwi, perlu dipastikan di simulator. Simulasi versi ini belum dijalankan.
> Hasil "PASSED" di tabel pengujian tidak cocok dengan `diagram.json` di bagian 5: mungkin diagram di dokumen berbeda dengan yang dipakai di Wokwi. Perlu dikonfirmasi ke teman.

## Kritis (membuat demo gagal)

| # | Temuan | Keyakinan | Perbaikan |
|---|---|---|---|
| 1 | Board `wokwi-esp32-devkit-v1` menamai pinnya `D12`, `D32`, dst., tetapi koneksi memakai `esp:12`, `esp:32` (gaya `board-esp32-devkit-c-v4`), sehingga kabel tidak tersambung | Kemungkinan besar | Pakai `board-esp32-devkit-c-v4`, atau ganti nama pin ke gaya `Dxx` |
| 2 | `mq2:A0` tidak ada; pin sensor gas bernama `AOUT`, `DOUT`, `VCC`, `GND`. Kode membaca digital | Pasti | `esp:12` → `mq2:DOUT` |
| 3 | `stepper:A1/A2/B1/B2` tidak dikenal; pin stepper bernama `A-`, `A+`, `B+`, `B-` | Pasti | Pakai nama pin yang benar |
| 4 | Tombol ke **GND** dengan `INPUT_PULLDOWN`: ditekan atau tidak, pin tetap LOW, sehingga alarm tidak pernah bisa di-reset. Nama pin `1.L`/`2.R` juga harusnya huruf kecil | Pasti | Tombol ke **3V3**, nama pin `1.l`/`2.l` |
| 5 | `libraries.txt` berisi `PubSubClient` tidak disebut; tanpa itu build gagal (`PubSubClient.h: No such file`) | Pasti | Tambah `libraries.txt` di Wokwi |
| 6 | Colab tidak menjalankan `!pip install paho-mqtt`, padahal paho tidak terpasang bawaan di Colab | Pasti | Tambah sel install |

## Penting

| # | Temuan | Keyakinan | Dampak |
|---|---|---|---|
| 7 | `setup_wifi()` dan `reconnect()` menunggu tanpa batas sebelum sensor dibaca | Pasti | Kalau broker atau WiFi mati, kebocoran gas tidak pernah terdeteksi. Cacat desain untuk alat keselamatan |
| 8 | Knob 180° lewat gir 1:3 butuh 540° motor = 300 langkah, tetapi kode memutar 200 langkah (knob hanya 120°) | Pasti | Regulator tidak tertutup penuh; tidak konsisten dengan analisis gir di dokumen |
| 9 | Topic `tsabit/wokwi/control` (`RESET`/`TEST_ALARM`) ada di dokumen, tetapi tidak diimplementasikan | Pasti | Hapus dari dokumen atau implementasikan |
| 10 | Reset selalu mundur 200 langkah tanpa melihat `count` (bug lama yang dulu sudah diperbaiki dengan `Hitung = count`) | Pasti | Motor bisa mundur melewati posisi awal |
| 11 | Colab membuat figure baru setiap detik tanpa `plt.close(fig)` | Pasti | Memori terus naik selama demo, muncul peringatan setelah 20 figure |
| 12 | A4988 tanpa `VDD`/`GND` dan tanpa sambungan `SLEEP`–`RESET` | Perlu dicek | Belum diketahui apakah motor tetap bergerak di Wokwi |

## Minor dan isi dokumen

- `bool lastAsap = -1;`: `bool` tidak bisa -1 (menjadi `true`), jadi penanda "belum tahu" tidak bekerja.
- Istilah `asap` / `ADA_ASAP`: use case-nya kebocoran **LPG**, sebaiknya `gas` / `ADA_GAS`.
- "Sembilan puluh persen rumah tangga…": angka tanpa sumber.
- "Meningkatkan torsi sebesar 300% (3x lipat)": rasio 1:3 berarti torsi menjadi 3x, atau naik 200%.
- "100% menjaga sertifikasi keamanan pabrik": klaim yang tidak bisa dibuktikan.
- "poros Stepper Motor A4988": A4988 adalah driver, bukan motor.
- `random(0xffff)` tanpa `randomSeed`: Client ID sama di setiap simulasi, sehingga dua orang yang menjalankan bersamaan saling memutus koneksi di broker publik.
- KeepAlive tertulis 60 detik, padahal bawaan PubSubClient 15 detik dan kode tidak mengubahnya.

## Kelebihan yang layak dipertahankan

- Analisis K3 (memutar tuas regulator ke OFF, bukan melepas selang) dan analisis gir: bahan bagus untuk latar belakang laporan.
- Dashboard HTML via WebSocket 8084: bonus visual untuk video demo.
- Topic per sensor dengan payload teks: mudah dibaca di MQTTX.
- Broker `broker.emqx.io` tanpa password: sama dengan keputusan tim, sehingga penguji bisa menjalankan semuanya.

## Saran

Gabungkan kedua versi: kelebihan versi ini (analisis K3 dan gir, dashboard HTML, topic per sensor) di atas versi tim di `wokwi/` (diagram yang benar, alarm tetap jalan saat offline, data analog untuk grafik tren, Last Will). Jika tim memilih versi ini, minimal perbaiki poin 1–8 sebelum demo.
