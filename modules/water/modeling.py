"""Seven-day supervised regression with chronological, purged evaluation."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from source import ROOT, load_rows, now, write_json
from portable_model import export

LOOKBACK = 14
HORIZON = 7
FEATURES = ["volume_t", "volume_t_minus_1", "volume_t_minus_7", "volume_t_minus_14", "change_1d", "change_7d", "change_14d", "rain_7d_mm", "rain_14d_mm", "inflow_7d_m3s", "withdrawal_7d_m3s", "annual_sin", "annual_cos"]
REGULATION_URL = "https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias/2017/925"
LIMITATIONS = [
    "Estimativa acadêmica de volume útil a 7 dias; não é previsão oficial nem indicação de potabilidade.",
    "Intervalo empírico calibrado em resíduos passados; dependência temporal e mudanças de operação/clima podem reduzir a cobertura futura.",
    "Sem chuva futura, previsão meteorológica, demanda municipal ou modelagem física dos reservatórios.",
    "Volume agregado do Cantareira não descreve disponibilidade por bairro, desigualdade de acesso ou qualidade da água.",
    "Faixa diária de referência não determina a faixa operacional mensal, que depende de decisão ANA/SP-Águas.",
    "Qualquer ação de alto impacto exige validação e decisão humana de profissional responsável.",
]


def features(rows, i):
    if i < LOOKBACK:
        return None
    window = rows[i - LOOKBACK:i + 1]
    origin = date.fromisoformat(rows[i]["date"])
    if any(date.fromisoformat(row["date"]) != origin - timedelta(days=LOOKBACK - j) for j, row in enumerate(window)):
        return None
    if any(row[field] is None for row in window for field in ("volumePct", "rainMm", "inflowM3s", "withdrawalM3s")):
        return None
    level = lambda lag: rows[i - lag]["volumePct"]
    recent7, recent14 = rows[i - 6:i + 1], rows[i - 13:i + 1]
    phase = 2 * math.pi * (origin.timetuple().tm_yday - 1) / 365.2425
    return [level(0), level(1), level(7), level(14), level(0) - level(1), level(0) - level(7), level(0) - level(14), sum(r["rainMm"] for r in recent7), sum(r["rainMm"] for r in recent14), sum(r["inflowM3s"] for r in recent7) / 7, sum(r["withdrawalM3s"] for r in recent7) / 7, math.sin(phase), math.cos(phase)]


def samples(rows):
    result = []
    for i in range(LOOKBACK, len(rows) - HORIZON):
        x = features(rows, i)
        if x is None:
            continue
        origin = date.fromisoformat(rows[i]["date"])
        # Need an actual target exactly seven calendar days after the origin.
        if any(date.fromisoformat(rows[i + j]["date"]) != origin + timedelta(days=j) for j in range(1, HORIZON + 1)):
            continue
        result.append({"origin": rows[i]["date"], "inputStart": rows[i - LOOKBACK]["date"], "targetDate": rows[i + HORIZON]["date"], "x": x, "level": rows[i]["volumePct"], "y": rows[i + HORIZON]["volumePct"], "delta": rows[i + HORIZON]["volumePct"] - rows[i]["volumePct"], "drift": rows[i]["volumePct"] + HORIZON * (rows[i]["volumePct"] - rows[i - 7]["volumePct"]) / 7})
    return result


def split_samples(rows, data):
    # Splits are determined from observation dates before looking at any labels.
    n = len(rows)
    boundaries = [rows[int(n * f)]["date"] for f in (0, .60, .75, .85)]
    end = (date.fromisoformat(rows[-1]["date"]) + timedelta(days=1)).isoformat()
    spans = list(zip(boundaries, boundaries[1:] + [end]))
    parts = {}
    for name, (start, stop) in zip(("train", "validation", "calibration", "test"), spans):
        # Each complete feature/target window must fit inside one partition.
        # This excludes 14 days after + 7 days before each internal boundary.
        parts[name] = [s for s in data if s["inputStart"] >= start and s["targetDate"] < stop]
        if len(parts[name]) < 25:
            raise ValueError(f"Partição {name} insuficiente: {len(parts[name])} amostras")
    ordered = list(parts.values())
    for left, right in zip(ordered, ordered[1:]):
        if max(s["targetDate"] for s in left) >= min(s["inputStart"] for s in right):
            raise AssertionError("Vazamento entre janelas temporais")
    return parts


def score(actual, predicted):
    error = np.asarray(actual) - np.asarray(predicted)
    return {"mae": round(float(np.mean(np.abs(error))), 6), "rmse": round(float(np.sqrt(np.mean(error ** 2))), 6), "bias": round(float(-np.mean(error)), 6), "n": len(error), "unit": "p.p. de volume útil"}


def predict(model, data):
    return np.array([s["level"] for s in data]) + model.predict(np.array([s["x"] for s in data]))


def candidates():
    for alpha in (0.1, 1.0, 10.0, 100.0):
        yield f"ridge_alpha_{alpha:g}", make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    for depth, leaf in ((6, 10), (12, 5)):
        yield f"random_forest_depth_{depth}_leaf_{leaf}", RandomForestRegressor(n_estimators=180, max_depth=depth, min_samples_leaf=leaf, random_state=42, n_jobs=1)


def quantile_radius(residuals, level=.9):
    # Finite-sample upper rank; exchangeability is NOT asserted for this series.
    rank = min(len(residuals), math.ceil((len(residuals) + 1) * level))
    return float(sorted(residuals)[rank - 1])


def band(value):
    if value >= 60:
        return "Normal"
    if value >= 40:
        return "Atenção"
    if value >= 30:
        return "Alerta"
    if value >= 20:
        return "Restrição"
    return "Especial"


def run(root: Path = ROOT, as_of: date | None = None):
    rows, quality = load_rows(root)
    if len(rows) < 500:
        raise ValueError("Histórico insuficiente: mínimo 500 observações reais")
    data = samples(rows)
    parts = split_samples(rows, data)
    train, validation, calibration, test = [parts[k] for k in ("train", "validation", "calibration", "test")]
    x_train = np.array([s["x"] for s in train])
    y_train = np.array([s["delta"] for s in train])
    ranking = []
    fitted = {}
    for name, model in candidates():
        model.fit(x_train, y_train)
        result = score([s["y"] for s in validation], predict(model, validation))
        ranking.append({"model": name, **result})
        fitted[name] = model
    ranking.sort(key=lambda item: (item["mae"], item["model"]))
    selected = ranking[0]["model"]
    model = fitted[selected]
    model_snapshot = export(model, FEATURES)
    model_snapshot.update({"name": selected, "datasetSha256": quality["normalizedSha256"], "trainedThrough": train[-1]["targetDate"], "selectedThrough": validation[-1]["targetDate"], "frozen": True})
    write_json(root / "artifacts/model.json", model_snapshot)
    # Freeze the selected model. No refit on calibration or test.
    validation_baseline = score([s["y"] for s in validation], [s["level"] for s in validation])
    validation_drift = score([s["y"] for s in validation], [s["drift"] for s in validation])
    cal_sparse = calibration[::HORIZON]
    cal_pred = predict(model, cal_sparse)
    residuals = np.abs(np.array([s["y"] for s in cal_sparse]) - cal_pred)
    radius = quantile_radius(residuals)
    test_pred = predict(model, test)
    actual = np.array([s["y"] for s in test])
    test_metrics = score(actual, test_pred)
    baseline_metrics = score(actual, [s["level"] for s in test])
    drift_metrics = score(actual, [s["drift"] for s in test])
    covered = np.abs(actual - test_pred) <= radius
    nonoverlap = covered[::HORIZON]
    partition_metadata = {name: {"n": len(items), "firstInputDate": items[0]["inputStart"], "firstOrigin": items[0]["origin"], "lastOrigin": items[-1]["origin"], "lastTargetDate": items[-1]["targetDate"]} for name, items in parts.items()}
    evaluation = {"schemaVersion": 1, "generatedAt": now(), "datasetSha256": quality["normalizedSha256"], "target": "volume útil Cantareira em t+7; modelo aprende variação em p.p.", "lookbackDays": LOOKBACK, "horizonDays": HORIZON, "seed": 42, "selectionRule": "Menor MAE na validação; teste não participa da seleção. Modelo permanece congelado após treino.", "split": "Cronológico 60%/15%/10%/15%; janelas inteiras em cada partição; exclusão de 21 origens por fronteira (14 de histórico + 7 de horizonte).", "partitions": partition_metadata, "featureNames": FEATURES, "selectedModel": selected, "candidates": ranking, "validationBaseline": validation_baseline, "validationDrift": validation_drift, "test": test_metrics, "baseline": baseline_metrics, "drift": drift_metrics, "relativeMaeImprovementVsPersistence": round(1 - test_metrics["mae"] / baseline_metrics["mae"], 6), "interval": {"method": "Raio do quantil superior de resíduos absolutos de calibração, origens a cada 7 dias", "nominalCoverage": .9, "radiusPp": round(radius, 6), "calibrationSamples": len(cal_sparse), "testCoverage": round(float(np.mean(covered)), 6), "nonOverlappingTestCoverage": round(float(np.mean(nonoverlap)), 6), "nonOverlappingTestSamples": len(nonoverlap), "meanWidthPp": round(radius * 2, 6), "guarantee": "Sem garantia de cobertura futura: série temporal não permutável; cobertura publicada é empírica."}, "coverage": round(float(np.mean(covered)), 6), "versions": {"python": platform.python_version(), "numpy": np.__version__, "scikitLearn": sklearn.__version__}, "limitations": LIMITATIONS}
    write_json(root / "artifacts/evaluation.json", evaluation)
    prediction_path = root / "artifacts/test_predictions.csv"
    with prediction_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["origin", "targetDate", "actualPct", "predictedPct", "persistencePct", "driftPct", "lowerPct", "upperPct", "covered"])
        writer.writeheader()
        for sample, estimate, is_covered in zip(test, test_pred, covered):
            writer.writerow({"origin": sample["origin"], "targetDate": sample["targetDate"], "actualPct": sample["y"], "predictedPct": round(float(estimate), 6), "persistencePct": sample["level"], "driftPct": round(sample["drift"], 6), "lowerPct": round(float(estimate - radius), 6), "upperPct": round(float(estimate + radius), 6), "covered": bool(is_covered)})
    latest = rows[-1]
    x_latest = features(rows, len(rows) - 1)
    if x_latest is None:
        raise ValueError("Janela atual incompleta: nenhuma previsão publicada")
    forecast_value = latest["volumePct"] + float(model.predict(np.asarray([x_latest]))[0])
    target_date = (date.fromisoformat(latest["date"]) + timedelta(days=HORIZON)).isoformat()
    forecast = {"targetDate": target_date, "valuePct": round(forecast_value, 5), "lowerPct": round(forecast_value - radius, 5), "upperPct": round(forecast_value + radius, 5), "horizonDays": HORIZON, "model": selected, "intervalLevel": .9, "requiresHumanReview": True, "trainedThrough": train[-1]["targetDate"], "calibratedThrough": calibration[-1]["targetDate"], "publishedAfterEvaluation": True}
    as_of = as_of or datetime.now(timezone(timedelta(hours=-3))).date()
    age = (as_of - date.fromisoformat(latest["date"])).days
    if age < 0:
        raise ValueError("Data de referência anterior à última observação")
    valid_until = (date.fromisoformat(latest["date"]) + timedelta(days=2)).isoformat()
    forecast["usableUntil"] = valid_until
    forecast["expired"] = age > 2
    series = [{"date": r["date"], "observed": r["volumePct"], "forecast": None, "lower": None, "upper": None} for r in rows[-120:]]
    series.append({"date": target_date, "observed": None, "forecast": forecast["valuePct"], "lower": forecast["lowerPct"], "upper": forecast["upperPct"]})
    metrics = {key: latest[key] for key in ("volumePct", "volumeHm3", "rainMm", "inflowM3s", "withdrawalM3s")}
    metrics.update({"change7dPp": round(latest["volumePct"] - rows[-8]["volumePct"], 5), "band": band(latest["volumePct"]), "bandType": "referência diária; não é enquadramento operacional mensal", "unit": "volumePct em %; variação e erros em pontos percentuais"})
    alerts = [{"level": "info" if metrics["band"] == "Normal" else "warning", "title": f"Cantareira: referência diária de {metrics['band'].lower()}", "justification": f"Volume útil observado {latest['volumePct']:.2f}% em {latest['date']}. Limiares de referência do art. 4º da Resolução ANA/DAEE 925/2017; enquadramento operacional mensal exige consulta oficial.", "confidence": None, "sourceUrl": REGULATION_URL, "limitations": LIMITATIONS, "requiresHumanReview": True}, {"level": "info", "title": "Projeção acadêmica para sete dias", "justification": f"{selected}: {forecast_value:.2f}%, intervalo empírico de 90% [{forecast_value-radius:.2f}%, {forecast_value+radius:.2f}%]. MAE teste {test_metrics['mae']:.2f} p.p.; persistência {baseline_metrics['mae']:.2f} p.p.; cobertura observada {100*float(np.mean(covered)):.1f}%.", "confidence": None, "limitations": LIMITATIONS, "requiresHumanReview": True}]
    if age > 2:
        alerts.append({"level": "warning", "title": "Coleta desatualizada", "justification": f"Última observação tem {age} dias na referência {as_of}; atualizar antes de usar a projeção.", "confidence": None, "limitations": ["Previsão marcada como expirada após dois dias sem nova observação."], "requiresHumanReview": True})
    if test_metrics["mae"] >= baseline_metrics["mae"]:
        alerts.append({"level": "warning", "title": "Modelo não superou a persistência no teste", "justification": "A avaliação não demonstra ganho preditivo frente a repetir o último volume observado.", "confidence": None, "limitations": ["Não usar a complexidade do modelo como evidência de superioridade."], "requiresHumanReview": True})
    if float(np.mean(covered)) < .9:
        alerts.append({"level": "warning", "title": "Intervalo abaixo da cobertura nominal no teste", "justification": f"O intervalo nominal de 90% cobriu {100*float(np.mean(covered)):.1f}% dos alvos reais de teste. A incerteza está subestimada neste período; não tratar 90% como probabilidade de acerto individual.", "confidence": None, "limitations": ["Não recalibrar usando o teste e reapresentar esse mesmo teste como evidência independente.", "Validar novamente em período futuro antes de uso operacional."], "requiresHumanReview": True})
    dashboard = {"schemaVersion": 1, "dataMode": "real", "generatedAt": now(), "observedAt": latest["date"], "source": {"name": "SABESP — Portal dos Mananciais", "url": "https://mananciais.sabesp.com.br/", "apiUrl": "https://mananciais.sabesp.com.br/api/v4", "manifestPath": "modules/water/data/manifest.json", "license": quality["license"]}, "freshness": {"status": "stale" if age > 2 else "current", "ageDays": age, "asOfDate": as_of.isoformat(), "maxAgeDays": 2, "usableUntil": valid_until, "offline": quality["offline"]}, "metrics": metrics, "series": series, "forecast": forecast, "evaluation": evaluation, "dataQuality": quality, "alerts": alerts}
    write_json(root / "artifacts/dashboard.json", dashboard)
    return dashboard
