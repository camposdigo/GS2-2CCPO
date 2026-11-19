"""Independently recompute published scores from the immutable test predictions."""
import csv
import json
import math
from source import ROOT


def evaluate(root=ROOT):
    report = json.loads((root / "artifacts/evaluation.json").read_text(encoding="utf-8"))
    with (root / "artifacts/test_predictions.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    result = {}
    for label, column in (("test", "predictedPct"), ("baseline", "persistencePct"), ("drift", "driftPct")):
        errors = [float(row[column]) - float(row["actualPct"]) for row in rows]
        metrics = {"mae": sum(abs(e) for e in errors) / len(errors), "rmse": math.sqrt(sum(e * e for e in errors) / len(errors))}
        for metric, value in metrics.items():
            if not math.isclose(value, report[label][metric], abs_tol=0.000002):
                raise AssertionError(f"Métrica publicada diverge: {label}/{metric}")
        result[label] = {**metrics, "n": len(rows)}
    coverage = sum(float(row["lowerPct"]) <= float(row["actualPct"]) <= float(row["upperPct"]) for row in rows) / len(rows)
    if not math.isclose(coverage, report["coverage"], abs_tol=0.000002):
        raise AssertionError("Cobertura publicada diverge")
    result["coverage"] = coverage
    return result


if __name__ == "__main__":
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
