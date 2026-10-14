/*
 * ESP8266 Hardware Mining Trigger
 * ---------------------------------
 * Menghubungkan ESP8266 (NodeMCU) ke WiFi, lalu mengirim POST /trigger ke
 * server blockchain lokal. Setiap trigger menambang 1 blok dan memberi reward
 * coin ke alamat device ini.
 *
 * Tanpa komponen tambahan:
 *  - Tombol = tombol FLASH onboard (GPIO0 = D3, sudah pull-up di board).
 *  - LED    = LED onboard (GPIO2 = D4, aktif LOW).
 *
 * Cara pakai: lihat README.md di folder ini.
 * GANTI: alamat IP PC di jaringan WiFi yang sama.
 *
 * CATATAN: jangan menekan tombol FLASH saat board baru menyala / RST — GPIO0
 * LOW saat boot membuat ESP masuk mode flash, bukan menjalankan sketch.
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

// ================== KONFIGURASI (GANTI SESUAI JARINGAN) ==================
const char *WIFI_SSID = "UNAND5G";
const char *WIFI_PASS = "HardiknasDiAndalas";

// IP PC yang menjalankan server (hasil `ipconfig`). Jangan localhost!
const char *SERVER_URL = "http://10.44.52.168:5000/trigger";
const char *API_KEY = "dev-secret";
const char *DEVICE_ID = "esp01";
// =========================================================================

// Pakai nomor GPIO, bukan alias D3/D4: alias itu hanya ada bila board yang
// dipilih di Arduino IDE varian NodeMCU/Wemos. GPIO0/GPIO2 valid di semua varian.
const int BUTTON_PIN = 0; // tombol FLASH onboard (GPIO0 = D3)
const int LED_PIN = 2;    // LED onboard NodeMCU (GPIO2 = D4, aktif LOW)

void blink(int times)
{
  for (int i = 0; i < times; i++)
  {
    digitalWrite(LED_PIN, LOW);
    delay(120);
    digitalWrite(LED_PIN, HIGH);
    delay(120);
  }
}

bool sendTrigger()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("[!] WiFi terputus, mencoba konek ulang...");
    WiFi.reconnect();
    return false;
  }

  WiFiClient client;
  HTTPClient http;
  http.begin(client, SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  String body = String("{\"device\":\"") + DEVICE_ID +
                "\",\"miner\":\"esp8266-" + DEVICE_ID + "\"}";

  int code = http.POST(body);
  Serial.print("[trigger] HTTP ");
  Serial.println(code);
  if (code > 0)
  {
    Serial.println(http.getString());
  }
  http.end();

  if (code == 200)
  {
    blink(3);
    return true;
  }
  return false;
}

void setup()
{
  Serial.begin(115200);
  delay(200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH); // LED mati

  Serial.println();
  Serial.print("Menghubungkan ke WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Terhubung. IP device: ");
  Serial.println(WiFi.localIP());
  Serial.print("Target server: ");
  Serial.println(SERVER_URL);
  blink(2);
}

void loop()
{
  // Trigger hanya pada TEPI tekan (LOW -> baru), jadi satu klik = satu blok.
  bool pressed = (digitalRead(BUTTON_PIN) == LOW);
  static bool wasPressed = false;

  if (pressed && !wasPressed)
  {
    Serial.println("[tombol] memicu mining...");
    sendTrigger();
    delay(50); // debounce kontak
  }
  wasPressed = pressed;
}
