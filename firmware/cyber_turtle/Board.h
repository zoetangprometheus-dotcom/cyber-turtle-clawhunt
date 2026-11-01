#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <initializer_list>

namespace Board {
constexpr int SDA_PIN = 6, SCL_PIN = 7, BACKLIGHT = 2;
constexpr int TOUCH_RESET = 13, TOUCH_INTERRUPT = 5;
// Proposed printer pins only; printer UART remains disabled.
constexpr int PRINTER_TX = 16, PRINTER_RX = 17;
constexpr unsigned PRINTER_BAUD = 115200;
constexpr bool PRINTER_ENABLED = false;
// GPIO18/21 are exposed on SH1.0 and unused by the screen, touch and IMU.
// Enable each output only after its wiring/power has been confirmed.
constexpr int LIGHT_DATA = 18, VIBRATION_SIGNAL = 21;
constexpr bool LIGHTS_ENABLED = false, VIBRATION_ENABLED = true;
uint8_t imuAddress = 0;

bool read(uint8_t address, uint8_t reg, uint8_t *bytes, size_t count) {
  Wire.beginTransmission(address); Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(address, (uint8_t)count) != count) return false;
  for (size_t i = 0; i < count; ++i) bytes[i] = Wire.read();
  return true;
}
bool write(uint8_t address, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(address); Wire.write(reg); Wire.write(value);
  return Wire.endTransmission() == 0;
}
bool initImu() {
  // QMI8658 register values checked against Waveshare's board example.
  for (uint8_t address : {uint8_t(0x6a), uint8_t(0x6b)}) {
    uint8_t who = 0;
    if (!read(address, 0x00, &who, 1) || who != 0x05) continue;
    // Auto-increment; disable while configuring; +/-8g, 125Hz; accel only.
    if (!write(address, 0x02, 0x60) || !write(address, 0x08, 0x00) ||
        !write(address, 0x03, 0x26) || !write(address, 0x06, 0x00) ||
        !write(address, 0x08, 0x01)) return false;
    imuAddress = address;
    return true;
  }
  return false;
}
bool acceleration(float &x, float &y, float &z) {
  uint8_t bytes[6];
  if (!imuAddress || !read(imuAddress, 0x35, bytes, 6)) return false;
  x = int16_t(uint16_t(bytes[1]) << 8 | bytes[0]) / 4096.0f;
  y = int16_t(uint16_t(bytes[3]) << 8 | bytes[2]) / 4096.0f;
  z = int16_t(uint16_t(bytes[5]) << 8 | bytes[4]) / 4096.0f;
  return true;
}
}
