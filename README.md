# Blockchain Lokal dengan Reward Mining & Trigger Hardware ESP8266

Sistem blockchain Proof-of-Work sederhana berbasis server lokal, dengan:

- **Reward coin** (`STRK`, 50 per blok) untuk penambang.
- **1 node utama** (full node Python + Flask) sebagai sumber kebenaran ledger.
- **4 node tambahan** hasil simulasi **Wokwi (ESP32)** sebagai *light node* yang
  membaca ledger lewat **Cloudflare Tunnel**.
- **Pemicu hardware asli** ESP8266 yang mengirim perintah mining ke node utama.

> Tugas Pengganti UTS — Sistem Blockchain. Lihat `laporan/LAPORAN.md` untuk
> laporan lengkap dan `docs/superpowers/specs/` untuk desain sistem.

## Struktur Proyek

```
blockchain.py            Logika inti: Block, PoW, reward, konsensus
node.py                  Node utama = server Flask (REST API)
benchmark.py             Uji performa mining & konsensus
tests/                   Unit test + uji integrasi API
firmware/esp8266_trigger/    Firmware ESP8266 fisik (pemicu mining)
firmware/wokwi_node-1..4/    Proyek Wokwi ESP32 (4 light node)
laporan/LAPORAN.md       Laporan lengkap
docs/bukti/              Output pengujian (benchmark, pytest)
```

## Prasyarat

- Python 3.10+
- Koneksi jaringan lokal (untuk ESP8266 fisik)
- `cloudflared` untuk mengekspos node utama ke node Wokwi

## Instalasi

```bash
pip install -r requirements.txt
```

## Menjalankan Node Utama

```bash
python node.py --port 5000 --difficulty 4
```

Node utama siap di `http://127.0.0.1:5000`.

## REST API

| Method & Path | Fungsi |
|---|---|
| `GET /status` | Info node: tinggi chain, peer, saldo, blok terakhir |
| `GET /chain` | Seluruh chain + panjangnya |
| `GET /snapshot` | Gabungan `/chain`+`/status` untuk light node (satu request) |
| `POST /transactions/new` | Tambah transaksi `{sender, recipient, amount}` |
| `POST /mine` | Tambang blok `{miner}` (reward 50 STRK ke miner) |
| `POST /trigger` | **Pemicu hardware**; header `X-API-Key` wajib |
| `POST /nodes/register` | Daftarkan peer baru `{nodes: ["http://..."]}` |
| `GET /nodes/resolve` | Konsensus longest-chain dengan semua peer |

Contoh:

```bash
# Tambang blok (reward ke kelompok6)
curl -X POST http://127.0.0.1:5000/mine \
     -H "Content-Type: application/json" -d "{\"miner\":\"kelompok6\"}"

# Picu seperti hardware
curl -X POST http://127.0.0.1:5000/trigger \
     -H "Content-Type: application/json" -H "X-API-Key: dev-secret" \
     -d "{\"device\":\"esp01\",\"miner\":\"esp8266-esp01\"}"

# Lihat status
curl http://127.0.0.1:5000/status
```

## Pengujian

```bash
python -m pytest -v                    # semua tes
python -m pytest tests/test_blockchain.py -v   # hanya inti
python blockchain.py                   # self-check cepat
```

## Benchmark

```bash
python benchmark.py
```

Menghasilkan tabel waktu mining (difficulty 2–5) dan waktu konsensus node,
ditulis ke `docs/bukti/benchmark.md`.

## Menghubungkan ESP8266

Ikuti `firmware/esp8266_trigger/README.md`. Ringkasnya: ganti `WIFI_SSID`,
`WIFI_PASS`, dan `SERVER_URL` (IP LAN PC, **bukan** `localhost`), lalu upload
dan buka Serial Monitor 115200.

## Node Simulasi Wokwi (4 node tambahan)

Ikuti `firmware/wokwi_node-1/README.md`. Ringkasnya (node Wokwi adalah **ESP32**,
dijalankan lewat **Wokwi for VS Code**):

1. Ekspos node utama: `cloudflared tunnel --url http://localhost:5000`.
2. Salin URL `https://....trycloudflare.com` ke baris `SERVER_URL` di **keempat**
   `src/sketch.ino` (`wokwi_node-1`..`wokwi_node-4`) — harus sama persis.
3. Build dengan `pio run` di tiap folder, lalu jalankan 4 node **Wokwi for VS
   Code** (4 window) dengan `NODE_ID` berbeda (`wokwi-1`..`wokwi-4`, sudah diatur
   via `build_flags` di `platformio.ini`).

Node Wokwi adalah **light node yang ikut sinkronisasi**: tiap `POLL_MS` (default
2 detik) menarik `GET /snapshot` (satu request berisi tinggi chain + header blok
+ saldo), memverifikasi keterkaitan hash antar-blok (`previous_hash` blok ke-i ==
`hash` blok ke-(i-1)), lalu menampilkan tinggi chain + status verifikasi
(`OK`/`BAD`) di LCD. Satu request per poll + TLS keep-alive (`setReuse`) memangkas
jeda LCD — dulu dua request `/chain`+`/status` berarti dua TLS handshake tiap
poll. Node Wokwi tetap tidak menambang dan tidak menyimpan chain penuh di disk
(RAM terbatas) — verifikasi hanya atas rantai hash, bukan mengulang PoW.

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `Address already in use` | Port 5000 dipakai proses lain. Pakai `--port 5001`. |
| ESP dapat `HTTP -1` | `SERVER_URL` harus IP LAN PC; pastikan ESP & PC satu WiFi (2.4 GHz); izinkan port 5000 di firewall Windows. |
| ESP dapat `HTTP 401` | `API_KEY` sketch != `--api-key` server. |
| Wokwi tidak konek | Pakai URL Cloudflare Tunnel (bukan `localhost`); pastikan `cloudflared` masih jalan. |
| Wokwi `Server offline` | URL tunnel berubah tiap restart `cloudflared` — salin ulang ke `SERVER_URL` di keempat `sketch.ino`, `pio run` ulang, lalu restart simulator (Wokwi memuat binary, bukan `.ino`). |
