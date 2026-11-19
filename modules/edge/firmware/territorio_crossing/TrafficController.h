#pragma once
#include <stdint.h>

namespace crossing {
enum class Light { Red, Yellow, Green };
enum class Pedestrian { Red, Walk, Clear };
enum class Phase { AllRed, NsOpening, NsGreen, NsYellow, EwOpening, EwGreen,
                   EwYellow, PedWalk, PedClear, Maintenance, Fault };

struct Demand { bool ns; bool ew; bool pedestrian; };
struct Output {
  Light ns = Light::Red;
  Light ew = Light::Red;
  Pedestrian pedestrian = Pedestrian::Red;
  bool nsGateOpen = false;
  bool ewGateOpen = false;

  bool valid() const {
    if (ns != Light::Red && ew != Light::Red) return false;
    if (nsGateOpen && ewGateOpen) return false;
    if (pedestrian != Pedestrian::Red &&
        (ns != Light::Red || ew != Light::Red || nsGateOpen || ewGateOpen)) return false;
    if (ns == Light::Green && !nsGateOpen) return false;
    if (ew == Light::Green && !ewGateOpen) return false;
    return true;
  }
};

class TrafficController {
 public:
  static constexpr uint32_t MIN_GREEN = 8000;
  static constexpr uint32_t MAX_GREEN = 18000;
  static constexpr uint32_t YELLOW = 3000;
  static constexpr uint32_t ALL_RED = 2000;
  static constexpr uint32_t GATE_OPENING = 2000;
  static constexpr uint32_t WALK_ENTRY = 4000;
  // 3 s de partida + ceil(12 m / 0.8 m/s). Parametros de demonstracao.
  static constexpr uint32_t PED_CLEARANCE = 18000;

  explicit TrafficController(uint32_t now = 0) : entered_(now) {}
  Phase phase() const { return phase_; }
  bool isMaintenance() const { return phase_ == Phase::Maintenance; }
  void fault(uint32_t now) { enter(Phase::Fault, now); }

  Output tick(uint32_t now, Demand demand, bool maintenanceRequested = false) {
    // Subtracao sem sinal continua correta quando millis() transborda.
    const uint32_t elapsed = now - entered_;
    switch (phase_) {
      case Phase::AllRed:
        if (elapsed >= ALL_RED) {
          if (maintenanceRequested) enter(Phase::Maintenance, now);
          else {
            const bool pending[3] = {demand.ns, demand.ew, demand.pedestrian};
            for (int offset = 1; offset <= 3; ++offset) {
              const int flow = (lastFlow_ + offset) % 3;
              if (pending[flow]) {
                enter(flow == 0 ? Phase::NsOpening : flow == 1 ? Phase::EwOpening : Phase::PedWalk, now);
                break;
              }
            }
          }
        }
        break;
      case Phase::NsOpening:
      case Phase::EwOpening:
        if (maintenanceRequested) enter(Phase::AllRed, now);
        else if (elapsed >= GATE_OPENING)
          enter(phase_ == Phase::NsOpening ? Phase::NsGreen : Phase::EwGreen, now);
        break;
      case Phase::NsGreen:
      case Phase::EwGreen: {
        const bool ns = phase_ == Phase::NsGreen;
        const bool ownDemand = ns ? demand.ns : demand.ew;
        const bool competing = (ns ? demand.ew : demand.ns) || demand.pedestrian;
        if (elapsed >= MAX_GREEN || (elapsed >= MIN_GREEN &&
            (maintenanceRequested || (!ownDemand && competing))))
          enter(ns ? Phase::NsYellow : Phase::EwYellow, now);
        break;
      }
      case Phase::NsYellow:
      case Phase::EwYellow:
        if (elapsed >= YELLOW) enter(Phase::AllRed, now);
        break;
      case Phase::PedWalk:
        if (elapsed >= WALK_ENTRY) enter(Phase::PedClear, now);
        break;
      case Phase::PedClear:
        if (elapsed >= PED_CLEARANCE) enter(Phase::AllRed, now);
        break;
      case Phase::Maintenance:
        if (!maintenanceRequested) enter(Phase::AllRed, now);
        break;
      case Phase::Fault:
        break; // Falha travada: somente reinicio com diagnostico libera.
    }
    Output result = output();
    if (!result.valid()) {
      fault(now);
      return Output{};
    }
    return result;
  }

  Output output() const {
    Output out;
    switch (phase_) {
      case Phase::NsOpening: out.nsGateOpen = true; break;
      case Phase::NsGreen: out.ns = Light::Green; out.nsGateOpen = true; break;
      case Phase::NsYellow: out.ns = Light::Yellow; out.nsGateOpen = true; break;
      case Phase::EwOpening: out.ewGateOpen = true; break;
      case Phase::EwGreen: out.ew = Light::Green; out.ewGateOpen = true; break;
      case Phase::EwYellow: out.ew = Light::Yellow; out.ewGateOpen = true; break;
      case Phase::PedWalk: out.pedestrian = Pedestrian::Walk; break;
      case Phase::PedClear: out.pedestrian = Pedestrian::Clear; break;
      default: break;
    }
    return out;
  }

 private:
  Phase phase_ = Phase::AllRed;
  uint32_t entered_;
  int lastFlow_ = 2;

  void enter(Phase next, uint32_t now) {
    phase_ = next;
    entered_ = now;
    if (next == Phase::NsGreen) lastFlow_ = 0;
    if (next == Phase::EwGreen) lastFlow_ = 1;
    if (next == Phase::PedWalk) lastFlow_ = 2;
  }
};
}  // namespace crossing
