"""Analytical charts API ("Gráficos analíticos").

Every endpoint shares the dashboard filters (year, agent, bairro, base de
análise, gravidade, sintomas) so the charts always agree with the rest of
the app.
"""

# FastAPI resolve as anotações em runtime: estes imports não podem ir para TYPE_CHECKING.
# ruff: noqa: TC001, TC002

from typing import Annotated, cast

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from srag.api.core import apply_surveillance_filters, get_df, sanitize_data
from srag.api.dependencies import CommonFiltersDep
from srag.api.types import ClinicalFlowResponse, OddsRatioRow, SymptomsSignatureResponse
from srag.data.analytics import (
    SIGNATURE_PROFILES,
    apply_global_filters,
    compute_clinical_flow,
    compute_comorbidities_odds_ratio,
    compute_symptoms_signature,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _filtered_df(filters: CommonFiltersDep) -> pd.DataFrame:
    df = apply_global_filters(
        get_df(), filters.bairros, filters.base, filters.gravidade, filters.sintomas
    )
    return apply_surveillance_filters(df, filters.years, filters.agents, filters.classi)


@router.get("/clinical_flow")
def clinical_flow(filters: CommonFiltersDep) -> ClinicalFlowResponse:
    """Sankey: origem, UTI ou enfermaria, suporte ventilatório e desfecho."""
    return cast(
        "ClinicalFlowResponse", sanitize_data(compute_clinical_flow(_filtered_df(filters)))
    )


@router.get("/comorbidities_odds_ratio")
def comorbidities_odds_ratio(filters: CommonFiltersDep) -> list[OddsRatioRow]:
    """Frequência, letalidade e Odds Ratio (IC 95%) de cada fator de risco."""
    rows = compute_comorbidities_odds_ratio(_filtered_df(filters))
    return cast("list[OddsRatioRow]", sanitize_data(rows))


@router.get("/symptoms_signature")
def symptoms_signature(
    filters: CommonFiltersDep,
    profile: Annotated[str, Query()] = "all",
) -> SymptomsSignatureResponse:
    """Prevalência de sintomas por faixa etária: COVID-19, Influenza e VSR."""
    if profile not in SIGNATURE_PROFILES:
        raise HTTPException(
            status_code=422,
            detail=f"profile '{profile}' invalid, expected one of {list(SIGNATURE_PROFILES)}",
        )
    result = compute_symptoms_signature(_filtered_df(filters), profile)
    return cast("SymptomsSignatureResponse", sanitize_data(result))
