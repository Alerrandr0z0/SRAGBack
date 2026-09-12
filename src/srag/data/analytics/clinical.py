from __future__ import annotations

import math
from typing import Any

import pandas as pd

RISK_FIELDS: list[tuple[str, str]] = [
    ("PUERPERA", "Puérpera"),
    ("CARDIOPATI", "Cardiopatia"),
    ("HEMATOLOGI", "Doença hematológica"),
    ("SIND_DOWN", "Síndrome de Down"),
    ("HEPATICA", "Doença hepática"),
    ("ASMA", "Asma"),
    ("DIABETES", "Diabetes"),
    ("NEUROLOGIC", "Doença neurológica"),
    ("PNEUMOPATI", "Pneumopatia"),
    ("IMUNODEPRE", "Imunodepressão"),
    ("RENAL", "Doença renal"),
    ("OBESIDADE", "Obesidade"),
    ("TABAG", "Tabagismo"),
    ("OUT_MORBI", "Outros fatores"),
]


def compute_flu_vaccination_donut(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Flu vaccination status in fixed donut order (dicionário, campo 40).

    Raw ``classificar_status_gripe`` keys: protegido/vencida/dose_* →
    Vacinado; nao_vacinado → Não vacinado; ignorado/inconsistencia →
    Ignorado (same rule as the ``resumo`` counts).
    """
    from srag.data.analytics.surveillance import classificar_status_gripe

    labels = ["Vacinado", "Não vacinado", "Ignorado"]
    counts = [0, 0, 0]
    if not df.empty:
        raw = df.apply(classificar_status_gripe, axis=1).value_counts().to_dict()
        non_vaccinated = ("nao_vacinado", "ignorado", "inconsistencia")
        vaccinated = sum(v for k, v in raw.items() if k not in non_vaccinated)
        counts = [
            int(vaccinated),
            int(raw.get("nao_vacinado", 0)),
            int(raw.get("ignorado", 0) + raw.get("inconsistencia", 0)),
        ]
    return [{"label": label, "count": count} for label, count in zip(labels, counts, strict=True)]


def compute_risk_factors_full_profile(df: pd.DataFrame) -> list[dict[str, int | str]]:
    """Aggregate full SIVEP risk-factor set as frequencies."""
    if df.empty:
        return []

    risk_fields = [
        ("PUERPERA", "Puérpera"),
        ("CARDIOPATI", "Cardiopatia"),
        ("HEMATOLOGI", "Doença hematológica"),
        ("SIND_DOWN", "Síndrome de Down"),
        ("HEPATICA", "Doença hepática"),
        ("ASMA", "Asma"),
        ("DIABETES", "Diabetes"),
        ("NEUROLOGIC", "Doença neurológica"),
        ("PNEUMOPATI", "Pneumopatia"),
        ("IMUNODEPRE", "Imunodepressão"),
        ("RENAL", "Doença renal"),
        ("OBESIDADE", "Obesidade"),
        ("TABAG", "Tabagismo"),
        ("OUT_MORBI", "Outros fatores"),
    ]

    out: list[dict[str, int | str]] = []
    for col, label in risk_fields:
        if col not in df.columns:
            out.append({"factor": label, "count": 0})
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        out.append({"factor": label, "count": int((s == 1).sum())})
    out.sort(key=lambda x: int(x["count"]), reverse=True)
    return out


def compute_comorbidities_pareto(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Comorbidity mentions (SIVEP == 1) sorted desc with cumulative % (Pareto).

    Cumulative uses round-half-up to 1 decimal. Bands with zero mentions
    are omitted.
    """
    if df.empty:
        return []
    items: list[dict[str, Any]] = []
    for col, label in RISK_FIELDS:
        count = 0
        if col in df.columns:
            count = int((pd.to_numeric(df[col], errors="coerce") == 1).sum())
        if count > 0:
            items.append({"name": label, "value": count})
    items.sort(key=lambda x: int(x["value"]), reverse=True)
    total = sum(int(i["value"]) for i in items)
    acc = 0
    for item in items:
        acc += int(item["value"])
        item["cumulative"] = math.floor(acc / total * 1000 + 0.5) / 10 if total else 0.0
    return items


def compute_maternal_profile(df: pd.DataFrame) -> dict[str, object]:
    """Count gestantes (CS_GESTANT 1-4 among females); the only maternal figure consumed."""
    if df.empty or "CS_SEXO" not in df.columns:
        return {"gestantes_total": 0}
    fem = df[df["CS_SEXO"] == "F"]
    if fem.empty or "CS_GESTANT" not in fem.columns:
        return {"gestantes_total": 0}
    gestantes = int(pd.to_numeric(fem["CS_GESTANT"], errors="coerce").isin([1, 2, 3, 4]).sum())
    return {"gestantes_total": gestantes}


