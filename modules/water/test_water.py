"""Leakage, data integrity and independently recomputed evaluation checks.

Small constructed values below are unit-test fixtures only; they never enter the
official dataset, model training or dashboard.
"""
import copy
import hashlib
import json
import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from source import BASE, ROOT, Cache, load_rows, normalize, unavailable, write_json
from modeling import HORIZON, LOOKBACK, band, features, quantile_radius, samples, split_samples
from evaluate import evaluate
from portable_model import predict_delta


def fixture_rows(n=900):
    return [{"date": (date(2020, 1, 1) + timedelta(days=i)).isoformat(), "volumePct": 40 + i * .01, "rainMm": float(i % 4), "inflowM3s": 25.0, "withdrawalM3s": 20.0} for i in range(n)]


class DataIntegrity(unittest.TestCase):
    def test_real_cache_checksum_and_normalized_snapshot(self):
        cache = Cache(offline=True)
        for url, item in cache.manifest["responses"].items():
            with self.subTest(url=url):
                payload = (ROOT / item["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])
                self.assertTrue(json.loads(payload)["succeeded"])
        rows, quality = load_rows()
        self.assertEqual(len(rows), quality["rows"])
        self.assertEqual(rows[-1]["date"], quality["lastObservedAt"])
        self.assertGreater(len(rows), 500)

    def test_invalid_nan_future_and_duplicate_are_rejected(self):
        record = {"idSistema": 64, "date": "2026-01-01T00:00:00", "volumeUtilArmazenadoPorcentagem": 40.0}
        for records, cutoff in (([dict(record, volumeUtilArmazenadoPorcentagem=float("nan"))], date(2026, 1, 2)), ([record], date(2025, 12, 31)), ([record, record], date(2026, 1, 2))):
            with self.assertRaises(ValueError):
                normalize(records, cutoff)

    def test_cache_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "data/raw.json").write_text('{"succeeded":true,"data":[]}', encoding="utf-8")
            write_json(root / "data/manifest.json", {"responses": {BASE + "/test": {"file": "data/raw.json", "sha256": "wrong"}}})
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                Cache(root, offline=True).fetch("test")

    def test_failure_artifact_never_claims_real_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = unavailable("Erro de teste", Path(temporary))
            self.assertEqual(result["dataMode"], "unavailable")
            self.assertIsNone(result["forecast"])
            self.assertEqual(result["series"], [])
            self.assertTrue(result["alerts"][0]["requiresHumanReview"])


class TemporalEvaluation(unittest.TestCase):
    def test_feature_engineering_cannot_read_future(self):
        original = fixture_rows()
        modified = copy.deepcopy(original)
        for row in modified[101:]:
            for field in ("volumePct", "rainMm", "inflowM3s", "withdrawalM3s"):
                row[field] += 99999
        self.assertEqual(features(original, 100), features(modified, 100))

    def test_missing_history_or_target_is_never_interpolated(self):
        rows = fixture_rows(60)
        del rows[20]
        self.assertIsNone(features(rows, 25))
        result = samples(rows)
        self.assertFalse(any(s["inputStart"] <= "2020-01-21" <= s["targetDate"] for s in result))

    def test_all_features_and_targets_are_separated_between_partitions(self):
        rows = fixture_rows()
        parts = split_samples(rows, samples(rows))
        ordered = list(parts.values())
        for left, right in zip(ordered, ordered[1:]):
            self.assertLess(max(s["targetDate"] for s in left), min(s["inputStart"] for s in right))
            origin_gap = (date.fromisoformat(right[0]["origin"]) - date.fromisoformat(left[-1]["origin"])).days
            self.assertGreaterEqual(origin_gap, LOOKBACK + HORIZON + 1)
        for data in ordered:
            for s in data:
                self.assertEqual((date.fromisoformat(s["targetDate"]) - date.fromisoformat(s["origin"])).days, HORIZON)

    def test_interval_uses_upper_finite_sample_rank(self):
        self.assertEqual(quantile_radius(list(range(1, 11))), 10)

    def test_official_reference_band_boundaries(self):
        self.assertEqual([band(x) for x in (19.999, 20, 30, 40, 60)], ["Especial", "Restrição", "Alerta", "Atenção", "Normal"])

    def test_published_real_scores_and_coverage_recompute(self):
        result = evaluate()
        self.assertGreater(result["test"]["n"], 25)
        self.assertGreaterEqual(result["test"]["rmse"], result["test"]["mae"])
        self.assertTrue(0 <= result["coverage"] <= 1)

    def test_exported_model_reproduces_published_forecast(self):
        rows, _ = load_rows()
        model = json.loads((ROOT / "artifacts/model.json").read_text(encoding="utf-8"))
        dashboard = json.loads((ROOT / "artifacts/dashboard.json").read_text(encoding="utf-8"))
        reproduced = rows[-1]["volumePct"] + predict_delta(model, features(rows, len(rows) - 1))
        self.assertAlmostEqual(reproduced, dashboard["forecast"]["valuePct"], places=5)


if __name__ == "__main__":
    unittest.main()
