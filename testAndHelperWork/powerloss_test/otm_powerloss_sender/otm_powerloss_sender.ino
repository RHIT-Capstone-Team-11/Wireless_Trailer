// OTM stand-in for the power-loss hold-up test (ESP32 / ESP32-S3, Arduino core 2.x or 3.x)
//
// Normal state: radio on, waiting (like a real OTM listening for the ICM).
// When SENSE_PIN falls (supply cut upstream of the diode), it:
//   1. reads VCAP, raises MARK_PIN,
//   2. sends POWER_LOST to the receiver, retrying until the ESP-NOW ACK (up to MAX_ATTEMPTS),
//   3. drops MARK_PIN, then keeps sending ALIVE packets (time since detection + VCAP)
//      until power returns, the chip browns out, or ALIVE_FOR_MS passes.
// The receiver does all the logging, because this board loses power during the test.
//
// RAMP_TEST = true: ignore SENSE and send ALIVE packets nonstop. Use it with the supply feeding
// 3V3 directly (no capacitor) and turn the supply down slowly; the last packet the receiver gets
// shows the lowest voltage this board can still transmit at.
//
// Flash and set up over USB, then UNPLUG USB for the trials (USB would keep the board alive).

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_idf_version.h>

// ---------------- settings ----------------
uint8_t RECEIVER_MAC[6] = {0xAC, 0x27, 0x6E, 0xAA, 0xC9, 0x6C};  // the receiver prints its MAC at boot
const int SENSE_PIN = 4;          // supply side of the diode, through a 1k / 4.7k divider (~3.3 V when on)
const int MARK_PIN  = 5;          // scope marker: high from detection until POWER_LOST is ACKed
const int VCAP_PIN  = 6;          // VCAP through a 100k / 100k divider + 0.1 uF, ADC1 pin.
                                  // ESP32-S3: GPIO6 is fine. Classic ESP32: use 34 (GPIO6 is the flash bus).
const float VCAP_DIVIDER = 2.0;   // VCAP = pin voltage x this
const uint8_t CHANNEL = 1;        // same on both boards
const uint8_t MAX_ATTEMPTS = 5;   // app-level retries on top of ESP-NOW's own MAC retries
const uint32_t CONFIRM_US = 2000; // supply must stay off this long before we call it a power loss
                                  // (filters switch bounce; a real OTM needs a glitch filter too)
const uint32_t ACK_TIMEOUT_MS = 50;
const uint32_t ALIVE_PERIOD_MS = 10;
const uint32_t ALIVE_FOR_MS = 3000;
const bool RAMP_TEST = false;
// ------------------------------------------

struct __attribute__((packed)) Msg {
  uint8_t  type;          // 1 = POWER_LOST, 2 = ALIVE
  uint8_t  attempts;      // POWER_LOST attempts used (ALIVE: copy of the final count)
  uint8_t  acked;         // ALIVE: 1 if POWER_LOST was ACKed
  uint16_t seq;
  uint32_t t_us;          // microseconds since the sense edge, at send time
  uint32_t t_ack_us;      // microseconds from sense edge to POWER_LOST ACK (ALIVE packets)
  uint16_t v_mv;          // VCAP at send time
  uint16_t v_detect_mv;   // VCAP at the sense edge
};

volatile bool lost = false;
volatile uint32_t t_edge = 0;
volatile bool sendDone = false;
volatile bool sendOk = false;

void IRAM_ATTR onSenseFall() {
  if (!lost) { t_edge = micros(); lost = true; }
}

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 5, 0)
void onSent(const esp_now_send_info_t *info, esp_now_send_status_t status) {
#else
void onSent(const uint8_t *mac, esp_now_send_status_t status) {
#endif
  sendOk = (status == ESP_NOW_SEND_SUCCESS);
  sendDone = true;
}

uint16_t readVcap() {
  return (uint16_t)(analogReadMilliVolts(VCAP_PIN) * VCAP_DIVIDER);
}

bool sendAndWait(const Msg &m) {
  sendDone = false;
  sendOk = false;
  if (esp_now_send(RECEIVER_MAC, (const uint8_t *)&m, sizeof(m)) != ESP_OK) return false;
  uint32_t t0 = millis();
  while (!sendDone && millis() - t0 < ACK_TIMEOUT_MS) { }
  return sendDone && sendOk;
}

void setup() {
  pinMode(SENSE_PIN, INPUT);
  pinMode(MARK_PIN, OUTPUT);
  digitalWrite(MARK_PIN, LOW);
  analogReadResolution(12);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_ps(WIFI_PS_NONE);                      // radio fully on, like an OTM listening for commands
  esp_wifi_set_channel(CHANNEL, WIFI_SECOND_CHAN_NONE);
  if (esp_now_init() != ESP_OK) { while (true) delay(1000); }
  esp_now_register_send_cb(onSent);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, RECEIVER_MAC, 6);
  peer.channel = CHANNEL;
  peer.encrypt = false;
  esp_now_add_peer(&peer);

  attachInterrupt(digitalPinToInterrupt(SENSE_PIN), onSenseFall, FALLING);
}

void loop() {
  if (RAMP_TEST) {
    static uint16_t seq = 0;
    Msg m = {};
    m.type = 2; m.seq = ++seq; m.t_us = micros(); m.v_mv = readVcap();
    sendAndWait(m);
    delay(ALIVE_PERIOD_MS);
    return;
  }

  if (!lost) { delay(1); return; }

  // ---- confirm it is a real loss, not a bounce or a glitch ----
  while (micros() - t_edge < CONFIRM_US) { }
  if (digitalRead(SENSE_PIN) == HIGH) { lost = false; return; }

  // ---- power lost ----
  digitalWrite(MARK_PIN, HIGH);
  const uint16_t vDetect = readVcap();
  Msg m = {};
  m.type = 1;
  m.v_detect_mv = vDetect;
  bool acked = false;
  uint8_t attempts = 0;
  while (!acked && attempts < MAX_ATTEMPTS) {
    attempts++;
    m.attempts = attempts;
    m.t_us = micros() - t_edge;
    m.v_mv = readVcap();
    acked = sendAndWait(m);
  }
  const uint32_t tAck = micros() - t_edge;
  digitalWrite(MARK_PIN, LOW);

  // ---- report how long it keeps going and how far VCAP falls ----
  uint16_t seq = 0;
  const uint32_t tStart = millis();
  while (millis() - tStart < ALIVE_FOR_MS && digitalRead(SENSE_PIN) == LOW) {
    Msg a = {};
    a.type = 2; a.seq = ++seq; a.attempts = attempts; a.acked = acked;
    a.t_us = micros() - t_edge; a.t_ack_us = tAck;
    a.v_mv = readVcap(); a.v_detect_mv = vDetect;
    sendAndWait(a);
    delay(ALIVE_PERIOD_MS);
  }

  // wait for power to come back, then re-arm
  while (digitalRead(SENSE_PIN) == LOW) delay(5);
  delay(300);
  lost = false;
}
