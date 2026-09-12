"""Clinical API routers (lean: 12 tópicos + sociodemográfico)."""

# ruff: noqa

import logging
from typing import Any

import pandas as pd

from fastapi import APIRouter

logger = logging.getLogger(__name__)

from srag.api.types import ComorbiditiesParetoResponse
from srag.api.dependencies import CommonFiltersDep
from srag.api.core import get_df, apply_surveillance_filters, sanitize_data
from srag.data.analytics import (
    apply_global_filters,
    classificar_status_gripe,
    compute_age_pareto,
    compute_covid_vaccination_profile,
    compute_population_pyramid,
    compute_citizen_pyramid,
    compute_comorbidities_pareto,
    compute_flu_vaccination_donut,
    compute_maternal_profile,
    compute_race_profile,
    compute_risk_factors_full_profile,
    compute_rt_pcr_summary,
    compute_schooling_profile,
)

router = APIRouter(tags=["clinical"])


def _apply_base_filters(df: pd.DataFrame, filters: CommonFiltersDep) -> pd.DataFrame:
    df = apply_global_filters(df, filters.bairros)
    return apply_surveillance_filters(df, filters.years, filters.agents, filters.classi)


@router.get("/vaccination_profile")
def vaccination_profile(
    filters: CommonFiltersDep,
) -> Any:
    """Esquema vacinal COVID-19 e Influenza (tópicos 35/40)."""
    df = _apply_base_filters(get_df(), filters)
    if df.empty:
        return {}

    raw_gripe = df.apply(classificar_status_gripe, axis=1).value_counts().to_dict()

    # Contagens oficiais por código-fonte (não por rótulo): vacinado contra
    # gripe = qualquer status diferente de não vacinado/ignorado/inconsistência;
    # vacinado contra COVID = VACINA_COV == 1 (dicionário, campo 36).
    gripe_vacinados = int(
        sum(v for k, v in raw_gripe.items() if k not in ("nao_vacinado", "ignorado", "inconsistencia"))
    )
    covid_vacinados = int(pd.to_numeric(df["VACINA_COV"], errors="coerce").eq(1).sum())

    return sanitize_data(
        {
            "gripe_donut": compute_flu_vaccination_donut(df),
            "resumo": {
                "gripe_vacinados": gripe_vacinados,
                "covid_vacinados": covid_vacinados,
            },
        }
    )


@router.get("/citizen_bootstrap")
def citizen_bootstrap(
    filters: CommonFiltersDep,
) -> Any:
    """Idade, sexo, gestante (pirâmide + maternal) e sociodemográfico (raça, escolaridade, ocupação)."""
    df_filtered = _apply_base_filters(get_df(), filters)

    return sanitize_data(
        {
            "citizen_pyramid": compute_citizen_pyramid(df_filtered),
            "population_pyramid": compute_population_pyramid(df_filtered),
            "age_pareto": compute_age_pareto(df_filtered),
            "covid_vaccination_profile": compute_covid_vaccination_profile(df_filtered),
            "race_profile": compute_race_profile(df_filtered),
            "schooling_profile": compute_schooling_profile(df_filtered),
            "risk_factors_full": compute_risk_factors_full_profile(df_filtered),
            "maternal_profile": compute_maternal_profile(df_filtered),
        }
    )


@router.get("/laboratory_network")
def laboratory_network(
    filters: CommonFiltersDep,
) -> Any:
    """RT-PCR (tópico 70): detectáveis (PCR_RESUL==1)."""
    df = _apply_base_filters(get_df(), filters)
    if df.empty:
        return {"total_cases": 0}
    return sanitize_data(compute_rt_pcr_summary(df))


@router.get("/clinical/comorbidities_pareto")
def comorbidities_pareto(
    filters: CommonFiltersDep,
) -> ComorbiditiesParetoResponse:
    """Comorbidity mentions sorted desc with cumulative % (Pareto contract)."""
    df = _apply_base_filters(get_df(), filters)
    res = compute_comorbidities_pareto(df)
    return sanitize_data(res)
