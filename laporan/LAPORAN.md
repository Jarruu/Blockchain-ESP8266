# LAPORAN TUGAS PENGGANTI UTS
## Sistem Blockchain Sederhana dengan Reward Cryptocurrency, Distributed Ledger (1 Node Utama + 4 Light Node Wokwi), dan Pemicu Hardware ESP8266

**Mata Kuliah:** Strategi Teknologi
**Semester:** 7

---

## 1. Pendahuluan

### 1.1 Latar Belakang

Blockchain adalah ledger terdistribusi yang menyimpan data secara berantai
dan diamankan dengan kriptografi. Setiap blok memuat hash blok sebelumnya,
sehingga mengubah satu blok akan merusak seluruh rantai setelahnya. Mekanisme
*Proof of Work* (PoW) memaksa penambang melakukan kerja komputasi sebelum
sebuah blok dianggap sah, dan sebagai imbalannya penambang menerima reward
berupa coin.

Tugas ini bertujuan membangun sistem blockchain sederhana di server lokal yang
mendemonstrasikan: (a) pembuatan blok dan penambangan (mining), (b) pemberian
reward coin, (c) distributed ledger yang dapat dibaca banyak node, dan (d)
integrasi perangkat keras asli sebagai pemicu proses mining.

### 1.2 Tujuan

1. Merancang dan membangun blockchain PoW lokal dengan reward coin.
2. Mengimplementasikan distributed ledger dengan 1 node utama (full node) dan
   4 node tambahan hasil simulasi Wokwi sebagai light node.
3. Mengintegrasikan mikrokontroler ESP8266 sebagai pemicu mining.
4. Menguji performa (waktu mining) dan menganalisis keterbatasan sistem.

### 1.3 Batasan Masalah

Sistem dirancang untuk keperluan demonstrasi akademik, bukan produksi. Batasan
yang disengaja: tanpa tanda tangan digital (ECDSA), tanpa smart contract, dan
tanpa mekanisme konsensus Byzantine.

---

## 2. Studi Literatur

Berikut referensi (9 sumber) yang menjadi dasar perancangan sistem.

1. **Nakamoto, S. (2008). _Bitcoin: A Peer-to-Peer Electronic Cash System_.**
   Whitepaper asli Bitcoin. Menjadi dasar konsep rantai blok yang saling
   terhubung melalui hash, Proof of Work, dan konsensus rantai terpanjang
   (*longest chain rule*) yang diterapkan pada sistem ini.

2. **Antonopoulos, A. M. (2017). _Mastering Bitcoin_ (2nd ed.). O'Reilly.**
   Menjelaskan detail struktur blok, fungsi hash kriptografis, proses mining,
   dan penyesuaian difficulty. Menjadi rujukan implementasi field blok
   (`index`, `timestamp`, `transactions`, `previous_hash`, `nonce`, `hash`).

3. **Dokumentasi resmi Flask — https://flask.palletsprojects.com/.**
   Rujukan untuk membangun REST API server lokal (routing, `jsonify`,
   `request.get_json`, test client) yang menjadi antarmuka tiap node.

4. **Dokumentasi resmi Python — modul `hashlib`.**
   https://docs.python.org/3/library/hashlib.html. Rujukan implementasi
   SHA-256 sebagai fungsi hash blok dan dasar Proof of Work.

5. **Dokumentasi Wokwi — https://docs.wokwi.com/.**
   Rujukan untuk simulasi node tambahan berbasis ESP32 dan penjelasan
   keterbatasan konektivitas simulasi (tidak dapat mengakses `localhost`,
   hanya koneksi keluar).

6. **Espressif ESP8266 Arduino Core — https://arduino-esp8266.readthedocs.io/.**
   Rujukan penggunaan `ESP8266WiFi`, `WiFiClient`, dan `ESP8266HTTPClient`
   untuk mengirim HTTP request dari mikrokontroler ke server lokal.

7. **Dokumentasi Cloudflare Tunnel — https://developers.cloudflare.com/cloudflare-one/.**
   Rujukan cara mengekspos server lokal ke internet dengan URL HTTPS publik
   (`cloudflared tunnel --url`), sehingga node Wokwi dapat menjangkau node utama.
8. **Dokumentasi Wokwi for VS Code — https://docs.wokwi.com/vscode/.**
   Rujukan menjalankan simulasi dari VS Code (file `wokwi.toml` + firmware
   terkompilasi) dan penegasan bahwa engine simulasi tetap berjalan di cloud
   pada akun free.
9. **Dokumentasi PlatformIO — https://docs.platformio.org/.**
   Rujukan toolchain build firmware ESP32 (`platformio.ini`, `lib_deps`) yang
   menghasilkan binary untuk dijalankan Wokwi.

---

## 3. Arsitektur Sistem

### 3.1 Topologi

```
   [ESP8266 fisik] --POST /trigger (X-API-Key, IP LAN)--> NODE UTAMA :5000
    (pemicu mining)                                        Flask + Blockchain
                                                           PoW + Reward + /status
                                                                  ^
                                                                  | Cloudflare Tunnel
                                                                  | (HTTPS)
                          +----------------+----------------+-----+-----+
                          |                |                |           |
                     [Wokwi-1]        [Wokwi-2]        [Wokwi-3]   [Wokwi-4]
                     light node       light node       light node  light node
                     GET /snapshot     GET /snapshot     GET /snapshot  GET /snapshot
                     (+ verifikasi)   (+ verifikasi)   (+verifikasi)(+verifikasi)
```

Sistem terdiri atas tiga lapisan:

1. **Perangkat keras (ESP8266)** — pemicu mining, mengirim `POST /trigger`.
2. **Node utama (Flask)** — logika blok, mining, reward, dan REST API; satu-satunya
   full node yang menyimpan dan menambang chain.
3. **Node tambahan (Wokwi)** — 4 light node yang menarik chain lewat Cloudflare
   Tunnel, memverifikasi keterkaitan hash antar-blok, dan menampilkan tinggi
   chain + status verifikasi + saldo pada LCD.

### 3.2 Skema Komunikasi

| Dari | Ke | Protokol | Endpoint |
|---|---|---|---|
| ESP8266 | Node utama | HTTP POST + `X-API-Key` | `/trigger` |
| Wokwi light node | Node utama (via tunnel) | HTTPS GET | `/snapshot` (chain + saldo, satu request) |
| Node Python (uji) | Node Python lain | HTTP GET | `/chain` (via `/nodes/resolve`) |

### 3.3 Struktur Data Blok

```json
{
  "index": 3,
  "timestamp": 1760000000.0,
  "transactions": [
    {"sender": "0", "recipient": "esp8266-esp01", "amount": 50.0, "type": "reward"}
  ],
  "previous_hash": "00ab...",
  "nonce": 41237,
  "hash": "0000c1..."
}
```

Hash blok dihitung sebagai:

```
sha256("{index}|{timestamp}|{transactions_json}|{previous_hash}|{nonce}")
```

### 3.4 Konsensus

Node mengadopsi chain milik peer hanya jika chain tersebut **valid** dan
**lebih panjang** (longest-chain rule). Chain tidak valid selalu ditolak
meskipun lebih panjang.

---

## 4. Implementasi

### 4.1 Komponen

| File | Tanggung jawab |
|---|---|
| `blockchain.py` | Block, PoW (SHA-256), validasi chain, konsensus, reward, persistensi |
| `node.py` | Server Flask node utama + REST API + peer |
| `benchmark.py` | Pengukuran performa mining & konsensus |
| `firmware/esp8266_trigger/` | Firmware pemicu mining (hardware asli) |
| `firmware/wokwi_node-1/` … `wokwi_node-4/` | Node simulasi Wokwi (4 light node) |

### 4.2 Proof of Work

Blok ditambang dengan menaikkan `nonce` hingga hash memenuhi target
`difficulty` karakter nol di depan. Optimasi: bagian header yang statis
dihitung sekali agar hashing tidak mengulang serialisasi JSON tiap iterasi.

### 4.3 Reward

Setiap blok yang berhasil ditambang menambahkan transaksi coinbase:

```
{sender: "0", recipient: <alamat-miner>, amount: 50.0, type: "reward"}
```

Saldo tiap alamat dihitung dari seluruh transaksi di chain: penerima bertambah,
pengirim berkurang, dan `sender == "0"` (coinbase) hanya menambah.

### 4.4 Distributed Ledger

Node utama menyimpan chain dan menambang blok. Ledger didistribusikan ke 4 node
tambahan Wokwi yang berperan sebagai *light node* **yang ikut sinkronisasi**:
setiap `POLL_MS` (default 2 detik) mereka menarik snapshot ledger (`GET
/snapshot`) lewat Cloudflare Tunnel, **memverifikasi keterkaitan hash
antar-blok**, lalu menampilkan tinggi chain + status verifikasi + saldo miner di
LCD. Node Wokwi tidak menambang dan tidak menyimpan chain penuh ke disk (lihat
keterbatasan di §6.2). Satu request `/snapshot` memuat header blok + saldo
sekaligus, menggantikan dua request `/chain`+`/status` yang sebelumnya berarti
dua TLS handshake per polling.

Verifikasi yang dilakukan tiap light node:

1. `previous_hash` blok genesis == `"0"`.
2. `index` blok berurutan `0,1,2,...`.
3. `previous_hash` blok ke-i == `hash` blok ke-(i-1) (linkage).

Bila salah satu tautan putus (chain di-tamper), LCD menampilkan `BAD`. Yang
dicek adalah **rantai hash**, bukan pengulangan PoW — menghitung ulang SHA-256
tiap blok butuh mereplikasi serialisasi header persis dan terlalu berat untuk
MCU (dicatat di §6.2).

Kode `node.py` juga menyediakan `POST /nodes/register` dan `GET /nodes/resolve`
(longest-chain) untuk konsensus penuh antar proses Python.

### 4.5 Integrasi Hardware

ESP8266 terhubung ke WiFi, lalu mengirim HTTP POST ke `/trigger` dengan header
`X-API-Key`. Server memverifikasi API key, menambang blok, dan mengembalikan
JSON berisi hash blok serta reward. LED pada device berkedip saat sukses.

---

## 5. Hasil Pengujian

### 5.1 Unit Test

```bash
python -m pytest -v
```

Hasil: **20 passed** (lihat `docs/bukti/pytest.txt`).

Cakupan pengujian (`tests/test_blockchain.py` 9 tes, `tests/test_node.py` 8 tes,
`tests/test_chain_contract.py` 3 tes):

- Genesis valid dan tunggal.
- Blok hasil mining memenuhi PoW.
- Manipulasi transaksi terdeteksi (`is_chain_valid` = False).
- Reward masuk ke alamat penambang dengan nilai tepat.
- Transfer menggeser saldo.
- Konsensus menerima chain valid lebih panjang, menolak chain tidak valid.
- API: trigger tanpa API key → 401; JSON rusak → 400; amount ≤ 0 → 400.
- Peer mati saat resolve tidak membuat node crash (tetap HTTP 200).
- Chain bertahan setelah restart (persistensi).
- Kontrak JSON `/snapshot` cocok dengan parser & verifier sketch Wokwi (3 tes).

### 5.2 Konsensus antar-Node (Uji Kode)

Konsensus longest-chain diuji dua lapis: unit test `replace_chain`
(`tests/test_blockchain.py`) dan `benchmark.py`, yang menyalakan dua node Python
(port 5200/5201), menambang 10 blok di node sumber, lalu mengukur waktu node
kedua mengejar chain via `/nodes/resolve`. Hasilnya: node kedua mencapai tinggi
chain yang sama dengan sumber, membuktikan mekanisme konsensus bekerja.

### 5.3 Sinkronisasi & Verifikasi Ledger oleh 4 Light Node Wokwi

Node utama diekspos lewat Cloudflare Tunnel. Empat instance Wokwi menarik
`GET /snapshot` tiap `POLL_MS` (default 2 detik), memverifikasi keterkaitan hash
antar-blok, lalu menampilkan tinggi chain + status (`OK`/`BAD`) + saldo miner
pada LCD. Bukti berupa screenshot keempat LCD (`docs/bukti/wokwi_*.png` — **tempel
sebelum dikumpul**). Setelah
mining dipicu hardware, tinggi chain dan saldo miner pada keempat LCD naik pada
polling berikutnya dengan status `OK` — membuktikan ledger yang sama
**tersinkron dan terverifikasi** dari luar jaringan lokal.

Verifikasi negatif juga diuji di tingkat kode: `tests/test_chain_contract.py`
meniru parser & verifier sketch terhadap output Flask asli, dan memastikan
tautan chain yang sengaja diputus terdeteksi (`BAD`).

### 5.4 Benchmark

```bash
python benchmark.py
```

Hasil lengkap: `docs/bukti/benchmark.md`. Ringkasan (13 Oktober 2026):

| difficulty | rata-rata detik/blok |
|---|---|
| 2 | 0.0006 |
| 3 | 0.0030 |
| 4 | 0.0763 |
| 5 | 1.1365 |

| blok | detik konsensus |
|---|---|
| 10 | 0.049 |

Waktu mining naik tajam seiring bertambahnya difficulty: dari 0.0006 detik
(difficulty 2) menjadi 1.14 detik (difficulty 5) — sekitar 1.900 kali lebih
lambat. Kenaikan antar-tingkat berkisar 5–15 kali, mendekati faktor teoretis
16 kali (probabilitas hash memenuhi target = 16^-difficulty). Konsensus 10 blok
antar dua node di jaringan lokal selesai dalam 0.049 detik.

### 5.5 Pengujian Hardware ESP8266

Serial Monitor (115200) saat tombol ditekan. Salinan output lengkap disimpan di
`docs/bukti/serial_esp.txt`. Bentuk output:

```
Menghubungkan ke WiFi: <SSID>
Terhubung. IP device: 192.168.1.55
Target server: http://192.168.1.10:5000/trigger
[tombol] memicu mining...
[trigger] HTTP 200
{"block":{...,"hash":"0000a1b2...","index":1},"device":"esp01","reward":50.0,"height":2}
```

> ⚠️ **Wajib diisi sebelum dikumpul:** tempel output Serial Monitor asli (bukan
> contoh di atas) ke `docs/bukti/serial_esp.txt`, lalu jalankan demo sekali lagi
> untuk memastikan angka `height` pada output sesuai dengan kondisi awal chain.

---

## 6. Analisis dan Keterbatasan

### 6.1 Analisis Performa

- **Waktu mining tumbuh eksponensial terhadap difficulty.** Setiap penambahan
  satu karakter nol di depan menaikkan jumlah percobaan hash rata-rata 16 kali
  lipat. Ini sesuai teori (probabilitas = 16^-difficulty).
- **Konsensus cepat untuk skala kecil.** Dengan chain pendek dan peer di
  jaringan lokal, node mengejar chain utama dalam hitungan detik.
- **Latensi pembacaan light node.** Node Wokwi polling tiap `POLL_MS` (default
  2 detik), sehingga perubahan ledger terlihat dengan jeda ≤2 detik.

### 6.2 Keterbatasan

1. **Longest-chain tidak deterministik saat seri.** Jika dua node menambang
   blok bersamaan dengan panjang sama, konsensus bergantung urutan resolusi.
   Solusi produksi: tie-break deterministik atau protokol seperti Nakamoto
   dengan akumulasi kerja.
2. **Tanpa tanda tangan kripto.** Alamat miner hanya string bebas, sehingga
   identitas dapat dipalsukan. Sistem produksi memerlukan ECDSA dan wallet.
3. **Wokwi hanya bisa koneksi keluar (outbound).** Node Wokwi dapat *menarik*
   chain (`GET /snapshot`) dan memverifikasi keterkaitannya, tetapi tidak dapat
   menerima koneksi masuk, sehingga tidak bisa *di-pull* peer lain. Karena itu
   ia **tidak bisa menjadi full node** yang berpartisipasi dalam konsensus
   longest-chain; konsensus penuh antar-node tetap diuji dengan proses Python.
4. **Verifikasi light node atas rantai hash, bukan PoW.** Light node memeriksa
   `previous_hash`/`index` (linkage) tetapi tidak menghitung ulang SHA-256 tiap
   blok, karena itu butuh mereplikasi serialisasi header persis dan terlalu
   berat untuk MCU. Konsekuensinya, PoW tidak divalidasi ulang di sisi Wokwi.
5. **Wokwi tidak dapat mengakses `localhost`.** Simulasi berjalan di cloud,
   sehingga butuh tunnel publik (Cloudflare/ngrok). Ini membuat node Wokwi
   bergantung pada tunnel yang bisa mati/berubah URL, sehingga lebih rapuh
   untuk demo langsung dibanding node Python.
6. **RAM terbatas.** ESP8266 hanya ~40–80 KB RAM dan ESP32 di Wokwi juga
   terbatas, sehingga device embedded tidak dirancang menyimpan chain penuh.
   Verifikasi dibatasi `MAX_BLOCKS = 64` blok; di luar itu node menandai `BAD`
   (jujur "tidak sanggup memverifikasi"), bukan memotong chain diam-diam.
7. **Verifikasi sertifikat TLS dilewati.** Klien Wokwi memakai `setInsecure()`
   sehingga sertifikat HTTPS tunnel tidak diverifikasi (tanpa CA bundle).
   Cukup untuk demo, tetapi bukan praktik aman untuk produksi.
8. **Tanpa mekanisme fee dan mempool prioritas.** Transaksi diproses
   berdasarkan urutan kedatangan.
9. **Skala demo.** Sistem dirancang untuk demonstrasi kelas, bukan beban
   produksi; belum diuji dengan ratusan node atau chain panjang.

---

## 7. Kesimpulan

Sistem blockchain sederhana dengan reward coin berhasil dibangun dan diuji:
penambangan blok berbasis Proof of Work berjalan dan reward 50 STRK diberikan ke
penambang. Distributed ledger diimplementasikan dengan 1 node utama (full node
Python) sebagai sumber kebenaran, dan 4 node tambahan hasil simulasi Wokwi
sebagai light node yang membaca ledger lewat Cloudflare Tunnel. Perangkat keras
asli (ESP8266) berhasil memicu proses mining melalui endpoint `/trigger`
ber-API-key, sedangkan keterbatasan Wokwi (hanya koneksi keluar dan RAM kecil)
dianalisis sebagai alasan peran light node.

Pengujian menunjukkan konsensus longest-chain bekerja sebagaimana mestinya,
termasuk penolakan terhadap chain tidak valid. Keterbatasan utama terletak pada
ketiadaan tanda tangan kripto, non-determinisme konsensus saat seri, dan
keterbatasan fisik perangkat embedded — yang semuanya menjadi arah
pengembangan lanjutan.
