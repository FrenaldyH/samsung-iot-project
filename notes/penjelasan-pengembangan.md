# Penjelasan Sistem: Serial, MQTT, Dashboard, dan Pengujian

> Lanjutan dari [pemahaman-proyek.md](pemahaman-proyek.md). Dokumen ini menjelaskan **bagaimana data mengalir dari ESP32 ke dashboard, kenapa dibuat begitu, dan cara menjalankannya**.
> **Keputusan tim (2026-10-30):** kode Wokwi dan dashboard memakai **versi Tsabit** ([versi-teman-tsabit.md](versi-teman-tsabit.md)). Kode Wokwi dipakai apa adanya. Dashboard Colab hanya ditambah dua perbaikan kecil (bagian 6.2).
> Alur lengkap Wokwi → broker → dashboard **belum saya jalankan**. Yang sudah diverifikasi ada di bagian 8.

---

## 1. Ringkasan file

| File | Sumber | Isi |
|---|---|---|
| `wokwi/sketch.ino` | Tsabit, apa adanya | Logika alarm + WiFi + MQTT (5 topic teks) |
| `wokwi/diagram.json` | Tsabit, apa adanya | Rangkaian ESP32 DevKit V1 |
| `wokwi/libraries.txt` | Tim | Library `PubSubClient` untuk Wokwi. Tanpa file ini, build gagal (`PubSubClient.h: No such file`) |
| `wokwi/secrets.h` | Versi tim lama | **Tidak dipakai lagi**: sketch Tsabit menulis alamat broker langsung di kode |
| `dashboard/dashboard.ipynb` | Tsabit + 2 perbaikan | Dashboard Google Colab (paho-mqtt + Matplotlib), 5 grafik status live |
| `dashboard/dashboard.html` | Tsabit, apa adanya | Dashboard web (kartu status berwarna) lewat WebSocket |

Versi tim sebelumnya (payload JSON, data analog AOUT untuk grafik tren, Last Will, alarm tetap jalan saat offline) masih tersimpan di riwayat git, sebelum perubahan ini.

---

## 2. Serial Monitor

Serial adalah **syarat minimum brief**. Sketch membuka Serial di `115200` baud (kecepatan standar ESP32, dipakai otomatis oleh Serial Monitor Wokwi).

| Pesan | Kapan muncul |
|---|---|
| `[WiFi] Connecting to Wokwi-GUEST...` lalu titik-titik | Menunggu WiFi (tanpa batas waktu) |
| `[WiFi] Connected!` | WiFi tersambung |
| `[MQTT] Connecting to broker.emqx.io... CONNECTED!` | Tersambung ke broker. Jika gagal, baris yang sama berulang tiap 5 detik |

**Keterbatasan:** kejadian penting (gas terdeteksi, orang terdeteksi, motor bergerak, reset) **tidak dicetak ke Serial**, dan hanya terlihat lewat MQTT/dashboard. Untuk screenshot laporan, Serial Monitor menunjukkan koneksi, dan MQTTX atau dashboard menunjukkan kejadiannya.

---

## 3. Konsep MQTT dan broker

**MQTT** adalah cara perangkat IoT bertukar pesan, mirip grup WhatsApp. Pengirim (**publisher**) menaruh pesan di sebuah **topic** (nama grup), dan siapa pun yang **subscribe** ke topic itu menerimanya. Di proyek ini, ESP32 adalah publisher, sedangkan dashboard Colab, dashboard HTML, dan MQTTX adalah subscriber.

**Broker** adalah perantara yang menerima dan meneruskan pesan. Broker diperlukan karena ESP32 dan laptop tidak bisa saling terhubung langsung lewat internet (terhalang router/firewall). Jadi keduanya sama-sama menghubungi broker dari sisi masing-masing.

**Port** adalah "nomor pintu" di server. Satu broker punya beberapa pintu untuk jenis koneksi berbeda, tapi pesannya sama:
- **1883**: MQTT biasa lewat TCP, tanpa enkripsi. Dipakai ESP32 dan Colab.
- **8084**: MQTT di dalam **WebSocket aman** (`wss://`, path `/mqtt`). Dipakai dashboard HTML dan MQTTX Web. Browser tidak bisa membuka koneksi TCP mentah seperti ESP32, jadi MQTT harus dibungkus WebSocket. Versi amannya (`wss`) dipakai karena halaman HTTPS dilarang browser membuka WebSocket tanpa enkripsi (*mixed content*).
- **8883**: MQTT dengan TLS. Tidak dipakai di simulasi, tapi menjadi pilihan untuk ESP32 fisik dengan broker pribadi.

Di broker **publik tanpa password**, enkripsi hampir tidak menambah privasi: siapa pun yang tahu topic tetap bisa subscribe dan membaca datanya. Karena itu port 1883 dapat diterima untuk simulasi ini.

---

## 4. Topic dan payload

Setiap komponen punya **topic sendiri** dengan payload **teks biasa** (UTF-8), sehingga mudah dibaca langsung di MQTTX.

| Topic | Payload | Arti |
|---|---|---|
| `tsabit/wokwi/status/asap` | `ADA_ASAP` / `AMAN` | Gas terdeteksi (DOUT `LOW`) / udara normal |
| `tsabit/wokwi/status/pir` | `GERAKAN_DETECTED` / `NORMAL` | Ada gerakan manusia / area kosong |
| `tsabit/wokwi/status/buzzer` | `BUNYI` / `DIAM` | Buzzer evakuasi aktif / mati |
| `tsabit/wokwi/status/motor` | `BERPUTAR` / `DIAM` | Status motor stepper (lihat catatan di bawah) |
| `tsabit/wokwi/status/button` | `PRESSED` / `RELEASED` | Tombol reset ditekan / dilepas |

Nama `asap`/`ADA_ASAP` berasal dari kode Tsabit. Yang dideteksi tetap **gas LPG**. Di laporan ditulis "gas", sedangkan nama topic disebut apa adanya.

**Dua cara pengiriman:**
1. **Saat berubah** (`checkAndPublishAll()`): setiap putaran `loop()`, nilai sensor dibandingkan dengan nilai sebelumnya, dan hanya yang berubah yang dikirim. Hasilnya, kejadian langsung sampai ke dashboard tanpa membanjiri broker.
2. **Rutin tiap 1 detik** (`sendRutin()`): kelima status dikirim ulang. Gunanya, subscriber yang baru bergabung langsung mendapat kondisi terkini. Ini fungsi yang mirip dengan pesan *retained*, yang tidak dipakai (`retain = false`).

Semua pesan memakai **QoS 0** ("kirim sekali, tanpa konfirmasi"). Pesan bisa hilang saat jaringan putus sesaat, tapi pengiriman rutin tiap detik menutupinya.

**Catatan `motor`:** `BERPUTAR` dikirim sebelum motor maju, tapi status baru kembali ke `DIAM` setelah reset selesai. Jadi selama alarm, dashboard menampilkan `BERPUTAR` walau motor sudah diam (temuan di [pemahaman-proyek.md](pemahaman-proyek.md) 6.1, poin 5).

---

## 5. Broker: broker publik EMQX (`broker.emqx.io`)

**Kenapa bukan HiveMQ Cloud?** Brief menyebut HiveMQ Cloud, tetapi per 2026 paket gratis HiveMQ Cloud (Serverless) **sudah tidak bisa dibuat oleh pengguna baru**. Yang tersisa hanya paket Starter (trial 15 hari, lalu berbayar) dan Enterprise. Karena itu dipakai **broker publik EMQX**: gratis, **tanpa akun dan tanpa password**, dengan protokol MQTT standar yang sama. Hanya alamat broker yang berubah.

**Kenapa broker publik?** Tanpa password, **penguji bisa langsung menjalankan** Wokwi, Colab, dashboard HTML, dan MQTTX tanpa diberi kredensial, dan tidak ada risiko password bocor lewat link Wokwi.

| Klien | Protokol | Port | Path | Client ID |
|---|---|---|---|---|
| ESP32 (Wokwi) | MQTT TCP | 1883 | — | `ESP32-Wokwi-<hex>` |
| Colab | MQTT TCP | 1883 | — | `Colab_Full_5in1_<timestamp>` |
| Dashboard HTML | WebSocket aman (`wss`) | 8084 | `/mqtt` | `web_dash_<hex>` |
| MQTTX Web | WebSocket aman (`wss`) | 8084 | `/mqtt` | bebas, harus unik |

Username dan password dikosongkan. Topic yang di-subscribe: `tsabit/wokwi/#` (`#` artinya semua sub-topic).

Konsekuensi yang perlu dipahami:
- **Publik:** siapa pun yang tahu topic bisa membaca datanya. Data proyek ini hanya simulasi, jadi ini dapat diterima.
- **Tanpa jaminan uptime:** broker publik ditujukan untuk belajar dan menguji. Jika koneksi gagal saat demo, tunggu beberapa menit lalu coba lagi.
- **Client ID ESP32 tidak benar-benar acak:** `random()` tanpa `randomSeed()` menghasilkan angka yang sama setiap simulasi dimulai. Jika dua orang menjalankan project yang sama bersamaan, broker memutus salah satunya karena Client ID-nya sama.

---

## 6. Cara menjalankan

### 6.1 Wokwi
1. Buka project di **wokwi.com**, lalu salin isi `sketch.ino` dan `diagram.json`.
2. Pastikan library **PubSubClient** ada: tambahkan file `libraries.txt` yang berisi `PubSubClient`, atau pasang lewat *Library Manager*.
3. Klik **Run**, lalu tunggu Serial Monitor menampilkan `CONNECTED!`.
4. Picu kondisi: klik sensor gas lalu naikkan nilainya, klik PIR lalu picu gerakan, dan klik tombol untuk reset.
5. **Simpan project** dan masukkan link-nya ke laporan (deliverable brief).

### 6.2 Dashboard Colab (`dashboard/dashboard.ipynb`)
1. Buka **colab.research.google.com**, pilih *File → Upload notebook*, lalu pilih `dashboard/dashboard.ipynb`.
2. Jalankan sel 1 (install paho-mqtt), lalu sel 2. Lima grafik (gas, PIR, buzzer, motor, tombol) diperbarui tiap 1 detik dan menampilkan 20 titik terakhir.
3. Hentikan dengan tombol **Stop** (■) di sel 2.

Dua perbaikan yang ditambahkan ke kode Tsabit:
- **Sel `!pip install -q paho-mqtt`**: paho-mqtt tidak terpasang bawaan di Colab. Tanpa sel ini, sel utama gagal dengan `ModuleNotFoundError`.
- **`plt.close(fig)` setelah `plt.show()`**: kode membuat figure baru setiap detik. Tanpa ditutup, semua figure lama tetap tersimpan di memori. Setelah 20 figure Matplotlib memberi peringatan, dan memori terus naik selama demo.

### 6.3 Dashboard HTML (`dashboard/dashboard.html`)
Buka file ini di browser (klik dua kali). Kelima kartu status berubah warna saat pesan masuk: merah berkedip untuk gas atau buzzer, biru untuk kondisi aktif. Library Paho JS dimuat dari CDN, jadi butuh internet.

### 6.4 MQTTX Web
Host `wss://broker.emqx.io`, port `8084`, path `/mqtt`, username dan password kosong. Lalu subscribe ke `tsabit/wokwi/#`.

---

## 7. Skenario pengujian

Kolom **Actual Result** dan **Status** diisi tim setelah menjalankan simulasi, sambil mengambil screenshot Serial Monitor, MQTTX, dan dashboard. Dokumen Tsabit menulis TC1, TC3, dan TC4 sebagai PASSED, tetapi temuan wiring di [pemahaman-proyek.md](pemahaman-proyek.md) 6.1 (poin 1–3) bisa membuat deteksi gas dan reset gagal. Jadi hasilnya perlu dibuktikan ulang dengan screenshot.

| ID | Test Case | Input / Condition | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| TC1 | Kondisi normal | Gas rendah, tidak ada gerakan, tombol tidak ditekan | Motor diam, buzzer diam. Dashboard: `AMAN`, `NORMAL`, `DIAM`, `DIAM`, `RELEASED`, diperbarui tiap 1 detik | Diisi tim | Diisi tim |
| TC2 | Gas terdeteksi, tanpa orang | Nilai gas dinaikkan melewati ambang, PIR diam | Motor maju 200 langkah (tuas ON → OFF), buzzer **diam**. Dashboard: `ADA_ASAP`, motor `BERPUTAR` | Diisi tim | Diisi tim |
| TC3 | Gas + ada orang | Saat alarm aktif, PIR dipicu | Buzzer **berbunyi**. Dashboard: `GERAKAN_DETECTED`, `BUNYI` | Diisi tim | Diisi tim |
| TC4 | Reset manual | Saat alarm aktif, tombol ditekan | Buzzer mati, motor mundur 200 langkah (tuas kembali ON). Dashboard: `PRESSED`, lalu motor `DIAM` | Diisi tim | Diisi tim |

> Jika TC2 gagal (alarm tidak aktif saat gas dinaikkan), periksa kabel sensor gas (`mq2:A0`) dan polaritas DOUT. Jika TC4 gagal (alarm tidak bisa di-reset), periksa wiring tombol (GND vs 3V3).

---

## 8. Yang sudah dan belum diverifikasi

| Item | Hasil |
|---|---|
| `diagram.json` valid sebagai JSON | ✅ Lolos (validitas nama pin **tidak** dicek, lihat temuan 6.1) |
| Notebook valid dan sel kode bisa di-parse | ✅ Lolos |
| Kode Colab menerima pesan dari broker publik (port 1883) | ✅ Lolos: pesan uji `ADA_ASAP` dikirim ke broker asli, `asap_val` berubah menjadi 1 (2026-10-30) |
| Kompilasi `sketch.ino` | ❌ **Belum**, karena `arduino-cli` tidak tersedia. Akan terlihat saat klik Run di Wokwi |
| Dashboard HTML | ❌ **Belum** dibuka di browser |
| Perilaku di simulasi Wokwi (TC1–TC4) | ❌ **Belum**, diisi tim |

---

## 9. Catatan dan keterbatasan

- **Temuan pada versi yang dipakai** (tim memutuskan memakai apa adanya): lihat [pemahaman-proyek.md](pemahaman-proyek.md) 6.1.
- **Ditunda ke tahap produk nyata** (EN, polaritas DOUT, buzzer DC, strapping pin, level 5 V, VMOT): lihat [pemahaman-proyek.md](pemahaman-proyek.md) 6.2.
- **Jaringan sebagai pengambil keputusan:** sketch menunggu WiFi dan broker sebelum membaca sensor. Untuk produk nyata, alarm lokal sebaiknya tetap bekerja tanpa internet, dan jaringan hanya menjadi "pelapor".
- **Keamanan:** broker publik tanpa autentikasi dan tanpa enkripsi (port 1883). Untuk produk nyata, perlu broker pribadi dengan username/password dan TLS (port 8883).
- **Tidak ada data analog:** dashboard hanya menampilkan 0/1, tanpa tren kadar gas atau peringatan dini.
- **Remote control:** dokumen Tsabit menyebut topic `tsabit/wokwi/control` (`RESET`/`TEST_ALARM`), tetapi kode tidak men-subscribe topic itu. Fitur ini **belum ada**, jadi tidak ditulis di laporan.

---

## 10. Checklist terhadap brief

| Syarat brief | Status | Di mana |
|---|---|---|
| ESP32 sebagai controller | ✅ | `diagram.json` |
| ≥1 sensor, ≥1 aktuator | ✅ | MQ-2, PIR, tombol / stepper, buzzer |
| Wokwi sebagai simulasi | ✅ | `wokwi/` |
| Serial Monitor | ✅ (hanya status koneksi) | Bagian 2 |
| MQTT + broker (broker publik EMQX, pengganti HiveMQ Cloud) | ✅ | Bagian 3–5 |
| Dashboard Python (paho-mqtt + Matplotlib) | ✅ | `dashboard/dashboard.ipynb` |
| Dashboard tambahan (HTML) | ✅ bonus | `dashboard/dashboard.html` |
| ≥3 skenario uji | ✅ (hasil diisi tim) | Bagian 7 |
| Link project Wokwi | ⏳ Link project Tsabit | — |
| Laporan .docx, video .mp4, screenshot | ⏳ Tim | — |
