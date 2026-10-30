# Pemahaman Proyek: Sistem Deteksi Kebocoran Gas LPG (ESP32 + Wokwi)

> Dokumen ini menjelaskan isi folder `notes/` dan `wokwi/`.
> **Keputusan tim (2026-10-30):** `wokwi/sketch.ino` dan `wokwi/diagram.json` memakai **versi Muhammad Sayyid Tsabit apa adanya** (dokumen aslinya di [versi-teman-tsabit.md](versi-teman-tsabit.md)). Versi tim sebelumnya (JSON + AOUT + Last Will) masih tersimpan di riwayat git.
> MQTT, dashboard, dan pengujian dijelaskan di [penjelasan-pengembangan.md](penjelasan-pengembangan.md).
>
> Penanda keyakinan yang dipakai:
> - **[Pasti]**: terlihat langsung di file.
> - **[Kemungkinan besar]**: berdasarkan pengetahuan tentang komponen Wokwi, perlu dipastikan di simulator.
> - **[Dugaan]**: tafsiran saya, belum dikonfirmasi tim.
> - **[Belum dipastikan]**: butuh simulasi atau pengecekan.

---

## 1. Apa yang diminta brief

File `Study Case Guideline Stage 2 - SIC 8.pdf` adalah brief **Samsung Innovation Campus Batch 8 – Selection Phase 2: IoT Device and Hardware Discovery**.

Inti brief: tim bebas memilih masalah IoT, asalkan solusinya mengikuti alur IoT lengkap:

```
INPUT / SENSOR → ESP32 / LOGIC → OUTPUT / ACTUATOR
                       ↓
SERIAL / MQTT → HIVEMQ / APPLICATION → PYTHON DASHBOARD
```

Alur ini penting karena penilaian tidak hanya melihat "alatnya jalan". Penilai ingin melihat bahwa tim paham *aliran data*: sensor membaca, ESP32 memutuskan, aktuator bertindak, lalu datanya dikirim dan ditampilkan.

**Syarat minimum** (wajib ada):
- ESP32 sebagai controller utama.
- Minimal 1 sensor/input dan 1 aktuator/output.
- Wokwi sebagai media simulasi.
- Program yang menunjukkan fungsi utama.
- **Serial Monitor** untuk debugging/data output.
- Dokumentasi wiring dan logika.

**Fitur yang direkomendasikan** (nilai tambah): MQTT + HiveMQ Cloud, Python + paho-mqtt, dashboard Plotly/Matplotlib, serta komponen tambahan seperti buzzer atau servo.

**Deliverable akhir:** laporan **.docx** (bukan slide), link project Wokwi, source code, video demo .mp4, dan screenshot hasil pengujian.

**Rubrik penilaian:**

| Kategori | Bobot | Rincian |
|---|---|---|
| Project Structure | 10% | Ide & relevansi 5%, Problem statement & tujuan 5% |
| Device & Hardware Discovery | 20% | Pemilihan komponen 5%, Fungsi/GPIO 5%, Wiring & arsitektur 10% |
| Programming & Functionality | 30% | Logika 15%, Input-output 10%, Debugging/stabilitas 5% |
| Communication & Visualization | 15% | Serial 5%, MQTT/HiveMQ 5%, Dashboard 5% |
| Documentation, Testing & Teamwork | 25% | Laporan 5%, Testing 5%, Kontribusi 5%, Video demo 10% |

Bobot terbesar ada di **Programming (30%)** dan **Dokumentasi/Testing (25%)**. Artinya, logika yang jelas dan dokumentasi yang rapi lebih berharga daripada jumlah komponen yang banyak.

---

## 2. Format laporan (`format.txt`)

`format.txt` berisi aturan format penulisan laporan bergaya akademik:
- Kertas A4. Margin atas 4 cm, kiri 4 cm, bawah 3 cm, kanan 3 cm (banyak kampus memakai 3 cm di semua sisi).
- Font Times New Roman. Isi 12 pt, judul bab 14 pt tebal kapital, subbab 12 pt tebal.
- Spasi 1,5 untuk isi, dan 1,0 untuk daftar pustaka dan kutipan panjang.
- Paragraf rata kiri-kanan dengan indentasi baris pertama sekitar 1 cm.
- Nomor halaman: bagian awal (kata pengantar sampai daftar tabel) memakai angka Romawi kecil (i, ii, iii), dan mulai Bab I memakai angka Arab (1, 2, 3).

Aturan ini dipakai untuk **laporan .docx**. Brief meminta file .docx, jadi laporan paling praktis ditulis di Google Docs atau Word lalu diekspor ke .docx. LaTeX tidak disarankan, karena konversi LaTeX → .docx sering merusak tabel dan format.

---

## 3. Use case: apa yang dibangun

**Smart LPG Gas Leak Detection & Automatic Regulator Safety Shut-Off System**: sistem deteksi kebocoran gas elpiji (LPG) yang otomatis menutup regulator. Dalam daftar contoh di brief, proyek ini termasuk kategori **Smart Alert/Security**, dengan konteks K3 (Keselamatan dan Kesehatan Kerja) rumah tangga.

Cara kerjanya:
1. **Sensor gas (MQ-2)** terus memantau udara. Pertanyaannya hanya satu: *ada kebocoran gas atau tidak?* Untuk itu output digital (DOUT) sudah cukup.
2. Saat gas terdeteksi, **alarm terkunci** (*latching*) dan **motor stepper memutar tuas regulator LPG dari ON ke OFF** (200 langkah = 1 putaran motor di simulasi), sehingga aliran gas dari tabung terhenti dari sumbernya.
3. Selama alarm aktif, **sensor PIR** mendeteksi apakah ada orang. Jika ada, **buzzer** berbunyi sebagai peringatan evakuasi. Jika tidak ada orang, buzzer diam, tapi regulator tetap ditutup.
4. **Tombol reset** ditekan untuk memulihkan sistem: buzzer mati, motor memutar tuas kembali ke ON (mundur 200 langkah), dan sistem siap mendeteksi lagi.

**Kenapa memutar tuas regulator, bukan mencabut selang? (prinsip K3)** Mencabut selang saat tuas masih ON justru berbahaya, karena gas dari tabung keluar bebas ke ruangan. Memutar tuas ke OFF menghentikan aliran dari sumbernya. Penggerak dipasang di luar regulator (non-invasif), jadi ruang kedap gas regulator tidak perlu dibongkar. Rasio gir dan sudut tuas sebenarnya ditentukan saat prototipe fisik dibuat. Analisis gir Tsabit disimpan di [versi-teman-tsabit.md](versi-teman-tsabit.md) sebagai bahan prototipe, dan **tidak dimasukkan ke laporan** karena angka dan mereknya belum bersumber.

**Kenapa alarm dibuat terkunci?** Kebocoran gas tetap berbahaya walau konsentrasinya turun sesaat, misalnya tertiup angin. Jika alarm mati sendiri saat sensor berhenti mendeteksi, kebocoran bisa luput. Dengan alarm terkunci, **manusia harus memastikan dulu** situasinya aman sebelum menekan reset. Ini pola yang umum di sistem keselamatan.

---

## 4. Hardware dan wiring (`diagram.json`)

### 4.1 Komponen dan alasan pemilihannya

- **ESP32 DevKit V1** (`wokwi-esp32-devkit-v1`): controller utama (wajib menurut brief), dengan WiFi bawaan untuk MQTT.
- **Sensor gas MQ-2** (`wokwi-gas-sensor`): mendeteksi gas mudah terbakar, termasuk LPG. Kode hanya membaca sinyal digital (ada atau tidak ada gas).
- **Sensor PIR**: mendeteksi gerakan dan panas tubuh manusia, untuk mengetahui ada orang atau tidak.
- **Buzzer**: indikator suara untuk evakuasi.
- **Motor stepper NEMA 17** + **driver A4988**. Stepper dipilih karena posisinya bisa dihitung per langkah, jadi bisa kembali tepat ke posisi awal tanpa sensor posisi. Driver diperlukan karena pin ESP32 tidak sanggup mengalirkan arus koil motor. A4988 menerjemahkan dua sinyal sederhana (STEP = maju satu langkah, DIR = arah) menjadi arus koil.
- **Push button**: input reset manual.

### 4.2 Peta pin

| Fungsi | Pin ESP32 | Ujung kabel di `diagram.json` | Mode di kode |
|---|---|---|---|
| STEP | GPIO 32 | `driver:STEP` | OUTPUT |
| DIR | GPIO 33 | `driver:DIR` | OUTPUT |
| ENABLE | GPIO 25 | `driver:ENABLE` | OUTPUT |
| Sensor gas | GPIO 12 | `mq2:A0` | INPUT |
| PIR | GPIO 0 | `pir:OUT` | INPUT |
| Tombol reset | GPIO 2 | `btn:2.R` (kaki lain ke GND) | INPUT_PULLDOWN |
| Buzzer | GPIO 4 | `buzz:2` (kaki `1` ke GND) | OUTPUT |

### 4.3 Power dan ground

- **3V3** ke VCC sensor gas dan VCC PIR.
- **GND** bersama di `GND.1`: sensor gas, PIR, tombol, dan buzzer. Semua ground harus tersambung, karena tegangan sinyal hanya bermakna jika diukur dari titik nol yang sama.
- **A4988**: hanya STEP, DIR, ENABLE, dan keempat output koil yang dikabel. `VDD`, `GND`, `VMOT`, `SLEEP`, dan `RESET` tidak dikabel.

### 4.4 Detail wiring

- **[Pasti]** Koil stepper: `1A → A1`, `1B → A2`, `2A → B1`, `2B → B2`.
- **[Pasti]** `ENABLE` A4988 bersifat **aktif-LOW**: `LOW` berarti motor bertenaga, `HIGH` berarti motor lemas. Kode memberi `LOW` tepat sebelum motor bergerak dan `HIGH` setelahnya.
- **[Pasti]** Tombol menghubungkan **GND** dengan GPIO 2, sementara kode memakai `INPUT_PULLDOWN` (lihat 6.1, poin 1).
- **[Dugaan]** `MS1`/`MS2`/`MS3` A4988 tidak dikabel, jadi driver bekerja di mode *full-step*: motor 1,8°/langkah, **200 langkah = 1 putaran penuh**.

---

## 5. Logika program (`sketch.ino`)

Program memakai gaya **loop bersarang yang blocking**: kode menunggu sampai satu tugas selesai sebelum lanjut ke tugas lain.

### 5.1 `setup()`: kondisi awal

`Serial.begin(115200)`, semua pin diatur modenya, lalu `EN = HIGH` (driver mati) dan buzzer `LOW`. Setelah itu `setup_wifi()` **menunggu sampai WiFi tersambung**, lalu alamat broker `broker.emqx.io:1883` diset.

### 5.2 `loop()`: alur utama

```
loop():
  jika MQTT putus → reconnect()            ← menunggu sampai berhasil (coba ulang tiap 5 detik)
  client.loop()
  checkAndPublishAll()                      ← baca gas, PIR, tombol; publish yang berubah
  sendRutin()                               ← publish kelima status tiap 1 detik
  JIKA gas == LOW (gas terdeteksi):
      SELAMA tombol belum ditekan:          ← alarm terkunci
          client.loop, checkAndPublishAll, sendRutin
          baca tombol
          buzzer ON jika PIR HIGH, OFF jika tidak
          JIKA count != 200:
              motorStatus = "BERPUTAR", publish
              EN = LOW, DIR = maju, 200× pulsa STEP (≈0,4 detik), EN = HIGH
      — tombol ditekan —
      motorStatus = "BERPUTAR", buzzer OFF, publish
      EN = LOW, DIR = mundur, 200× pulsa STEP, EN = HIGH
      motorStatus = "DIAM", publish, jeda 500 ms
  SELAIN ITU: buzzer OFF, motorStatus = "DIAM"
```

Penjelasan mekanismenya:
- **Kenapa `asap == LOW` berarti gas terdeteksi?** Modul MQ-2 bersifat **aktif-LOW**: DOUT turun ke `LOW` saat kadar gas melewati ambang potensiometer di modul.
- **Kenapa alarm terkunci?** Keluar dari `while` hanya bisa lewat tombol. Sensor gas tetap dibaca dan dilaporkan ke MQTT, tapi tidak bisa mematikan alarm.
- **Bagaimana motor tahu posisinya?** `count` bertambah 1 setiap langkah maju, dan `count != 200` mencegah motor maju dua kali. Saat reset, motor selalu mundur **tepat 200 langkah** (tidak melihat `count`).
- **Kecepatan motor**: 1 langkah = 2 ms, jadi 200 langkah ≈ 0,4 detik.

### 5.3 Trade-off gaya blocking

| | Blocking (yang dipakai) | Non-blocking (`millis()`) |
|---|---|---|
| Kelebihan | Mudah dibaca, urutan kerja jelas dari atas ke bawah | Tombol, PIR, dan jaringan tetap terbaca saat motor bergerak |
| Kekurangan | Selama motor bergerak (~0,4 detik) dan selama menunggu WiFi/broker, sensor tidak dibaca | Kode lebih rumit (perlu state machine) |

---

## 6. Temuan dan catatan

### 6.1 Diketahui, tim memutuskan memakai versi ini apa adanya (2026-10-30)
Evaluasi lengkap ada di [versi-teman-tsabit.md](versi-teman-tsabit.md), Bagian B. Simulasi versi ini **belum saya jalankan**. Dokumen Tsabit menulis semua tes PASSED, jadi ada kemungkinan `diagram.json` yang dipakai di Wokwi Tsabit berbeda dengan yang ada di dokumen.
1. **[Pasti]** Tombol ke GND + `INPUT_PULLDOWN`: pin selalu `LOW`, ditekan atau tidak, sehingga alarm **tidak bisa di-reset**. Wiring yang cocok dengan kode: tombol ke **3V3**.
2. **[Pasti]** `mq2:A0` bukan nama pin sensor gas Wokwi (yang ada `AOUT`, `DOUT`, `VCC`, `GND`), jadi GPIO 12 tidak tersambung ke sensor.
3. **[Kemungkinan besar]** Nama pin `esp:12` dan `stepper:A1`… tidak cocok dengan `wokwi-esp32-devkit-v1` (`D12`) dan stepper Wokwi (`A-`, `A+`, `B+`, `B-`).
4. **[Pasti]** `setup_wifi()` dan `reconnect()` menunggu tanpa batas. Jika WiFi atau broker mati, sensor gas tidak pernah dibaca. Untuk alat keselamatan, ini cacat desain.
5. **[Pasti]** `motorStatus` tetap `"BERPUTAR"` setelah motor selesai maju, dan baru menjadi `"DIAM"` setelah reset. Dashboard menampilkan motor berputar selama alarm, padahal motor sudah diam.
6. **[Pasti]** Reset selalu mundur 200 langkah. Jika gas terdeteksi saat tombol sedang ditahan, motor mundur tanpa pernah maju, melewati posisi awal.
7. **[Pasti]** Serial hanya mencetak status koneksi WiFi/MQTT, tidak mencetak kejadian (gas, PIR, motor, reset). Kejadian hanya terlihat lewat MQTT.

### 6.2 Ditunda, dipastikan di tahap produk nyata (tidak diubah)
- **[Pasti, maksud belum jelas]** `EN = HIGH` setelah motor sampai tujuan, sehingga motor kehilangan *holding torque* dan tuas bisa bergeser. Bisa disengaja (hemat daya, motor tidak panas).
- **[Belum dipastikan]** **Polaritas DOUT di Wokwi**: kode memakai `LOW` = gas, sesuai modul asli.
- **[Belum dipastikan]** **Buzzer** dinyalakan dengan `digitalWrite(HIGH)` (DC), bukan `tone()`. Buzzer pasif butuh gelombang supaya berbunyi, sedangkan buzzer aktif cukup DC.
- **[Risiko hardware asli]** **Strapping pin** GPIO 0, 2, dan 12 dibaca ESP32 saat boot. GPIO 12 `HIGH` saat boot (MQ-2 tanpa gas) bisa memilih tegangan flash yang salah, dan GPIO 0 `LOW` bisa membuat ESP32 masuk mode download.
- **[Risiko hardware asli]** **Level tegangan**: heater MQ-2 asli umumnya butuh 5 V (di Wokwi diberi 3V3), dan DOUT modul 5 V bisa mengeluarkan sinyal 5 V ke pin ESP32 yang hanya toleran 3,3 V.
- **[Risiko hardware asli]** **VMOT A4988** tidak wajib di Wokwi, tapi di hardware asli wajib sebagai suplai motor.

---

## 7. Ringkasan

### Komponen vs fungsi vs pin

| Komponen | Peran dalam alur IoT | Fungsi | Pin |
|---|---|---|---|
| MQ-2 (digital) | Input / sensing | Deteksi ada/tidaknya kebocoran gas | GPIO 12 |
| PIR | Input / sensing | Deteksi keberadaan orang | GPIO 0 |
| Push button | Input | Reset alarm | GPIO 2 |
| ESP32 DevKit V1 | Processing / logic | Keputusan alarm, kontrol motor & buzzer, MQTT | — |
| A4988 + NEMA 17 | Output / actuation | Memutar tuas regulator ON → OFF (200 langkah) | 32, 33, 25 |
| Buzzer | Output / indikator | Peringatan evakuasi saat ada orang | GPIO 4 |

### Temuan vs status

| Temuan | Keyakinan | Status |
|---|---|---|
| Tombol ke GND + pull-down (reset tidak bisa) | Pasti | Dipakai apa adanya (keputusan tim) |
| `mq2:A0` tidak ada | Pasti | Dipakai apa adanya |
| Nama pin board/stepper | Kemungkinan besar | Dipakai apa adanya |
| WiFi/MQTT memblokir alarm | Pasti | Dipakai apa adanya |
| `motorStatus` tetap BERPUTAR | Pasti | Dipakai apa adanya |
| Reset selalu mundur 200 langkah | Pasti | Dipakai apa adanya |
| Serial tanpa log kejadian | Pasti | Dipakai apa adanya |
| `EN` mati setelah bergerak, polaritas DOUT, buzzer DC | Belum jelas | Ditunda |
| Strapping pin, level 5 V, VMOT | Risiko hardware asli | Ditunda |

> Catatan: simulasi Wokwi **tidak dijalankan** saat dokumen ini ditulis. Semua penjelasan berasal dari membaca kode, diagram, dan brief.
