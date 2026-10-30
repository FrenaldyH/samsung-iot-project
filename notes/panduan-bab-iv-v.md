# Panduan Mengisi Bab IV (Pengujian) dan Bab V (Pembagian Peran)

> Untuk seluruh anggota tim. Isian yang dimaksud ada di tab **Laporan** pada Google Doc.
> Sumber aturan: brief SIC 8 bagian *Testing & Validation* dan *Isi Laporan*, serta `notes/format.txt`.
> Yang dinilai: Testing 5%, Kontribusi 5%, Video Demo 10% (total 20% dari nilai).

---

## Bab IV: Pengujian

### Apa yang diminta brief
- Minimal **3 skenario uji**. Laporan sudah menyiapkan 4 (TC1–TC4).
- Uji **kondisi normal dan kondisi abnormal**. TC1 adalah kondisi normal, TC2–TC4 kondisi abnormal.
- Untuk setiap skenario catat **Input/Condition, Expected Result, Actual Result, dan Status**. Kolom Skenario, Input, dan Hasil yang Diharapkan sudah terisi; tim tinggal mengisi **Hasil Aktual** dan **Status**.
- Dokumentasikan hasil dengan **screenshot atau video**.

### Langkah 1: siapkan semuanya sebelum menguji
1. Buka project Wokwi versi final, lalu klik **Run**. Tunggu Serial Monitor menampilkan `[MQTT] Connecting to broker.emqx.io... CONNECTED!`.
2. Buka dashboard Colab (`dashboard/dashboard.ipynb`): jalankan sel 1, lalu sel 2.
3. Buka `dashboard/dashboard.html` di browser, dan MQTTX Web yang sudah subscribe ke `tsabit/wokwi/#`.
4. Atur layar agar Wokwi dan dashboard terlihat berdampingan. Satu screenshot yang memperlihatkan keduanya sekaligus menjadi bukti yang lebih kuat daripada dua screenshot terpisah.
5. **Rekam layar sejak awal.** Rekaman pengujian ini bisa langsung menjadi bahan video demo (10%), jadi tidak perlu mengulang semuanya.

### Langkah 2: jalankan tiap skenario
Cara memicu kondisi di Wokwi (berdasarkan pengalaman umum memakai Wokwi; pastikan nama tombolnya di simulator):
- **Gas:** klik sensor gas, lalu geser nilai gas ke atas.
- **Orang:** klik sensor PIR, lalu tekan tombol simulasi gerakan.
- **Reset:** klik push button.

| ID | Yang dilakukan | Yang diamati |
|---|---|---|
| TC1 | Biarkan simulasi berjalan ±10 detik tanpa menyentuh apa pun | Motor diam, buzzer diam. Dashboard: `AMAN`, `NORMAL`, `DIAM`, `DIAM`, `RELEASED`, diperbarui tiap 1 detik |
| TC2 | Naikkan nilai gas, **jangan** picu PIR | Motor berputar satu kali lalu berhenti, buzzer diam. Dashboard: `ADA_ASAP`, motor `BERPUTAR` |
| TC3 | Saat alarm masih aktif, picu PIR | Buzzer berbunyi. Dashboard: `GERAKAN_DETECTED`, `BUNYI` |
| TC4 | Turunkan nilai gas, lalu tekan tombol reset | Buzzer mati, motor berputar balik. Dashboard: `PRESSED`, lalu motor `DIAM` |

Ambil **screenshot di setiap skenario** saat kondisi yang diharapkan terlihat. Di TC4, turunkan gas **sebelum** menekan reset. Jika gas masih tinggi, sistem langsung masuk alarm lagi setelah reset, dan itu memang perilaku yang benar.

### Langkah 3: isi kolom Hasil Aktual dan Status
**Hasil Aktual** ditulis berdasarkan apa yang benar-benar terlihat, bukan disalin dari Hasil yang Diharapkan. Tulis singkat, konkret, dan sebutkan gambar buktinya.

Contoh jika berhasil:
> Motor berputar satu kali lalu berhenti, buzzer tidak berbunyi. Dashboard menampilkan ADA_ASAP dan motor BERPUTAR (Gambar 4.2).

Contoh jika gagal:
> Alarm tidak aktif saat nilai gas dinaikkan; dashboard tetap menampilkan AMAN. Penyebab: kabel sensor gas pada diagram.json terhubung ke pin yang tidak tersedia (mq2:A0).

**Status:** pakai dua nilai saja secara konsisten, misalnya **Berhasil** / **Gagal** (atau PASS / FAIL, asal tidak dicampur).

**Kemungkinan gagal yang sudah diketahui.** Versi Tsabit dipakai apa adanya, jadi dua skenario berisiko gagal (rincian di `pemahaman-proyek.md` bagian 6.1):
- **TC2:** sensor gas disambung ke `mq2:A0`, padahal pin itu tidak ada di sensor gas Wokwi.
- **TC4:** tombol disambung ke GND, padahal pin memakai pull-down, jadi pin selalu LOW dan reset tidak pernah terbaca.

Jika gagal, ada dua pilihan, dan tim yang memutuskan:
- Tulis **Gagal** dengan jujur, lengkap dengan penyebabnya. Laporan yang jujur tentang kegagalan tetap menunjukkan kemampuan debugging.
- Perbaiki wiring-nya dulu, lalu uji ulang. Perbaikannya cukup dua kabel di `diagram.json`.

**Jangan menulis Berhasil tanpa bukti screenshot.** Penguji bisa menjalankan link Wokwi sendiri.

### Langkah 4: isi bagian Screenshot dan Output
Ganti dua penanda di subbab *Screenshot dan Output*:
- `[SISIPKAN SCREENSHOT SERIAL MONITOR]`: Serial Monitor sampai baris `CONNECTED!`.
- `[SISIPKAN SCREENSHOT DASHBOARD SAAT ALARM AKTIF]`: dashboard (Colab atau HTML) saat `ADA_ASAP`, idealnya juga `BUNYI` (TC3).

Screenshot per skenario dari Langkah 2 boleh ditambahkan di bawahnya.

Aturan gambar yang umum dipakai di laporan akademik (`format.txt` tidak mengaturnya, jadi samakan dengan kebiasaan kampus Anda):
- Beri nomor dan keterangan **di bawah gambar**, misalnya *Gambar 4.1 Serial Monitor saat ESP32 terhubung ke broker*. Nomor mengikuti bab (4.1, 4.2, …).
- Potong (crop) bagian yang tidak relevan, tapi pastikan teks di gambar tetap terbaca.
- Sebut gambar di teks atau tabel ("lihat Gambar 4.2"), supaya penguji tahu gambar mana membuktikan apa.

### Langkah 5: isi Kesimpulan di Bab VI
Penanda `[ISI KESIMPULAN BERDASARKAN HASIL PENGUJIAN TC1 SAMPAI TC4]` diisi **setelah** tabel selesai. Cukup 2–3 kalimat: berapa skenario yang berhasil, skenario mana yang gagal beserta penyebabnya, dan apa artinya bagi sistem. Contoh:
> Dari empat skenario, TC1 sampai TC3 berhasil, sedangkan TC4 gagal karena wiring tombol reset. Hal ini menunjukkan logika deteksi dan aktuasi berjalan sesuai rancangan, sementara jalur reset perlu diperbaiki pada rangkaian.

---

## Bab V: Pembagian Peran Anggota

### Apa yang diminta brief
Brief hanya menyebut "Pembagian peran anggota", tetapi kontribusi dinilai **5%**. Penilai ingin melihat bahwa setiap anggota punya peran yang jelas dan nyata.

### Cara mengisi Tabel 5.1
Tabel punya tiga kolom: **Nama Anggota**, **Peran**, dan **Kontribusi**.
- **Nama Anggota:** nama lengkap, sama persis dengan yang tertulis di cover. Isi juga penanda anggota 2 dan 3 di cover.
- **Peran:** satu label singkat. Agar mudah dinilai, ikuti tahapan di brief (ideasi, device discovery, hardware design, programming, communication, testing, documentation), misalnya:
  - Hardware & Wiring (pemilihan komponen, rangkaian Wokwi)
  - Programming & Communication (sketch ESP32, MQTT)
  - Dashboard & Testing (Colab/HTML, skenario uji, video)
  - Dokumentasi (laporan, block diagram)
- **Kontribusi:** hal **konkret yang bisa dicek**, seperti file, bagian laporan, atau pengujian yang dikerjakan. Hindari kalimat umum seperti "membantu mengerjakan proyek".

Contoh format. Ini **bukan** pembagian yang sebenarnya; isi sesuai siapa mengerjakan apa:

| Nama Anggota | Peran | Kontribusi |
|---|---|---|
| [Nama] | Programming & Hardware | Membuat sketch.ino dan diagram.json di Wokwi, termasuk logika alarm dan komunikasi MQTT |
| [Nama] | Dokumentasi & Dashboard | Menyusun laporan Bab I–III, block diagram, dan menyiapkan dashboard Colab |
| [Nama] | Testing & Video | Menjalankan TC1–TC4, mengambil screenshot, dan merekam video demo |

Tips:
- Satu orang boleh punya lebih dari satu peran, tapi setiap anggota harus punya **minimal satu kontribusi yang jelas**.
- Peran yang ditulis harus konsisten dengan video demo, misalnya siapa yang menjelaskan bagian mana.
- Tulis dengan jujur. Penilai bisa bertanya langsung kepada anggota tentang bagian yang ia kerjakan.

---

## Checklist sebelum laporan dikumpulkan

| Bagian | Yang diisi |
|---|---|
| Tabel 4.1 | Hasil Aktual + Status untuk TC1–TC4, dengan rujukan gambar |
| Screenshot dan Output | Serial Monitor + dashboard saat alarm, diberi nomor dan keterangan |
| Bab VI Kesimpulan | 2–3 kalimat berdasarkan hasil tabel |
| Tabel 5.1 | Nama, peran, dan kontribusi konkret setiap anggota |
| Cover | Nama dan NIM/ID anggota 2 dan 3 |
| Lampiran | Link Wokwi final, link repository, link video demo |
