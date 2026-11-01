#pragma once
#include <Arduino.h>
#include <driver/rmt.h>
#include "Board.h"

// Platform output for the existing 5V, 60-pixel strip. Never powers the strip.
// The provisional eight sectors need physical calibration before enabling LEDs.
class FeedbackOutput {
  static constexpr unsigned PIXELS = 60;
  static constexpr uint8_t WHITE_LEVEL = 12; // Low-brightness first bring-up only.
  rmt_item32_t items[PIXELS * 24 + 1] = {};
  bool lightReady = false;
  int lastMask = -1;
public:
  void begin() {
    if (Board::VIBRATION_ENABLED) {
      digitalWrite(Board::VIBRATION_SIGNAL, LOW);
      pinMode(Board::VIBRATION_SIGNAL, OUTPUT);
    }
    if (!Board::LIGHTS_ENABLED) return;
    rmt_config_t config = RMT_DEFAULT_CONFIG_TX(gpio_num_t(Board::LIGHT_DATA), RMT_CHANNEL_0);
    config.clk_div = 8;
    if (rmt_config(&config) != ESP_OK ||
        rmt_driver_install(RMT_CHANNEL_0, 0, 0) != ESP_OK) {
      Serial.println("LIGHT_INIT_FAILED"); return;
    }
    uint32_t clock = 0;
    if (rmt_get_counter_clock(RMT_CHANNEL_0, &clock) != ESP_OK || clock != 10000000) {
      rmt_driver_uninstall(RMT_CHANNEL_0);
      Serial.println("LIGHT_CLOCK_INVALID"); return;
    }
    lightReady = true;
    tick(0, false);
  }
  bool lightsReady() const { return lightReady; }
  void tick(uint8_t mask, bool motorOn) {
    if (Board::VIBRATION_ENABLED)
      digitalWrite(Board::VIBRATION_SIGNAL, motorOn ? HIGH : LOW);
    if (!lightReady || lastMask == mask) return;
    // Async RMT retains this buffer. Never edit it while the previous TX is active.
    if (rmt_wait_tx_done(RMT_CHANNEL_0, 0) != ESP_OK) return;
    unsigned item = 0;
    for (unsigned pixel = 0; pixel < PIXELS; ++pixel) {
      unsigned group = pixel * 8 / PIXELS;
      uint8_t value = mask & (1u << group) ? WHITE_LEVEL : 0;
      for (unsigned channel = 0; channel < 3; ++channel) {
        for (int bit = 7; bit >= 0; --bit) {
          bool one = value & (1u << bit);
          items[item].level0 = 1;
          items[item].duration0 = one ? 8 : 4;
          items[item].level1 = 0;
          items[item].duration1 = one ? 4 : 8;
          ++item;
        }
      }
    }
    items[item].level0 = 0; items[item].duration0 = 3000; // 300us latch/reset.
    items[item].level1 = 0; items[item].duration1 = 1;
    if (rmt_write_items(RMT_CHANNEL_0, items, item + 1, false) == ESP_OK) lastMask = mask;
    else Serial.println("LIGHT_WRITE_FAILED");
  }
};
