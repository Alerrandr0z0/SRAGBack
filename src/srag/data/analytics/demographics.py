"""Demographic analysis (Age, Race, Schooling, Profiles)."""

import math
from typing import Any

import pandas as pd

from srag.data.analytics.filters import age_years


def categorize_age(age: float) -> str:
    """Map numeric age in years to epidemiological age buckets with high granularity."""
    if age < 2:
        return "0-1 ano"
    if age < 5:
        return "2-4 anos"
    if age < 10:
        return "5-9 anos"
    if age < 15:
        return "10-14 anos"
    if age < 20:
        return "15-19 anos"
    if age < 30:
        return "20-29 anos"
    if age < 40:
        return "30-39 anos"
    if age < 50:
        return "40-49 anos"
    if age < 60:
        return "50-59 anos"
    if age < 70:
        return "60-69 anos"
    if age < 80:
        return "70-79 anos"
    return "80+ anos"


# Faixas fixas da pirâmide (contrato com o Front: SRAG_AGE_BANDS em sragMappers.ts).
AGE_PYRAMID_BANDS = [
    "0-1 ano",
    "2-4 anos",
    "5-9 anos",
    "10-14 anos",
    "15-19 anos",
    "20-29 anos",
    "30-39 anos",
    "40-49 anos",
    "50-59 anos",
    "60-69 anos",
    "70-79 anos",
    "80+ anos",
]


def compute_citizen_pyramid(df: pd.DataFrame) -> list[dict[str, int | str]]:
    """Build a single dynamic age pyramid based on the current filtered dataframe.

    Bins are the fixed ``categorize_age`` bands so consumers can rely on stable labels.
    """
    if df.empty:
        return []

    out = df.copy()
    age = age_years(out)
    if age.empty or age.isna().all():
        return []

    # age_years maps missing NU_IDADE_N to 0; without any real age info there is no pyramid.
    if "IDADE_ANOS" in out.columns and out["IDADE_ANOS"].notna().any():
        has_age_info = True
    else:
        nu_col = out["NU_IDADE_N"] if "NU_IDADE_N" in out.columns else pd.Series(dtype=float)
        has_age_info = bool(pd.to_numeric(nu_col, errors="coerce").notna().any())
    if not has_age_info:
        return []

    out["age_bin"] = pd.NA
    valid = age.notna()
    out.loc[valid, "age_bin"] = [categorize_age(float(a)) for a in age[valid]]

    pyramid = []
    counts = out.groupby(["age_bin", "CS_SEXO"], observed=False).size().unstack(fill_value=0)

    for label in AGE_PYRAMID_BANDS:
        male = int(counts.loc[label].get("M", 0)) if label in counts.index else 0  # type: ignore[arg-type]
        female = int(counts.loc[label].get("F", 0)) if label in counts.index else 0  # type: ignore[arg-type]
        pyramid.append({"age_band": label, "male": male, "female": female})

    return pyramid


def _pyramid_row(counts: pd.DataFrame, year: int) -> dict[str, int]:
    """Male/female counts for one age (missing age or sex → 0)."""
    if year not in counts.index:
        return {"age": year, "male": 0, "female": 0}
    male = int(counts.loc[year, "M"]) if "M" in counts.columns else 0  # type: ignore[arg-type]
    female = int(counts.loc[year, "F"]) if "F" in counts.columns else 0  # type: ignore[arg-type]
    return {"age": year, "male": male, "female": female}


def compute_population_pyramid(df: pd.DataFrame) -> list[dict[str, int]]:
    """Build a single-year age pyramid (one bar per age, male/female counts).

    Ages are floored to whole years and capped at 100+ (last bucket ``age == 100``
    aggregates 100 or more). Missing age info yields ``[]``.
    """
    if df.empty:
        return []

    out = df.copy()
    age = age_years(out)
    if age.empty or age.isna().all():
        return []

    if "IDADE_ANOS" in out.columns and out["IDADE_ANOS"].notna().any():
        has_age_info = True
    else:
        nu_col = out["NU_IDADE_N"] if "NU_IDADE_N" in out.columns else pd.Series(dtype=float)
        has_age_info = bool(pd.to_numeric(nu_col, errors="coerce").notna().any())
    if not has_age_info:
        return []

    valid = age.notna()
    out = out.loc[valid].copy()
    whole = age[valid].clip(lower=0).astype(int).clip(upper=100)

    counts = pd.crosstab(whole, out["CS_SEXO"])
    pyramid = []
    for year in range(int(whole.max()) + 1):
        pyramid.append(_pyramid_row(counts, year))

    return pyramid


def compute_race_profile(df: pd.DataFrame) -> list[dict[str, int | str]]:
    """Aggregate race/color profile using official SIVEP CS_RACA codes."""
    if df.empty or "CS_RACA" not in df.columns:
        return []

    labels = {
        1: "Branca",
        2: "Preta",
        3: "Amarela",
        4: "Parda",
        5: "Indígena",
    }

    out = df.copy()
    out["cs_raca_num"] = pd.to_numeric(out["CS_RACA"], errors="coerce")
    out = out[out["cs_raca_num"].isin(labels.keys())]
    if out.empty:
        return []

    grouped = out.groupby("cs_raca_num").size().reset_index(name="count")
    grouped = grouped.sort_values("cs_raca_num")

    result: list[dict[str, int | str]] = []
    for row in grouped.itertuples(index=False):
        code = int(row.cs_raca_num)  # type: ignore[arg-type]
        result.append(
            {
                "label": labels[code],
                "count": int(row.count),  # type: ignore[arg-type]
            }
        )
    return result


def compute_schooling_profile(df: pd.DataFrame) -> list[dict[Any, Any]]:
    """Schooling profile with SIVEP context rule for 'não se aplica'."""
    if df.empty or "CS_ESCOL_N" not in df.columns:
        return []

    out = df.copy()
    escol = pd.to_numeric(out["CS_ESCOL_N"], errors="coerce")
    age = age_years(out)

    valid = escol.notna()
    valid = valid & (~((escol == 5) & (age >= 7)))
    work = pd.DataFrame({"escol": escol[valid]})
    if work.empty:
        return []

    labels = {
        0: "Sem escolaridade",
        1: "Fundamental I",
        2: "Fundamental II",
        3: "Médio",
        4: "Superior",
        5: "Não se aplica",
        9: "Ignorado",
    }
    work["label"] = work["escol"].map(lambda v: labels.get(int(v), "Outro"))
    grouped = work.groupby("label").size().reset_index(name="count")
    grouped = grouped.sort_values("count", ascending=False)
    return grouped.to_dict(orient="records")


def compute_age_pareto(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Cases by age band (both sexes) sorted desc with cumulative % (Pareto).

    Bands are the fixed ``AGE_PYRAMID_BANDS``; bands with zero cases are
    omitted. Cumulative uses round-half-up to 1 decimal.
    """
    if df.empty:
        return []
    age = age_years(df)
    if age.empty or age.isna().all():
        return []
    counts = (
        pd.Series([categorize_age(float(a)) for a in age[age.notna()]])
        .value_counts()
        .reindex(AGE_PYRAMID_BANDS, fill_value=0)
    )
    total = int(counts.sum())
    items: list[dict[str, str | int | float]] = [
        {"label": label, "count": int(counts[label])}
        for label in AGE_PYRAMID_BANDS
        if int(counts[label]) > 0
    ]
    items.sort(key=lambda x: int(x["count"]), reverse=True)
    acc = 0
    for item in items:
        acc += int(item["count"])
        item["cumulative"] = math.floor(acc / total * 1000 + 0.5) / 10 if total else 0.0
    return items


def compute_covid_vaccination_profile(df: pd.DataFrame) -> list[dict[str, int | str]]:
    """Aggregate COVID-19 vaccination status using official SIVEP VACINA_COV codes.

    1-Sim → "Vacinado", 2-Não → "Não vacinado"; 9-Ignorado/missing →
    "Ignorado". Fixed 3-item contract (zeros included).
    """
    labels = {1: "Vacinado", 2: "Não vacinado"}
    counts = {1: 0, 2: 0, 0: 0}
    if not df.empty and "VACINA_COV" in df.columns:
        codes = pd.to_numeric(df["VACINA_COV"], errors="coerce")
        for code in (1, 2):
            counts[code] = int((codes == code).sum())
        counts[0] = int(len(df) - counts[1] - counts[2])
    return [
        {"label": labels[1], "count": counts[1]},
        {"label": labels[2], "count": counts[2]},
        {"label": "Ignorado", "count": counts[0]},
    ]
