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


class ClinicalFlowNode(TypedDict):
    """Sankey node."""

    name: str


class ClinicalFlowLink(TypedDict):
    """Sankey link between two stages of the patient journey."""

    source: str
    target: str
    value: int
    pct: float


class ClinicalFlowResponse(TypedDict):
    """Patient journey: origin -> ICU/ward -> ventilatory support -> outcome."""

    nodes: list[ClinicalFlowNode]
    links: list[ClinicalFlowLink]


class OddsRatioRow(TypedDict):
    """Risk factor with frequency, lethality and Odds Ratio (95% CI)."""

    name: str
    value: int
    deaths: int
    lethality: float
    prevalence: float
    odds_ratio: float
    ci_lower: float
    ci_upper: float


class SymptomsSignatureResponse(TypedDict):
    """Symptom prevalence per age band; each cell is [prevalence %, case count]."""

    labels: list[str]
    bands: list[str]
    matrices: dict[str, list[list[list[float]]]]


class IcuAccessStats(TypedDict):
    """Wait-time bands (days between hospital admission and ICU entry)."""

    total: int
    same_day: int
    d1_3: int
    d4_7: int
    d8_plus: int
    median_wait_days: float | None


class IcuAccessPeriod(IcuAccessStats):
    """Wait-time bands of one period (year, quarter or month)."""

    period: str


class IcuAccessSummary(IcuAccessStats):
    """Wait-time bands over every valid ICU admission."""

    same_day_pct: float
    over_limit: int
    over_limit_pct: float
    status: str | None


class IcuAccessResponse(TypedDict):
    """ICU access: summary plus one entry per period with enough admissions."""

    granularity: str
    limit_days: int
    min_cases: int
    summary: IcuAccessSummary
    periods: list[IcuAccessPeriod]


class DiagnosticMethodCounts(TypedDict):
    """Cases per confirmation group."""

    total: int
    rt_pcr: int
    antigeno_outros: int
    clinico_epi: int
    clinico_outros: int


class DiagnosticMethodsPeriod(DiagnosticMethodCounts):
    """Confirmation groups of one period."""

    period: str


class DiagnosticMethodsSummary(DiagnosticMethodCounts):
    """Confirmation groups over every case."""

    laboratory_pct: float
    rt_pcr_pct: float


class DiagnosticMethodsResponse(TypedDict):
    """How cases were confirmed, per period."""

    granularity: str
    min_cases: int
    summary: DiagnosticMethodsSummary
    periods: list[DiagnosticMethodsPeriod]


class OriginLethality(TypedDict):
    """Lethality of one infection origin (hospital or community)."""

    resolved: int
    deaths: int
    pct: float | None


class NosocomialLethality(TypedDict):
    """Hospital-acquired x community-acquired lethality."""

    nosocomial: OriginLethality
    community: OriginLethality


class NosocomialSummary(TypedDict):
    """Hospital-acquired infections over every case with known origin."""

    known: int
    nosocomial: int
    nosocomial_pct: float
    lethality: NosocomialLethality


class NosocomialPeriod(TypedDict):
    """Hospital-acquired share of one period."""

    period: str
    known: int
    nosocomial: int
    pct: float
    alert: bool


class NosocomialRiskResponse(TypedDict):
    """Hospital-acquired infection share per period with an optional alert limit."""

    granularity: str
    min_cases: int
    mean_pct: float | None
    alert_limit_pct: float | None
    summary: NosocomialSummary
    periods: list[NosocomialPeriod]


class DiagnosticLethalityMethod(TypedDict):
    """Lethality and time to outcome of one confirmation method."""

    method: str
    cases: int
    resolved: int
    deaths: int
    cfr: float
    median_days: float | None
    icu_pct: float


class DiagnosticLethalityOverall(TypedDict):
    """Lethality over every case with a known outcome."""

    cases: int
    resolved: int
    deaths: int
    cfr: float | None


class DiagnosticLethalityResponse(TypedDict):
    """Lethality ranked by confirmation method."""

    min_resolved: int
    overall: DiagnosticLethalityOverall
    methods: list[DiagnosticLethalityMethod]
    hidden: list[str]


class LabIndicator(TypedDict):
    """Share of cases meeting a lab indicator, with its target."""

    count: int
    pct: float
    target_pct: int


class LabWaitStats(TypedDict):
    """Distribution of waits in days."""

    count: int
    mean: float | None
    median: float | None
    p90: float | None
    p95: float | None


class RtPcrLatency(LabWaitStats):
    """RT-PCR latency with the share within the target."""

    within_target_pct: float | None
    target_days: int


class Turnaround(LabWaitStats):
    """Collection-to-result turnaround."""

    target_days: int


class LabPositivity(TypedDict):
    """Positivity among cases with a lab result."""

    tested: int
    positive: int
    pct: float | None


class LabPerformanceResponse(TypedDict):
    """Operational quality of the diagnostic network."""

    total: int
    result: LabIndicator
    collection: LabIndicator
    rt_pcr_latency: RtPcrLatency
    turnaround: Turnaround
    positivity: LabPositivity


class SamplePositivityRow(TypedDict):
    """Positivity of one sample type."""

    sample_type: str
    tested: int
    positive: int
    positivity_pct: float


class SamplePositivityResponse(TypedDict):
    """Positivity per sample type."""

    min_tested: int
    overall: LabPositivity
    types: list[SamplePositivityRow]
    hidden: list[str]


class AntiviralWindow(TypedDict):
    """Outcome of one antiviral start window."""

    key: str
    label: str
    total: int
    cure: int
    death: int
    cure_pct: float | None
    death_pct: float | None


class AntiviralWindowsResponse(TypedDict):
    """Cure and death by how fast the antiviral started."""

    treated: int
    with_dates: int
    median_days: float | None
    within_2d_pct: float | None
    cure_within_2d_pct: float | None
    cure_without_antiviral_pct: float | None
    death_after_5d_pct: float | None
    windows: list[AntiviralWindow]


class ImagingFinding(TypedDict):
    """Severity of one imaging finding."""

    finding: str
    total: int
    icu_pct: float
    resolved: int
    deaths: int
    death_pct: float | None


class ImagingGroup(TypedDict):
    """Findings of one imaging exam."""

    rows: list[ImagingFinding]
    hidden: list[str]


class ImagingSeverityResponse(TypedDict):
    """ICU admission and lethality by X-ray and CT result."""

    min_cases: int
    xray: ImagingGroup
    ct: ImagingGroup


class NotificationDelayOverall(TypedDict):
    """Delay between first symptoms and notification over every valid case."""

    total: int
    median_days: float | None
    within_limit_pct: float | None
    status: str | None


class NotificationDelayBairro(TypedDict):
    """Notification delay of one bairro."""

    bairro: str
    total: int
    median_days: float
    mean_days: float
    within_limit_pct: float
    status: str


class NotificationDelayResponse(TypedDict):
    """Notification delay overall and per bairro (longest median first)."""

    limit_days: int
    warn_days: int
    critical_days: int
    min_cases: int
    overall: NotificationDelayOverall
    bairros: list[NotificationDelayBairro]
    hidden_count: int


class MaternalGroup(TypedDict):
    """Outcome counts of one gestational group."""

    group: str
    total: int
    cure: int
    icu: int
    death: int
    other: int


class MaternalOutcomesResponse(TypedDict):
    """Outcome per gestational group (Gest. 1º/2º/3º tri, IG ignorada, Puérpera)."""

    gestantes_total: int
    puerperas_total: int
    min_cases: int
    groups: list[MaternalGroup]


class LabeledCount(TypedDict):
    """A category and its number of cases."""

    label: str
    count: int


class OccupationProfileResponse(TypedDict):
    """Most frequent occupations; ``informed`` excludes blank/ignored CBO."""

    total: int
    informed: int
    items: list[LabeledCount]


class AnimalContactResponse(TypedDict):
    """Contact with animals; ``ignored`` counts unfilled/ignored answers."""

    total: int
    ignored: int
    items: list[LabeledCount]


class CovidImmunizationResponse(TypedDict):
    """Last manufacturer and furthest dose reached for COVID-19."""

    manufacturers: list[LabeledCount]
    dose_stages: list[LabeledCount]


class NotifyingUnit(TypedDict):
    """One notifying unit with the outcome of its cases."""

    id_unidade: str
    name: str
    total: int
    cure: int
    death: int
    other: int


class NotifyingUnitsResponse(TypedDict):
    """Cases per notifying unit, most notifications first."""

    total: int
    unidentified: int
    items: list[NotifyingUnit]


class UnitDelayRow(TypedDict):
    """Notification delay of one notifying unit."""

    id_unidade: str
    unit: str
    total: int
    median_days: float
    mean_days: float
    within_limit_pct: float
    status: str


class UnitNotificationDelayResponse(TypedDict):
    """Notification delay per unit (longest median first)."""

    limit_days: int
    warn_days: int
    critical_days: int
    min_cases: int
    units: list[UnitDelayRow]
    hidden_count: int


class StayCurvePoint(TypedDict):
    """Share of closed cases already discharged or dead by a given day of stay."""

    day: int
    cure_pct: float
    death_pct: float


class HospitalStayResponse(TypedDict):
    """Length of stay of closed cases (cure or death with valid dates)."""

    closed: int
    median_days: float | None
    median_cure_days: float | None
    median_death_days: float | None
    mean_days: float | None
    bed_days: int
    daily_census: float | None
    curve: list[StayCurvePoint]


class VaccineJourneyStage(TypedDict):
    """Hospital journey of one COVID-19 vaccination stage."""

    stage: str
    total: int
    median_days_to_hospital: float | None
    median_stay_days: float | None
    icu_pct: float | None
    cure_pct: float | None
    death_pct: float | None
    resolved: int


class VaccineJourneyResponse(TypedDict):
    """Journey per vaccination stage; stages below ``min_cases`` are anecdotal."""

    min_cases: int
    stages: list[VaccineJourneyStage]
