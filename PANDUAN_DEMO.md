# Panduan Demo (Praktik Langsung)

Panduan mendemokan sistem di depan kelas / saat rekam video.
Perkiraan waktu: **12–15 menit**.

Arsitektur: **1 node utama (Python) + 4 light node Wokwi (ESP32) + 1 ESP8266 fisik**.
Node utama diekspos ke internet lewat **Cloudflare Tunnel** supaya node Wokwi bisa
menarik chain dan memverifikasinya.

---

## Persiapan (sebelum penonton masuk / sebelum rekam)

### 0.1 Install dependensi (sekali saja)

```bash
pip install -r requirements.txt
```

### 0.2 Tes cepat bahwa sistem hidup

```bash
python -m pytest -v
```
Harus **20 passed**. Kalau ada yang merah, jangan lanjut — perbaiki dulu.

### 0.3 Bersihkan data lama (supaya demo mulai dari genesis)

```bash
# Windows (Git Bash)
rm -rf data/
# Windows (CMD)
rmdir /s /q data
```

### 0.4 Nyalakan node utama

Buka **Terminal 1**:

```bash
python node.py --port 5000
```

Yang harus terlihat:
```
[node] http://127.0.0.1:5000  peers=[]
 * Running on http://0.0.0.0:5000
```

> ⚠️ **Jalankan versi terbaru `node.py`.** Endpoint `/snapshot` yang dipakai node
> Wokwi baru muncul setelah server dijalankan ulang. Kalau server lama masih
> jalan, LCD akan menampilkan `Server offline`.

### 0.5 Buka tunnel ke internet

Buka **Terminal 2**:

```bash
cloudflared tunnel --url http://localhost:5000
```
Salin URL `https://....trycloudflare.com` yang muncul.

> ⚠️ **Urutan penting:** server (0.4) harus hidup dulu, baru tunnel. Kalau tunnel
> dijalankan sebelum server, request balas 502.

### 0.6 Build & jalankan 4 node Wokwi (ESP32)

Node Wokwi adalah **ESP32** (board `esp32dev`), dijalankan lewat **Wokwi for VS
Code** — bukan ESP8266, dan bukan Wokwi browser.

**Satu URL untuk keempat node.** URL tunnel dari 0.5 di-hardcode di baris
`SERVER_URL` **tiap** `src/sketch.ino` — keempatnya harus sama persis:

```cpp
const char *SERVER_URL = "https://<url-tunnel-kalian>.trycloudflare.com";
```

Edit di keempat node (`wokwi_node-1` s/d `wokwi_node-4`), lalu build tiap node

Buka **4 window VS Code** (folder `wokwi_node-1` .. `wokwi_node-4`), masing-masing
**F1 → "Wokwi: Start Simulator"**. `NODE_ID` (`wokwi-1`..`wokwi-4`) sudah diatur di
`build_flags` tiap `platformio.ini` — tidak perlu diubah. Keempat LCD harus
menampilkan `wokwi-N  H:1` dan `Bal:0.0 OK`.

### 0.7 Siapkan hardware ESP8266

- ESP8266 (NodeMCU) sudah di-flash firmware `firmware/esp8266_trigger/`.
- `WIFI_SSID`, `WIFI_PASS`, `SERVER_URL` di sketch **sudah disesuaikan** dengan
  WiFi kelas + IP laptop kalian.
- **Tanpa wiring tambahan:** tombol = tombol FLASH onboard (`D3`/GPIO0), LED = LED
  onboard (`D4`/GPIO2). Mining **hanya** saat tombol ditekan.
- Colok ke USB, buka **Serial Monitor** Arduino IDE (baud **115200**). Tunggu
  sampai muncul:
  ```
  Terhubung. IP device: 192.168.1.55
  Target server: http://192.168.1.10:5000/trigger
  ```

### 0.8 Susun tata letak layar (penting untuk demo serentak)

Atur supaya **ketiganya terlihat bersamaan** di satu layar:

```
┌───────────────────────┬───────────────────────┐
│ Terminal 1: node.py   │ Serial Monitor ESP    │
│ (ledger / server)     │ (tekan tombol di sini)│
├───────────────────────┼───────────────────────┤
│ Wokwi 1 │ Wokwi 2     │ Wokwi 3 │ Wokwi 4     │
│ (4 LCD, H & saldo)    │                     │
└───────────────────────┴───────────────────────┘
```

- 1 monitor: bagi jadi 4 kuadran (`Win + ←/→` untuk split, `Win + Z` snap layout).
- Proyektor + laptop: tampilkan server & Wokwi di proyektor, pegang ESP8266 di
  tangan untuk menekan tombol.

### 0.9 Catat IP laptop kalian

```bash
ipconfig
```
Lihat **IPv4 Address** pada adapter WiFi, mis. `192.168.1.10`. Ini yang dipakai ESP.
⚠️ WiFi kelas sering berubah IP — cek ulang tepat sebelum demo.

---

## Buka (skrip pembuka — 30 detik)

👉 **Narasi:**

> *"Selamat pagi/siang. Kami mendemokan sistem blockchain Proof-of-Work
> sederhana dengan tiga lapis yang sekarang sudah hidup semua di layar: satu
> **node utama** Python yang menyimpan ledger penuh, empat **light node** simulasi
> Wokwi yang ikut menyinkronkan dan memverifikasi ledger dari luar jaringan, dan
> satu **perangkat keras asli** — ESP8266 — sebagai pemicu mining. Yang penting:
> **tidak ada mining manual**. Blok baru lahir hanya saat tombol hardware ditekan.
> Perhatikan ketiga layar ini bersamaan."*

⏸️

---

## Demo Utama — Satu Tekanan Tombol, Tiga Layar Berubah (8 menit)

Ini inti demo. Ketiga layar sudah hidup (lihat Persiapan). Di sini hanya:
**tunjukkan kondisi awal → tekan tombol → tunjukkan ketiganya berubah bersamaan
→ ulangi beberapa kali.**

### Langkah 1 — Tunjukkan kondisi awal di ketiga layar

**A. Ledger di node utama** (Terminal 1, atau Terminal 3 baru):

```bash
curl http://127.0.0.1:5000/status
```

**B. Hardware** — Serial Monitor ESP sudah menunjukkan:
```
Terhubung. IP device: 192.168.1.55
Target server: http://192.168.1.10:5000/trigger
```

**C. Keempat LCD Wokwi** — semua menampilkan `wokwi-N  H:1` dan `Bal:0.0 OK`.

👉 **Narasi:**

> *"Perhatikan tiga layar sekaligus. Kiri atas, node utama — server Flask penyimpan
> seluruh chain. Tingginya **satu**: cuma blok genesis, belum ada transaksi dan
> reward. Kanan atas, ESP8266 sudah terhubung ke WiFi yang sama. Di bawah, keempat
> LCD Wokwi — semua menunjukkan tinggi satu, saldo nol, status `OK`. ⏸️ Ledger masih
> kosong di ketiga tempat. Sekarang saya tekan tombolnya."*

### Langkah 2 — Tekan tombol FLASH → lihat tiga layar berubah

Tekan **tombol FLASH onboard** di ESP8266 **sekali**. Lalu perhatikan ketiganya,
urut:

**A. Serial Monitor** langsung menampilkan:
```
[tombol] memicu mining...
[trigger] HTTP 200
{"block":{...,"hash":"0000a1b2..."},"device":"esp01","reward":50.0,"height":2}
```
LED onboard berkedip **3x**.

**B. Ledger di node utama** (jalankan `curl` lagi):
```bash
curl http://127.0.0.1:5000/status
```
`height` naik dari 1 → 2, saldo `esp8266-esp01` bertambah 50.

**C. Keempat LCD Wokwi** — dalam **≤2 detik**, `H:1` → `H:2` dan `Bal:0.0` →
`Bal:50.0` di **semua** LCD, status tetap `OK`.

👉 **Narasi:**

> *"Saya tekan tombol FLASH di board ESP8266. ⏸️ Perhatikan ketiganya bersamaan. **Pertama**, di Serial Monitor,
> device mengirim `POST /trigger` ke server dengan API key, server balas HTTP 200,
> dan LED berkedip tiga kali sebagai konfirmasi fisik. **Kedua**, di node utama,
> tinggi chain naik dari satu ke dua, saldo `esp8266-esp01` bertambah lima puluh —
> reward masuk ke alamat device. **Ketiga**, di keempat LCD Wokwi, dalam dua detik
> tinggi chain ikut naik dan saldo ikut bertambah, status tetap `OK`. ⏸️ Jadi satu
> tekanan tombol di hardware langsung terlihat di ketiga lapis: perangkat keras,
> node utama, dan keempat light node."*

### Langkah 3 — Ulangi beberapa kali (tunjukkan konsistensi)

Tekan tombol **2–3 kali lagi** dengan jeda. Setiap kali, tunjukkan ketiga layar ikut
berubah bersamaan:

```bash
curl http://127.0.0.1:5000/status
```
`height` naik terus (3, 4, 5…), saldo bertambah 50 tiap blok, keempat LCD ikut naik
di tiap tekanan.

👉 **Narasi:**

> *"Saya tekan lagi — dua, tiga kali. ⏸️ Perhatikan: setiap **satu** klik
> menghasilkan tepat **satu** blok baru dengan reward lima puluh. Tinggi chain
> naik, saldo bertambah, dan keempat LCD ikut bergerak di setiap tekanan. Ini
> membuktikan dua hal: **pertama**, pemicu mining benar-benar perangkat keras asli
> — bukan perintah manual; **kedua**, ledger di node utama tersinkron dan
> terverifikasi oleh empat light node di luar jaringan lokal. Tiap blok terhubung
> ke blok sebelumnya lewat `previous_hash`, membentuk rantai."*

### Langkah 4 — Jelaskan apa yang diverifikasi keempat light node

👉 **Narasi:**

> *"Sekilas soal keempat node Wokwi. Mereka **bukan** penambang — mereka **light
> node**. Tiap dua detik mereka menarik snapshot ledger lewat Cloudflare Tunnel,
> lalu memverifikasi keterkaitan hash antar-blok: blok pertama harus genesis dengan
> `previous_hash` nol, index harus berurutan nol, satu, dua, dan seterusnya, dan
> `previous_hash` blok ke-i harus sama dengan `hash` blok sebelumnya. Kalau satu
> tautan putus — misalnya ledger diubah diam-diam — statusnya langsung jadi `BAD`.
> ⏸️ Karena Wokwi hanya bisa koneksi keluar dan RAM-nya terbatas, mereka jadi
> penyinkron dan pemverifikasi ledger, bukan penambang. Ini batasan yang kami
> analisis di laporan."*

### Langkah 5 — Bukti bahwa verifikasi benar-benar mendeteksi manipulasi

Menunjukkan verifier **tidak** asal bilang `OK`. Test kontrak mensimulasikan chain
yang di-tamper lalu memastikan ditolak:

```bash
python tests/test_chain_contract.py
```

👉 **Narasi:**

> *"Sebagai bukti verifikasi tadi bukan sekadar tampilan, saya jalankan test ini.
> Dia membangun chain valid, lalu sengaja memutuskan satu tautan hash — persis
> seperti ledger yang diubah diam-diam. Verifier langsung menolaknya. Jadi kalau
> ada yang mencoba memalsukan blok, keempat light node akan menampilkan `BAD`,
> bukan `OK`."*

---

## Bagian Pendukung — Benchmark (opsional, 2 menit)

Kalau masih ada waktu. Di Terminal 3:

```bash
python benchmark.py
```
Keluar tabel waktu mining per difficulty + waktu konsensus.

👉 **Narasi:**

> *"Sebagai pelengkap, kita ukur performanya. Benchmark ini menambang rata-rata
> lima blok di tiap tingkat difficulty, dari dua sampai lima. Lihat polanya: tiap
> kali difficulty naik satu, waktu mining naik sekitar **enam belas kali lipat**.
> Kenapa enam belas? Karena target-nya angka heksadesimal — satu digit tambahan
> berarti enam belas kali lebih banyak kemungkinan yang harus dicoba. Ini sesuai
> teori probabilitas, sekaligus menunjukkan kenapa difficulty empat seimbang untuk
> demo: cukup berat untuk terasa sebagai Proof-of-Work, tapi tidak bikin menunggu
> lama."*

> Catatan: benchmark ini menambang lewat `POST /mine` (bukan hardware) karena
> tujuannya mengukur performa PoW murni di berbagai tingkat difficulty. Ini alat
> ukur laboratorium, bukan bagian dari alur demo utama.

---

## Penutup (skrip penutup — 30 detik)

👉 **Narasi:**

> *"Kesimpulannya: kami membangun blockchain Proof-of-Work dengan reward coin, di
> mana mining **hanya** bisa dipicu oleh perangkat keras asli — bukan perintah
> manual. Satu tekanan tombol di ESP8266 langsung terlihat di node utama dan di
> keempat light node simulasi secara bersamaan, membuktikan ledger tersinkron dan
> terverifikasi dari luar jaringan lokal. Integritas rantai hash-nya juga terbukti
> tahan manipulasi. Sekian demo kami, terima kasih."*

⏸️

---

## Kartu Contekan (cue card — pegang saat tampil)

**Urutan klik, 6 baris:**

1. **Tunjuk layar** → "kondisi awal: H:1, saldo 0, status OK."
2. **Tekan tombol FLASH 1x** → tunjuk Serial Monitor, node utama, 4 LCD.
3. **Tekan 2–3x lagi** → "satu klik = satu blok, reward 50."
4. **Jelaskan** → light node verifikasi linkage hash, bukan menambang.
5. **(opsional)** `python tests/test_chain_contract.py` → verifier menolak chain di-tamper.
6. **(opsional)** `python benchmark.py` → "difficulty naik 1 = mining ~16x lebih lambat."

**Kalimat kunci yang wajib keluar:**

- "Tidak ada mining manual — hanya tombol hardware."
- "Satu tekanan tombol, tiga layar berubah serentak."
- "Keempat light node memverifikasi linkage hash; kalau diputus → `BAD`."

**Angka yang harus benar:** genesis `H:1`; tiap blok reward **50 STRK**; LCD update
**≤2 detik**; difficulty demo **4**; total test **20 passed**.

---

## Checklist Cepat Sebelum Demo

- [ ] `pip install -r requirements.txt` sudah dijalankan
- [ ] `python -m pytest` → **20 passed**
- [ ] `data/` sudah dihapus (mulai dari genesis)
- [ ] `node.py` versi terbaru sudah di-restart (endpoint `/snapshot` aktif)
- [ ] `cloudflared` sudah jalan & URL-nya sudah disalin ke `SERVER_URL` di **keempat** `sketch.ino`
- [ ] PlatformIO terpasang & `pio run` sukses di tiap `firmware/wokwi_node-*`
- [ ] 4 window VS Code Wokwi siap (`NODE_ID` = wokwi-1..4), semua LCD tampil `H:1`
- [ ] IP laptop dicek ulang (`ipconfig`) & sudah diganti di sketch ESP
- [ ] ESP8266 & laptop di WiFi yang sama (2.4 GHz!)
- [ ] Firewall Windows mengizinkan port 5000 (kalau ESP gagal konek)
- [ ] Serial Monitor ESP terbuka (baud 115200), sudah muncul "Terhubung"
- [ ] **Tata letak layar sudah disusun** — ketiga layar terlihat bersamaan (0.8)
- [ ] Laptop terisi daya / tercolok

---

## Troubleshooting Saat Demo

| Gejala | Penyebab | Solusi cepat |
|---|---|---|
| `Address already in use` | Port 5000 dipakai proses lama | Tutup terminal lama, atau `--port 5001` |
| ESP `HTTP -1` | Salah IP / beda WiFi / firewall | Cek `ipconfig`, samakan WiFi, izinkan port 5000 |
| ESP `HTTP 401` | API key beda | Samakan `API_KEY` sketch dengan `--api-key` server |
| Wokwi tidak konek | tunnel mati / URL berubah | Restart `cloudflared`, salin URL baru ke `SERVER_URL` keempat sketch, `pio run` ulang |
| Wokwi `Server offline` | `/snapshot` balas 404 → server lama belum restart | Restart `python node.py`, cek Serial Monitor |
| Wokwi `Server offline` | URL tunnel beda setelah restart | Salin ulang URL ke `SERVER_URL` keempat sketch, `pio run` ulang |
| Wokwi `Server offline` padahal URL sudah benar | simulator masih memuat binary lama | Tutup tab simulator, `pio run` ulang bila perlu, F1 → "Wokwi: Start Simulator" lagi |
| Wokwi `Server offline` | URL tunnel beda antar-node (satu node di-update, lainnya tidak) | Cek `SERVER_URL` di **keempat** sketch — harus sama persis |
| Wokwi lambat berubah | `POLL_MS` besar / tunnel lambat | Turunkan `POLL_MS` (mis. 1000) di `sketch.ino` |
| Wokwi ext: "firmware not found" | Belum `pio run` | Jalankan `pio run`, cek path di `wokwi.toml` |
| Wokwi ext: board tak cocok | `diagram.json` bukan `esp32-devkit-c-v4` | Samakan board di `diagram.json` & `platformio.ini` |
| `ModuleNotFoundError` | Dependensi belum install | `pip install -r requirements.txt` |

> **Cara cepat baca Serial Monitor Wokwi.** `getPath()` mencetak kode HTTP tiap
> request gagal:
> - `GET /snapshot -> 404` → server lama masih jalan, restart `node.py`.
> - `GET /snapshot -> -1` (atau negatif lain) → gagal konek/TLS: cek tunnel & WiFi.
> - `GET /snapshot -> 502/530` → tunnel hidup tapi server origin mati.
> - `GET /snapshot -> 200` tapi LCD tetap offline → server yang jalan bukan versi terbaru.

---

## Urutan Demo Paling Aman (kalau waktu mepet)

Semua sudah hidup dari Persiapan — tinggal pilih mana yang ditunjukkan:

1. **Langkah 1–3** — kondisi awal → tekan tombol → tiga layar berubah (wajib, inti tugas)
2. **Langkah 4** — penjelasan light node & verifikasi (cepat)
3. **Bagian Pendukung (benchmark)** — angka untuk laporan, hanya kalau waktu ada
4. **Langkah 5** — bukti anti-manipulasi, hanya kalau waktu ada

> **Penegasan:** seluruh mining dalam demo dilakukan lewat ESP8266. Tidak ada
> penambangan manual lewat `curl /mine` supaya ketentuan "hardware wajib sebagai
> pemicu" terpenuhi secara nyata di depan penguji.
