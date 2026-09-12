"""Type definitions for API responses."""

from typing import Any, TypedDict


class SummaryResponse(TypedDict):
    """Summary metrics response."""

    uti_total: int
    death_rate: float
    death_count: int
    total: int
    hospitalized: int
    notification_total: int
    available_years: list[int]


class TrendsResponse(TypedDict):
    """Weekly trends."""

    history: list[dict[str, Any]]


class VirusDistributionItem(TypedDict):
    """Virus distribution item."""

    virus: str
    count: int


class TerritoryBootstrapResponse(TypedDict):
    """Territory bootstrap response (lean: bairro + zona)."""

    territory: dict[str, Any]


class LaboratoryNetworkResponse(TypedDict):
    """RT-PCR summary (tópico 70)."""

    total_cases: int


class VaccinationProfileResponse(TypedDict):
    """Vaccination profile response."""

    gripe_donut: list[dict[str, Any]]
    resumo: dict[str, Any]


class CitizenBootstrapResponse(TypedDict):
    """Citizen bootstrap response (lean: pirâmide, sociodemográfico, gestante)."""

    citizen_pyramid: list[dict[str, Any]]
    population_pyramid: list[dict[str, Any]]
    race_profile: list[dict[str, Any]]
    schooling_profile: list[dict[str, Any]]
    risk_factors_full: list[dict[str, Any]]
    maternal_profile: dict[str, Any]


class ComorbiditiesParetoItem(TypedDict):
    """A comorbidity mention with cumulative % (Pareto, value desc)."""

    name: str
    value: int
    cumulative: float


ComorbiditiesParetoResponse = list[ComorbiditiesParetoItem]
