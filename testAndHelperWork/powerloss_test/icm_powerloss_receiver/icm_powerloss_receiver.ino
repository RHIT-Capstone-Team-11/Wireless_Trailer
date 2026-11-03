// ICM stand-in for the power-loss hold-up test (ESP32 / ESP32-S3, Arduino core 2.x or 3.x)
//
// Powered from the laptop USB; open the Serial Monitor at 115200.
// It is wired to the SAME sense line as the sender (and shares GND), so it timestamps the
// moment the supply is cut with its own clock and measures the true end-to-end delay to the
// POWER_LOST message. One CSV summary line per trial:
//
// trial,got_msg,rx_latency_ms,sender_ack_ms,attempts,v_detect_mV,v_after_ack_mV,energy_mJ,
//   alive_pkts,last_alive_ms,v_last_mV,rssi
//
// energy_mJ = 0.5 x C_TEST_F x (v_detect^2 - v_after_ack^2): the energy the sender used from the
// power cut until it got the ACK. Set C_TEST_F to the MEASURED value of your test capacitor.

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_idf_version.h>

// ---------------- settings ----------------
const int SENSE_PIN = 4;          // same 1k / 4.7k sense node as the sender (common GND!)
const uint8_t CHANNEL = 1;
const float C_TEST_F = 0.0376;     // test capacitance in farads (measure it; electrolytics are +-20 %)
const uint32_t TRIAL_END_MS = 600;// trial ends after this long with no packets
const uint32_t CONFIRM_US = 2000; // same glitch filter as the sender
const bool RAMP_TEST = false;     // true: ignore SENSE, just print every packet (min-voltage test)
// ------------------------------------------

struct __attribute__((packed)) Msg {
  uint8_t  type;
  uint8_t  attempts;
  uint8_t  acked;
  uint16_t seq;
  uint32_t t_us;
  uint32_t t_ack_us;
  uint16_t v_mv;
  uint16_t v_detect_mv;
};

struct Rx { uint32_t t_rx; Msg m; int8_t rssi; };
static Rx ring[256];
static volatile uint16_t head = 0, tail = 0;

volatile uint32_t t_edge = 0;
volatile bool newEdge = false;

void IRAM_ATTR onSenseFall() {
  uint32_t now = micros();
  if (!newEdge && now - t_edge > 200000) { t_edge = now; newEdge = true; }   // ignore bounce
}

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  int8_t rssi = (info && info->rx_ctrl) ? info->rx_ctrl->rssi : 0;
#else
void onRecv(const uint8_t *mac, const uint8_t *data, int len) {
  int8_t rssi = 0;
#endif
  if (len != (int)sizeof(Msg)) return;
  uint16_t next = (head + 1) & 0xFF;
  if (next == tail) return;                     // buffer full, drop
  ring[head].t_rx = micros();
  memcpy(&ring[head].m, data, sizeof(Msg));
  ring[head].rssi = rssi;
  head = next;
}

// per-trial state
uint16_t trial = 0;
bool inTrial = false;
uint32_t trialEdge = 0, lastPktMs = 0;
bool gotMsg = false;
float rxLatencyMs = -1, senderAckMs = -1;
int attempts = 0, vDetect = 0, vAfterAck = 0, vLast = 0, alivePkts = 0, rssi = 0;
float lastAliveMs = 0;

void startTrial() {
  trial++; inTrial = true; trialEdge = t_edge; lastPktMs = millis();
  gotMsg = false; rxLatencyMs = senderAckMs = -1;
  attempts = vDetect = vAfterAck = vLast = alivePkts = rssi = 0; lastAliveMs = 0;
}

void endTrial() {
  float energy_mJ = (vDetect > 0 && vAfterAck > 0)
      ? 0.5f * C_TEST_F * ((vDetect / 1000.0f) * (vDetect / 1000.0f) - (vAfterAck / 1000.0f) * (vAfterAck / 1000.0f)) * 1000.0f
      : -1;
  Serial.printf("%u,%d,%.2f,%.2f,%d,%d,%d,%.1f,%d,%.1f,%d,%d\n", trial, gotMsg, rxLatencyMs, senderAckMs, attempts,
                vDetect, vAfterAck, energy_mJ, alivePkts, lastAliveMs, vLast, rssi);
  inTrial = false;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(SENSE_PIN, INPUT);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_ps(WIFI_PS_NONE);
  esp_wifi_set_channel(CHANNEL, WIFI_SECOND_CHAN_NONE);
  delay(2000);
  uint8_t mac[6];
  esp_wifi_get_mac(WIFI_IF_STA, mac);
  Serial.printf("Receiver MAC, paste into the sender: {0x%02X, 0x%02X, 0x%02X, 0x%02X, 0x%02X, 0x%02X}\n",
                mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  if (esp_now_init() != ESP_OK) { Serial.println("esp_now_init failed"); while (true) delay(1000); }
  esp_now_register_recv_cb(onRecv);
  if (!RAMP_TEST) attachInterrupt(digitalPinToInterrupt(SENSE_PIN), onSenseFall, FALLING);
  Serial.println("trial,got_msg,rx_latency_ms,sender_ack_ms,attempts,v_detect_mV,v_after_ack_mV,energy_mJ,"
                 "alive_pkts,last_alive_ms,v_last_mV,rssi");
}

void loop() {
  if (newEdge && !RAMP_TEST && micros() - t_edge >= CONFIRM_US) {
    newEdge = false;
    if (digitalRead(SENSE_PIN) == LOW) {          // real loss (not a bounce while reconnecting)
      if (inTrial) endTrial();
      startTrial();
    }
  }
  while (tail != head) {
    Rx r = ring[tail];
    tail = (tail + 1) & 0xFF;
    lastPktMs = millis();
    if (!inTrial) {                               // RAMP_TEST mode or stray packets: just print them
      Serial.printf("alive seq=%u v=%u mV rssi=%d\n", r.m.seq, r.m.v_mv, r.rssi);
      continue;
    }
    if (r.m.type == 1 && !gotMsg) {
      gotMsg = true;
      rxLatencyMs = (r.t_rx - trialEdge) / 1000.0f;
      vDetect = r.m.v_detect_mv;
      attempts = r.m.attempts;
      rssi = r.rssi;
    } else if (r.m.type == 2) {
      if (alivePkts == 0) {                       // first ALIVE is sent right after the ACK
        vAfterAck = r.m.v_mv;
        senderAckMs = r.m.t_ack_us / 1000.0f;
        attempts = r.m.attempts;
        if (!vDetect) vDetect = r.m.v_detect_mv;
      }
      alivePkts++;
      lastAliveMs = r.m.t_us / 1000.0f;
      vLast = r.m.v_mv;
    }
  }
  if (inTrial && millis() - lastPktMs > TRIAL_END_MS) endTrial();
}
