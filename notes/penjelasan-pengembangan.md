# Penjelasan Pengembangan: Serial, MQTT, Dashboard, dan Pengujian

> Lanjutan dari [pemahaman-proyek.md](pemahaman-proyek.md). Dokumen ini menjelaskan **apa yang ditambahkan, kenapa, dan cara menjalankannya**.
> Simulasi Wokwi dan koneksi HiveMQ Cloud **belum pernah dijalankan** saat dokumen ini ditulis, karena butuh akun dan kredensial tim. Yang sudah diverifikasi dijelaskan di bagian 9.

---

## 1. Ringkasan perubahan

| File | Status | Isi perubahan |
|---|---|---|
| `wokwi/sketch.ino` | Diubah | + Serial, + WiFi, + MQTT, + baca AOUT. **Logika alarm tidak diubah.** |
| `wokwi/secrets.h` | Baru | Tempat SSID, host, username, dan password (diisi tim) |
| `wokwi/libraries.txt` | Baru | Library `PubSubClient` untuk Wokwi |
| `wokwi/diagram.json` | Diubah | + 1 kabel: `gas1:AOUT → esp:34` |
| `dashboard/dashboard.ipynb` | Baru | Dashboard Google Colab (paho-mqtt + Plotly) |

Prinsip yang dipegang selama pengembangan:
1. **Logika alarm milik tim tidak diubah.** Kode baru hanya *disisipkan* (log, kirim data), tidak mengubah keputusan alarm.
2. **Alarm lokal tidak boleh bergantung pada internet.** Jika WiFi atau broker mati, sensor, motor, dan buzzer tetap bekerja seperti biasa. Bagi alat keselamatan, jaringan hanyalah "pelapor", bukan "pengambil keputusan".
3. **Rahasia dipisah dari kode.** Password ada di `secrets.h`, bukan di `sketch.ino`.

---

## 2. Penambahan Serial Monitor

Serial adalah **syarat minimum brief**. Sebelumnya, kode sama sekali tidak memakai Serial, padahal diagram Wokwi sudah menyambung TX/RX ke Serial Monitor.

**Yang ditambahkan:**
- `Serial.begin(115200)` di awal `setup()`. 115200 adalah kecepatan komunikasi (baud rate) standar ESP32, dan Serial Monitor Wokwi otomatis memakainya.
- Pesan log hanya dicetak **saat ada kejadian (event)**, tidak di setiap putaran `loop()`.

**Kenapa hanya saat event?** `loop()` berjalan ribuan kali per detik. Jika setiap putaran mencetak status, Serial Monitor akan banjir teks dan kejadian penting malah tenggelam. Mencetak hanya saat ada perubahan membuat log mudah dibaca, mudah di-screenshot untuk laporan, dan tidak memperlambat program.

**Daftar pesan Serial:**

| Pesan | Kapan muncul |
|---|---|
| `[BOOT] Sistem deteksi kebocoran gas` | ESP32 menyala |
| `[WIFI] Menghubungkan ke Wokwi-GUEST` lalu `[WIFI] Terhubung` / `[WIFI] Gagal, ...` | Saat menyambung WiFi (maksimal 10 detik) |
| `[MQTT] Terhubung ke broker` / `[MQTT] Gagal terhubung, kode=...` | Saat menyambung ke HiveMQ |
| `[SIAP] Memantau gas...` | Setup selesai |
| `[ALARM] Kebocoran gas terdeteksi, raw=...` | Gas terdeteksi, alarm mulai terkunci |
| `[MOTOR] Sampai posisi 200 langkah` | Stepper selesai bergerak |
| `[PIR] Ada orang, buzzer ON` / `[PIR] Tidak ada orang, buzzer OFF` | Status PIR berubah selama alarm |
| `[RESET] Alarm dimatikan, motor kembali ke posisi 0` | Tombol reset ditekan dan motor sudah kembali |

Arti `kode=` pada pesan MQTT gagal (dari library PubSubClient): `-2` berarti server tidak terjangkau (host salah atau tidak ada internet), dan `4`/`5` berarti username atau password ditolak.

---

## 3. Konsep MQTT, broker, dan TLS

**MQTT** adalah cara perangkat IoT bertukar pesan, mirip grup WhatsApp. Pengirim (**publisher**) menaruh pesan di sebuah **topic** (nama grup), dan siapa pun yang **subscribe** ke topic itu menerimanya. Di proyek ini, ESP32 adalah publisher dan dashboard Colab adalah subscriber.

**Broker** adalah perantara yang menerima dan meneruskan pesan. Broker diperlukan karena ESP32 dan laptop tidak bisa saling terhubung langsung lewat internet (terhalang router/firewall). Jadi keduanya sama-sama menghubungi broker dari sisi masing-masing. **HiveMQ Cloud** adalah broker yang sudah di-hosting, jadi tim tidak perlu menyiapkan server sendiri.

**TLS dan port 8883.** Port adalah "nomor pintu" di server. MQTT biasa memakai pintu 1883 dengan pesan terbuka (seperti HTTP). MQTT dengan **TLS** memakai pintu **8883**, dan pesannya dienkripsi (seperti HTTPS, gembok di browser). HiveMQ Cloud memakai TLS, jadi ESP32 memakai `WiFiClientSecure`, bukan `WiFiClient` biasa.

**`setInsecure()`, sebuah trade-off yang disengaja.** TLS punya dua fungsi: (1) mengenkripsi isi pesan, dan (2) memastikan server benar-benar HiveMQ, dengan memeriksa sertifikatnya.
- `setInsecure()` tetap menjalankan fungsi (1) tapi **melewati** fungsi (2). Kodenya pendek dan tidak rusak saat sertifikat server diperbarui.
- Risikonya, secara teori pihak lain bisa menyamar sebagai server (*man-in-the-middle*). Untuk simulasi tugas, risiko ini dapat diterima.
- Untuk produk nyata, sertifikat root CA perlu dipasang dengan `net.setCACert(...)`.

---

## 4. Topic dan payload

| Topic | Isi | Kapan dikirim | Retained |
|---|---|---|---|
| `sic8/gasleak/status` | JSON status (lihat bawah) | Setiap event + heartbeat tiap 2 detik | Tidak |
| `sic8/gasleak/availability` | `online` / `offline` | `online` saat terhubung, `offline` otomatis oleh broker saat ESP32 hilang | Ya |

Contoh payload status:
```json
{"gas":1,"raw":3150,"motion":0,"alarm":1,"pos":200,"event":"motor_open"}
```

| Field | Arti | Sumber |
|---|---|---|
| `gas` | 1 = gas terdeteksi **saat ini** | DOUT dibaca langsung (`LOW` → 1) |
| `raw` | Kadar gas relatif, 0–4095 | AOUT di GPIO 34 (ADC 12-bit) |
| `motion` | 1 = ada orang saat ini | PIR dibaca langsung |
| `alarm` | 1 = alarm sedang terkunci | Status program |
| `pos` | Posisi motor dalam langkah (0–200) | Variabel `count` |
| `event` | `heartbeat`, `alarm_start`, `motor_open`, `motion_on`, `motion_off`, `reset` | Jenis kejadian |

Kenapa `gas` dan `alarm` dipisah? Karena alarm **terkunci**. Di dashboard akan terlihat `gas` kembali ke 0 (gas sudah hilang), sementara `alarm` tetap 1 sampai tombol ditekan. Ini cara visual untuk membuktikan bahwa *latching* bekerja.

**Heartbeat** adalah pesan rutin tiap 2 detik walau tidak ada kejadian. Gunanya: (1) dashboard tetap mendapat data tren gas, dan (2) kalau heartbeat berhenti, berarti ada masalah.

**Last Will (LWT)** adalah "pesan wasiat" yang dititipkan ke broker saat ESP32 terhubung. Jika ESP32 tiba-tiba mati tanpa pamit, broker sendiri yang mengirim `offline`. Karena `retained`, subscriber yang baru bergabung langsung tahu status terakhir perangkat.

JSON disusun dengan `snprintf`, tanpa library ArduinoJson, karena payload-nya kecil dan tetap sehingga tidak perlu dependensi tambahan.

---

## 5. Perubahan di `sketch.ino`, per bagian

- **`#include` di paling atas, sebelum `#define`.** `#define` adalah substitusi teks. Seandainya ada kode library yang memakai nama `Reset` atau `DIR`, nama itu akan ikut terganti dan menyebabkan error yang membingungkan. Menaruh `#include` lebih dulu mencegah hal itu.
- **`connectWifi()`**: menyambung ke `Wokwi-GUEST` (WiFi simulasi Wokwi, tanpa password). Jika dalam 10 detik belum tersambung, fungsi ini menyerah dan sistem tetap berjalan offline.
- **`ensureMqtt()`**: menyambung ulang ke broker **paling sering tiap 5 detik**. Tanpa batas ini, ESP32 akan terus mencoba konek (setiap percobaan TLS bisa makan waktu 1–3 detik) dan alarm jadi lambat bereaksi.
- **`publishStatus(event)`**: menyusun dan mengirim JSON. Jika tidak terhubung, fungsi ini langsung keluar tanpa error.
- **`netLoop()`**: memanggil `ensureMqtt()` dan `mqtt.loop()`, lalu mengirim heartbeat. Fungsi ini dipanggil di `loop()` **dan** di dalam `while` alarm. Alasannya, `mqtt.loop()` harus rutin dipanggil supaya koneksi tidak dianggap mati oleh broker, sementara program bisa lama berada di dalam `while` alarm.
- **Titik event** disisipkan di logika yang sudah ada: `alarm_start` saat masuk blok alarm, `motion_on/off` saat PIR berubah, `motor_open` setelah 200 langkah, dan `reset` setelah motor kembali.
- **AOUT (GPIO 34)**: hanya dibaca untuk dikirim ke dashboard. **Keputusan alarm tetap memakai DOUT.** GPIO 34 dipilih karena (1) termasuk ADC1, sedangkan ADC2 tidak bisa dipakai saat WiFi aktif, dan (2) merupakan pin input-only, jadi cocok untuk sensor.

---

## 6. Panduan HiveMQ Cloud

> Langkah ini berdasarkan pengetahuan saya tentang HiveMQ Cloud. **Nama menu bisa sedikit berbeda.**

1. Buka **console.hivemq.cloud** lalu daftar (Sign up). Login dengan Google bisa dipakai.
2. Buat cluster baru dan pilih paket **Serverless / Free**.
3. Buka detail cluster dan catat **URL cluster**, misalnya `abc123.s1.eu.hivemq.cloud`. Port TLS-nya **8883**.
4. Buka menu **Access Management / Credentials** dan buat **username + password khusus proyek ini**, dengan izin *Publish and Subscribe*.
   - Kenapa khusus proyek? Link Wokwi akan dibagikan di laporan, sehingga siapa pun yang membukanya bisa melihat `secrets.h`. Dengan user khusus, cukup **hapus user tersebut setelah penilaian** dan akun utama tetap aman.
5. Isi `wokwi/secrets.h` (`MQTT_HOST`, `MQTT_USER`, `MQTT_PASS`) dan sel 2 notebook (`MQTT_HOST`, `MQTT_USER`).

---

## 7. Cara menjalankan

### 7.1 Wokwi
1. Buka project di **wokwi.com** (ESP32).
2. Salin isi `sketch.ino` dan `diagram.json`.
3. Tambah file baru `secrets.h` (menu tab file → *New file*), lalu salin isinya dan isi kredensial.
4. Pastikan library **PubSubClient** terpasang: lewat *Library Manager*, atau tambahkan file `libraries.txt`.
5. Klik **Run** dan tunggu Serial Monitor menampilkan `[MQTT] Terhubung ke broker`.
6. **Simpan project** dan salin link-nya. **Link ini wajib dimasukkan ke laporan** (deliverable brief).

Cara memicu kondisi di simulasi: klik sensor gas lalu geser nilai gas, klik sensor PIR lalu picu gerakan, dan klik push button untuk reset.

### 7.2 Dashboard (Google Colab)
1. Buka **colab.research.google.com**, pilih *File → Upload notebook*, lalu pilih `dashboard/dashboard.ipynb`.
2. Isi `MQTT_HOST` dan `MQTT_USER` di sel 2.
3. Jalankan sel 1 sampai 4. Saat sel 4 berjalan (60 detik), lakukan skenario uji di Wokwi.
4. Jalankan sel 5. Muncul grafik kadar gas, tiga timeline status (gas/alarm/orang), dan tabel event.

---

## 8. Skenario pengujian

Kolom **Actual Result** dan **Status** diisi tim setelah menjalankan simulasi, sambil mengambil screenshot Serial Monitor dan dashboard untuk laporan.

| ID | Test Case | Input / Condition | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| TC1 | Kondisi normal | Gas rendah, tidak ada gerakan, tombol tidak ditekan | Buzzer mati, motor diam, Serial tidak menampilkan `[ALARM]`, heartbeat `alarm:0` muncul di dashboard tiap 2 detik | Belum diuji | Belum diuji |
| TC2 | Gas terdeteksi, tanpa orang | Nilai gas dinaikkan melewati ambang, PIR diam | Serial `[ALARM]` lalu `[MOTOR] Sampai posisi 200 langkah`, motor berputar 1 putaran, buzzer **mati**, event `alarm_start` dan `motor_open`, `alarm:1`, `pos:200` | Belum diuji | Belum diuji |
| TC3 | Gas + ada orang | Saat alarm aktif, PIR dipicu, lalu ditunggu sampai PIR kembali diam | Buzzer **berbunyi**, Serial `[PIR] Ada orang, buzzer ON`, event `motion_on`. Setelah PIR diam: buzzer mati, event `motion_off` | Belum diuji | Belum diuji |
| TC4 | Reset | Saat alarm aktif, tombol ditekan | Buzzer mati, motor kembali ke posisi awal, Serial `[RESET]`, event `reset`, `alarm:0`, `pos:0` | Belum diuji | Belum diuji |

Tambahan opsional untuk menunjukkan stabilitas (bagian dari rubrik Debugging/Stability): **TC5, alarm tanpa internet.** Isi `MQTT_PASS` dengan nilai salah. Serial akan menampilkan `[MQTT] Gagal terhubung`, tapi TC2–TC4 tetap berjalan normal. Ini membuktikan alarm tidak bergantung pada jaringan.

> Jika TC2 gagal (alarm tidak aktif saat gas dinaikkan, atau justru aktif terus sejak awal), kemungkinan besar penyebabnya adalah **polaritas DOUT sensor gas di Wokwi** (lihat bagian 10).

---

## 9. Yang sudah dan belum diverifikasi

| Item | Hasil |
|---|---|
| Notebook valid (nbformat) dan semua sel kode bisa di-parse | ✅ Lolos |
| Parser + dashboard dijalankan dengan data sintetis alur TC1–TC4 (termasuk payload rusak) | ✅ Lolos, grafik dan tabel event terbentuk, payload rusak dilewati |
| API paho-mqtt v2 yang dipakai notebook tersedia | ✅ Lolos |
| `diagram.json` valid dan kabel AOUT → GPIO 34 ada | ✅ Lolos |
| Kurung kurawal/kurung biasa di `sketch.ino` seimbang | ✅ Lolos (cek kasar, **bukan** kompilasi) |
| Kompilasi `sketch.ino` | ❌ **Belum**, karena `arduino-cli` tidak tersedia. Akan terlihat saat klik Run di Wokwi |
| Koneksi nyata ke HiveMQ Cloud | ❌ **Belum**, butuh kredensial tim |
| Perilaku di simulasi Wokwi (TC1–TC5) | ❌ **Belum**, diisi tim |

---

## 10. Catatan untuk tahap produk nyata (ditunda, dipastikan nanti)

Proyek masih di tahap ide dan laporan. Poin berikut **sengaja tidak diubah** dan hanya dicatat:

- **Polaritas DOUT di Wokwi [belum dipastikan].** Kode memakai `LOW` = gas terdeteksi, sesuai modul MQ-2 asli. Belum dicek apakah sensor gas Wokwi berperilaku sama.
- **Buzzer DC vs `tone()` [belum dipastikan].** Kode menyalakan buzzer dengan `digitalWrite(HIGH)`. Buzzer *aktif* berbunyi dengan sinyal DC, sedangkan buzzer *pasif* butuh gelombang (`tone()`). Jenis buzzer yang dipakai di Wokwi atau di produk nyata perlu dipastikan.
- **`EN` mati saat alarm [maksud belum jelas].** Driver dimatikan di setiap putaran `while` alarm, sehingga motor tidak menahan posisinya. Jika stepper menahan katup, holding torque mungkin diperlukan.
- **Strapping pin GPIO 0, 2, 12 [risiko hardware asli].** ESP32 membaca pin-pin ini saat menyala untuk menentukan mode boot. Contohnya, MQ-2 asli mengeluarkan `HIGH` saat tidak ada gas, sehingga GPIO 12 `HIGH` saat boot dan ESP32 bisa memilih tegangan flash yang salah lalu gagal boot. PIR di GPIO 0 yang `LOW` saat boot bisa membuat ESP32 masuk mode download. Di Wokwi hal ini tidak bermasalah.
- **Level 5 V vs 3,3 V [risiko hardware asli].** DOUT dan AOUT modul MQ-2 yang diberi 5 V bisa mengeluarkan tegangan di atas 3,3 V, padahal pin ESP32 maksimal 3,3 V. Perlu level shifter atau pembagi tegangan.
- **VMOT A4988.** Tidak wajib di Wokwi (konfirmasi tim), tapi di hardware asli VMOT adalah suplai daya motor yang wajib ada.

Keterbatasan teknis lain: `setInsecure()` (bagian 3), publish memakai QoS 0 (pesan bisa hilang jika jaringan putus sesaat, dan heartbeat berikutnya akan menutupinya), serta percobaan koneksi TLS yang bisa memblokir 1–3 detik.

---

## 11. Checklist terhadap brief

| Syarat brief | Status | Di mana |
|---|---|---|
| ESP32 sebagai controller | ✅ | `diagram.json` |
| ≥1 sensor, ≥1 aktuator | ✅ | MQ-2, PIR, tombol / stepper, buzzer |
| Wokwi sebagai simulasi | ✅ | `wokwi/` |
| Serial Monitor | ✅ | Bagian 2 |
| MQTT + HiveMQ Cloud | ✅ (kredensial diisi tim) | Bagian 3–6 |
| Dashboard Python (paho-mqtt + Plotly) | ✅ | `dashboard/dashboard.ipynb` |
| Topic dan payload konsisten | ✅ | Bagian 4 |
| ≥3 skenario uji | ✅ (hasil diisi tim) | Bagian 8 |
| Link project Wokwi | ⏳ **Tim**: simpan project lalu tempel link di sini → `[ISI LINK WOKWI]` | — |
| Laporan .docx, video .mp4, screenshot | ⏳ Tim | — |
