"""Health-unit analytical computations ("Gráficos analíticos" → Unid. Saúde).

Ported from the legacy SRAG dashboard. Every function is pure: it receives the
already-filtered DataFrame and returns a JSON-friendly structure.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from srag.data.analytics.advanced import (
    _DELAY_CRITICAL_MEDIAN_DAYS,
    _DELAY_WARN_MEDIAN_DAYS,
    _MAX_DELAY_DAYS,
    NOTIFICATION_DELAY_LIMIT_DAYS,
    _date_column,
    _delay_row,
    _pct,
)
from srag.data.analytics.citizen import _DOSE_ORDER, _numeric, covid_stage_series
from srag.data.analytics.filters import outcome_death_mask
from srag.data.cnes import unit_name

MIN_UNIT_DELAY_CASES = 5
MAX_STAY_DAYS = 90
CURVE_LAST_DAY = 45
# Below this many cases the per-stage figures are anecdotal, not a rate.
MIN_JOURNEY_CASES = 10

_MISSING_CODES = {"", "nan", "<NA>", "None"}


def _unit_codes(df: pd.DataFrame) -> pd.Series:
    """CNES code of the notifying unit per case; <NA> when blank."""
    if "ID_UNIDADE" not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="string")
    codes = df["ID_UNIDADE"].astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    return codes.mask(codes.isin(_MISSING_CODES))


# ---------------------------------------------------------------------------
# Unidades notificadoras
# ---------------------------------------------------------------------------


def compute_notifying_units(df: pd.DataFrame) -> dict[str, Any]:
    """Cases per notifying unit with their outcome, most notifications first."""
    if df.empty:
        return {"total": 0, "unidentified": 0, "items": []}
    evolution = _numeric(df, "EVOLUCAO")
    frame = pd.DataFrame(
        {
            "unit": _unit_codes(df),
            "cure": evolution == 1,
            "death": outcome_death_mask(evolution),
        }
    )
    unidentified = int(frame["unit"].isna().to_numpy().sum())
    grouped = (
        frame.loc[frame["unit"].notna()]
        .groupby("unit")
        .agg(total=("cure", "size"), cure=("cure", "sum"), death=("death", "sum"))
    )
    codes = [str(code) for code in grouped.index.tolist()]
    totals = grouped["total"].tolist()
    cures = grouped["cure"].tolist()
    deaths = grouped["death"].tolist()
    items: list[dict[str, Any]] = [
        {
            "id_unidade": code,
            "name": unit_name(code),
            "total": int(total),
            "cure": int(cure),
            "death": int(death),
            "other": int(total - cure - death),
        }
        for code, total, cure, death in zip(codes, totals, cures, deaths, strict=True)
    ]
    items.sort(key=lambda item: (-item["total"], item["name"]))
    return {"total": len(df), "unidentified": unidentified, "items": items}


# ---------------------------------------------------------------------------
# Atraso de notificação por unidade
# ---------------------------------------------------------------------------


def compute_unit_notification_delay(df: pd.DataFrame) -> dict[str, Any]:
    """Median days between the first symptoms and the notification, per notifying unit.

    Same rule as the per-bairro chart: delay kept when between 0 and 60 days, units with
    fewer than 5 valid cases are only counted in ``hidden_count``, longest median first.
    """
    delays = (_date_column(df, "DT_NOTIFIC") - _date_column(df, "DT_SIN_PRI")).dt.days
    frame = pd.DataFrame({"code": _unit_codes(df), "days": delays})
    valid = frame["days"].between(0, _MAX_DELAY_DAYS) & frame["code"].notna()
    frame = frame.loc[valid]

    units: list[dict[str, Any]] = []
    hidden = 0
    for code, group in frame.groupby("code"):
        if len(group) < MIN_UNIT_DELAY_CASES:
            hidden += 1
            continue
        row = _delay_row(unit_name(str(code)), pd.Series(group["days"]))
        units.append({"id_unidade": str(code), "unit": row.pop("bairro"), **row})
    units.sort(key=lambda row: (-row["median_days"], -row["total"], row["unit"]))
    return {
        "limit_days": NOTIFICATION_DELAY_LIMIT_DAYS,
        "warn_days": _DELAY_WARN_MEDIAN_DAYS,
        "critical_days": _DELAY_CRITICAL_MEDIAN_DAYS,
        "min_cases": MIN_UNIT_DELAY_CASES,
        "units": units,
        "hidden_count": hidden,
    }


# ---------------------------------------------------------------------------
# Tempo de internação
# ---------------------------------------------------------------------------


def _stay_days(df: pd.DataFrame) -> pd.Series:
    """Days between hospital admission and outcome date; NaN when invalid."""
    days = (_date_column(df, "DT_EVOLUCA") - _date_column(df, "DT_INTERNA")).dt.days
    return days.where(days.between(0, MAX_STAY_DAYS))


def _closed_stays(df: pd.DataFrame) -> pd.DataFrame:
    """Cases that ended in cure or death with a valid stay, as ``outcome`` + ``days``."""
    evolution = _numeric(df, "EVOLUCAO")
    outcome = pd.Series(
        np.select([evolution == 1, outcome_death_mask(evolution)], ["cure", "death"], default=""),
        index=df.index,
    )
    frame = pd.DataFrame({"outcome": outcome, "days": _stay_days(df)})
    return frame.loc[(frame["outcome"] != "") & frame["days"].notna()]


def _median(values: np.ndarray) -> float | None:
    """Median ignoring NaN, rounded to one decimal; None when nothing is left."""
    finite = values[~np.isnan(values)]
    return round(float(np.median(finite)), 1) if finite.size else None


def _cumulative_curve(closed: pd.DataFrame) -> list[dict[str, Any]]:
    """Share of closed cases already discharged / dead by each day of stay."""
    grid = np.arange(CURVE_LAST_DAY + 1)
    total = len(closed)
    days = closed["days"].to_numpy(dtype=float)
    outcome = closed["outcome"].to_numpy()
    cure_days = np.sort(days[outcome == "cure"])
    death_days = np.sort(days[outcome == "death"])
    cure_counts = np.searchsorted(cure_days, grid, side="right")
    death_counts = np.searchsorted(death_days, grid, side="right")
    return [
        {
            "day": int(day),
            "cure_pct": _pct(int(cure_counts[day]), total),
            "death_pct": _pct(int(death_counts[day]), total),
        }
        for day in grid
    ]


def _average_daily_census(df: pd.DataFrame, bed_days: int) -> float | None:
    """Average inpatients per day: bed-days over the span of the symptom dates."""
    onset = _date_column(df, "DT_SIN_PRI").dropna()
    if onset.empty:
        return None
    period_days = max(1, int((onset.max() - onset.min()).days))
    return round(bed_days / period_days, 1)


def compute_hospital_stay(df: pd.DataFrame) -> dict[str, Any]:
    """Length of stay of closed cases: medians by outcome, bed-days and cumulative curve."""
    closed = _closed_stays(df)
    if closed.empty:
        return {
            "closed": 0,
            "median_days": None,
            "median_cure_days": None,
            "median_death_days": None,
            "mean_days": None,
            "bed_days": 0,
            "daily_census": None,
            "curve": [],
        }
    days = closed["days"].to_numpy(dtype=float)
    outcome = closed["outcome"].to_numpy()
    bed_days = int(days.sum())
    return {
        "closed": len(closed),
        "median_days": _median(days),
        "median_cure_days": _median(days[outcome == "cure"]),
        "median_death_days": _median(days[outcome == "death"]),
        "mean_days": round(float(days.mean()), 1),
        "bed_days": bed_days,
        "daily_census": _average_daily_census(df, bed_days),
        "curve": _cumulative_curve(closed),
    }


# ---------------------------------------------------------------------------
# Jornada clínica por perfil vacinal (COVID-19)
# ---------------------------------------------------------------------------


def _journey_row(stage: str, group: pd.DataFrame) -> dict[str, Any]:
    cure = int(group["cure"].to_numpy().sum())
    death = int(group["death"].to_numpy().sum())
    icu = int(group["icu"].to_numpy().sum())
    icu_known = int(group["icu_known"].to_numpy().sum())
    resolved = cure + death
    return {
        "stage": stage,
        "total": len(group),
        "median_days_to_hospital": _median(group["to_hospital"].to_numpy(dtype=float)),
        "median_stay_days": _median(group["stay"].to_numpy(dtype=float)),
        "icu_pct": _pct(icu, icu_known) if icu_known else None,
        "cure_pct": _pct(cure, resolved) if resolved else None,
        "death_pct": _pct(death, resolved) if resolved else None,
        "resolved": resolved,
    }


def compute_vaccine_journey(df: pd.DataFrame) -> dict[str, Any]:
    """Time to hospital, stay, ICU and outcome per COVID-19 vaccination stage."""
    if df.empty:
        return {"min_cases": MIN_JOURNEY_CASES, "stages": []}
    evolution = _numeric(df, "EVOLUCAO")
    icu = _numeric(df, "UTI")
    to_hospital = (_date_column(df, "DT_INTERNA") - _date_column(df, "DT_SIN_PRI")).dt.days
    frame = pd.DataFrame(
        {
            "stage": covid_stage_series(df),
            "to_hospital": to_hospital.where(to_hospital.between(0, _MAX_DELAY_DAYS)),
            "stay": _stay_days(df),
            "icu": icu == 1,
            "icu_known": icu.isin([1, 2]),
            "cure": evolution == 1,
            "death": outcome_death_mask(evolution),
        }
    )
    present = {str(name): group for name, group in frame.groupby("stage")}
    stages = [_journey_row(name, present[name]) for name in _DOSE_ORDER if name in present]
    return {"min_cases": MIN_JOURNEY_CASES, "stages": stages}
