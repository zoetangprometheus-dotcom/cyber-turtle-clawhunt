#include "../firmware/cyber_turtle/Flow.h"
#include "../firmware/cyber_turtle/Hexagrams.h"
#include "../firmware/cyber_turtle/QrLink.h"
#include <cassert>
#include <cstdio>
#include <limits>
#include <cstring>

int main() {
  Flow f;
  assert(f.start(10));
  assert(!f.start(20)); // One physical gesture creates one event while busy.
  assert(!f.tick(1409));
  assert(f.tick(1410) && f.stage == Stage::Lower);
  assert(f.tick(2810) && f.stage == Stage::Reading);
  assert(!f.tick(8809) && f.stage == Stage::Reading);
  assert(f.tick(8810) && f.stage == Stage::Qr);
  assert(!f.tick(999999)); // QR stays visible; tapping returns to both trigrams.
  assert(f.toggleResult(1000000) && f.stage == Stage::Reading);
  assert(f.toggleResult(1000000) && f.stage == Stage::Qr);
  assert(f.start(1000000)); // A fresh shake may start another reading.
  f.reset(1000000); assert(f.start(1000001));
  f.reset(UINT32_MAX - 500); assert(f.start(UINT32_MAX - 500));
  assert(f.tick(900) && f.stage == Stage::Lower);
  assert(!f.toggleResult(901));
  const std::string base = "https://example.org/turtle/";
  assert(makeQrLink(base, 64, 1, 2, 3) == base + "#d=64.0000000100000002.3");
  assert(makeQrLink(base, 1, UINT32_MAX, UINT32_MAX, UINT32_MAX) == base + "#d=1.ffffffffffffffff.4294967295");
  assert(makeQrLink(base, 0, 1, 2, 3).empty());
  assert(makeQrLink(base, 65, 1, 2, 3).empty());
  assert(makeQrLink(base, 1, 1, 2, 0).empty());
  for (const char *bad : {"", "http://example.org", "https://", "https:///a", "https://user@host", "https://host/?a", "https://host/#a", "https://host/ a", "https://host/\n"})
    assert(!validQrBase(bad));

  bool masks[64] = {};
  for (unsigned i = 0; i < 64; ++i) {
    const auto &h = HEXAGRAMS[i];
    assert(h.id == i + 1 && h.lines < 64 && !masks[h.lines]);
    masks[h.lines] = true;
    assert(h.upper[0] && h.lower[0]);
  }
  assert(HEXAGRAMS[0].lines == 63 && !strcmp(HEXAGRAMS[0].upper, "乾"));
  assert(HEXAGRAMS[1].lines == 0 && !strcmp(HEXAGRAMS[1].lower, "坤"));
  assert(HEXAGRAMS[2].lines == 17 && !strcmp(HEXAGRAMS[2].upper, "坎") && !strcmp(HEXAGRAMS[2].lower, "震"));

  // Sensor traces at the real 50Hz polling rate. Rotation keeps norm near 1g,
  // reproducing the old magnitude-only detector's blind spot.
  for (unsigned scenario = 0; scenario < 19; ++scenario) {
    ShakeDetector s;
    unsigned events = 0;
    for (unsigned t = 0; t < 6000; t += 20) {
      float x = 0, y = 0, z = 1.045f;
      if (scenario == 0) x = 0.02f * sinf(t * 0.07f); // idle noise
      if (scenario == 1 && t == 500) x = 0.8f; // single short bump
      if (scenario == 2) { float a = t * 0.0002f; x = sinf(a); z = cosf(a); } // slow tilt
      bool shaking = t >= 500 && t < 1700;
      float wave = 0.65f * sinf((t - 500.0f) * 0.015708f);
      if (scenario == 3 && shaking) x = wave; // three continuous back-and-forth cycles
      if (scenario == 4 && shaking) { x = sinf(wave); z = cosf(wave); } // wrist rotation
      if (scenario == 5 && t >= 500) x = 0.8f; // sustained offset is not repeated shaking
      if (scenario == 6 && shaking) x = wave * (0.35f / 0.65f); // light sway used to trigger
      if (scenario == 7 && (t == 500 || t == 740 || t == 980)) x = 0.9f; // three handling bumps
      if (scenario == 8 && t >= 500 && t < 900) x = wave; // one brief back-and-forth is insufficient
      if (scenario == 9 && t >= 500 && t < 1100) // set-down shock followed by a decaying ring
        x = t == 500 ? 1.8f : 0.8f * expf(-(t-500.0f)/120.0f) * sinf((t-500.0f)*0.05f);
      if (scenario == 10 && (t == 500 || t == 1100 || t == 1700 || t == 2300))
        x = 1.0f; // separated same-direction bumps used to accumulate
      if (scenario == 11) { // pick up, hold still, then set down within three seconds
        if ((t >= 500 && t < 580) || (t >= 1740 && t < 1820)) x = 1;
        if ((t >= 740 && t < 820) || (t >= 1980 && t < 2060)) x = -1;
      }
      if (scenario == 12 && t >= 500 && t < 1300) x = wave; // two continuous cycles
      if (scenario == 13 && t >= 500 && t < 1700 && (t-500)%200 == 0)
        x = ((t-500)/200)%2 ? -1.0f : 1.0f; // six alternating 20ms impacts
      if (scenario == 14) { // two cycles split by a pause are not one gesture
        if (t >= 500 && t < 900) x = wave;
        if (t >= 2100 && t < 2500) x = 0.65f * sinf((t-2100.0f)*0.015708f);
      }
      if (scenario == 15 && shaking) { y = wave; z += wave * 0.3f; } // another shake axis
      if ((scenario == 16 || scenario == 17) && t >= 500 && t < 2300) {
        float gentle = 0.5f * sinf((t-500.0f)*0.010472f); // slower 600ms cycles
        if (scenario == 16) x = gentle;
        else { x = sinf(gentle); z = cosf(gentle); }
      }
      if (scenario == 18 && t >= 500 && t < 2100) // sustained same-direction knocks
        x = ((t-500)%400 < 80) ? 0.8f : 0;
      if (s.update(x, y, z, UINT32_MAX - 1000 + t)) {
        ++events;
        unsigned end = scenario == 12 ? 1300 : (scenario == 16 || scenario == 17 ? 2300 : 1700);
        assert(t >= end + 400); // the gesture must finish and settle
      }
    }
    assert(events == ((scenario == 3 || scenario == 4 || scenario == 12 ||
                      scenario == 15 || scenario == 16 || scenario == 17) ? 1u : 0u));
  }
  ShakeDetector s;
  assert(!s.update(0, 0, 1, 0));
  assert(!s.update(std::numeric_limits<float>::quiet_NaN(), 0, 1, 20));
  for (unsigned t = 0; t < 4000; t += 200) assert(!s.update(t % 400 ? 1 : -1, 0, 1, t));
  puts("PASS: result/QR flow, timer wrap, 64 mappings; 19 motion traces reject handling and impacts; two-cycle and gentler/slower translation/wrist gestures pass");
}
