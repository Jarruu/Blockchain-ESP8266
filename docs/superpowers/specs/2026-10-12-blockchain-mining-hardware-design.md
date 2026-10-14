# Desain: Blockchain Lokal dengan Reward Mining & Trigger Hardware ESP8266

Tanggal: 2026-10-12 (revisi: arsitektur 1 node utama + 4 light node Wokwi)
Tugas: Pengganti UTS — Sistem Blockchain sederhana, reward cryptocurrency, distributed ledger, pemicu hardware.

## 1. Tujuan & Ruang Lingkup

Membangun sistem blockchain Proof-of-Work sederhana yang:

- Menerima **transaksi** dan menambang **blok** dengan reward coin.
- Menjalankan **distributed ledger**: 1 **node utama** (full node, Python)
  sebagai sumber kebenaran, dan 4 **node tambahan** hasil simulasi Wokwi
  sebagai *light node* yang membaca ledger.
- Dipicu oleh **hardware asli** (ESP8266) yang mengirim perintah mining ke
  node utama.
- Node utama **di-forward ke internet** lewat Cloudflare Tunnel agar node
  Wokwi (yang berjalan di cloud) dapat membacanya.
- Disertai **laporan** (studi literatur >= 5 sumber, arsitektur, hasil uji,
  analisis) dan **dokumentasi cara menjalankan**.

**Non-tujuan (YAGNI):** wallet dengan tanda tangan ECDSA, konsensus Byzantine
(PBFT/Raft), smart contract, mempool berbayar (fee), UI grafis. Semua ini dicatat
sebagai batasan sistem di laporan, bukan dikerjakan.

## 2. Keputusan yang Sudah Disepakati

| Topik | Keputusan |
|---|---|
| Hardware trigger | ESP8266 fisik (1 unit), WiFi + HTTP POST ke IP LAN |
| Server | Python + Flask |
| Node utama | 1 proses Python (port 5000), full node + PoW + reward |
| Node tambahan | 4 instance Wokwi ESP32 sebagai **light node** (read-only) |
| Akses node Wokwi | Node utama di-forward via **Cloudflare Tunnel** (HTTPS) |
| Dashboard | Tidak ada; cukup CLI + REST API + LCD node Wokwi |
| Deliverable | Kode jalan, dokumen laporan, dokumentasi cara menjalankan |

### Catatan teknis penting (jujur, masuk laporan)

1. **Wokwi berjalan di cloud, bukan di PC.** Simulasi tidak bisa menjangkau
   `localhost`. Karena itu node utama diekspos lewat Cloudflare Tunnel
   (`cloudflared tunnel --url http://localhost:5000`), yang memberi URL HTTPS
   publik tanpa akun.
2. **Node Wokwi hanya bisa keluar (outbound), tidak bisa dijemput.** Node dapat
   *menarik* chain (`GET /snapshot`) dan memverifikasi keterkaitannya, tetapi tidak
   dapat menerima koneksi masuk, sehingga tidak bisa *di-pull* peer lain. Karena
   itu ia **tidak bisa** menjadi full node yang berpartisipasi dalam konsensus
   longest-chain — ia berperan sebagai *light node* penyinkron + pemverifikasi.
3. **RAM terbatas.** ESP8266 hanya ~40–80 KB RAM; ESP32 di Wokwi juga terbatas.
   Keduanya tidak dirancang menyimpan chain penuh; verifikasi dibatasi
   `MAX_BLOCKS` blok. Ini batasan fisik yang dianalisis di laporan.
4. **Verifikasi TLS dilewati.** Klien Wokwi memakai `setInsecure()`, jadi
   sertifikat HTTPS tunnel tidak diverifikasi (tanpa CA bundle). Cukup untuk
   demo, dicatat sebagai batasan.

## 3. Arsitektur & Topologi

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
                     GET /status      GET /status      GET /status GET /status
```

- **Node utama** menjalankan seluruh logika: menerima transaksi, menambang
  blok (PoW), memberi reward coinbase, dan menyimpan chain ke disk.
- **4 node Wokwi** memanggil `GET /snapshot` tiap `POLL_MS` (default 2 detik) lewat tunnel,
  memverifikasi keterkaitan hash antar-blok (genesis, index berurutan, linkage
  `previous_hash`), lalu menampilkan tinggi chain + status verifikasi (`OK`/`BAD`)
  + saldo miner pada LCD. Mereka tidak menambang dan tidak menyimpan chain penuh.
  Verifikasi atas rantai hash, bukan pengulangan PoW (terlalu berat untuk MCU).
- **ESP8266 fisik** memicu mining lewat `POST /trigger` langsung ke IP LAN
  (tidak lewat tunnel, lebih andal).

Kode node (`node.py`) tetap mendukung mode multi-node Python (via `--peers` dan
`GET /nodes/resolve`) untuk keperluan pengujian konsensus; namun **topologi demo
yang dipakai adalah 1 node utama + 4 light node Wokwi** sesuai ketentuan tugas.

## 4. Komponen

| File | Tanggung jawab |
|---|---|
| `blockchain.py` | `Block`, `Blockchain`, PoW (SHA-256), validasi chain, longest-chain consensus, reward coinbase, persistensi JSON |
| `node.py` | Server Flask. 1 proses = node utama. CLI `--port --peers --difficulty --api-key --data-dir` |
| `benchmark.py` | Mengukur waktu mining vs difficulty, dan waktu konsensus antar-node (uji kode) |
| `tests/test_blockchain.py` | Self-check: genesis, PoW, deteksi tamper, konsensus, reward |
| `tests/test_node.py` | Uji REST API: status, mine, trigger API-key, validasi input, persistensi |
| `firmware/esp8266_trigger/` | Sketch Arduino ESP8266: WiFi + HTTP trigger + LED indikator |
| `firmware/wokwi_node-1..4/` | Proyek Wokwi: sketch (4 instance) + `diagram.json` light node |
| `README.md` | Cara menjalankan end-to-end |
| `laporan/LAPORAN.md` | Laporan lengkap (studi literatur, arsitektur, hasil, analisis) |

## 5. Model Data

```jsonc
// Block
{
  "index": 3,
  "timestamp": 1760000000.0,
  "transactions": [
    {"sender": "0", "recipient": "<alamat-miner>", "amount": 50.0, "type": "reward"},
    {"sender": "alice", "recipient": "bob", "amount": 10.0, "type": "transfer"}
  ],
  "previous_hash": "00ab...",
  "nonce": 41237,
  "hash": "0000c1..."
}
```

- Hash = SHA-256 dari `index|timestamp|json(transactions)|previous_hash|nonce`.
- Genesis block dibuat dengan `previous_hash = "0"` dan tanpa transaksi.
- Persistensi: `data/node_<port>.json` (chain) — tahan restart.

## 6. Aturan Inti

1. **PoW:** hash blok harus berawalan `difficulty` karakter `"0"` (default `4`).
2. **Reward:** setiap blok yang berhasil ditambang memberi `REWARD = 50 STRK`
   kepada `miner_address` sebagai transaksi coinbase (`sender: "0"`).
3. **Chain valid** bila: setiap blok `previous_hash` cocok dengan hash blok
   sebelumnya, dan hash tiap blok memenuhi PoW.
4. **Konsensus:** node memilih chain valid dengan panjang terbesar (longest-chain).
   Chain tidak valid diabaikan meskipun lebih panjang.

## 7. REST API (node utama)

| Method & Path | Fungsi |
|---|---|
| `GET /status` | id node, peer, tinggi chain, saldo, blok terakhir, difficulty |
| `GET /chain` | seluruh chain + panjang |
| `GET /snapshot` | gabungan `/chain`+`/status` untuk light node (satu request) |
| `POST /transactions/new` | tambah tx `{sender, recipient, amount}` |
| `POST /mine` | tambang blok (tx pending + reward) → kembalikan blok baru |
| `POST /trigger` | **pintu masuk hardware**; header `X-API-Key` wajib; body `{device, miner}`; menambang lalu broadcast |
| `POST /nodes/register` | daftarkan node/peer baru secara dinamis `{nodes: ["http://..."]}` |
| `GET /nodes/resolve` | jalankan konsensus dengan semua peer, ganti chain bila ada yang lebih panjang |

Node Wokwi memakai `GET /snapshot` (sinkronisasi + verifikasi + saldo dalam satu
request). ESP8266 hanya memakai `POST /trigger`.

## 8. Alur End-to-End

1. Node utama dinyalakan (`python node.py --port 5000`), chain mulai dari genesis.
2. Cloudflare Tunnel diekspos: `cloudflared tunnel --url http://localhost:5000`
   → URL HTTPS publik.
3. 4 node Wokwi (VS Code extension) dijalankan; URL tunnel diisi di
   `firmware/wokwi_config.ini` (satu tempat untuk keempat node), `NODE_ID`
   dibedakan tiap node (wokwi-1..4). Tiap node
   menampilkan `Height` + status verifikasi + `Bal`.
4. ESP8266 boot → konek WiFi → kirim `POST /trigger` dengan `X-API-Key` dan
   `miner` = alamat device ke IP LAN node utama.
5. Node utama memverifikasi API key → menambang blok baru (PoW + coinbase 50 STRK).
6. Pada polling berikutnya, keempat node Wokwi menampilkan tinggi chain yang
   naik dan saldo miner bertambah — bukti ledger terdistribusi terbaca dari
   luar jaringan lokal.
7. ESP8266 menerima respons JSON (index, hash, nonce, reward) → LED berkedip +
   log serial sebagai bukti fisik pemicu mining.

## 9. Penanganan Error & Batasan

- **API key salah/kosong** → `401`, mining tidak jalan.
- **Payload tidak valid** (field hilang, amount <= 0) → `400`.
- **Peer tidak dapat dijangkau** saat resolve → di-skip, dicatat di log; node tetap
  jalan (tidak crash).
- **Chain peer tidak valid** → diabaikan walau lebih panjang.
- **Tunnel mati / URL berubah** → node Wokwi menampilkan "Server offline";
  node utama tidak terpengaruh.
- **Keamanan:** alamat miner adalah string bebas tanpa tanda tangan kripto, jadi
  sistem tidak tahan terhadap pemalsuan identitas. Dicatat sebagai batasan.
- **Skala:** dirancang untuk demonstrasi kelas, bukan produksi.

## 10. Strategi Pengujian

- `tests/test_blockchain.py`:
  1. Genesis block valid dan tepat satu.
  2. Blok hasil mining memenuhi PoW.
  3. `is_chain_valid` mendeteksi manipulasi transaksi.
  4. Konsensus mengganti chain bila ada chain valid lebih panjang, dan menolak
     chain lebih panjang yang tidak valid.
  5. Reward coinbase bernilai tepat dan masuk ke alamat miner.
- `tests/test_node.py`: API status, mine, `/trigger` wajib API-key, validasi
  input 400, peer mati tidak crash, persistensi setelah restart.
- `benchmark.py`:
  - Waktu mining rata-rata pada difficulty 2, 3, 4, 5.
  - Waktu konsensus antar dua node Python (uji kode longest-chain).
  - Hasilnya jadi tabel di bab "Hasil & Analisis" laporan.
- Uji integrasi manual: ESP8266 fisik → `/trigger` → chain tumbuh; 4 node
  Wokwi → `GET /status` via tunnel → LCD naik.

## 11. Studi Literatur (>= 5 sumber, diisi lengkap di laporan)

1. Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash System* (whitepaper).
2. Antonopoulos, A. M. *Mastering Bitcoin* (Bab mining & konsensus).
3. Dokumentasi resmi Flask (flask.palletsprojects.com).
4. Dokumentasi Python `hashlib` (hashlib SHA-256).
5. Dokumentasi Wokwi (docs.wokwi.com) — WiFi & keterbatasan konektivitas simulasi.
6. Dokumentasi Espressif ESP8266 Arduino Core (WiFiClient / ESP8266HTTPClient).
7. Dokumentasi Cloudflare Tunnel (developers.cloudflare.com/cloudflare-one/connections/connect-networks/).
8. Dokumentasi Wokwi for VS Code (docs.wokwi.com/vscode/) — `wokwi.toml` + firmware terkompilasi; engine tetap di cloud pada akun free.
9. Dokumentasi PlatformIO (docs.platformio.org/) — build firmware ESP32 untuk dijalankan Wokwi.

## 12. Kriteria Sukses

- Node utama berjalan, mining menghasilkan blok dengan reward 50 STRK.
- ESP8266 fisik memicu mining lewat `POST /trigger` dan menerima respons sukses.
- 4 node Wokwi membaca ledger yang sama via Cloudflare Tunnel dan menampilkan
  tinggi chain + saldo yang konsisten dengan node utama.
- Ada bukti uji: output tes, tabel benchmark, screenshot serial ESP & LCD Wokwi.
- Laporan lengkap dengan >= 5 sumber dan bab analisis keterbatasan.
