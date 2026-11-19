"""Official SABESP acquisition, immutable response cache and strict normalization.

No credentials, third-party mirror, synthetic values, or interpolation are used.
The update command is deliberately separate from model training.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
BASE = "https://mananciais.sabesp.com.br/api/v4"
LICENSE = {
    "identifier": "not-specified-by-source",
    "termsUrl": "https://mananciais.sabesp.com.br/",
    "note": "Portal público; licença específica de reutilização não localizada. Acesso público não equivale a licença aberta. Atribuir SABESP, preservar origem e confirmar termos antes de redistribuição comercial.",
}
FIELDS = {
    "volumePct": "volumeUtilArmazenadoPorcentagem",
    "rainMm": "chuva",
    "inflowM3s": "vazaoAfluente",
    "withdrawalM3s": "vazaoCaptada",
    "downstreamM3s": "vazaoJusante",
    "volumeHm3": "volumeUtilArmazenadoHm3",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


class Cache:
    def __init__(self, root: Path = ROOT, offline: bool = False):
        self.root = root
        self.offline = offline
        path = root / "data/manifest.json"
        self.manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schemaVersion": 1, "publisher": "SABESP", "license": LICENSE, "responses": {}}

    def fetch(self, suffix: str):
        url = BASE + "/" + suffix
        entries = self.manifest["responses"]
        if self.offline:
            entry = entries.get(url)
            if entry is None:
                raise ValueError(f"Resposta não existe no cache: {url}")
            body = (self.root / entry["file"]).read_bytes()
            if hashlib.sha256(body).hexdigest() != entry["sha256"]:
                raise ValueError(f"SHA-256 do cache diverge: {url}")
        else:
            request = Request(url, headers={"User-Agent": "TerritorioVivo-Academic/1.0", "Accept": "application/json"})
            with urlopen(request, timeout=45) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "")
                status = response.status
            # Validate before replacing manifest. An HTTP 200 HTML error is not data.
            payload = json.loads(body)
            if payload.get("succeeded") is not True:
                raise ValueError(f"Fonte declarou erro: {url}: {payload.get('errors')}")
            digest = hashlib.sha256(body).hexdigest()
            relative = "data/raw/" + digest + ".json"
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(body)
            entries[url] = {"url": url, "file": relative, "sha256": digest, "bytes": len(body), "fetchedAt": now(), "httpStatus": status, "contentType": content_type}
            write_json(self.root / "data/manifest.json", self.manifest)
        payload = json.loads(body)
        if payload.get("succeeded") is not True or "data" not in payload:
            raise ValueError(f"Resposta inválida: {url}")
        return payload["data"]


def finite(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Medição não numérica/finita: {value!r}")
    return float(value)


def normalize(records, as_of: date):
    by_date = {}
    for record in records:
        if record.get("idSistema") != 64:
            raise ValueError("Série contém sistema diferente do Cantareira (64)")
        observed = date.fromisoformat(record["date"][:10])
        if observed > as_of:
            raise ValueError("Fonte retornou observação posterior à data de corte")
        row = {"date": observed.isoformat(), **{k: finite(record.get(v)) for k, v in FIELDS.items()}}
        if row["volumePct"] is None:
            continue  # Never replace missing volume by zero.
        if observed in by_date:
            raise ValueError(f"Data duplicada na fonte: {observed}")
        by_date[observed] = row
    if not by_date:
        raise ValueError("Nenhuma observação de volume utilizável")
    rows = [by_date[d] for d in sorted(by_date)]
    first, last = min(by_date), max(by_date)
    missing = [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1) if first + timedelta(days=i) not in by_date]
    return rows, {"rows": len(rows), "firstObservedAt": first.isoformat(), "lastObservedAt": last.isoformat(), "missingDates": missing, "nullFields": {k: sum(r[k] is None for r in rows) for k in FIELDS}, "imputation": "none"}


def acquire(as_of: date, start_year: int = 2018, offline: bool = False, root: Path = ROOT):
    cache = Cache(root, offline)
    published = date.fromisoformat(cache.fetch("dados/ultima-data")[:10])
    cutoff = min(as_of, published)
    if cutoff.year < start_year:
        raise ValueError("Data de corte anterior ao início da coleta")
    cache.fetch("parametros")
    records = []
    for year in range(start_year, cutoff.year + 1):
        end = min(date(year, 12, 31), cutoff)
        suffix = f"sistemas/64/dados/diario/{year}-01-01/{end}"
        portion = cache.fetch(suffix)
        if not isinstance(portion, list) or not portion:
            raise ValueError(f"Sem série histórica para {year}")
        print(f"SABESP {year}: {len(portion)} registros", flush=True)
        records.extend(portion)
    current = cache.fetch(f"sistemas/dados/resumo-diario/{cutoff}")
    rows, quality = normalize(records, cutoff)
    if rows[-1]["date"] != cutoff.isoformat():
        raise ValueError("Série histórica não cobre a data do resumo atual")
    current_cantareira = next((r for r in current if r.get("idSistema") == 64), None)
    if current_cantareira is None:
        raise ValueError("Resumo atual sem Cantareira")
    if current_cantareira["date"][:10] != cutoff.isoformat():
        raise ValueError("Data do resumo não corresponde ao corte solicitado")
    if abs(current_cantareira["volumeUtilArmazenadoPorcentagem"] - rows[-1]["volumePct"]) > 0.001:
        raise ValueError("Resumo atual e série histórica divergem; verificar revisão da fonte")
    csv_path = root / "data/cantareira.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", *FIELDS])
        writer.writeheader()
        writer.writerows(rows)
    quality.update({"requestedAsOf": as_of.isoformat(), "sourceLastDate": published.isoformat(), "processedAt": now(), "offline": offline, "normalizedSha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(), "license": LICENSE})
    write_json(root / "data/quality.json", quality)
    write_json(root / "data/current_rmsp.json", current)
    return quality


def load_rows(root: Path = ROOT):
    path = root / "data/cantareira.csv"
    quality = json.loads((root / "data/quality.json").read_text(encoding="utf-8"))
    if hashlib.sha256(path.read_bytes()).hexdigest() != quality["normalizedSha256"]:
        raise ValueError("CSV normalizado foi modificado após a coleta")
    with path.open(encoding="utf-8", newline="") as f:
        rows = [{"date": r["date"], **{key: float(r[key]) if r[key] else None for key in FIELDS}} for r in csv.DictReader(f)]
    return rows, quality


def unavailable(reason: str, root: Path = ROOT):
    value = {"schemaVersion": 1, "dataMode": "unavailable", "generatedAt": now(), "observedAt": None, "source": {"name": "SABESP — Portal dos Mananciais", "url": "https://mananciais.sabesp.com.br/", "license": LICENSE}, "freshness": {"status": "unavailable"}, "metrics": {}, "series": [], "forecast": None, "evaluation": None, "alerts": [{"level": "warning", "title": "Dados hídricos indisponíveis", "justification": reason, "confidence": None, "limitations": ["Nenhum dado ou previsão foi inventado.", "Consultar a fonte oficial antes de qualquer decisão."], "requiresHumanReview": True}]}
    write_json(root / "artifacts/dashboard.json", value)
    return value
