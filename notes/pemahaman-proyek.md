# Pemahaman Proyek: Sistem Deteksi Kebocoran Gas (ESP32 + Wokwi)

> Dokumen ini adalah hasil pembacaan isi folder `notes/` dan `wokwi/`.
> Kondisi yang dijelaskan: `wokwi/sketch.ino` versi 29-10-2026 19:20 (variabel `asap` sudah diganti menjadi `gas`) dan `wokwi/diagram.json` versi 29-10-2026 17:41, **sebelum** Serial, WiFi, MQTT, dan AOUT ditambahkan.
> Penambahan berikutnya dijelaskan di [penjelasan-pengembangan.md](penjelasan-pengembangan.md).
>
> Penanda keyakinan yang dipakai:
> - **[Pasti]**: terlihat langsung di file.
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

**Sistem deteksi kebocoran gas elpiji (LPG).** Dalam daftar contoh di brief, proyek ini termasuk kategori **Smart Alert/Security**.

Cara kerjanya:
1. **Sensor gas (MQ-2)** terus memantau udara. Intinya hanya satu pertanyaan: *ada kebocoran gas atau tidak?* Untuk pertanyaan itu, output digital (DOUT) modul MQ-2 sudah cukup.
2. Saat gas terdeteksi, **alarm terkunci** (*latching*) dan **motor stepper memutar tuas regulator LPG dari ON ke OFF**, sehingga aliran gas dari tabung terhenti dari sumbernya.
   - **[Keputusan tim, 2026-10-30]** Fungsi ini diambil dari narasi K3 versi Tsabit (lihat [versi-teman-tsabit.md](versi-teman-tsabit.md)). Di simulasi, 200 langkah (1 putaran motor) merepresentasikan gerakan tuas ON ke OFF; rasio gir dan sudut tuas sebenarnya ditentukan saat prototipe fisik dibuat.
3. Selama alarm aktif, **sensor PIR** mendeteksi apakah ada orang di dekatnya. Jika ada, **buzzer** berbunyi sebagai peringatan.
   - **[Dugaan]** Buzzer hanya bunyi saat ada orang, mungkin supaya peringatan ditujukan ke orang yang berada di lokasi (misalnya agar tidak menyalakan api).
4. **Tombol reset** ditekan oleh petugas atau penghuni untuk mematikan alarm. Motor memutar tuas kembali ke posisi ON, dan sistem siap mendeteksi lagi.

**Kenapa memutar tuas regulator, bukan mencabut selang? (prinsip K3)** Saat terjadi kebocoran, tindakan yang aman adalah menutup aliran gas dari sumbernya. Mencabut selang dari regulator saat tuas masih ON justru berbahaya, karena gas dari tabung keluar bebas ke ruangan. Memutar tuas ke OFF menghentikan aliran dari tabung. Penggerak dipasang di luar regulator (non-invasif), jadi bagian kedap gas regulator tidak perlu dibongkar. Regulator rumah tangga yang umum dipakai hanya punya tuas manual, sehingga aliran gas baru tertutup kalau ada orang yang memutarnya; sistem ini mengotomatiskan langkah tersebut.

Kenapa alarm dibuat terkunci? Kebocoran gas berbahaya walau konsentrasinya turun sesaat, misalnya karena angin. Jika alarm otomatis mati saat sensor berhenti mendeteksi, kebocoran bisa luput. Dengan alarm terkunci, **manusia harus memastikan dulu** situasinya aman sebelum menekan reset. Ini pola yang umum di sistem keselamatan.

---

## 4. Hardware dan wiring (`diagram.json`)

### 4.1 Komponen dan alasan pemilihannya

- **ESP32 DevKit C v4**: controller utama (wajib menurut brief). Punya WiFi bawaan, jadi nanti bisa langsung mengirim data lewat MQTT tanpa modul tambahan.
- **Sensor gas MQ-2** (`wokwi-gas-sensor`): mendeteksi gas mudah terbakar, termasuk LPG. Punya dua output: **DOUT** (digital, ada/tidak ada gas, berdasarkan ambang potensiometer di modul) dan **AOUT** (analog, kadar relatif). Saat ini hanya DOUT yang dipakai.
- **Sensor PIR**: mendeteksi gerakan dan panas tubuh manusia, jadi bisa dipakai untuk mengetahui ada orang atau tidak.
- **Buzzer**: indikator suara, cara paling sederhana untuk memperingatkan orang.
- **Motor stepper NEMA 17** (`size: 17`) + **driver A4988**. Stepper dipilih karena posisinya bisa dihitung per langkah, jadi bisa kembali tepat ke posisi awal tanpa sensor posisi. Driver dibutuhkan karena pin ESP32 tidak sanggup mengalirkan arus untuk koil motor. A4988 menerjemahkan dua sinyal sederhana (STEP = maju satu langkah, DIR = arah) menjadi arus koil yang benar.
- **Push button**: input reset manual.

### 4.2 Peta pin

| Fungsi | Pin ESP32 | Komponen | Mode di kode |
|---|---|---|---|
| STEP | GPIO 32 | A4988 STEP | OUTPUT |
| DIR | GPIO 33 | A4988 DIR | OUTPUT |
| ENABLE | GPIO 25 | A4988 ENABLE | OUTPUT |
| Sensor gas | GPIO 12 | MQ-2 DOUT | INPUT |
| PIR | GPIO 0 | PIR OUT | INPUT |
| Tombol reset | GPIO 2 | Push button | INPUT_PULLDOWN |
| Buzzer | GPIO 4 | Buzzer (+) | OUTPUT |

### 4.3 Power dan ground

- **5V** ke A4988 VDD, VCC sensor gas, dan VCC PIR. Ketiganya modul 5 V.
- **3V3** ke satu kaki tombol.
- **GND** bersama: A4988, sensor gas, dan PIR ke `GND.1`, sedangkan buzzer ke `GND.2`. Semua ground harus tersambung, karena tegangan sinyal hanya bermakna jika diukur dari titik nol yang sama.
- Serial Monitor Wokwi sudah tersambung ke TX/RX ESP32. Di level wiring sudah siap, tapi kode belum memakainya (lihat bagian 6).

### 4.4 Detail penting wiring

- **[Pasti]** **Koil stepper**: `2A/2B → A+/A-` dan `1A/1B → B+/B-`. Setiap pasangan output A4988 menggerakkan satu koil. Jika pasangannya tertukar, motor hanya bergetar.
- **[Pasti]** **`ENABLE` dikontrol GPIO 25**. Pin ini **aktif-LOW**: `LOW` berarti driver hidup dan motor bertenaga, `HIGH` berarti driver mati dan motor lemas. Karena itu kode menulis `EN = HIGH` saat diam (hemat daya, motor tidak panas) dan `EN = LOW` saat motor akan bergerak.
- **[Pasti]** **`SLEEP` disambung ke `RESET`** di A4988. Ini cara standar jika kedua fitur itu tidak dipakai, supaya `RESET` tidak menggantung (*floating*) dan driver tidak ter-reset secara acak.
- **[Pasti]** **Tombol: 3V3 → tombol → GPIO 2**, dengan `INPUT_PULLDOWN` di kode. Resistor pull-down internal menahan pin di `LOW` saat tombol dilepas. Saat ditekan, 3V3 masuk dan pin menjadi `HIGH`. Wiring dan kode sudah konsisten.
- **[Dugaan]** Pin `MS1`/`MS2`/`MS3` A4988 tidak dikabel, jadi driver bekerja di mode *full-step*. Motor 1,8°/langkah butuh 200 langkah per putaran, jadi **200 langkah = 1 putaran penuh**.
- **[Pasti]** `VMOT` dan `GND` kedua A4988 tidak dikabel. **Menurut konfirmasi tim, ini tidak wajib di Wokwi.** Di hardware asli, VMOT adalah suplai daya motor (umumnya 8–35 V) dan wajib ada.

---

## 5. Logika program (`sketch.ino`)

Program memakai gaya **loop bersarang yang blocking**: kode menunggu (dengan `delayMicroseconds`/`delay`) sampai satu tugas selesai sebelum lanjut ke tugas lain.

### 5.1 `setup()`: kondisi awal

Semua pin diatur modenya. Lalu `EN = HIGH` (driver mati) dan `Buzz = LOW` (buzzer diam). Sistem mulai dalam kondisi aman dan hening.

### 5.2 `loop()`: alur utama

```
loop():
  baca sensor gas (gas) dan tombol (butsig)
  JIKA gas == LOW (gas terdeteksi):
      SELAMA tombol belum ditekan:           ← alarm terkunci
          EN = HIGH
          baca tombol
          baca PIR → buzzer ON jika ada orang, OFF jika tidak
          JIKA motor belum di posisi 200:
              EN = LOW, DIR = maju
              200× pulsa STEP (1 ms HIGH + 1 ms LOW)  ≈ 0,4 detik
      — tombol ditekan —
      buzzer OFF, EN = LOW, DIR = mundur
      mundur sebanyak `count` langkah (Hitung = count)
      EN = HIGH, jeda 500 ms
```

Penjelasan mekanismenya:
- **Kenapa `gas == LOW` berarti gas terdeteksi?** Modul MQ-2 asli bersifat **aktif-LOW**: DOUT turun ke `LOW` saat kadar gas melewati ambang. Variabel `gas` menyimpan *level mentah* pin. Karena itu namanya `gas`, bukan `gasDetected`, sebab `true`/`HIGH` justru berarti tidak ada gas.
- **Kenapa alarm terkunci?** Sensor gas hanya dibaca **sekali** sebelum masuk `while`. Di dalam `while`, yang diperiksa hanya tombol, jadi alarm tidak bisa mati sendiri walau gas sudah hilang.
- **Bagaimana motor tahu posisinya?** Variabel global `count` bertambah 1 setiap langkah maju. Saat reset, `Hitung = count` menyimpan jumlah langkah yang sudah dimajukan, lalu motor mundur **tepat sebanyak itu**, dan `count` dikurangi sampai 0. Ini mencegah motor mundur melewati posisi awal jika ternyata belum pernah maju.
- **Kecepatan motor**: 1 langkah = 2 ms. Jadi 200 langkah = 0,4 detik, setara 1 putaran per 0,4 detik (sekitar 150 RPM jika full-step).

### 5.3 Trade-off gaya blocking

| | Blocking (yang dipakai sekarang) | Non-blocking (`millis()`) |
|---|---|---|
| Kelebihan | Mudah dibaca, urutan kerja jelas dari atas ke bawah | Tombol, PIR, dan jaringan tetap terbaca saat motor bergerak |
| Kekurangan | Selama motor bergerak (~0,4 detik), tombol dan PIR tidak dibaca | Kode lebih rumit (perlu state machine) |

Untuk gerakan sependek 0,4 detik, blocking masih bisa diterima dan lebih mudah dijelaskan di laporan.

---

## 6. Temuan dan catatan

### 6.1 Sudah diperbaiki tim (dibanding versi sebelumnya)
- **[Pasti]** Sketch sekarang lengkap dan `#define` sudah benar. Versi lama memakai `#define X = 32;`, yang menyebabkan error kompilasi.
- **[Pasti]** Wiring tombol sudah benar. Versi lama menyambungkan 3V3 dan GND di sisi tombol yang sama, sehingga tombol yang ditekan menyebabkan korsleting.
- **[Pasti]** `SLEEP`–`RESET` A4988 sudah disambung, dan `ENABLE` sudah dikontrol GPIO 25.
- **[Pasti]** Reset memakai `Hitung = count`, jadi motor hanya mundur sebanyak langkah yang sudah dimajukan, dan posisi tetap sinkron.

### 6.2 Belum ada (gap terhadap brief)
- **[Pasti]** Tidak ada `Serial.begin`/`Serial.print`, padahal Serial Monitor adalah **syarat minimum**.
- **[Pasti]** Belum ada WiFi, MQTT/HiveMQ, dan dashboard Python, yang mempengaruhi bobot Communication & Visualization (15%).
- **[Pasti]** Belum ada tabel skenario pengujian (minimal 3 skenario).
- **[Pasti]** Hanya DOUT yang dipakai, jadi belum ada data kadar gas untuk grafik tren di dashboard.
- **[Pasti]** Link Wokwi belum ada (yang lama dihapus karena usang). Link ini wajib ada di deliverable.

➡️ Semua gap ini ditangani, dan penjelasannya ada di [penjelasan-pengembangan.md](penjelasan-pengembangan.md), kecuali link Wokwi yang harus dibuat tim sendiri.

### 6.3 Sedang didiskusikan tim (tidak diubah)
Proyek masih di tahap **ide dan laporan**, belum produk nyata, jadi poin berikut **hanya dicatat** untuk dipastikan nanti:
- **[Pasti, maksudnya belum jelas]** `EN = HIGH` ditulis di awal setiap iterasi `while` alarm. Akibatnya, setelah motor sampai di posisi 200, driver langsung dimatikan dan motor kehilangan *holding torque* (bisa digeser dengan tangan). Ini bisa disengaja (hemat daya, motor tidak panas) atau tidak. Jika stepper harus menahan posisi tuas regulator, holding torque mungkin dibutuhkan.
- **[Belum dipastikan]** **Polaritas DOUT di Wokwi.** Kode memakai `LOW` = gas terdeteksi (sesuai modul asli), sedangkan versi kode sebelumnya mengasumsikan `HIGH` di Wokwi. Hanya simulasi yang bisa memastikan mana yang benar.
- **[Belum dipastikan]** **Buzzer** dinyalakan dengan `digitalWrite(HIGH)` (DC), bukan `tone()` (gelombang kotak). Buzzer *pasif* butuh gelombang supaya berbunyi, sedangkan buzzer *aktif* cukup DC. Belum dicek apakah buzzer Wokwi berbunyi dengan DC.
- **[Risiko hardware asli]** **Strapping pin ESP32**: GPIO 0, 2, dan 12 dibaca ESP32 saat boot untuk menentukan mode boot dan tegangan flash. Modul MQ-2 asli mengeluarkan `HIGH` saat tidak ada gas, sehingga GPIO 12 bisa `HIGH` saat boot. Pada banyak modul ESP32, kondisi ini memilih tegangan flash 1,8 V dan ESP32 gagal boot. GPIO 0 yang `LOW` saat boot juga bisa membuat ESP32 masuk mode download. Di Wokwi ini tidak bermasalah.
- **[Risiko hardware asli]** **Level tegangan**: DOUT modul MQ-2 yang diberi 5 V bisa mengeluarkan sinyal 5 V, sedangkan pin ESP32 hanya toleran 3,3 V. Solusinya level shifter atau pembagi tegangan.

---

## 7. Ringkasan

### Komponen vs fungsi vs pin

| Komponen | Peran dalam alur IoT | Fungsi | Pin |
|---|---|---|---|
| MQ-2 (DOUT) | Input / sensing | Deteksi ada/tidaknya kebocoran gas | GPIO 12 |
| PIR | Input / sensing | Deteksi keberadaan orang | GPIO 0 |
| Push button | Input | Reset alarm | GPIO 2 |
| ESP32 | Processing / logic | Keputusan alarm, kontrol motor & buzzer | — |
| A4988 + NEMA 17 | Output / actuation | Memutar tuas regulator ON → OFF (200 langkah di simulasi) | 32, 33, 25 |
| Buzzer | Output / indikator | Peringatan suara saat ada orang | GPIO 4 |

### Temuan vs status

| Temuan | Keyakinan | Status |
|---|---|---|
| Serial belum dipakai | Pasti | Ditangani di pengembangan |
| MQTT, dashboard, tes belum ada | Pasti | Ditangani di pengembangan |
| AOUT belum dipakai | Pasti | Ditangani di pengembangan (GPIO 34) |
| Link Wokwi belum ada | Pasti | **Tim** perlu menyimpan project di Wokwi |
| `EN` mati saat alarm | Pasti (maksud belum jelas) | Diskusi tim |
| Polaritas DOUT di Wokwi | Belum dipastikan | Diskusi tim |
| Buzzer DC vs `tone()` | Belum dipastikan | Diskusi tim |
| Strapping pin 0/2/12 | Risiko hardware asli | Diskusi tim |
| DOUT 5 V ke pin 3,3 V | Risiko hardware asli | Diskusi tim |
| VMOT A4988 tidak dikabel | Pasti | Tidak wajib di Wokwi (konfirmasi tim) |

> Catatan: simulasi Wokwi **tidak dijalankan** saat dokumen ini ditulis. Semua penjelasan berasal dari membaca kode, diagram, dan brief.
