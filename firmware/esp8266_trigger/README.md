# ESP8266 Hardware Trigger

Mikrokontroler ESP8266 (NodeMCU) bertindak sebagai **pemicu (trigger) proses
mining**. Setiap kali **tombol FLASH onboard** ditekan, device mengirim
`POST /trigger` ke server blockchain lokal, dan server menambang satu blok
dengan reward coin ke alamat device ini. Satu klik = satu blok (tidak ada
trigger otomatis).

## Alat & bahan

- 1x ESP8266 **NodeMCU** — tanpa komponen tambahan:
  - Tombol = **tombol FLASH** yang sudah ada di board (GPIO0 = `D3`).
  - LED = **LED onboard** (GPIO2 = `D4`, aktif LOW).
- Kabel micro-USB
- Arduino IDE + board package **esp8266 by ESP8266 Community**

## Langkah

1. **Cari IP PC** yang menjalankan server:
   - Windows: buka CMD, jalankan `ipconfig`, lihat `IPv4 Address` pada adapter WiFi.
   - Contoh: `192.168.1.10`.
   - Pastikan ESP8266 dan PC berada di **jaringan WiFi yang sama**.

2. **Jalankan node utama** di PC:
   ```
   python node.py --port 5000 --difficulty 4
   ```

3. **Edit sketch** `esp8266_trigger.ino`, ganti:
   - `WIFI_SSID`, `WIFI_PASS` → kredensial WiFi kalian
   - `SERVER_URL` → `http://<IP_PC>:5000/trigger`
   - `API_KEY` → samakan dengan `--api-key` server (default `dev-secret`)
   - `DEVICE_ID` → nama device, mis. `esp01`

4. **Upload** ke board:
   - Board: `NodeMCU 1.0 (ESP-12E Module)`
   - Port: pilih port COM device
   - Klik Upload.

5. **Buka Serial Monitor** (baud `115200`). Contoh output sukses:

   ```
   Terhubung. IP device: 192.168.1.55
   Target server: http://192.168.1.10:5000/trigger
   [tombol] memicu mining...
   [trigger] HTTP 200
   {"block":{...,"hash":"0000a1b2..."},"device":"esp01","height":2,...}
   ```

6. **Verifikasi** di PC bahwa chain bertambah:
   ```
   curl http://127.0.0.1:5000/status
   ```

## Tombol & LED — tanpa wiring

Tidak perlu merangkai apa pun:

| Fungsi | Pin | Komponen |
|---|---|---|
| Tombol trigger | GPIO0 (`D3`) | tombol **FLASH** onboard |
| Indikator sukses | GPIO2 (`D4`) | LED onboard (aktif LOW) |

> Sketch memakai **nomor GPIO** (`0` dan `2`), bukan alias `D3`/`D4`. Alias itu
> hanya ada kalau board yang dipilih di Arduino IDE varian NodeMCU/Wemos —
> kalau board lain, `D3`/`D4` error "not declared in this scope". Nomor GPIO
> selalu valid.

Sketch memakai `INPUT_PULLUP`; tombol FLASH onboard menarik GPIO0 ke GND saat
ditekan, sama seperti tombol eksternal. LED berkedip 3x tiap trigger sukses.

> ⚠️ **Jangan tekan tombol FLASH saat board baru menyala / ditekan RST** —
> GPIO0 LOW saat boot membuat ESP masuk mode flash, bukan menjalankan sketch.
> Tekan hanya setelah board berjalan (muncul "Terhubung. IP device: ...").

*Kalau tetap ingin tombol eksternal, rangkai `D3 → tombol → GND`; kodenya sama.*

## Troubleshooting

- **HTTP -1 / gagal konek**: cek `SERVER_URL` (harus IP LAN, bukan `127.0.0.1`),
  pastikan ESP & PC satu WiFi, dan firewall Windows mengizinkan port 5000.
- **HTTP 401**: `API_KEY` di sketch tidak sama dengan `--api-key` server.
- **WiFi tidak konek**: ESP8266 hanya mendukung WiFi 2.4 GHz, bukan 5 GHz.
- **`'D3' was not declared in this scope`**: board yang dipilih di Arduino IDE
  bukan varian NodeMCU. Pilih **NodeMCU 1.0 (ESP-12E Module)**, atau biarkan
  saja — sketch sudah memakai nomor GPIO sehingga tetap compile di board mana pun.
