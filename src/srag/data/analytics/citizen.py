"""Citizen-facing analytical computations ("Gráficos analíticos" → Cidadão).

Ported from the legacy SRAG dashboard. Every function is pure: it receives the
already-filtered DataFrame and returns a JSON-friendly structure.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd

from srag.data.analytics.filters import outcome_death_mask

# ---------------------------------------------------------------------------
# Desfecho por grupo materno
# ---------------------------------------------------------------------------

MATERNAL_GROUPS = (
    "Gest. 1º tri",
    "Gest. 2º tri",
    "Gest. 3º tri",
    "Gest. IG ignorada",
    "Puérpera",
)
# Below this many cases per group the percentages are anecdotal, not a rate.
MATERNAL_MIN_CASES = 10


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    """Column as float64 (so nullable dtypes give plain boolean masks, never NA)."""
    if column not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return pd.Series(pd.to_numeric(df[column], errors="coerce"), index=df.index, dtype="float64")


def compute_maternal_outcomes(df: pd.DataFrame) -> dict[str, Any]:
    """Outcome (cura, UTI sobrevivente, óbito, outro) per gestational group.

    Only women are considered. A puérpera is never counted as gestante, even
    when both fields are filled in.
    """
    empty: dict[str, Any] = {
        "gestantes_total": 0,
        "puerperas_total": 0,
        "min_cases": MATERNAL_MIN_CASES,
        "groups": [],
    }
    if df.empty or "CS_SEXO" not in df.columns:
        return empty
    fem = df.loc[df["CS_SEXO"] == "F"].copy()
    if fem.empty:
        return empty

    puerp = _numeric(fem, "PUERPERA")
    gest = _numeric(fem, "CS_GESTANT")
    group = pd.Series(
        np.select(
            [puerp == 1, gest == 1, gest == 2, gest == 3, gest == 4],
            [MATERNAL_GROUPS[4], *MATERNAL_GROUPS[:4]],
            default="",
        ),
        index=fem.index,
    )
    outcome = pd.Series(
        np.select(
            [
                outcome_death_mask(_numeric(fem, "EVOLUCAO")),
                _numeric(fem, "UTI") == 1,
                _numeric(fem, "EVOLUCAO") == 1,
            ],
            ["death", "icu", "cure"],
            default="other",
        ),
        index=fem.index,
    )

    groups: list[dict[str, Any]] = []
    gestantes = 0
    puerperas = 0
    for name in MATERNAL_GROUPS:
        counts = cast("dict[str, int]", outcome.loc[group == name].value_counts().to_dict())
        total = sum(counts.values())
        if total == 0:
            continue
        if name == "Puérpera":
            puerperas += total
        else:
            gestantes += total
        groups.append(
            {
                "group": name,
                "total": total,
                "cure": counts.get("cure", 0),
                "icu": counts.get("icu", 0),
                "death": counts.get("death", 0),
                "other": counts.get("other", 0),
            }
        )
    return {
        "gestantes_total": gestantes,
        "puerperas_total": puerperas,
        "min_cases": MATERNAL_MIN_CASES,
        "groups": groups,
    }


# ---------------------------------------------------------------------------
# Ocupação e contato com animais
# ---------------------------------------------------------------------------

_NOT_INFORMED = {"", "NAN", "NONE", "NA", "<NA>", "999999", "IGNORADO", "NÃO INFORMADO"}


def compute_occupation_profile(df: pd.DataFrame, top_n: int = 15) -> dict[str, Any]:
    """Most frequent occupations (CBO description) among notified cases."""
    total = len(df)
    if df.empty or "PAC_DSCBO" not in df.columns:
        return {"total": total, "informed": 0, "items": []}
    names = df["PAC_DSCBO"].astype("string").str.strip().str.upper()
    valid = names[~names.isin(_NOT_INFORMED) & names.notna()]
    counts = valid.value_counts().head(top_n)
    return {
        "total": total,
        "informed": len(valid),
        "items": [{"label": str(name), "count": int(n)} for name, n in counts.items()],
    }


_ANIMAL_LABELS = {1: "Aves ou suínos", 3: "Outros animais", 2: "Sem contato"}


def compute_animal_contact(df: pd.DataFrame) -> dict[str, Any]:
    """Contact with birds/swine or other animals (AVE_SUINO); ``Ignorado`` kept apart."""
    if df.empty or "AVE_SUINO" not in df.columns:
        return {"total": len(df), "ignored": len(df), "items": []}
    codes = _numeric(df, "AVE_SUINO")
    counts = [int((codes == code).sum()) for code in _ANIMAL_LABELS]
    return {
        "total": len(df),
        "ignored": len(df) - sum(counts),
        "items": [
            {"label": label, "count": count}
            for label, count in zip(_ANIMAL_LABELS.values(), counts, strict=True)
        ],
    }


# ---------------------------------------------------------------------------
# Imunização COVID-19
# ---------------------------------------------------------------------------

# Latest dose first: the last recorded manufacturer wins.
_FAB_COLUMNS = ("FAB_RE_BI", "FAB_ADIC", "FAB_COVRF2", "FAB_COVRF", "FAB_COV2", "FAB_COV1")
_MANUFACTURERS = (
    (("ASTRAZENECA", "FIOCRUZ", "CHADOX1", "OXFORD"), "AstraZeneca/Oxford"),
    (("PFIZER", "BIONTECH"), "Pfizer/BioNTech"),
    (("BUTANTAN", "CORONAVAC", "SINOVAC"), "Butantan/Sinovac"),
    (("JANSSEN", "JOHNSON"), "Janssen"),
)
_FAB_INVALID = _NOT_INFORMED | {"0", "9"}


def _clean_manufacturer(name: str) -> str:
    for keys, label in _MANUFACTURERS:
        if any(key in name for key in keys):
            return label
    return name.title()


def compute_vaccine_manufacturers(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Cases per manufacturer of the last COVID-19 dose on record, most common first."""
    columns = [c for c in _FAB_COLUMNS if c in df.columns]
    if df.empty or not columns:
        return []
    last = pd.Series(pd.NA, index=df.index, dtype="string")
    for column in columns:
        name = df[column].astype("string").str.strip().str.upper()
        last = last.fillna(name.where(~name.isin(_FAB_INVALID)))
    counts = last.dropna().map(_clean_manufacturer).value_counts()
    return [{"label": str(label), "count": int(n)} for label, n in counts.items()]


_DOSE_STAGES = (
    ("DOS_RE_BI", "Reforço bivalente"),
    ("DOSE_2REF", "2º reforço"),
    ("DOSE_REF", "1º reforço"),
    ("DOSE_2_COV", "Esquema completo"),
    ("DOSE_1_COV", "Só a 1ª dose"),
)
_DOSE_ORDER = (
    "Não vacinado",
    "Só a 1ª dose",
    "Esquema completo",
    "1º reforço",
    "2º reforço",
    "Reforço bivalente",
    "Ignorado",
)


def compute_covid_dose_stage(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Cases by the furthest COVID-19 dose reached, from unvaccinated to booster."""
    if df.empty:
        return []
    stage = pd.Series("", index=df.index, dtype="object")
    for column, label in _DOSE_STAGES:
        if column in df.columns:
            stage = stage.mask((stage == "") & df[column].notna(), label)
    unvaccinated = _numeric(df, "VACINA_COV") == 2
    fallback = pd.Series(np.where(unvaccinated, "Não vacinado", "Ignorado"), index=df.index)
    stage = pd.Series(np.where(stage == "", fallback, stage), index=df.index)
    counts = {str(label): int(n) for label, n in stage.value_counts().items()}
    return [{"label": label, "count": counts.get(label, 0)} for label in _DOSE_ORDER]
