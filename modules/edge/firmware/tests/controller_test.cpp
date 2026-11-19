#include "../territorio_crossing/TrafficController.h"
#include <cassert>
#include <iostream>
#include <limits>

using namespace crossing;

int main() {
  TrafficController controller;
  uint32_t lastGrant[3] = {0, 0, 0};
  int grants[3] = {0, 0, 0};
  Phase previous = Phase::AllRed;
  for (uint32_t now = 0; now <= 1000000; now += 100) {
    Output output = controller.tick(now, Demand{true, true, true});
    assert(output.valid());
    Phase current = controller.phase();
    if (current != previous) {
      if (previous == Phase::NsGreen) assert(current == Phase::NsYellow);
      if (previous == Phase::EwGreen) assert(current == Phase::EwYellow);
      if (previous == Phase::NsYellow || previous == Phase::EwYellow || previous == Phase::PedClear)
        assert(current == Phase::AllRed);
      int flow = current == Phase::NsGreen ? 0 : current == Phase::EwGreen ? 1
                 : current == Phase::PedWalk ? 2 : -1;
      if (flow >= 0) {
        if (grants[flow]) assert(now - lastGrant[flow] <= 80000);
        lastGrant[flow] = now;
        grants[flow]++;
      }
    }
    previous = current;
  }
  for (int count : grants) assert(count > 10);

  TrafficController pedestrian;
  assert(pedestrian.tick(2000, Demand{false, false, true}).pedestrian == Pedestrian::Walk);
  // Pedido de manutencao nao interrompe os 4 s de entrada + 18 s de limpeza.
  assert(pedestrian.tick(5999, Demand{false, false, false}, true).pedestrian == Pedestrian::Walk);
  assert(pedestrian.tick(6000, Demand{false, false, false}, true).pedestrian == Pedestrian::Clear);
  assert(pedestrian.tick(23999, Demand{false, false, false}, true).pedestrian == Pedestrian::Clear);
  assert(!pedestrian.isMaintenance());
  pedestrian.tick(24000, Demand{false, false, false}, true);
  assert(pedestrian.phase() == Phase::AllRed);
  pedestrian.tick(26000, Demand{false, false, false}, true);
  assert(pedestrian.isMaintenance());
  assert(pedestrian.output().valid());
  pedestrian.tick(27000, Demand{true, true, true}, true);
  assert(pedestrian.isMaintenance());
  pedestrian.tick(28000, Demand{true, true, true}, false);
  assert(pedestrian.phase() == Phase::AllRed);

  const uint32_t initial = std::numeric_limits<uint32_t>::max() - 1000;
  TrafficController rollover(initial);
  rollover.tick(initial + 1999U, Demand{true, false, false});
  assert(rollover.phase() == Phase::AllRed);
  rollover.tick(initial + 2000U, Demand{true, false, false});
  assert(rollover.phase() == Phase::NsOpening);
  rollover.tick(initial + 4000U, Demand{true, false, false});
  assert(rollover.phase() == Phase::NsGreen);
  rollover.fault(initial + 4001U);
  Output safe = rollover.tick(initial + 90000U, Demand{true, true, true});
  assert(rollover.phase() == Phase::Fault && safe.ns == Light::Red && safe.ew == Light::Red);
  assert(!safe.nsGateOpen && !safe.ewGateOpen && safe.pedestrian == Pedestrian::Red);

  Output invalid;
  invalid.ns = Light::Green;
  assert(!invalid.valid());
  invalid.nsGateOpen = true;
  assert(invalid.valid());
  invalid.ew = Light::Green;
  assert(!invalid.valid());
  std::cout << "C++: intertravamento, fairness, manutencao, falha e rollover aprovados.\n";
}
