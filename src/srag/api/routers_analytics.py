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
from srag.api.types import (
    AnimalContactResponse,
    AntiviralWindowsResponse,
    ClinicalFlowResponse,
    CovidImmunizationResponse,
    DiagnosticLethalityResponse,
    DiagnosticMethodsResponse,
    IcuAccessResponse,
    ImagingSeverityResponse,
    LabPerformanceResponse,
    MaternalOutcomesResponse,
    NosocomialRiskResponse,
    NotificationDelayResponse,
    OccupationProfileResponse,
    OddsRatioRow,
    SamplePositivityResponse,
    SymptomsSignatureResponse,
)
from srag.data.analytics import (
    ICU_GRANULARITIES,
    SIGNATURE_PROFILES,
    apply_global_filters,
    compute_animal_contact,
    compute_antiviral_windows,
    compute_clinical_flow,
    compute_comorbidities_odds_ratio,
    compute_covid_dose_stage,
    compute_diagnostic_lethality,
    compute_diagnostic_methods,
    compute_icu_access,
    compute_imaging_severity,
    compute_lab_performance,
    compute_maternal_outcomes,
    compute_nosocomial_risk,
    compute_notification_delay,
    compute_occupation_profile,
    compute_sample_positivity,
    compute_symptoms_signature,
    compute_vaccine_manufacturers,
)
from srag.data.analytics.territorial import normalize_territory_labels

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _check_granularity(granularity: str) -> None:
    if granularity not in ICU_GRANULARITIES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"granularity '{granularity}' invalid, expected one of {list(ICU_GRANULARITIES)}"
            ),
        )


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


@router.get("/icu_access")
def icu_access(
    filters: CommonFiltersDep,
    granularity: Annotated[str, Query()] = "year",
) -> IcuAccessResponse:
    """Tempo entre a internação e a entrada na UTI, por ano, trimestre ou mês."""
    _check_granularity(granularity)
    result = compute_icu_access(_filtered_df(filters), granularity)
    return cast("IcuAccessResponse", sanitize_data(result))


@router.get("/diagnostic_methods")
def diagnostic_methods(
    filters: CommonFiltersDep,
    granularity: Annotated[str, Query()] = "year",
) -> DiagnosticMethodsResponse:
    """Como os casos foram confirmados (laboratório x clínico), por período."""
    _check_granularity(granularity)
    result = compute_diagnostic_methods(_filtered_df(filters), granularity)
    return cast("DiagnosticMethodsResponse", sanitize_data(result))


@router.get("/nosocomial_risk")
def nosocomial_risk(
    filters: CommonFiltersDep,
    granularity: Annotated[str, Query()] = "year",
) -> NosocomialRiskResponse:
    """Percentual de infecção hospitalar por período e letalidade por origem."""
    _check_granularity(granularity)
    result = compute_nosocomial_risk(_filtered_df(filters), granularity)
    return cast("NosocomialRiskResponse", sanitize_data(result))


@router.get("/diagnostic_lethality")
def diagnostic_lethality(filters: CommonFiltersDep) -> DiagnosticLethalityResponse:
    """Letalidade e tempo até o desfecho por método de confirmação."""
    result = compute_diagnostic_lethality(_filtered_df(filters))
    return cast("DiagnosticLethalityResponse", sanitize_data(result))


@router.get("/lab_performance")
def lab_performance(filters: CommonFiltersDep) -> LabPerformanceResponse:
    """Qualidade operacional do diagnóstico: resultado, coleta, latência e tempo de resposta."""
    result = compute_lab_performance(_filtered_df(filters))
    return cast("LabPerformanceResponse", sanitize_data(result))


@router.get("/sample_positivity")
def sample_positivity(filters: CommonFiltersDep) -> SamplePositivityResponse:
    """Positividade (RT-PCR ou antígeno) por tipo de amostra."""
    result = compute_sample_positivity(_filtered_df(filters))
    return cast("SamplePositivityResponse", sanitize_data(result))


@router.get("/antiviral_windows")
def antiviral_windows(filters: CommonFiltersDep) -> AntiviralWindowsResponse:
    """Cura e óbito conforme a rapidez do início do antiviral."""
    result = compute_antiviral_windows(_filtered_df(filters))
    return cast("AntiviralWindowsResponse", sanitize_data(result))


@router.get("/imaging_severity")
def imaging_severity(filters: CommonFiltersDep) -> ImagingSeverityResponse:
    """UTI e letalidade por resultado de Raio-X e de tomografia."""
    result = compute_imaging_severity(_filtered_df(filters))
    return cast("ImagingSeverityResponse", sanitize_data(result))


@router.get("/notification_delay")
def notification_delay(filters: CommonFiltersDep) -> NotificationDelayResponse:
    """Atraso entre os primeiros sintomas e a notificação, geral e por bairro."""
    df = normalize_territory_labels(_filtered_df(filters))
    return cast("NotificationDelayResponse", sanitize_data(compute_notification_delay(df)))


@router.get("/maternal_outcomes")
def maternal_outcomes(filters: CommonFiltersDep) -> MaternalOutcomesResponse:
    """Desfecho (cura, UTI sobrevivente, óbito) por grupo gestacional."""
    result = compute_maternal_outcomes(_filtered_df(filters))
    return cast("MaternalOutcomesResponse", sanitize_data(result))


@router.get("/occupation_profile")
def occupation_profile(filters: CommonFiltersDep) -> OccupationProfileResponse:
    """Ocupações (CBO) mais frequentes entre os casos notificados."""
    result = compute_occupation_profile(_filtered_df(filters))
    return cast("OccupationProfileResponse", sanitize_data(result))


@router.get("/animal_contact")
def animal_contact(filters: CommonFiltersDep) -> AnimalContactResponse:
    """Contato com aves, suínos ou outros animais."""
    result = compute_animal_contact(_filtered_df(filters))
    return cast("AnimalContactResponse", sanitize_data(result))


@router.get("/covid_immunization")
def covid_immunization(filters: CommonFiltersDep) -> CovidImmunizationResponse:
    """Fabricante da última dose e etapa vacinal mais avançada contra COVID-19."""
    df = _filtered_df(filters)
    result = {
        "manufacturers": compute_vaccine_manufacturers(df),
        "dose_stages": compute_covid_dose_stage(df),
    }
    return cast("CovidImmunizationResponse", sanitize_data(result))
