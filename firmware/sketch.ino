/*
 * EMSafe - Monitor EMF + Alertas (Safe/Caution/Danger) + Actuador
 * Equipo GAUSS | UPC - Desarrollo de Soluciones IoT
 *
 * Embebido (ESP32): sensor A3144 (custom chip, ADC GPIO34) + LED RGB semaforo
 *   + rele que simula el enchufe inteligente (corta en DANGER, con histeresis).
 * Envia un data record por cambio de nivel o enchufe (anti-saturacion).
 *
 * Sistema de alertas:
 *   SAFE    (verde)    -> campo < 100 uT
 *   CAUTION (amarillo) -> 100 - 200 uT
 *   DANGER  (rojo)     -> >= 200 uT  (corta el enchufe)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>

// ---------- WiFi ----------
#define WIFI_SSID      "Wokwi-GUEST"
#define WIFI_PASSWORD  ""

// ---------- Endpoint (por ahora Beeceptor; luego cambia a la URL del edge) ----------
#define ENDPOINT_URL   "https://iot-edge-202610-6766-flizano.free.beeceptor.com/api/v1/data_records"

// ---------- NTP (Peru UTC-5) ----------
const char* NTP_SERVER     = "pool.ntp.org";
const long  GMT_OFFSET_SEC = -5 * 3600;
const int   DST_OFFSET_SEC = 0;

// ---------- Dispositivo ----------
#define DEVICE_ID      "EMSAFE-6766-01"
#define EMF_PIN        34        // OUT del custom chip -> GPIO34 (ADC)

// LED RGB (catodo comun -> HIGH = encendido)
#define LED_R  27
#define LED_G  25
#define LED_B  26
#define LED_ON  HIGH
#define LED_OFF LOW

// Rele = enchufe inteligente
#define RELE_PIN 32
#define RELE_ON  HIGH            // energiza -> equipo ENCENDIDO
#define RELE_OFF LOW             // corta    -> equipo APAGADO

#define ADC_MAX               4095.0
#define FIELD_MAX_UT          1000.0

// Umbrales del sistema de alertas (uT)
#define UMBRAL_CAUTION_UT     100.0
#define UMBRAL_DANGER_UT      200.0
#define UMBRAL_HISTERESIS_UT  150.0   // reconecta el enchufe por debajo de esto

#define INTERVALO_MS          1000
#define MIN_POST_INTERVAL_MS  3000

unsigned long ultimaLectura  = 0;
unsigned long ultimoPost     = 0;
String        nivelEnviado   = "";
bool          enchufeOn      = true;
bool          enchufeEnviado = true;
int           enviosTotales  = 0;

void setColor(bool r, bool g, bool b) {
  digitalWrite(LED_R, r ? LED_ON : LED_OFF);
  digitalWrite(LED_G, g ? LED_ON : LED_OFF);
  digitalWrite(LED_B, b ? LED_ON : LED_OFF);
}

String timestampActual() {
  struct tm t;
  char buf[25];
  if (!getLocalTime(&t)) return String("");
  strftime(buf, sizeof(buf), "%d/%m/%Y %H:%M:%S", &t);
  return String(buf);
}

bool wifiOK() {
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 8000) delay(200);
  return WiFi.status() == WL_CONNECTED;
}

void enviarDataRecord(float campo_uT, const String& nivel, bool plugOn) {
  if (!wifiOK()) {
    Serial.println("  [POST] WiFi no disponible, se omite envio.");
    return;
  }

  JsonDocument doc;
  doc["deviceId"] = DEVICE_ID;
  doc["field_uT"] = round(campo_uT * 10) / 10.0;
  doc["level"]    = nivel;                 // SAFE / CAUTION / DANGER
  doc["plug"]     = plugOn ? "ON" : "OFF";
  doc["time"]     = timestampActual();

  String payload;
  serializeJson(doc, payload);

  HTTPClient http;
  http.begin(ENDPOINT_URL);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(payload);

  enviosTotales++;
  Serial.print("  [POST #"); Serial.print(enviosTotales);
  Serial.print("] -> ");     Serial.print(payload);
  Serial.print("  | HTTP ");  Serial.println(code);

  if (code > 0) {
    String respuesta = http.getString();
    JsonDocument resp;
    if (!deserializeJson(resp, respuesta)) {
      const char* msg = resp["message"];
      if (msg) { Serial.print("  [EDGE] "); Serial.println(msg); }
    }
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);
  pinMode(RELE_PIN, OUTPUT);
  setColor(false, false, false);
  digitalWrite(RELE_PIN, RELE_ON);   // equipo energizado al inicio

  Serial.println();
  Serial.println("==================================================");
  Serial.println("  EMSafe | Alertas Safe/Caution/Danger + Enchufe");
  Serial.print  ("  Device: "); Serial.println(DEVICE_ID);
  Serial.println("==================================================");

  WiFi.mode(WIFI_STA);
  wifiOK();
  configTime(GMT_OFFSET_SEC, DST_OFFSET_SEC, NTP_SERVER);

  struct tm t;                       // espera breve a NTP (hora en 1er registro)
  unsigned long t0 = millis();
  while (!getLocalTime(&t) && millis() - t0 < 5000) delay(200);
}

void loop() {
  if (millis() - ultimaLectura < INTERVALO_MS) return;
  ultimaLectura = millis();

  int   raw      = analogRead(EMF_PIN);
  float campo_uT = (raw / ADC_MAX) * FIELD_MAX_UT;

  // Sistema de alertas + semaforo
  String nivel;
  if (campo_uT < UMBRAL_CAUTION_UT) {
    nivel = "SAFE";    setColor(false, true,  false);  // verde
  } else if (campo_uT < UMBRAL_DANGER_UT) {
    nivel = "CAUTION"; setColor(true,  true,  false);  // amarillo
  } else {
    nivel = "DANGER";  setColor(true,  false, false);  // rojo
  }

  // Actuador: corta el enchufe en DANGER, con histeresis
  if (campo_uT >= UMBRAL_DANGER_UT) {
    enchufeOn = false;
  } else if (campo_uT < UMBRAL_HISTERESIS_UT) {
    enchufeOn = true;
  }
  digitalWrite(RELE_PIN, enchufeOn ? RELE_ON : RELE_OFF);

  // Consola local
  Serial.print("[");        Serial.print(DEVICE_ID);
  Serial.print("] raw=");   Serial.print(raw);
  Serial.print("  campo="); Serial.print(campo_uT, 1);
  Serial.print(" uT  alerta="); Serial.print(nivel);
  Serial.print("  enchufe="); Serial.println(enchufeOn ? "ON" : "OFF");

  // Envio: solo si cambio el nivel O el enchufe (anti-saturacion)
  bool cambio = (nivel != nivelEnviado) || (enchufeOn != enchufeEnviado);
  bool intervaloOk = (nivelEnviado == "") || (millis() - ultimoPost > MIN_POST_INTERVAL_MS);
  if (cambio && intervaloOk) {
    enviarDataRecord(campo_uT, nivel, enchufeOn);
    nivelEnviado   = nivel;
    enchufeEnviado = enchufeOn;
    ultimoPost     = millis();
  }
}
