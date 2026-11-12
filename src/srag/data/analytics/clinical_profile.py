"""Perfil clínico: indicadores de leitura rápida para a equipe de saúde.

Três perguntas objetivas, cada uma com um número que dá para ler de relance:

- ``compute_severity_cascade``: de cada 100 casos, quantos internam, vão à UTI e precisam de
  ventilação invasiva, e qual a letalidade em cada etapa?
- ``compute_warning_signs``: a letalidade é maior em quem chega com falta de ar, desconforto
  respiratório ou saturação baixa?
- ``compute_risk_factor_load``: a letalidade cresce com o número de fatores de risco?

Todas as funções são puras: recebem o DataFrame já filtrado e devolvem estruturas JSON.
Letalidade = óbitos / casos com desfecho conhecido (``EVOLUCAO`` em ``VALID_OUTCOMES``);
óbito é só ``EVOLUCAO == 2``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from srag.data.references import DEATH_OUTCOMES, SYMPTOM_FIELDS, VALID_OUTCOMES

# Abaixo disso o percentual de letalidade oscila demais para ser lido como tendência.
MIN_RELIABLE_RESOLVED = 10

# Fatores de risco (coluna do SIVEP, rótulo). "Outros fatores" fica de fora: é um campo livre
# e inflaria a contagem sem significar um fator clínico específico.
RISK_FACTOR_FIELDS = (
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
)

_CASCADE_STEPS = (
    ("notified", "Casos notificados"),
    ("hospitalized", "Internados"),
    ("icu", "Internados em UTI"),
    ("invasive_ventilation", "Ventilação invasiva"),
)

# chave em SYMPTOM_FIELDS -> rótulo do sinal de alerta respiratório
_WARNING_SIGNS = (
    ("dispneia", "Falta de ar (dispneia)"),
    ("desc_resp", "Desconforto respiratório"),
    ("saturacao", "Saturação abaixo de 95%"),
)

_RISK_BUCKETS = (("0", "Nenhum fator"), ("1", "1 fator"), ("2", "2 fatores"), ("3+", "3 ou mais"))


def _round(value: float) -> float:
    return round(value, 1)


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    """Column as float64 (NaN where missing), so comparisons give plain boolean masks."""
    if column not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return pd.Series(pd.to_numeric(df[column], errors="coerce"), index=df.index, dtype="float64")


def _flag(df: pd.DataFrame, column: str, code: int = 1) -> pd.Series:
    """True where the SIVEP column holds ``code`` (1 = "sim"); absent column means nobody."""
    return _numeric(df, column) == code


def _outcome_masks(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """(resolved, death) masks; without ``EVOLUCAO`` nothing is resolved."""
    outcome = _numeric(df, "EVOLUCAO")
    resolved = pd.Series(outcome.isin(sorted(VALID_OUTCOMES)), index=df.index)
    death = pd.Series(outcome.isin(sorted(DEATH_OUTCOMES)), index=df.index)
    return resolved, death


def _group(mask: pd.Series, resolved: pd.Series, death: pd.Series) -> dict[str, Any]:
    """Counts and lethality of the cases selected by ``mask``."""
    cases = int(mask.sum())
    known = int((mask & resolved).sum())
    deaths = int((mask & death).sum())
    return {
        "cases": cases,
        "resolved": known,
        "deaths": deaths,
        "lethality": _round(deaths / known * 100) if known else None,
        "reliable": known >= MIN_RELIABLE_RESOLVED,
    }


def compute_severity_cascade(df: pd.DataFrame) -> dict[str, Any]:
    """Share of cases reaching each severity step, with the lethality at that step."""
    if df.empty:
        return {"total": 0, "steps": []}

    resolved, death = _outcome_masks(df)
    everyone = pd.Series(True, index=df.index)
    masks = {
        "notified": everyone,
        "hospitalized": _flag(df, "HOSPITAL") | _flag(df, "UTI"),
        "icu": _flag(df, "UTI"),
        "invasive_ventilation": _flag(df, "SUPORT_VEN"),
    }
    total = len(df)
    steps = []
    for key, label in _CASCADE_STEPS:
        group = _group(masks[key], resolved, death)
        steps.append(
            {"key": key, "label": label, "pct": _round(group["cases"] / total * 100), **group}
        )
    return {"total": total, "steps": steps}


def _lethality_or_floor(sign: dict[str, Any]) -> float:
    """Sort key: signs without a computable lethality go last."""
    value = sign["lethality"]
    return -1.0 if value is None else float(value)


def compute_warning_signs(df: pd.DataFrame) -> dict[str, Any]:
    """Lethality with versus without each respiratory warning sign, worst sign first."""
    if df.empty:
        return {"baseline": None, "signs": []}

    resolved, death = _outcome_masks(df)
    baseline = _group(pd.Series(True, index=df.index), resolved, death)["lethality"]
    signs = []
    for key, label in _WARNING_SIGNS:
        present = _flag(df, SYMPTOM_FIELDS[key])
        with_sign = _group(present, resolved, death)
        without = _group(~present, resolved, death)
        signs.append(
            {
                "key": key,
                "label": label,
                **with_sign,
                "lethality_without": without["lethality"],
                "reliable_without": without["reliable"],
            }
        )
    signs.sort(key=_lethality_or_floor, reverse=True)
    return {"baseline": baseline, "signs": signs}


def _risk_factor_count(df: pd.DataFrame) -> pd.Series:
    """How many of the listed risk factors each case has (only factors informed as "sim")."""
    count = pd.Series(0, index=df.index)
    for column, _ in RISK_FACTOR_FIELDS:
        count = count + _flag(df, column).astype(int)
    return count


def compute_risk_factor_load(df: pd.DataFrame) -> dict[str, Any]:
    """Cases and lethality by number of risk factors: none, 1, 2 and 3 or more."""
    if df.empty:
        return {"baseline": None, "factors": [], "buckets": []}

    resolved, death = _outcome_masks(df)
    count = _risk_factor_count(df)
    selectors = {
        "0": count == 0,
        "1": count == 1,
        "2": count == 2,
        "3+": count >= 3,
    }
    total = len(df)
    buckets = []
    for key, label in _RISK_BUCKETS:
        group = _group(selectors[key], resolved, death)
        buckets.append(
            {"key": key, "label": label, "pct": _round(group["cases"] / total * 100), **group}
        )
    return {
        "baseline": _group(pd.Series(True, index=df.index), resolved, death)["lethality"],
        "factors": [label for _, label in RISK_FACTOR_FIELDS],
        "buckets": buckets,
    }
