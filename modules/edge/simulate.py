"""Cruzamento didatico deterministico. Apenas biblioteca padrao do Python.

As duas politicas recebem exatamente as mesmas chegadas. O legado e uma
reconstrucao sintetica de defeitos comuns, nao o firmware real do professor.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

FLOWS = ("ns", "ew", "ped")


@dataclass(frozen=True)
class Config:
    min_green: int = 8
    max_green: int = 18
    yellow: int = 3
    all_red: int = 2
    gate_opening: int = 2
    walk_entry: int = 4
    crossing_metres: float = 12.0
    walking_metres_per_second: float = 0.8
    pedestrian_startup: int = 3

    def __post_init__(self):
        integral = (self.min_green, self.max_green, self.yellow, self.all_red,
                    self.gate_opening, self.walk_entry, self.pedestrian_startup)
        if any(type(value) is not int or value <= 0 for value in integral):
            raise ValueError("Tempos devem ser inteiros positivos.")
        if self.max_green < self.min_green:
            raise ValueError("Verde maximo menor que o minimo.")
        if (not math.isfinite(self.crossing_metres) or self.crossing_metres <= 0
                or not math.isfinite(self.walking_metres_per_second)
                or self.walking_metres_per_second <= 0):
            raise ValueError("Distancia e velocidade devem ser finitas e positivas.")

    @property
    def clearance(self):
        # Parametro didatico conservador; nao e dimensionamento regulamentar.
        return self.pedestrian_startup + math.ceil(
            self.crossing_metres / self.walking_metres_per_second)


@dataclass(frozen=True)
class Outputs:
    phase: str
    ns: str = "red"
    ew: str = "red"
    pedestrian: str = "red"
    gate_ns_open: bool = False
    gate_ew_open: bool = False

    def conflicts(self):
        faults = []
        if self.ns != "red" and self.ew != "red":
            faults.append("vehicle_conflict")
        if self.pedestrian != "red" and (self.ns != "red" or self.ew != "red"):
            faults.append("pedestrian_signal_conflict")
        if self.ns == "green" and not self.gate_ns_open:
            faults.append("ns_gate_closed_on_green")
        if self.ew == "green" and not self.gate_ew_open:
            faults.append("ew_gate_closed_on_green")
        if self.pedestrian != "red" and (self.gate_ns_open or self.gate_ew_open):
            faults.append("gate_open_during_crossing")
        return faults


class SafeController:
    """Maquina de estados com intertravamento e concessao circular de fases.

    Fairness garante oportunidades de fase, nao espera limitada por pessoa em
    demanda acima da capacidade. Nao interrompe travessia nem elimina amarelo.
    """
    def __init__(self, config=Config()):
        self.config = config
        self.phase = "ALL_RED"
        self.entered = 0
        self.last_flow = 2  # primeiro ciclo inicia em ns, se houver demanda
        self.grants = []

    def _enter(self, phase, tick):
        self.phase, self.entered = phase, tick
        if phase in ("NS_GREEN", "EW_GREEN", "PED_WALK"):
            flow = {"NS_GREEN": "ns", "EW_GREEN": "ew", "PED_WALK": "ped"}[phase]
            self.last_flow = FLOWS.index(flow)
            self.grants.append((tick, flow))

    def _next_flow(self, queues):
        for offset in range(1, 4):
            flow = FLOWS[(self.last_flow + offset) % 3]
            if queues[flow]:
                return flow
        return None

    def step(self, tick, queues):
        c = self.config
        elapsed = tick - self.entered
        p = self.phase
        if p == "ALL_RED" and elapsed >= c.all_red:
            flow = self._next_flow(queues)
            if flow:
                self._enter({"ns": "NS_OPENING", "ew": "EW_OPENING", "ped": "PED_WALK"}[flow], tick)
        elif p in ("NS_OPENING", "EW_OPENING") and elapsed >= c.gate_opening:
            self._enter(p.replace("OPENING", "GREEN"), tick)
        elif p in ("NS_GREEN", "EW_GREEN"):
            current = "ns" if p == "NS_GREEN" else "ew"
            competing = any(queues[other] for other in FLOWS if other != current)
            if elapsed >= c.max_green or (elapsed >= c.min_green and not queues[current] and competing):
                self._enter(p.replace("GREEN", "YELLOW"), tick)
        elif p in ("NS_YELLOW", "EW_YELLOW") and elapsed >= c.yellow:
            self._enter("ALL_RED", tick)
        elif p == "PED_WALK" and elapsed >= c.walk_entry:
            self._enter("PED_CLEAR", tick)
        elif p == "PED_CLEAR" and elapsed >= c.clearance:
            self._enter("ALL_RED", tick)
        result = self.outputs()
        if result.conflicts():
            raise RuntimeError("Falha de intertravamento: " + str(result.conflicts()))
        return result

    def outputs(self):
        p = self.phase
        if p in ("NS_OPENING", "NS_GREEN", "NS_YELLOW"):
            return Outputs(p, ns={"NS_OPENING": "red", "NS_GREEN": "green", "NS_YELLOW": "yellow"}[p],
                           gate_ns_open=True)
        if p in ("EW_OPENING", "EW_GREEN", "EW_YELLOW"):
            return Outputs(p, ew={"EW_OPENING": "red", "EW_GREEN": "green", "EW_YELLOW": "yellow"}[p],
                           gate_ew_open=True)
        if p in ("PED_WALK", "PED_CLEAR"):
            return Outputs(p, pedestrian="walk" if p == "PED_WALK" else "clear")
        return Outputs(p)


class LegacyController:
    """Baseline defeituoso e SINTETICO; jamais usar em hardware.

    Ciclo fixo: NS 0..37, EW 36..44 (sobreposicao!), pedestres 45..49.
    Sem amarelo, sem intervalo vermelho e sem tempo de travessia suficiente.
    """
    def step(self, tick, queues):
        second = tick % 50
        ns = second < 38
        ew = 36 <= second < 45
        ped = second >= 45
        return Outputs("LEGACY", "green" if ns else "red", "green" if ew else "red",
                       "walk" if ped else "red", ns, ew)


def synthetic_schedule(duration, seed):
    if duration <= 0:
        raise ValueError("Duracao deve ser positiva.")
    generator = random.Random(seed)
    schedule = {}
    for tick in range(duration):
        # Pico inicial em NS, seguido de maior demanda em EW.
        probabilities = ((0.30 if tick < duration / 2 else 0.16),
                         (0.12 if tick < duration / 2 else 0.25), 0.07)
        counts = {flow: int(generator.random() < p) for flow, p in zip(FLOWS, probabilities)}
        if any(counts.values()):
            schedule[tick] = counts
    return schedule


def read_schedule(path, duration):
    """CSV do laboratorio: second,flow,count; nao coleta dados pessoais."""
    schedule = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["second", "flow", "count"]:
            raise ValueError("Cabecalho esperado: second,flow,count")
        for row in reader:
            second, flow, count = int(row["second"]), row["flow"], int(row["count"])
            if second < 0 or second >= duration or flow not in FLOWS or count < 0:
                raise ValueError("Chegada invalida: " + str(row))
            counts = schedule.setdefault(second, {name: 0 for name in FLOWS})
            counts[flow] += count
    return schedule


def simulate(controller, schedule, duration, config=Config(), trace=False):
    if duration <= 0:
        raise ValueError("Duracao deve ser positiva.")
    queues = {flow: deque() for flow in FLOWS}
    waits = {flow: [] for flow in FLOWS}
    arrivals = {flow: 0 for flow in FLOWS}
    queue_area = {flow: 0 for flow in FLOWS}
    crossing_ends = []
    completed_pedestrians = 0
    conflicting_seconds = 0
    crossing_conflict_seconds = 0
    trace_rows = []
    for tick in range(duration):
        for flow, count in schedule.get(tick, {}).items():
            if flow not in FLOWS or type(count) is not int or count < 0:
                raise ValueError("Fluxo ou contagem invalida.")
            queues[flow].extend([tick] * count)
            arrivals[flow] += count
        completed_pedestrians += sum(end <= tick for end in crossing_ends)
        crossing_ends = [end for end in crossing_ends if end > tick]
        output = controller.step(tick, queues)
        conflicting_seconds += bool(output.conflicts())
        crossing_conflict_seconds += bool(crossing_ends and (output.ns != "red" or output.ew != "red"))
        for flow, signal in (("ns", output.ns), ("ew", output.ew)):
            if signal == "green" and queues[flow]:
                waits[flow].append(tick - queues[flow].popleft())
        if output.pedestrian == "walk":
            # Capacidade didatica: ate tres pessoas iniciam por segundo.
            for _ in range(min(3, len(queues["ped"]))):
                waits["ped"].append(tick - queues["ped"].popleft())
                crossing_ends.append(tick + config.clearance)
        for flow in FLOWS:
            queue_area[flow] += len(queues[flow])
        if trace:
            trace_rows.append({"second": tick, **asdict(output),
                               "queues": {flow: len(queues[flow]) for flow in FLOWS}})
    # Uma travessia concluida exatamente no horizonte conta como concluida.
    completed_pedestrians += sum(end <= duration for end in crossing_ends)
    unfinished_crossings = sum(end > duration for end in crossing_ends)
    flows = {}
    for flow in FLOWS:
        observed = waits[flow] + [duration - arrival for arrival in queues[flow]]
        flows[flow] = {
            "arrivals": arrivals[flow], "started": len(waits[flow]),
            "completed": completed_pedestrians if flow == "ped" else len(waits[flow]),
            "queued_at_end": len(queues[flow]),
            "crossing_at_end": unfinished_crossings if flow == "ped" else 0,
            "mean_wait_started_seconds": round(sum(waits[flow]) / len(waits[flow]), 3) if waits[flow] else None,
            "largest_observed_wait_seconds": max(observed, default=0),
            "mean_queue": round(queue_area[flow] / duration, 3),
        }
    result = {"flows": flows, "conflicting_signal_seconds": conflicting_seconds,
              "pedestrian_crossing_conflict_seconds": crossing_conflict_seconds}
    if trace:
        result["trace"] = trace_rows
    return result


def comparison(schedule, duration, seed=None, source="synthetic"):
    config = Config()
    return {
        "scenario": {"source": source, "seed": seed, "duration_seconds": duration,
                     "config": asdict(config), "pedestrian_clearance_seconds": config.clearance,
                     "notice": "Simulacao didatica; baseline nao e algoritmo do professor."},
        "before_synthetic_legacy": simulate(LegacyController(), schedule, duration, config),
        "after_safe_controller": simulate(SafeController(config), schedule, duration, config),
        "measurement_limits": [
            "Espera media considera quem iniciou atendimento; filas finais sao exibidas para evitar ocultar censura.",
            "Largest observed wait inclui a espera ja acumulada de quem segue na fila.",
            "Fairness oferece fases a todos os fluxos pendentes; demanda acima da capacidade pode aumentar filas.",
            "Conflitos sao eventos da simulacao, nao acidentes observados nem evidencia de hardware.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--input", type=Path, help="CSV second,flow,count do laboratorio")
    parser.add_argument("--output", type=Path, help="Salvar relatorio JSON")
    args = parser.parse_args()
    schedule = (read_schedule(args.input, args.duration) if args.input
                else synthetic_schedule(args.duration, args.seed))
    report = comparison(schedule, args.duration, None if args.input else args.seed,
                        str(args.input) if args.input else "synthetic")
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
