// Maquete ESP32-WROOM-32. Nao usar em transito real.
// Arduino-ESP32 3.x: WiFi, WebServer, Update e LEDC pertencem ao core.
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Update.h>
#include <cstring>
#include "TrafficController.h"
#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#endif

using namespace crossing;
constexpr uint8_t NS_RED = 25, NS_YELLOW = 26, NS_GREEN = 27;
constexpr uint8_t EW_RED = 32, EW_YELLOW = 33, EW_GREEN = 14;
constexpr uint8_t PED_RED = 16, PED_GREEN = 17;
constexpr uint8_t GATE_NS = 18, GATE_EW = 19, BUZZER = 13, SIGN_WAIT = 21;
constexpr uint8_t DETECTOR_NS = 34, DETECTOR_EW = 35; // entradas com pulldown EXTERNO
constexpr uint8_t PED_BUTTON = 22, MAINTENANCE_SWITCH = 23; // ativos em LOW
constexpr uint32_t SERVO_CLOSED_US = 1000, SERVO_OPEN_US = 2000;

WebServer server(80);
TrafficController controller;
bool pwmReady = false;
bool pedestrianPending = false;
bool uploadActive = false;
bool rebootPending = false;
uint32_t rebootAt = 0;
Phase previousPhase = Phase::AllRed;

struct UploadState {
  bool authorized = false;
  bool started = false;
  bool succeeded = false;
  bool failed = false;
  String error;
} uploadState;

bool maintenanceArmed() { return digitalRead(MAINTENANCE_SWITCH) == LOW; }
bool otaKeyConfigured() {
  return strlen(OTA_KEY) >= 32 && strncmp(OTA_KEY, "CHANGE", 6) != 0;
}
bool keyMatches(const String &candidate) {
  const size_t size = strlen(OTA_KEY);
  if (candidate.length() != size) return false;
  uint8_t difference = 0;
  for (size_t i = 0; i < size; ++i) difference |= candidate[i] ^ OTA_KEY[i];
  return difference == 0;
}

void servoPulse(uint8_t pin, bool open) {
  if (!pwmReady) return;
  const uint32_t micros = open ? SERVO_OPEN_US : SERVO_CLOSED_US;
  ledcWrite(pin, (micros * 16383UL) / 20000UL); // 50 Hz, 14 bits
}

void writeOutputs(crossing::Output out, uint32_t now) {
  if (!out.valid() || !pwmReady) {
    controller.fault(now);
    out = Output{};
  }
  // Apagar permissivos ANTES de liberar qualquer nova direcao.
  digitalWrite(NS_GREEN, LOW); digitalWrite(EW_GREEN, LOW); digitalWrite(PED_GREEN, LOW);
  digitalWrite(NS_YELLOW, LOW); digitalWrite(EW_YELLOW, LOW);
  digitalWrite(NS_RED, HIGH); digitalWrite(EW_RED, HIGH); digitalWrite(PED_RED, HIGH);
  servoPulse(GATE_NS, out.nsGateOpen);
  servoPulse(GATE_EW, out.ewGateOpen);
  digitalWrite(NS_RED, out.ns == Light::Red);
  digitalWrite(EW_RED, out.ew == Light::Red);
  digitalWrite(NS_YELLOW, out.ns == Light::Yellow);
  digitalWrite(EW_YELLOW, out.ew == Light::Yellow);
  digitalWrite(NS_GREEN, out.ns == Light::Green);
  digitalWrite(EW_GREEN, out.ew == Light::Green);
  const bool walking = out.pedestrian == Pedestrian::Walk;
  const bool clearing = out.pedestrian == Pedestrian::Clear;
  digitalWrite(PED_RED, !walking); // vermelho de espera tambem durante a limpeza
  digitalWrite(PED_GREEN, walking);
  digitalWrite(BUZZER, walking && (now / 250) % 2 == 0); // buzzer ativo, sinal didatico
  digitalWrite(SIGN_WAIT, pedestrianPending || maintenanceArmed()
      || controller.phase() == Phase::Fault || (clearing && (now / 500) % 2 == 0));
}

void failUpload(const String &reason) {
  if (uploadState.started && !uploadState.succeeded) Update.abort();
  uploadState.failed = true;
  uploadState.error = reason;
  uploadActive = false;
}

void uploadChunk() {
  HTTPUpload &upload = server.upload();
  if (upload.status == UPLOAD_FILE_START) {
    uploadState = UploadState{};
    if (!otaKeyConfigured() || !keyMatches(server.header("X-OTA-Key"))) {
      failUpload("Chave ausente ou invalida.");
      return;
    }
    uploadState.authorized = true;
    if (!maintenanceArmed() || !controller.isMaintenance()) {
      failUpload("Armar manutencao e aguardar todos os sinais vermelhos.");
      return;
    }
    const String origin = server.header("Origin");
    if (origin.length() && origin != String("http://") + server.header("Host")) {
      failUpload("Origem rejeitada.");
      return;
    }
    uploadActive = true;
    if (!Update.begin(UPDATE_SIZE_UNKNOWN, U_FLASH)) {
      failUpload("Nao foi possivel iniciar OTA; conferir particoes e tamanho.");
      return;
    }
    uploadState.started = true;
  } else if (upload.status == UPLOAD_FILE_WRITE) {
    if (!uploadState.started || uploadState.failed) return;
    if (!maintenanceArmed()) { failUpload("Manutencao desarmada durante upload."); return; }
    if (Update.write(upload.buf, upload.currentSize) != upload.currentSize)
      failUpload("Falha na escrita do firmware.");
  } else if (upload.status == UPLOAD_FILE_END) {
    if (!uploadState.started || uploadState.failed) return;
    if (!maintenanceArmed()) { failUpload("Manutencao desarmada durante upload."); return; }
    if (!Update.end(true)) { failUpload("Imagem invalida ou gravacao incompleta."); return; }
    uploadState.succeeded = true;
    uploadActive = false;
  } else if (upload.status == UPLOAD_FILE_ABORTED) {
    failUpload("Upload interrompido; reenvie uma imagem valida.");
  }
}

void setupServer() {
  const char *headers[] = {"X-OTA-Key", "Origin", "Host"};
  server.collectHeaders(headers, 3);
  server.on("/status", HTTP_GET, []() {
    server.sendHeader("Cache-Control", "no-store");
    server.send(200, "application/json", String("{\"phase\":\"MAINTENANCE\",\"ota_enabled\":")
                + (otaKeyConfigured() ? "true" : "false") + ",\"scope\":\"maquete didatica\"}");
  });
  server.on("/update", HTTP_POST, []() {
    server.sendHeader("Connection", "close");
    server.sendHeader("Cache-Control", "no-store");
    if (!otaKeyConfigured() || !keyMatches(server.header("X-OTA-Key"))) {
      server.send(401, "text/plain", "Chave invalida."); return;
    }
    if (rebootPending) { server.send(409, "text/plain", "Reinicio ja agendado."); return; }
    if (!uploadState.authorized) { server.send(401, "text/plain", "Chave invalida."); return; }
    if (!uploadState.succeeded || uploadState.failed) {
      server.send(400, "text/plain", uploadState.error.length() ? uploadState.error : "Sem imagem valida.");
      uploadState = UploadState{};
      return;
    }
    server.send(200, "text/plain", "Firmware gravado. Reiniciando com sinais vermelhos.");
    rebootPending = true;
    rebootAt = millis() + 800;
  }, uploadChunk);
  server.onNotFound([]() { server.send(404, "text/plain", "Use GET /status ou POST /update."); });
  server.begin();
}

void setup() {
  Serial.begin(115200);
  const uint8_t outputs[] = {NS_RED, NS_YELLOW, NS_GREEN, EW_RED, EW_YELLOW, EW_GREEN,
                             PED_RED, PED_GREEN, BUZZER, SIGN_WAIT};
  for (uint8_t pin : outputs) { pinMode(pin, OUTPUT); digitalWrite(pin, LOW); }
  digitalWrite(NS_RED, HIGH); digitalWrite(EW_RED, HIGH); digitalWrite(PED_RED, HIGH);
  pinMode(DETECTOR_NS, INPUT); pinMode(DETECTOR_EW, INPUT);
  pinMode(PED_BUTTON, INPUT_PULLUP); pinMode(MAINTENANCE_SWITCH, INPUT_PULLUP);
  const bool nsPwm = ledcAttach(GATE_NS, 50, 14);
  const bool ewPwm = ledcAttach(GATE_EW, 50, 14);
  pwmReady = nsPwm && ewPwm;
  writeOutputs(Output{}, millis());
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 10000) delay(20);
  setupServer();
  Serial.println("Territorio Alerta | somente maquete; OTA exige chave e chave fisica de manutencao.");
  Serial.print("IP local: "); Serial.println(WiFi.localIP());
  Serial.println(pwmReady ? "PWM configurado." : "FALHA PWM: sinais permanecem vermelhos.");
}

void loop() {
  const uint32_t now = millis();
  if (digitalRead(PED_BUTTON) == LOW) pedestrianPending = true;
  const Demand demand{digitalRead(DETECTOR_NS) == HIGH, digitalRead(DETECTOR_EW) == HIGH,
                      pedestrianPending};
  const bool maintain = maintenanceArmed() || uploadActive || rebootPending;
  Output out = controller.tick(now, demand, maintain);
  // Botao fica travado ate o fim da janela de entrada. Pressao durante a
  // limpeza permanece pendente para a proxima fase.
  if (previousPhase == Phase::PedWalk && controller.phase() == Phase::PedClear)
    pedestrianPending = false;
  previousPhase = controller.phase();
  writeOutputs(out, now);
  // Parser HTTP so roda com todas as direcoes paradas; um cliente lento nao
  // congela um verde ou encurta uma travessia.
  if (controller.isMaintenance()) server.handleClient();
  if (rebootPending && static_cast<int32_t>(now - rebootAt) >= 0) ESP.restart();
  delay(2);
}
