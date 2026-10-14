#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

const char *WIFI_SSID = "Wokwi-GUEST";
const char *WIFI_PASS = "";

// GANTI dengan URL publik tunnel (Cloudflare/ngrok) ke node utama kalian.
// URL tunnel berubah tiap kali di-restart — salin ulang ke KEEMPAT node.
const char *SERVER_URL = "https://printable-wrapping-pork-attitudes.trycloudflare.com";

#ifndef NODE_ID
#define NODE_ID "wokwi-1"
#endif

const char *MINER_ADDRESS = "esp8266-esp01";
const int MAX_BLOCKS = 64;

// Jeda antar polling (ms). Turunkan (mis. 1000) supaya LCD lebih cepat
// mengikuti, dengan konsekuensi request tunnel lebih sering. Naikkan (mis.
// 10000) kalau kena rate limit ngrok/Cloudflare. Ini knob kalibrasi demo.
const unsigned long POLL_MS = 2000;

LiquidCrystal_I2C lcd(0x27, 16, 2);

String g_prev[MAX_BLOCKS];
String g_hash[MAX_BLOCKS];
String g_index[MAX_BLOCKS];

int extractValues(const String &body, const String &key, String *out, int maxN)
{
  String pat = String("\"") + key + "\":";
  int count = 0;
  int pos = 0;
  while (count < maxN)
  {
    int i = body.indexOf(pat, pos);
    if (i < 0)
      break;
    i += pat.length();
    while (i < (int)body.length() && (body[i] == ' ' || body[i] == '\t'))
      i++;
    if (i >= (int)body.length())
      break;
    String v = "";
    if (body[i] == '"')
    {
      i++;
      while (i < (int)body.length() && body[i] != '"')
        v += body[i++];
    }
    else
    {
      while (i < (int)body.length() &&
             (isDigit(body[i]) || body[i] == '-' || body[i] == '.'))
        v += body[i++];
    }
    out[count++] = v;
    pos = i + 1;
  }
  return count;
}

int countKey(const String &body, const String &key)
{
  String pat = String("\"") + key + "\":";
  int c = 0;
  int pos = 0;
  while (true)
  {
    int i = body.indexOf(pat, pos);
    if (i < 0)
      break;
    c++;
    pos = i + pat.length();
  }
  return c;
}

// Verifikasi keterkaitan chain dari array yang sudah di-parse.
bool verifyChain(int n)
{
  if (n <= 0)
    return false;
  if (g_prev[0] != "0")
    return false; // genesis
  for (int i = 0; i < n; i++)
  {
    if (g_index[i].toInt() != i)
      return false; // index berurutan
    if (g_hash[i].length() == 0)
      return false;
    if (i > 0 && g_prev[i] != g_hash[i - 1])
      return false; // linkage
  }
  return true;
}

// Ambil saldo `<miner>` dari objek balances (mis. {"esp8266-esp01":50.0}).
float jsonBalance(const String &body, const String &miner)
{
  String tmp[1];
  // Miner belum muncul di balances (mis. tepat setelah genesis) = saldo 0.0,
  // bukan -1: LCD harus menampilkan "Bal:0.0" di kondisi awal, bukan "-1.0".
  if (extractValues(body, miner, tmp, 1) < 1)
    return 0.0;
  return tmp[0].toFloat();
}

void showOnLcd(int height, bool ok, float balance)
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(NODE_ID);
  lcd.print(" H:");
  lcd.print(height);
  lcd.setCursor(0, 1);
  lcd.print("Bal:");
  lcd.print(balance, 1);
  lcd.print(ok ? " OK" : " BAD");
}

// GET satu path; isi bodyOut bila HTTP 200.
// `client` & `http` statis: koneksi TLS dipakai ulang antar-poll (setReuse),
// jadi handshake mahal hanya sekali, bukan tiap 2 detik.
bool getPath(const String &path, String &bodyOut)
{
  static WiFiClientSecure client;
  static HTTPClient http;
  client.setInsecure(); // Cloudflare tunnel: lewati verifikasi CA
  String url = String(SERVER_URL) + path;
  if (!http.begin(client, url))
    return false;
  http.setReuse(true);
  int code = http.GET();
  if (code == 200)
  {
    bodyOut = http.getString();
  }
  else
  {
    // Diagnostik: tampilkan kode HTTP / pesan error supaya akar masalah terlihat.
    //  -1..-11  = gagal konek/TLS (lihat http.errorToString)
    //  502/530  = tunnel hidup tapi origin tak terjangkau
    //  404      = URL/path salah
    //  403      = diblok Cloudflare
    Serial.printf("[%s] GET %s -> %d (%s)\n",
                  NODE_ID, url.c_str(), code,
                  http.errorToString(code).c_str());
  }
  http.end();
  return code == 200;
}

void pollServer()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("[!] WiFi terputus");
    return;
  }

  // Satu request /snapshot = height + header blok + saldo sekaligus.
  // Menggantikan dua request (/chain lalu /status) yang dulu bikin LCD
  // menunggu dua TLS handshake berurutan.
  String body;
  int height = 0;
  bool ok = false;
  float balance = -1;

  if (getPath("/snapshot", body))
  {
    height = countKey(body, "index");
    if (height > 0 && height <= MAX_BLOCKS)
    {
      extractValues(body, "previous_hash", g_prev, MAX_BLOCKS);
      extractValues(body, "hash", g_hash, MAX_BLOCKS);
      extractValues(body, "index", g_index, MAX_BLOCKS);
      ok = verifyChain(height);
    }
    balance = jsonBalance(body, MINER_ADDRESS);
    Serial.printf("[%s] GET /snapshot -> %d blok, verifikasi %s\n",
                  NODE_ID, height, ok ? "OK" : "GAGAL");
  }
  else
  {
    Serial.printf("[%s] /snapshot tidak terjangkau\n", NODE_ID);
  }

  if (height > 0)
  {
    showOnLcd(height, ok, balance);
  }
  else
  {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(NODE_ID);
    lcd.setCursor(0, 1);
    lcd.print("Server offline");
  }
}

void setup()
{
  Serial.begin(115200);
  delay(300);
  Wire.begin(21, 22); // SDA=GPIO21, SCL=GPIO22
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print(NODE_ID);
  lcd.setCursor(0, 1);
  lcd.print("sync...");

  Serial.print("Menghubungkan WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nTerhubung: " + WiFi.localIP().toString());
}

void loop()
{
  pollServer();
  delay(POLL_MS);
}
