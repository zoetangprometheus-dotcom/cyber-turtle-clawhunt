#pragma once
#include <stdint.h>
#include <math.h>

// All durations use unsigned subtraction so millis() wrap is safe.
enum class Stage { Idle = 0, Upper = 1, Lower = 2, Reading = 3, Qr = 4 };
struct Flow {
  Stage stage = Stage::Idle;
  uint32_t since = 0;
  bool start(uint32_t now) {
    if (stage != Stage::Idle && stage != Stage::Reading && stage != Stage::Qr) return false;
    stage = Stage::Upper; since = now; return true;
  }
  bool tick(uint32_t now) {
    uint32_t elapsed = now - since;
    Stage next = stage;
    if (stage == Stage::Upper && elapsed >= 1400) next = Stage::Lower;
    if (stage == Stage::Lower && elapsed >= 1400) next = Stage::Reading;
    if (stage == Stage::Reading && elapsed >= 6000) next = Stage::Qr;
    if (next == stage) return false;
    stage = next; since = now; return true;
  }
  void reset(uint32_t now) { stage = Stage::Idle; since = now; }
  bool toggleResult(uint32_t now) {
    if (stage != Stage::Reading && stage != Stage::Qr) return false;
    stage = stage == Stage::Reading ? Stage::Qr : Stage::Reading;
    since = now; return true;
  }
};

struct ShakeDetector {
  static constexpr float PEAK_G = 0.35f;
  static constexpr unsigned REQUIRED_PEAKS = 4;
  uint32_t first = 0, lastPeak = 0, quietSince = 0;
  uint32_t lastSample = 0, candidateSince = 0;
  unsigned peaks = 0;
  bool candidate = false, quiet = false, primed = false;
  float gx = 0, gy = 0, gz = 0, px = 0, py = 0, pz = 0;
  void clearGesture() { peaks = 0; candidate = false; quiet = false; }
  void reset() { clearGesture(); primed = false; }
  bool update(float x, float y, float z, uint32_t now) {
    if (!isfinite(x) || !isfinite(y) || !isfinite(z)) { reset(); return false; }
    if (!primed || now - lastSample > 150) {
      reset(); gx = x; gy = y; gz = z; lastSample = now; primed = true;
      return false;
    }
    lastSample = now;
    // Track slow gravity/orientation drift; retain quicker three-axis motion.
    gx += 0.12f * (x - gx); gy += 0.12f * (y - gy); gz += 0.12f * (z - gz);
    float dx = x - gx, dy = y - gy, dz = z - gz;
    float dynamic = sqrtf(dx*dx + dy*dy + dz*dz);
    if (peaks && (now - first > 4000 ||
        (peaks < REQUIRED_PEAKS && now - lastPeak > 700))) clearGesture();
    bool high = dynamic > PEAK_G;
    // Each accepted lobe must oppose the previous one, not just cross a threshold.
    float previous = sqrtf(px*px + py*py + pz*pz);
    bool reversed = peaks && dx*px + dy*py + dz*pz <= -0.5f * dynamic * previous;
    if (high && (!peaks || reversed)) {
      if (!candidate) { candidate = true; candidateSince = now; }
      // A brief impact is not a sustained hand movement.
      if (now - candidateSince >= 20 && (!peaks || now - lastPeak >= 160)) {
        if (!peaks) first = now;
        ++peaks; lastPeak = now; candidate = false;
        px = dx; py = dy; pz = dz;
      }
    } else candidate = false;
    if (dynamic < 0.12f) {
      if (!quiet) { quiet = true; quietSince = now; }
      if (peaks >= REQUIRED_PEAKS && now - quietSince >= 400) { reset(); return true; }
      // Do not join a pick-up and a later set-down into one shake.
      if (peaks < REQUIRED_PEAKS && now - quietSince >= 200) clearGesture();
    } else quiet = false;
    return false;
  }
};
