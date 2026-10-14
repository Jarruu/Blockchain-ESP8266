# Wokwi Light Node (4 Node Tambahan)

Empat node tambahan hasil **simulasi Wokwi**, berperan sebagai **light node
yang ikut sinkronisasi**: tiap node menarik SELURUH chain dari node utama
(`GET /snapshot`), **memverifikasi keterkaitan blok**, lalu menampilkan tinggi
chain + status verifikasi (`OK`/`BAD`) + saldo miner di LCD 16x2 dan Serial.
Mereka **tidak menambang** dan **tidak menyimpan chain penuh ke disk**.

## Apa yang diverifikasi light node?

Setiap polling (`POLL_MS`, default 2 detik), node mem-parse array blok dari
`/snapshot` dan memeriksa:

1. Genesis: `previous_hash` blok pertama == `"0"`.
2. `index` blok berurutan `0,1,2,...`.
3. **Linkage**: `previous_hash` blok ke-i == `hash` blok ke-(i-1).

Kalau ada satu tautan yang putus (chain di-tamper/di-edit), LCD menampilkan
`BAD` — inilah bukti nyata bahwa node tambahan ikut menyinkronkan & memvalidasi
ledger, bukan sekadar membaca angka.

> **Cakupan:** yang dicek adalah **rantai hash (linkage)**, bukan mengulang
> Proof of Work. Menghitung ulang SHA-256 tiap blok butuh mereplikasi
> serialisasi header persis dan terlalu berat untuk MCU. Ini dicatat sebagai
> batasan di laporan.

## Kenapa light node, bukan full node?

1. **Wokwi berjalan di cloud, bukan di PC.** Baik versi browser maupun
   **VS Code extension** (free tier) menjalankan engine simulasi di cloud dan
   hanya bisa keluar ke internet publik — tidak bisa menjangkau `localhost`.
   Untuk menyentuh node utama dibutuhkan **Cloudflare Tunnel**
   (`cloudflared tunnel --url http://localhost:5000`) yang memberi URL HTTPS
   publik gratis. *(Engine lokal "offline mode" hanya untuk langganan Pro.)*
2. **Wokwi hanya bisa koneksi keluar (outbound).** Ia tidak dapat menerima
   koneksi masuk, sehingga tidak bisa *di-pull* peer lain lewat `GET /chain`.
   Node ini menarik chain (pull), tapi tidak bisa jadi peer yang ditarik.
3. **Keterbatasan RAM.** ESP8266 hanya ~40–80 KB RAM dan ESP32 terbatas;
   keduanya tidak dirancang menyimpan chain penuh. Karena itu verifikasi dibatasi
   `MAX_BLOCKS` blok; di luar itu ditandai `BAD` (jujur "tidak sanggup
   memverifikasi"), bukan dipotong diam-diam.

Node utama (proses Python di PC) adalah full node yang menyimpan penuh dan
menambang chain. Keempat node Wokwi membuktikan ledger itu **tersinkron dan
terverifikasi dari luar jaringan lokal**.

## Isi folder

| File | Fungsi |
|---|---|
| `sketch.ino` | Program light node: `GET /snapshot` + verifikasi tiap `POLL_MS`, tampil di LCD |
| `diagram.json` | Rangkaian Wokwi: ESP32 DevKit + LCD1602 (mode I2C) |
| `platformio.ini` | Build config PlatformIO (board `esp32dev`, lib LCD I2C) |
| `wokwi.toml` | Config **Wokwi for VS Code**: menunjuk firmware hasil build |

## Cara menjalankan (Wokwi for VS Code)

> **Wokwi for VS Code TIDAK meng-compile `.ino` sendiri.** Kita build dulu
> dengan PlatformIO, lalu Wokwi menjalankan binary hasilnya.

### 0. Prasyarat

- Ekstensi **Wokwi Simulator** + **PlatformIO IDE** terpasang di VS Code.
- Akun Wokwi **free** sudah cukup (butuh internet; engine jalan di cloud).

### 1. Ekspos node utama ke internet (Cloudflare Tunnel)

Jalankan di PC (node utama harus sudah jalan di port 5000):

```bash
cloudflared tunnel --url http://localhost:5000
# -> salin URL seperti https://random-words-here.trycloudflare.com
```

Alternatif: `ngrok http 5000` (juga jalan — cukup isi URL-nya di sketch).
Cloudflare lebih disarankan karena tidak ada halaman peringatan untuk request
API dan tidak perlu akun.

### 2. Isi URL di tiap sketch

Edit `src/sketch.ino`, ganti baris ini di **keempat** node (`wokwi_node-1` s/d
`wokwi_node-4`):

```cpp
const char* SERVER_URL = "https://GANTI-TUNNEL-CLOUDFLARE.trycloudflare.com";
```

### 3. Build & jalankan satu node

```bash
pio run                    # compile -> .pio/build/esp32dev/firmware.bin
```

Lalu di VS Code: **F1 → "Wokwi: Start Simulator"**. LCD akan menampilkan
`wokwi-1  H:<n>` / `Bal:<x> OK`.

### 4. Jalankan 4 node sekaligus

Wokwi for VS Code membuka satu simulator per workspace, jadi untuk 4 node:

- Salin folder ini 4x (mis. `wokwi-1/` .. `wokwi-4/`), atau buka 4 VS Code
  window berbeda dengan folder yang sama.
- Buka folder ke-N sebagai workspace, lalu ubah `NODE_ID` di `platformio.ini`
  (`build_flags = -D NODE_ID=\"wokwi-N\"`) — **tidak perlu edit sketch**.
- `pio run` + F1 → Start Simulator di tiap window.

Keempatnya menarik chain yang sama dan menampilkan tinggi + status verifikasi
yang konsisten.

### 5. Amati hasil

LCD menampilkan `<NODE_ID>` + `H:<tinggi chain>` di baris pertama dan
`Bal:<saldo>` + `OK`/`BAD` di baris kedua. Picu mining dari ESP8266 fisik, maka
angka tinggi chain di keempat LCD akan naik pada polling berikutnya (≤`POLL_MS`).
Status `OK` berarti rantai hash blok-blok yang ditarik tersambung benar.

> **Catatan:** kalau tetap ingin cara browser, isi `sketch.ino` + `diagram.json`
> bisa ditempel ke [wokwi.com](https://wokwi.com) seperti biasa — logikanya sama.

## Catatan teknis

- **Verifikasi TLS dilewati.** Sketch memakai `client.setInsecure()` sehingga
  sertifikat HTTPS tunnel tidak diverifikasi (tanpa CA bundle). Cukup untuk demo.
- **Wokwi Private IoT Gateway** (agar device Wokwi mengakses server lokal tanpa
  tunnel publik, hostname `host.wokwi.internal`) memerlukan akun Wokwi Club
  berbayar. Cara tunnel publik di atas cukup dan gratis.
- **URL tunnel berubah** tiap kali `cloudflared` direstart — salin ulang ke
  `src/sketch.ino` **keempat** node lalu `pio run` ulang bila node menampilkan
  "Server offline".
