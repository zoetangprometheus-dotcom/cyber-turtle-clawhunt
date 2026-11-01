#include <Arduino.h>
#include <TFT_eSPI.h>
#include <U8g2_for_TFT_eSPI.h>
#include <Preferences.h>
#include "CST816S.h"
#include "qrcodegen.h"
#include "Board.h"
#include "Flow.h"
#include "Feedback.h"
#include "FeedbackOutput.h"
#include "Hexagrams.h"
#include "BleProbe.h"
#include "Logo.h"
#include "QrLink.h"

// Local random hexagram demo only; no AI / claim / print success.
TFT_eSPI screen;
U8g2_for_TFT_eSPI chinese;
CST816S touch(Board::SDA_PIN, Board::SCL_PIN, Board::TOUCH_RESET, Board::TOUCH_INTERRUPT);
Flow flow;
ShakeDetector shake;
Feedback feedback(Board::LIGHTS_ENABLED, Board::VIBRATION_ENABLED);
FeedbackOutput feedbackOutput;
const Hexagram *reading = &HEXAGRAMS[0];
constexpr uint16_t PAPER = 0xffff, INK = 0x2124, BLUE = 0x32f1, MUTED = 0x7bcf;
constexpr uint8_t BRIGHTNESS = 180;
bool imuOk = false, motionLog = false, touchOk = false;
uint32_t lastSample = 0, lastMotionLog = 0, lastTouch = 0;
uint32_t eventNumber = 0, sessionNonce = 0, sessionNonceLow = 0;
Preferences settings;
String qrBase, readingUrl;
uint32_t transitionAt = 0;
bool transitioning = false, painted = false;
String serialLine;

const char *trigramLabel(const char *name) {
  // Shared data retains traditional spelling; the display font is GB2312.
  if (strcmp(name, "兌") == 0) return "兑";
  if (strcmp(name, "離") == 0) return "离";
  return name;
}

void text(const char *value, int baseline, uint16_t color = INK, int center = 120) {
  chinese.setForegroundColor(color);
  chinese.setCursor(center - chinese.getUTF8Width(value) / 2, baseline);
  chinese.print(value);
}

void trigram(uint8_t bits, int left, int top, int width = 88) {
  for (int i = 0; i < 3; ++i) {
    if (bits & (1 << (2 - i))) screen.fillRect(left, top + i * 15, width, 6, INK);
    else {
      int segment = (width - 16) / 2;
      screen.fillRect(left, top + i * 15, segment, 6, INK);
      screen.fillRect(left + width - segment, top + i * 15, segment, 6, INK);
    }
  }
}

void updateReadingUrl() {
  readingUrl = makeQrLink(qrBase.c_str(), reading->id, sessionNonce, sessionNonceLow, eventNumber).c_str();
}

bool encodeReadingQr(const char *url, uint8_t *scratch, uint8_t *qr) {
  return qrcodegen_encodeText(url, scratch, qr, qrcodegen_Ecc_MEDIUM,
                             1, 7, qrcodegen_Mask_AUTO, true);
}

void drawQr() {
  if (!readingUrl.length()) {
    text("网页待上线", 100, BLUE);
    text("轻触回看上下卦", 130);
    text("长按返回首页", 158, MUTED);
    return;
  }
  uint8_t scratch[qrcodegen_BUFFER_LEN_FOR_VERSION(7)];
  uint8_t qr[qrcodegen_BUFFER_LEN_FOR_VERSION(7)];
  if (!encodeReadingQr(readingUrl.c_str(), scratch, qr)) {
    text("二维码生成失败", 120); return;
  }
  int cells = qrcodegen_getSize(qr), scale = 160 / (cells + 8);
  int side = (cells + 8) * scale, origin = (240 - side) / 2;
  // Includes 4-module quiet zone; <=160px square fits inside the round display.
  for (int y = 0; y < cells; ++y)
    for (int x = 0; x < cells; ++x)
      if (qrcodegen_getModule(qr, x, y))
        screen.fillRect(origin + (x + 4) * scale, origin + (y + 4) * scale, scale, scale, TFT_BLACK);
  text((String("上 ") + trigramLabel(reading->upper) + "  下 " + trigramLabel(reading->lower)).c_str(), 31, BLUE);
  text("扫码查看同一卦", 215, MUTED);
}

void drawPage() {
  if (flow.stage == Stage::Idle) {
    screen.fillScreen(TFT_BLACK);
    screen.setSwapBytes(true);
    screen.pushImage((240 - LOGO_WIDTH) / 2, (240 - LOGO_HEIGHT) / 2,
                     LOGO_WIDTH, LOGO_HEIGHT, LOGO_PIXELS);
    screen.setSwapBytes(false);
    return;
  }
  screen.fillScreen(PAPER);
  screen.drawCircle(120, 120, 116, BLUE);
  if (flow.stage == Stage::Qr) { drawQr(); return; }
  text("赛博龟壳", 42, BLUE);
  switch (flow.stage) {
    case Stage::Upper:
      text("上卦", 79, MUTED); trigram(reading->lines >> 3, 76, 98);
      text(trigramLabel(reading->upper), 166); text("慢一点 感受此刻", 192, MUTED);
      break;
    case Stage::Lower:
      text("下卦", 79, MUTED); trigram(reading->lines & 7, 76, 98);
      text(trigramLabel(reading->lower), 166);
      text((String("上卦 ") + trigramLabel(reading->upper)).c_str(), 192, MUTED);
      break;
    case Stage::Reading:
      text("上卦", 77, MUTED, 66); text("下卦", 77, MUTED, 174);
      trigram(reading->lines >> 3, 34, 96, 64);
      trigram(reading->lines & 7, 142, 96, 64);
      text(trigramLabel(reading->upper), 160, INK, 66); text(trigramLabel(reading->lower), 160, INK, 174);
      text((String("第 ") + reading->id + " 卦").c_str(), 185, BLUE);
      text("轻触扫码 长按返回", 206, MUTED);
      break;
    default: break;
  }
  text("硬件联调", 222, MUTED);
}

void requestPage() {
  transitionAt = millis(); transitioning = true; painted = false;
  Serial.printf("STATE %u\n", unsigned(flow.stage));
}

void animatePage(uint32_t now) {
  if (!transitioning) return;
  uint32_t elapsed = now - transitionAt;
  if (elapsed < 90) { ledcWrite(0, BRIGHTNESS * (90 - elapsed) / 90); return; }
  if (!painted) { ledcWrite(0, 0); drawPage(); painted = true; }
  if (elapsed < 240) ledcWrite(0, BRIGHTNESS * (elapsed - 90) / 150);
  else { ledcWrite(0, BRIGHTNESS); transitioning = false; }
}

void startReading(const char *source) {
  if (!flow.start(millis())) { Serial.println("BUSY no duplicate event"); return; }
  // One 6-bit draw selects all 64 upper/lower pairs, including equal trigrams.
  reading = &HEXAGRAMS[esp_random() & 63];
  shake.reset(); ++eventNumber;
  feedback.begin(reading->lines, millis());
  if (!eventNumber) { sessionNonce = esp_random(); sessionNonceLow = esp_random(); ++eventNumber; }
  updateReadingUrl();
  Serial.printf("EVENT bringup-%08lx-%lu source=%s hexagram_id=%u upper=%s lower=%s lines=%u content_origin=demo_random\n",
                (unsigned long)sessionNonce, (unsigned long)eventNumber, source,
                reading->id, reading->upper, reading->lower, reading->lines);
  requestPage();
}

void resetReading() {
  uint32_t now = millis();
  flow.reset(now); shake.reset(); feedback.reset(now); requestPage();
}

void status() {
  Serial.printf("STATUS firmware=0.4.1-bringup state=%u imu=%s touch=%s printer=disabled backend=not_configured events=%lu shake_profile=balanced_v4\n",
    unsigned(flow.stage), imuOk ? "ok" : "error", touchOk ? "ok" : "unverified", (unsigned long)eventNumber);
  Serial.printf("QR configured=%s origin=public_device_demo\n", qrBase.length() ? "yes" : "no");
  Serial.printf("FEEDBACK lights=%s motor=%s\n",
    Board::LIGHTS_ENABLED ? (feedbackOutput.lightsReady() ? "ready" : "error") : "disabled",
    Board::VIBRATION_ENABLED ? "enabled" : "disabled");
}

void command(const String &line) {
  if (line.startsWith("bleprobe ")) {
    if (flow.stage != Stage::Idle && flow.stage != Stage::Reading) { Serial.println("BUSY"); return; }
    if (feedback.blocksShake(millis())) { Serial.println("BUSY motor feedback"); return; }
    probePrinterBle(line.substring(9));
  }
  else if (line == "start") startReading("serial");
  else if (line == "reset") resetReading();
  else if (line == "status") status();
  else if (line == "motion on") { motionLog = true; Serial.println("MOTION logging enabled"); }
  else if (line == "motion off") { motionLog = false; Serial.println("MOTION logging disabled"); }
  else if (line == "vibrate") {
    if (!Board::VIBRATION_ENABLED) Serial.println("MOTOR_DISABLED wiring not confirmed");
    else { feedback.testMotor(millis()); shake.reset(); Serial.println("MOTOR_TEST 140ms"); }
  }
  else if (line.startsWith("qrurl ")) {
    if (flow.stage == Stage::Upper || flow.stage == Stage::Lower) { Serial.println("BUSY"); return; }
    String candidate = line.substring(6);
    uint8_t scratch[qrcodegen_BUFFER_LEN_FOR_VERSION(7)], qr[qrcodegen_BUFFER_LEN_FOR_VERSION(7)];
    std::string longest = makeQrLink(candidate.c_str(), 64, UINT32_MAX, UINT32_MAX, UINT32_MAX);
    if (longest.empty() || !encodeReadingQr(longest.c_str(), scratch, qr)) {
      Serial.println("QR_URL_INVALID use HTTPS base without query/fragment; max 110 bytes"); return;
    }
    if (!settings.putString("qrbase", candidate)) { Serial.println("QR_SAVE_FAILED"); return; }
    qrBase = candidate; updateReadingUrl();
    if (flow.stage == Stage::Qr) requestPage();
    Serial.println("QR_URL_SAVED");
  } else if (line == "qr") {
    if (flow.stage != Stage::Reading && flow.stage != Stage::Qr) { Serial.println("READING_NOT_READY"); return; }
    flow.stage = Stage::Qr; flow.since = millis(); shake.reset(); requestPage();
    feedback.stage(Stage::Qr, millis());
    if (readingUrl.length()) Serial.println(String("QR_LINK ") + readingUrl);
    else Serial.println("QR_NOT_CONFIGURED");
  } else if (line == "print") Serial.println("PRINT_BLOCKED wiring and command mode not confirmed; no UART write");
  else if (line == "reading") {
    if (!eventNumber) Serial.println("READING_NONE");
    else Serial.printf("READING id=%u upper=%s lower=%s lines=%u\n", reading->id, reading->upper, reading->lower, reading->lines);
  }
  else Serial.println("Commands: status start reset qr qrurl <HTTPS base> reading motion on motion off vibrate print bleprobe <address>");
}

void setup() {
  Serial.begin(115200);
  serialLine.reserve(128);
  sessionNonce = esp_random(); sessionNonceLow = esp_random();
  settings.begin("turtle", false);
  qrBase = settings.getString("qrbase", "");
  if (!validQrBase(qrBase.c_str())) qrBase = "";
  screen.init(); screen.setRotation(2); // 180 degrees for the shell's screen orientation.
  ledcSetup(0, 5000, 8); ledcAttachPin(Board::BACKLIGHT, 0); ledcWrite(0, 0);
  chinese.begin(screen); chinese.setFont(u8g2_font_wqy16_t_gb2312);
  chinese.setFontMode(1); chinese.setBackgroundColor(PAPER);
  touch.begin(); Wire.setTimeOut(30);
  uint8_t touchId = 0;
  touchOk = Board::read(0x15, 0xa7, &touchId, 1);
  imuOk = Board::initImu();
  feedbackOutput.begin();
  Serial.printf("BOOT cyber-turtle 0.4.1-bringup flash=%u psram=%u imu_address=0x%02x touch_id=0x%02x\n",
    ESP.getFlashChipSize(), ESP.getPsramSize(), Board::imuAddress, touchId);
  status(); requestPage();
}

void loop() {
  uint32_t now = millis();
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') { serialLine.trim(); if (serialLine.length()) command(serialLine); serialLine = ""; }
    else if (c != '\r') {
      if (serialLine.length() < 127) serialLine += c;
      else { serialLine = ""; Serial.println("INPUT_TOO_LONG"); }
    }
  }
  now = millis();
  if (touch.available() && now - lastTouch > 450) {
    // Gesture-only dispatch prevents a held finger from creating new events.
    if (touch.data.gestureID == SINGLE_CLICK) {
      lastTouch = now;
      if (flow.stage == Stage::Idle) startReading("touch");
      else if (flow.toggleResult(now)) {
        shake.reset(); feedback.stage(flow.stage, millis()); requestPage();
      }
    } else if (touch.data.gestureID == LONG_PRESS &&
               (flow.stage == Stage::Reading || flow.stage == Stage::Qr)) {
      lastTouch = now; resetReading();
    }
  }
  now = millis();
  // Apply motor stop before considering IMU samples, including its cooldown.
  feedbackOutput.tick(feedback.mask(now), feedback.motorOn(now));
  if (imuOk && now - lastSample >= 20) {
    lastSample = now;
    float x, y, z;
    if (Board::acceleration(x, y, z)) {
      float g = sqrtf(x*x + y*y + z*z);
      if (motionLog && now - lastMotionLog >= 250) {
        lastMotionLog = now; Serial.printf("ACC %.3f %.3f %.3f norm=%.3f\n", x, y, z, g);
      }
      if ((flow.stage == Stage::Idle || flow.stage == Stage::Reading || flow.stage == Stage::Qr) &&
          !feedback.blocksShake(millis())) {
        if (shake.update(x, y, z, now)) startReading("shake");
      }
      else shake.reset();
    } else { shake.reset(); }
  }
  // Commands/touch can start a phase after the loop's original timestamp.
  now = millis();
  if (flow.tick(now)) { feedback.stage(flow.stage, now); requestPage(); }
  feedbackOutput.tick(feedback.mask(now), feedback.motorOn(now));
  animatePage(now);
  delay(5);
}
