"""Advanced analytical computations for the "Gráficos analíticos" dashboard.

Ported from the legacy SRAG dashboard. Every function is pure: it receives the
already-filtered DataFrame and returns a JSON-friendly structure, so it can be
unit-tested with synthetic data and reused by any router.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from srag.data.analytics.filters import age_years, outcome_death_mask
from srag.data.analytics.surveillance import infer_etiologic_agent
from srag.data.references import SYMPTOM_FIELDS, VALID_OUTCOMES

# ---------------------------------------------------------------------------
# Fluxo da jornada clínica (Sankey)
# ---------------------------------------------------------------------------

_ORIGEM_LABELS = {1: "Infecção Hospitalar", 2: "Comunitária"}
_UTI_LABELS = {1: "Internado em UTI", 2: "Internado em Enfermaria"}
_VENT_LABELS = {1: "Vent. Invasiva", 2: "Vent. Não Inv.", 3: "Sem Suporte"}
_FIM_LABELS = {1: "Cura", 2: "Óbito"}


def _label_column(
    df: pd.DataFrame, column: str, mapping: dict[int, str], fallback: str
) -> pd.Series:
    """Map a coded SIVEP column to labels; missing column/values use ``fallback``."""
    if column not in df.columns:
        return pd.Series(fallback, index=df.index, dtype="object")
    codes = pd.to_numeric(df[column], errors="coerce")
    return codes.map(mapping).fillna(fallback)


def _flow_links(stages: pd.DataFrame, source: str, target: str) -> list[dict[str, Any]]:
    counts = stages.groupby([source, target]).size().reset_index(name="value")
    source_totals = counts.groupby(source)["value"].transform("sum")
    counts["pct"] = (counts["value"] / source_totals * 100).round(1)
    return [
        {
            "source": row[source],
            "target": row[target],
            "value": int(row["value"]),
            "pct": float(row["pct"]),
        }
        for _, row in counts.iterrows()
    ]


def compute_clinical_flow(df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    """Patient journey for the Sankey: origem → UTI/enfermaria → suporte → desfecho."""
    if df.empty:
        return {"nodes": [], "links": []}

    stages = pd.DataFrame(
        {
            "origem": _label_column(df, "NOSOCOMIAL", _ORIGEM_LABELS, "Origem (Ignorado)"),
            "uti": _label_column(df, "UTI", _UTI_LABELS, "Internação (Ignorado)"),
            "vent": _label_column(df, "SUPORT_VEN", _VENT_LABELS, "Suporte (Ignorado)"),
            "fim": _label_column(df, "EVOLUCAO", _FIM_LABELS, "Em Aberto"),
        },
        index=df.index,
    )

    links = (
        _flow_links(stages, "origem", "uti")
        + _flow_links(stages, "uti", "vent")
        + _flow_links(stages, "vent", "fim")
    )
    names = sorted({link["source"] for link in links} | {link["target"] for link in links})
    return {"nodes": [{"name": name} for name in names], "links": links}


# ---------------------------------------------------------------------------
# Associação de comorbidades com o óbito (Odds Ratio)
# ---------------------------------------------------------------------------

_RISK_FIELDS = [
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


def _odds_ratio_with_ci(a: int, b: int, c: int, d: int) -> tuple[float, float, float]:
    """Odds Ratio with Woolf 95% CI from a 2x2 table.

    Cells: a=exposed+dead, b=exposed+alive, c=unexposed+dead, d=unexposed+alive.
    Applies the Haldane correction (+0.5) when any cell is zero.
    Returns (OR, ci_lower, ci_upper).
    """
    aa, bb, cc, dd = float(a), float(b), float(c), float(d)
    if 0 in (a, b, c, d):
        aa, bb, cc, dd = aa + 0.5, bb + 0.5, cc + 0.5, dd + 0.5
    if cc * bb == 0:
        return (0.0, 0.0, 0.0)

    odds = (aa * dd) / (bb * cc)
    se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    ln_or = math.log(odds)
    return (
        round(odds, 3),
        round(math.exp(ln_or - 1.96 * se), 3),
        round(math.exp(ln_or + 1.96 * se), 3),
    )


def compute_comorbidities_odds_ratio(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Each risk factor with frequency, lethality, Odds Ratio and 95% CI.

    The 2x2 table only uses clinically resolved cases (EVOLUCAO in VALID_OUTCOMES);
    death is EVOLUCAO == 2. Result is sorted by Odds Ratio, descending.
    """
    if df.empty:
        return []

    if "EVOLUCAO" in df.columns:
        evolucao = pd.to_numeric(df["EVOLUCAO"], errors="coerce")
        resolved_mask = evolucao.isin(VALID_OUTCOMES)
        death_mask = outcome_death_mask(df["EVOLUCAO"])
    else:
        resolved_mask = pd.Series(False, index=df.index)
        death_mask = pd.Series(False, index=df.index)

    total_resolved = int(resolved_mask.sum())
    total_deaths = int(death_mask.sum())

    rows: list[dict[str, Any]] = []
    for column, label in _RISK_FIELDS:
        if column not in df.columns:
            rows.append(_empty_risk_row(label))
            continue

        factor_mask = pd.to_numeric(df[column], errors="coerce") == 1
        count = int(factor_mask.sum())
        resolved_with = int((factor_mask & resolved_mask).sum())
        deaths_with = int((factor_mask & death_mask).sum())

        unexposed_deaths = total_deaths - deaths_with
        unexposed_resolved = total_resolved - resolved_with
        unexposed_alive = unexposed_resolved - unexposed_deaths
        # OR is undefined without resolved cases on both sides of the comparison
        # (the Haldane correction would otherwise invent a meaningless value).
        if resolved_with == 0 or unexposed_resolved == 0:
            odds_ratio, ci_lower, ci_upper = 0.0, 0.0, 0.0
        else:
            odds_ratio, ci_lower, ci_upper = _odds_ratio_with_ci(
                deaths_with, resolved_with - deaths_with, unexposed_deaths, unexposed_alive
            )

        rows.append(
            {
                "name": label,
                "value": count,
                "deaths": deaths_with,
                "lethality": round(deaths_with / resolved_with * 100, 2) if resolved_with else 0.0,
                "prevalence": round(count / len(df) * 100, 2),
                "odds_ratio": odds_ratio,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
            }
        )

    rows.sort(key=lambda row: row["odds_ratio"], reverse=True)
    return rows


def _empty_risk_row(label: str) -> dict[str, Any]:
    return {
        "name": label,
        "value": 0,
        "deaths": 0,
        "lethality": 0.0,
        "prevalence": 0.0,
        "odds_ratio": 0.0,
        "ci_lower": 0.0,
        "ci_upper": 0.0,
    }


# ---------------------------------------------------------------------------
# Assinatura clínica de sintomas (COVID-19, Influenza e VSR)
# ---------------------------------------------------------------------------

SIGNATURE_PROFILES = ("all", "crianca", "adolescente", "adulto", "idoso")

_SYMPTOM_LABELS = {
    "febre": "Febre",
    "tosse": "Tosse",
    "garganta": "Dor de garganta",
    "dispneia": "Dispneia",
    "desc_resp": "Desconforto respiratório",
    "saturacao": "Saturação <95%",
    "diarreia": "Diarreia",
    "vomito": "Vômito",
    "dor_abd": "Dor abdominal",
    "fadiga": "Fadiga",
    "perd_olft": "Perda de olfato",
    "perd_pala": "Perda de paladar",
    "outro_sin": "Outros sintomas",
}

# agent label (from infer_etiologic_agent) -> key used in the response
_SIGNATURE_AGENTS = {"COVID-19": "covid", "Influenza": "gripe", "VSR": "vsr"}


def _age_bands(age: pd.Series, profile: str) -> list[tuple[str, pd.Series]]:
    """(label, mask) pairs for the requested age profile."""
    if profile == "crianca":
        return [
            ("<2 anos", age < 2),
            ("2-5 anos", (age >= 2) & (age < 6)),
            ("6-11 anos", (age >= 6) & (age < 12)),
        ]
    if profile == "adolescente":
        return [("12-14 anos", (age >= 12) & (age < 15)), ("15-19 anos", (age >= 15) & (age < 20))]
    if profile == "adulto":
        return [("20-39 anos", (age >= 20) & (age < 40)), ("40-59 anos", (age >= 40) & (age < 60))]
    if profile == "idoso":
        return [
            ("60-69 anos", (age >= 60) & (age < 70)),
            ("70-79 anos", (age >= 70) & (age < 80)),
            ("80+ anos", age >= 80),
        ]
    return [
        ("Criança", age < 12),
        ("Adolescente", (age >= 12) & (age < 20)),
        ("Adulto", (age >= 20) & (age < 60)),
        ("Idoso", age >= 60),
    ]


def _has_symptom(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    return pd.to_numeric(df[column], errors="coerce") == 1


def _prevalence_row(
    has_symptom: pd.Series, agent_mask: pd.Series, band_masks: list[pd.Series]
) -> list[list[float | int]]:
    """[prevalence %, case count] of one symptom, for each age band."""
    row: list[list[float | int]] = []
    for band_mask in band_masks:
        subset = agent_mask & band_mask
        total = int(subset.sum())
        hits = int((has_symptom & subset).sum()) if total else 0
        row.append([round(hits / total * 100, 1) if total else 0.0, hits])
    return row


def _agent_matrix(
    df: pd.DataFrame, agent_mask: pd.Series, band_masks: list[pd.Series]
) -> list[list[list[float | int]]]:
    return [
        _prevalence_row(_has_symptom(df, column), agent_mask, band_masks)
        for column in SYMPTOM_FIELDS.values()
    ]


def _order_by_total_prevalence(
    matrices: dict[str, list[list[list[float | int]]]],
) -> list[int]:
    """Row indexes sorted by the symptom's summed prevalence, most frequent first."""
    count = len(SYMPTOM_FIELDS)
    totals = [
        sum(cell[0] for matrix in matrices.values() for cell in matrix[index])
        for index in range(count)
    ]
    return sorted(range(count), key=lambda index: totals[index], reverse=True)


def compute_symptoms_signature(df: pd.DataFrame, profile: str = "all") -> dict[str, Any]:
    """Symptom prevalence (%) per age band for COVID-19, Influenza and VSR.

    Each case belongs to exactly one agent group (the same ``infer_etiologic_agent``
    used by the agent filter, so VSR positives are not double counted as COVID/Flu).
    Each cell is ``[prevalence_pct, case_count]``; symptoms are ordered by their
    summed prevalence, most frequent first.
    """
    if df.empty:
        return {"labels": [], "bands": [], "matrices": {}}

    profile = profile if profile in SIGNATURE_PROFILES else "all"
    work = df.copy()
    bands = _age_bands(pd.to_numeric(age_years(work), errors="coerce"), profile)
    band_masks = [mask.fillna(False).astype(bool) for _, mask in bands]
    agents = infer_etiologic_agent(work)

    matrices = {
        key: _agent_matrix(work, agents == label, band_masks)
        for label, key in _SIGNATURE_AGENTS.items()
    }
    order = _order_by_total_prevalence(matrices)
    labels = [_SYMPTOM_LABELS[key] for key in SYMPTOM_FIELDS]
    return {
        "labels": [labels[index] for index in order],
        "bands": [label for label, _ in bands],
        "matrices": {key: [matrix[i] for i in order] for key, matrix in matrices.items()},
    }
