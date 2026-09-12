"""Core analytics and aggregation for Mossoró SRAG data (lean: 12 tópicos)."""

from srag.data.analytics.clinical import (
    compute_comorbidities_pareto,
    compute_flu_vaccination_donut,
    compute_maternal_profile,
    compute_risk_factors_full_profile,
)
from srag.data.analytics.demographics import (
    categorize_age,
    compute_age_pareto,
    compute_citizen_pyramid,
    compute_covid_vaccination_profile,
    compute_population_pyramid,
    compute_race_profile,
    compute_schooling_profile,
)
from srag.data.analytics.filters import (
    age_years,
    apply_global_filters,
    outcome_death_mask,
)
from srag.data.analytics.surveillance import (
    classificar_status_gripe,
    compute_rt_pcr_summary,
    compute_time_series,
    compute_virus_distribution,
    infer_etiologic_agent,
    normalize_agent_values,
)
from srag.data.analytics.territorial import (
    BAIRRO_LABELS,
    MISSING_BAIRRO_LABEL,
    RURAL_AGGREGATE_LABEL,
    compute_territory_distribution,
    compute_zone_distribution,
    normalize_territory_labels,
)

__all__ = [
    "BAIRRO_LABELS",
    "MISSING_BAIRRO_LABEL",
    "RURAL_AGGREGATE_LABEL",
    "age_years",
    "apply_global_filters",
    "categorize_age",
    "classificar_status_gripe",
    "compute_age_pareto",
    "compute_citizen_pyramid",
    "compute_comorbidities_pareto",
    "compute_covid_vaccination_profile",
    "compute_flu_vaccination_donut",
    "compute_maternal_profile",
    "compute_population_pyramid",
    "compute_race_profile",
    "compute_risk_factors_full_profile",
    "compute_rt_pcr_summary",
    "compute_schooling_profile",
    "compute_territory_distribution",
    "compute_time_series",
    "compute_virus_distribution",
    "compute_zone_distribution",
    "infer_etiologic_agent",
    "normalize_agent_values",
    "normalize_territory_labels",
    "outcome_death_mask",
]
