#include "../firmware/cyber_turtle/Feedback.h"
#include <cassert>
#include <cstdio>

int main() {
  Feedback disabled;
  disabled.begin(63, 100);
  disabled.testMotor(120);
  disabled.stage(Stage::Lower, 1500);
  disabled.stage(Stage::Reading, 2900);
  assert(disabled.mask(2900) == 0);
  assert(!disabled.motorOn(2900) && !disabled.blocksShake(2900));
  disabled.reset(3000);
  assert(!disabled.blocksShake(3000));

  Feedback lights(true, false);
  lights.begin((5 << 3) | 2, 100);
  for (unsigned group = 0; group < 8; ++group)
    assert(lights.mask(100 + group * 120) == (1u << group));
  assert(lights.mask(1060) == 1); // cursor loops after eight groups
  lights.stage(Stage::Upper, 1080); // repeated stage does not restart cursor
  assert(lights.mask(1180) == 2);
  lights.stage(Stage::Lower, 1500);
  assert(lights.mask(1500) == ((1u << 5) | 1));
  assert(lights.mask(1740) == ((1u << 5) | (1u << 2)));
  lights.testMotor(1750); // disabled motor cannot block shakes or change lights
  assert(lights.mask(1860) == ((1u << 5) | (1u << 3)));
  assert(!lights.motorOn(1860) && !lights.blocksShake(1860));
  lights.stage(Stage::Reading, 2900);
  assert(lights.mask(2900) == ((1u << 5) | (1u << 2)));
  lights.stage(Stage::Qr, 8900);
  assert(lights.mask(9900) == ((1u << 5) | (1u << 2)));
  lights.reset(10000);
  assert(lights.mask(10000) == 0);
  lights.begin((3 << 3) | 3, 10100);
  lights.stage(Stage::Lower, 11500);
  lights.stage(Stage::Reading, 12900);
  assert(lights.mask(12900) == (1u << 3)); // identical trigrams share one group

  Feedback motor(false, true);
  motor.begin(63, 100);
  assert(motor.motorOn(100) && motor.blocksShake(100));
  assert(motor.mask(100) == 0);
  motor.stage(Stage::Upper, 150); // duplicate must not extend the 80ms pulse
  assert(motor.motorOn(179));
  assert(!motor.motorOn(180) && motor.blocksShake(180));
  assert(motor.blocksShake(679));
  assert(!motor.blocksShake(680));
  motor.stage(Stage::Lower, 1500);
  assert(motor.motorOn(1579));
  assert(!motor.motorOn(1580));
  motor.stage(Stage::Lower, 1600);
  assert(!motor.motorOn(1600));
  motor.stage(Stage::Reading, 2900);
  assert(motor.motorOn(3039));
  assert(!motor.motorOn(3040));
  assert(!motor.blocksShake(3540));
  motor.stage(Stage::Reading, 3600);
  motor.stage(Stage::Qr, 4000);
  motor.stage(Stage::Reading, 4200);
  assert(!motor.motorOn(4200) && !motor.blocksShake(4200));

  Feedback both(true, true);
  both.begin((6 << 3) | 1, 100);
  both.reset(120); // immediate cancellation still needs a cooling interval
  assert(!both.motorOn(120) && both.mask(120) == 0);
  assert(both.blocksShake(619));
  both.reset(619); // repeated reset must not extend the cooling interval
  assert(!both.blocksShake(620));
  both.begin((6 << 3) | 1, 700);
  both.stage(Stage::Lower, 2100);
  both.stage(Stage::Reading, 3500);
  assert(!both.motorOn(3640));
  assert(!both.blocksShake(4140));
  both.testMotor(4200);
  assert(both.mask(4200) == ((1u << 6) | (1u << 1)));
  assert(both.motorOn(4339));
  assert(!both.motorOn(4340));
  assert(both.blocksShake(4839));
  assert(!both.blocksShake(4840));
  both.reset(4900);
  assert(!both.blocksShake(4900)); // resetting an inactive motor adds no delay
  both.testMotor(5000);
  assert(both.mask(5000) == 0); // a motor test does not leave Idle
  both.stage(Stage::Idle, 5010);
  both.reset(5020);
  assert(!both.motorOn(5020) && both.blocksShake(5020));

  Feedback late(false, true);
  late.testMotor(100);
  assert(!late.motorOn(1000)); // late poll observes the actual switch-off now
  assert(late.blocksShake(1499));
  assert(!late.blocksShake(1500));

  Feedback wrapped(true, true);
  uint32_t start = UINT32_MAX - 50;
  wrapped.begin((7 << 3) | 0, start);
  assert(wrapped.motorOn(start + 79));
  assert(!wrapped.motorOn(start + 80));
  assert(wrapped.blocksShake(start + 579));
  assert(!wrapped.blocksShake(start + 580));
  assert(wrapped.mask(start + 840) == 128);
  assert(wrapped.mask(start + 960) == 1);
  wrapped.stage(Stage::Lower, start + 1400);
  assert(wrapped.mask(start + 1400) == 129);
  wrapped.stage(Stage::Reading, start + 2800);
  assert(wrapped.mask(start + 2800) == 129);
  assert(wrapped.motorOn(start + 2939));
  wrapped.reset(start + 2940);
  assert(!wrapped.motorOn(start + 2940) && wrapped.mask(start + 2940) == 0);
  assert(wrapped.blocksShake(start + 3439));
  assert(!wrapped.blocksShake(start + 3440));
  puts("PASS: feedback defaults, LED groups, stage pulses, duplicate stages, reset, motor tests, cooling and timer wrap");
}
