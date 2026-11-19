import tempfile
import unittest
from collections import deque
from pathlib import Path

from simulate import (Config, FLOWS, LegacyController, SafeController, comparison,
                      read_schedule, simulate, synthetic_schedule)


class TrafficTests(unittest.TestCase):
    def test_accessible_clearance_and_input_validation(self):
        self.assertEqual(Config().clearance, 18)  # 3 + ceil(12 / 0.8)
        self.assertEqual(Config(walking_metres_per_second=0.6).clearance, 23)
        for params in ({"walking_metres_per_second": 0}, {"crossing_metres": float("nan")},
                       {"max_green": 2}, {"yellow": 0}):
            with self.assertRaises(ValueError):
                Config(**params)

    def test_no_conflicts_across_multiple_demand_patterns(self):
        for seed in range(12):
            report = simulate(SafeController(), synthetic_schedule(1200, seed), 1200)
            self.assertEqual(report["conflicting_signal_seconds"], 0, seed)
            self.assertEqual(report["pedestrian_crossing_conflict_seconds"], 0, seed)

    def test_legacy_exposes_real_measurable_failures(self):
        schedule = {45: {"ped": 3}, 0: {"ns": 2, "ew": 2}}
        report = simulate(LegacyController(), schedule, 100)
        self.assertEqual(report["conflicting_signal_seconds"], 4)
        self.assertGreater(report["pedestrian_crossing_conflict_seconds"], 0)
        corrected = simulate(SafeController(), schedule, 100)
        self.assertEqual(corrected["pedestrian_crossing_conflict_seconds"], 0)

    def test_every_transition_has_yellow_and_red_clearance(self):
        config = Config()
        controller = SafeController(config)
        queues = {flow: deque([0]) for flow in FLOWS}
        outputs = [controller.step(tick, queues) for tick in range(220)]
        for tick, output in enumerate(outputs):
            if tick and output.phase != outputs[tick - 1].phase:
                previous = outputs[tick - 1].phase
                if previous == "NS_GREEN": self.assertEqual(output.phase, "NS_YELLOW")
                if previous == "EW_GREEN": self.assertEqual(output.phase, "EW_YELLOW")
                if previous in ("NS_YELLOW", "EW_YELLOW", "PED_CLEAR"):
                    self.assertEqual(output.phase, "ALL_RED")
                if previous == "ALL_RED":
                    self.assertIn(output.phase, ("NS_OPENING", "EW_OPENING", "PED_WALK"))
                    self.assertTrue(all(row.phase == "ALL_RED" for row in outputs[tick - config.all_red:tick]))
        for phase in ("NS_YELLOW", "EW_YELLOW"):
            runs = []
            count = 0
            for row in outputs:
                if row.phase == phase: count += 1
                elif count: runs.append(count); count = 0
            self.assertTrue(runs)
            self.assertTrue(all(run == config.yellow for run in runs))

    def test_all_pending_flows_get_fair_opportunities_under_saturation(self):
        controller = SafeController()
        queues = {flow: deque([0] * 10000) for flow in FLOWS}
        for tick in range(1000):
            controller.step(tick, queues)
        for flow in FLOWS:
            grants = [tick for tick, name in controller.grants if name == flow]
            self.assertGreater(len(grants), 10)
            self.assertLessEqual(grants[0], 80)
            self.assertLessEqual(max(b - a for a, b in zip(grants, grants[1:])), 80)

    def test_people_enter_only_in_walk_and_finish_before_vehicles(self):
        schedule = {tick: {"ped": 3, "ns": 1, "ew": 1} for tick in range(180)}
        report = simulate(SafeController(), schedule, 180, trace=True)
        rows = report["trace"]
        self.assertEqual(report["pedestrian_crossing_conflict_seconds"], 0)
        for index, row in enumerate(rows):
            if row["phase"] == "PED_WALK":
                for following in rows[index:index + Config().clearance]:
                    self.assertEqual((following["ns"], following["ew"]), ("red", "red"))

    def test_conservation_and_censored_queues_are_reported(self):
        schedule = {tick: {"ns": 2, "ew": 2, "ped": 1} for tick in range(180)}
        report = simulate(SafeController(), schedule, 180)
        for flow in FLOWS:
            metrics = report["flows"][flow]
            self.assertEqual(metrics["arrivals"], metrics["completed"]
                             + metrics["queued_at_end"] + metrics["crossing_at_end"])
            self.assertGreater(metrics["queued_at_end"], 0)
        self.assertGreater(report["flows"]["ns"]["largest_observed_wait_seconds"], 0)

    def test_reproducibility_and_fair_comparison(self):
        first = synthetic_schedule(600, 42)
        self.assertEqual(first, synthetic_schedule(600, 42))
        self.assertNotEqual(first, synthetic_schedule(600, 43))
        report = comparison(first, 600, 42)
        for flow in FLOWS:
            self.assertEqual(report["before_synthetic_legacy"]["flows"][flow]["arrivals"],
                             report["after_safe_controller"]["flows"][flow]["arrivals"])

    def test_csv_schema_and_repeated_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            path.write_text("second,flow,count\n0,ns,2\n0,ns,1\n2,ped,1\n", encoding="utf-8")
            self.assertEqual(read_schedule(path, 10)[0]["ns"], 3)
            path.write_text("second,flow,count\n11,ns,1\n", encoding="utf-8")
            with self.assertRaises(ValueError): read_schedule(path, 10)
            path.write_text("second,flow,count\n0,wrong,1\n", encoding="utf-8")
            with self.assertRaises(ValueError): read_schedule(path, 10)


if __name__ == "__main__":
    unittest.main()
