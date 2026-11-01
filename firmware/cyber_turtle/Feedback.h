#pragma once
#include "Flow.h"

struct Feedback {
  Feedback(bool leds = false, bool motor = false)
    : ledsEnabled(leds), motorEnabled(motor) {}

  void begin(uint8_t lines, uint32_t now) {
    update(now);
    hexagram = lines & 63;
    current = Stage::Upper;
    stageSince = now;
    pulse(80, now);
  }

  void stage(Stage next, uint32_t now) {
    update(now);
    if (next == current) return;
    if (next == Stage::Idle) { reset(now); return; }
    Stage previous = current;
    current = next;
    stageSince = now;
    if (previous == Stage::Upper && next == Stage::Lower) pulse(80, now);
    else if (previous == Stage::Lower && next == Stage::Reading) pulse(140, now);
  }

  void reset(uint32_t now) {
    update(now);
    stopMotor(now);
    current = Stage::Idle;
    stageSince = now;
  }

  void testMotor(uint32_t now) {
    update(now);
    pulse(140, now);
  }

  uint8_t mask(uint32_t now) {
    update(now);
    if (!ledsEnabled || current == Stage::Idle) return 0;
    uint8_t upper = uint8_t(1u << (hexagram >> 3));
    uint8_t lower = uint8_t(1u << (hexagram & 7));
    uint8_t cursor = uint8_t(1u << (((now - stageSince) / 120) % 8));
    if (current == Stage::Upper) return cursor;
    if (current == Stage::Lower) return upper | cursor;
    return upper | lower;
  }

  bool motorOn(uint32_t now) {
    update(now);
    return active;
  }

  bool blocksShake(uint32_t now) {
    update(now);
    return motorEnabled && (active || cooling);
  }

private:
  bool ledsEnabled, motorEnabled;
  bool active = false, cooling = false;
  Stage current = Stage::Idle;
  uint8_t hexagram = 0;
  uint32_t stageSince = 0, pulseSince = 0, pulseLength = 0, stoppedAt = 0;

  void pulse(uint32_t duration, uint32_t now) {
    if (!motorEnabled) return;
    active = true;
    cooling = false;
    pulseSince = now;
    pulseLength = duration;
  }

  void stopMotor(uint32_t now) {
    if (!active) return;
    active = false;
    cooling = true;
    stoppedAt = now;
  }

  void update(uint32_t now) {
    // Cooling begins when the caller can actually switch the output off.
    if (active && now - pulseSince >= pulseLength) stopMotor(now);
    if (cooling && now - stoppedAt >= 500) cooling = false;
  }
};
