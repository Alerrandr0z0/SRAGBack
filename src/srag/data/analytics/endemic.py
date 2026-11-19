"""Corredor endêmico: casos de cada semana epidemiológica contra a faixa esperada.

A faixa vem dos anos anteriores ao ano de referência: para cada semana, o primeiro
quartil, a mediana e o terceiro quartil dos casos daqueles anos. Acima do limite de
alerta (terceiro quartil + 1,5 x amplitude interquartil) a semana é tratada como epidêmica.
São necessários pelo menos ``MIN_HISTORY_YEARS`` anos de histórico.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from srag.utils.epi_weeks import compute_epi_week_columns

MIN_HISTORY_YEARS = 3
MAX_HISTORY_YEARS = 5
WEEKS_PER_YEAR = 52  # a SE 53 (rara) fica de fora para manter a faixa comparável


def _round(value: float) -> float:
    return round(float(value), 1)


def _weekly_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Casos por (ano epidemiológico, semana 1-52), com colunas = semanas."""
    epi = compute_epi_week_columns(pd.Series(df["DT_SIN_PRI"], index=df.index))
    frame = pd.DataFrame({"year": epi["_epi_year"], "week": epi["_epi_week_int"]})
    frame = frame[(frame["year"] > 0) & frame["week"].between(1, WEEKS_PER_YEAR)]
    counts = pd.DataFrame(frame.groupby(["year", "week"]).size().unstack(fill_value=0))
    return counts.reindex(columns=range(1, WEEKS_PER_YEAR + 1), fill_value=0)


def _status(cases: int, p25: float, p75: float, alert: float) -> str:
    if cases > alert:
        return "epidemic"
    if cases > p75:
        return "elevated"
    if cases < p25:
        return "below"
    return "expected"


def _empty(reference_year: int | None, history_years: list[int]) -> dict[str, Any]:
    return {
        "enough_history": False,
        "min_years": MIN_HISTORY_YEARS,
        "reference_year": reference_year,
        "history_years": history_years,
        "current_week": None,
        "current_cases": None,
        "current_status": None,
        "weeks_above": 0,
        "weeks": [],
    }


def compute_endemic_channel(df: pd.DataFrame, reference_year: int | None = None) -> dict[str, Any]:
    """Weekly cases of ``reference_year`` against the band of the previous years.

    ``reference_year`` defaults to the latest epidemiological year in the data. The data
    must not be filtered by year: the earlier years are the baseline of the band.
    """
    if df.empty or "DT_SIN_PRI" not in df.columns:
        return _empty(reference_year, [])

    counts = _weekly_counts(df)
    if counts.empty:
        return _empty(reference_year, [])

    years = sorted(int(year) for year in counts.index.tolist())
    reference = int(reference_year) if reference_year else years[-1]
    history = [year for year in years if year < reference][-MAX_HISTORY_YEARS:]
    if len(history) < MIN_HISTORY_YEARS or reference not in years:
        return _empty(reference, history)

    past = counts.loc[history].to_numpy(dtype="float64")
    p25, median, p75 = (np.percentile(past, q, axis=0) for q in (25, 50, 75))
    alert = np.maximum(p75 + 1.5 * (p75 - p25), p75 + 1)

    current = counts.loc[reference].to_numpy(dtype="int64")  # posição i = semana i + 1
    last_week = int(np.flatnonzero(current > 0).max()) + 1
    weeks: list[dict[str, Any]] = []
    above = 0
    for index in range(WEEKS_PER_YEAR):
        week = index + 1
        cases = int(current[index]) if week <= last_week else None
        status = (
            _status(cases, p25[index], p75[index], alert[index]) if cases is not None else None
        )
        above += status in ("elevated", "epidemic")
        weeks.append(
            {
                "week": week,
                "cases": cases,
                "p25": _round(p25[index]),
                "median": _round(median[index]),
                "p75": _round(p75[index]),
                "alert": _round(alert[index]),
                "status": status,
            }
        )

    return {
        "enough_history": True,
        "min_years": MIN_HISTORY_YEARS,
        "reference_year": reference,
        "history_years": history,
        "current_week": last_week,
        "current_cases": weeks[last_week - 1]["cases"],
        "current_status": weeks[last_week - 1]["status"],
        "weeks_above": int(above),
        "weeks": weeks,
    }
