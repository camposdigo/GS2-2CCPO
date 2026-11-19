"""Exploration and scientific figures from the real cached observation snapshot."""
import csv
import json
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from source import ROOT, load_rows, write_json


def analyze(root=ROOT):
    rows, quality = load_rows(root)
    report = json.loads((root / "artifacts/evaluation.json").read_text(encoding="utf-8"))
    with (root / "artifacts/test_predictions.csv").open(encoding="utf-8", newline="") as f:
        predictions = list(csv.DictReader(f))
    volume = np.asarray([r["volumePct"] for r in rows])
    rain = np.asarray([r["rainMm"] for r in rows])
    summary = {"rows": len(rows), "start": rows[0]["date"], "end": rows[-1]["date"], "missingDates": len(quality["missingDates"]), "nulls": quality["nullFields"], "volumePct": {"min": float(np.min(volume)), "p25": float(np.quantile(volume, .25)), "median": float(np.median(volume)), "p75": float(np.quantile(volume, .75)), "max": float(np.max(volume)), "mean": float(np.mean(volume)), "std": float(np.std(volume))}, "rainMm": {"meanDaily": float(np.mean(rain)), "maxDaily": float(np.max(rain)), "zeroDays": int(np.sum(rain == 0))}, "correlationRainAndSameDayVolumeChange": float(np.corrcoef(rain[1:], np.diff(volume))[0, 1]), "correlationCaution": "Correlação exploratória contemporânea, sem interpretação causal nem uso na seleção de features após olhar o teste.", "byYear": []}
    for year in sorted({r["date"][:4] for r in rows}):
        values = [r for r in rows if r["date"].startswith(year)]
        summary["byYear"].append({"year": int(year), "days": len(values), "meanVolumePct": round(float(np.mean([r["volumePct"] for r in values])), 3), "rainSumMm": round(sum(r["rainMm"] for r in values), 3)})
    write_json(root / "artifacts/exploration.json", summary)
    figures = root / "artifacts/figures"
    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none"})
    dates = [date.fromisoformat(r["date"]) for r in rows]
    fig, ax = plt.subplots(figsize=(12, 4.2), layout="constrained")
    ax.plot(dates, volume, color="#087f8c", linewidth=1.4, label="Volume observado — SABESP")
    for level in (20, 30, 40, 60):
        ax.axhline(level, color="#777777", linewidth=.6, linestyle=":", alpha=.7)
    ax.set(title="Cantareira: volume útil observado (série real)", ylabel="Volume útil (%)", xlabel="Data de observação")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper left")
    fig.savefig(figures / "volume_historico.svg", metadata={"Date": None})
    plt.close(fig)
    dates_test = [date.fromisoformat(r["targetDate"]) for r in predictions]
    actual = np.array([float(r["actualPct"]) for r in predictions])
    estimate = np.array([float(r["predictedPct"]) for r in predictions])
    lower, upper = [[float(r[key]) for r in predictions] for key in ("lowerPct", "upperPct")]
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, layout="constrained", gridspec_kw={"height_ratios": [2, 1]})
    axes[0].fill_between(dates_test, lower, upper, color="#087f8c", alpha=.18, label=f"Intervalo nominal 90%; cobertura real {report['coverage']:.1%}")
    axes[0].plot(dates_test, actual, color="#152238", linewidth=1.5, label="Alvo observado")
    axes[0].plot(dates_test, estimate, color="#087f8c", linewidth=1.1, label="Modelo: previsão feita sete dias antes")
    axes[0].set(title="Teste temporal preservado: previsão e volume observado", ylabel="Volume útil (%)")
    axes[0].legend(loc="upper left", fontsize=8)
    axes[1].plot(dates_test, estimate - actual, color="#a6532c", linewidth=.9)
    axes[1].axhline(0, color="#555555", linewidth=.8)
    axes[1].set(ylabel="Erro (p.p.)", xlabel="Data do alvo (origem = data − 7 dias)")
    fig.savefig(figures / "avaliacao_temporal.svg", metadata={"Date": None})
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    ax.bar(["Modelo selecionado", "Persistência", "Deriva 7 dias"], [report[k]["mae"] for k in ("test", "baseline", "drift")], color=["#087f8c", "#8a8d91", "#c28a50"])
    ax.set(title="Mesmo período e mesmos alvos: comparação no teste", ylabel="MAE (p.p.; menor é melhor)")
    for i, key in enumerate(("test", "baseline", "drift")):
        ax.text(i, report[key]["mae"] + .02, f"{report[key]['mae']:.3f}", ha="center")
    ax.set_ylim(0, max(report[k]["mae"] for k in ("test", "baseline", "drift")) * 1.18)
    fig.savefig(figures / "comparacao_baselines.svg", metadata={"Date": None})
    plt.close(fig)
    return summary


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
