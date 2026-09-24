"""Core API routers."""

# ruff: noqa

import pandas as pd

from fastapi import APIRouter

from srag import __version__
from srag.api.dependencies import CommonFiltersDep
from srag.api.types import (
    SummaryResponse,
    TrendsResponse,
    VirusDistributionItem,
)
from srag.api.core import get_df, apply_surveillance_filters, sanitize_data
from srag.data.analytics import (
    apply_global_filters,
    compute_time_series,
    compute_virus_distribution,
)

router = APIRouter(tags=["core"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


from srag.data.analytics.filters import epi_week_year


@router.get("/summary")
def get_summary(
    filters: CommonFiltersDep,
) -> SummaryResponse:
    df_all = get_df()
    available_years: list[int] = []
    if not df_all.empty and "DT_SIN_PRI" in df_all.columns:
        dt_s = pd.to_datetime(df_all["DT_SIN_PRI"], errors="coerce")
        years_series = epi_week_year(dt_s).dropna()
        available_years = sorted({int(y) for y in years_series})

    df = apply_global_filters(
        df_all, filters.bairros, filters.base, filters.gravidade, filters.sintomas
    )
    df = apply_surveillance_filters(df, filters.years, filters.agents, filters.classi)
    if df.empty:
        return sanitize_data(
            {
                "uti_total": 0,
                "death_rate": 0.0,
                "death_count": 0,
                "total": 0,
                "hospitalized": 0,
                "notification_total": 0,
                "available_years": available_years,
            }
        )

    total = len(df)
    hospital_col = df.get("HOSPITAL")
    hospitalized = int((hospital_col.fillna(0) == 1).sum()) if hospital_col is not None else 0
    uti_cases = int((df["UTI"] == 1).sum())

    # Standard Epidemiological Lethality: deaths / (cure + deaths)
    closed_cases_mask = df["EVOLUCAO"].isin([1, 2])
    closed_count = closed_cases_mask.sum()
    death_cases = int((df["EVOLUCAO"] == 2).sum())

    return sanitize_data(
        {
            "uti_total": uti_cases,
            "death_rate": round((death_cases / closed_count * 100), 2)
            if closed_count > 0
            else 0.0,
            "death_count": death_cases,
            "total": total,
            "hospitalized": hospitalized,
            "notification_total": total,
            "available_years": available_years,
        }
    )


@router.get("/trends")
def get_trends(
    filters: CommonFiltersDep,
    last_n_weeks: int = 26,
) -> TrendsResponse:
    df = get_df()
    df = apply_global_filters(
        df, filters.bairros, filters.base, filters.gravidade, filters.sintomas
    )
    df = apply_surveillance_filters(df, filters.years, filters.agents, filters.classi)
    if df.empty:
        return {"history": []}

    ts = compute_time_series(df)
    full_history = ts.to_dict(orient="records")
    history = full_history if last_n_weeks <= 0 else full_history[-last_n_weeks:]

    # Curva acumulada oficial sobre o recorte retornado.
    acc = 0
    for h in history:
        acc += int(h["total"])
        h["cumulative"] = acc

    return sanitize_data({"history": history})


@router.get("/virus")
def get_virus(
    filters: CommonFiltersDep,
) -> list[VirusDistributionItem]:
    df = get_df()
    df = apply_global_filters(
        df, filters.bairros, filters.base, filters.gravidade, filters.sintomas
    )
    df = apply_surveillance_filters(df, filters.years, filters.agents, filters.classi)
    if df.empty:
        return []

    dist = compute_virus_distribution(df)

    return sanitize_data(dist.to_dict(orient="records"))  # type: ignore[return-value]
