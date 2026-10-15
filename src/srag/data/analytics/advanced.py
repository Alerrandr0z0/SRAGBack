"""Advanced analytical computations for the "Gráficos analíticos" dashboard.

Ported from the legacy SRAG dashboard. Every function is pure: it receives the
already-filtered DataFrame and returns a JSON-friendly structure, so it can be
unit-tested with synthetic data and reused by any router.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

import pandas as pd

from srag.data.analytics.filters import age_years, outcome_death_mask
from srag.data.analytics.surveillance import infer_etiologic_agent
from srag.data.references import SYMPTOM_FIELDS, VALID_OUTCOMES

# ---------------------------------------------------------------------------
# Fluxo da jornada clínica (Sankey)
# ---------------------------------------------------------------------------

_ORIGEM_LABELS = {1: "Infecção Hospitalar", 2: "Comunitária"}
_UTI_LABELS = {1: "Internado em UTI", 2: "Internado em Enfermaria"}
_VENT_LABELS = {1: "Vent. Invasiva", 2: "Vent. Não Inv.", 3: "Sem Suporte"}
_FIM_LABELS = {1: "Cura", 2: "Óbito"}


def _label_column(
    df: pd.DataFrame, column: str, mapping: dict[int, str], fallback: str
) -> pd.Series:
    """Map a coded SIVEP column to labels; missing column/values use ``fallback``."""
    if column not in df.columns:
        return pd.Series(fallback, index=df.index, dtype="object")
    codes = pd.to_numeric(df[column], errors="coerce")
    return codes.map(mapping).fillna(fallback)


def _flow_links(stages: pd.DataFrame, source: str, target: str) -> list[dict[str, Any]]:
    counts = stages.groupby([source, target]).size().reset_index(name="value")
    source_totals = counts.groupby(source)["value"].transform("sum")
    counts["pct"] = (counts["value"] / source_totals * 100).round(1)
    return [
        {
            "source": row[source],
            "target": row[target],
            "value": int(row["value"]),
            "pct": float(row["pct"]),
        }
        for _, row in counts.iterrows()
    ]


def compute_clinical_flow(df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    """Patient journey for the Sankey: origem → UTI/enfermaria → suporte → desfecho."""
    if df.empty:
        return {"nodes": [], "links": []}

    stages = pd.DataFrame(
        {
            "origem": _label_column(df, "NOSOCOMIAL", _ORIGEM_LABELS, "Origem (Ignorado)"),
            "uti": _label_column(df, "UTI", _UTI_LABELS, "Internação (Ignorado)"),
            "vent": _label_column(df, "SUPORT_VEN", _VENT_LABELS, "Suporte (Ignorado)"),
            "fim": _label_column(df, "EVOLUCAO", _FIM_LABELS, "Em Aberto"),
        },
        index=df.index,
    )

    links = (
        _flow_links(stages, "origem", "uti")
        + _flow_links(stages, "uti", "vent")
        + _flow_links(stages, "vent", "fim")
    )
    names = sorted({link["source"] for link in links} | {link["target"] for link in links})
    return {"nodes": [{"name": name} for name in names], "links": links}


# ---------------------------------------------------------------------------
# Associação de comorbidades com o óbito (Odds Ratio)
# ---------------------------------------------------------------------------

_RISK_FIELDS = [
    ("PUERPERA", "Puérpera"),
    ("CARDIOPATI", "Cardiopatia"),
    ("HEMATOLOGI", "Doença hematológica"),
    ("SIND_DOWN", "Síndrome de Down"),
    ("HEPATICA", "Doença hepática"),
    ("ASMA", "Asma"),
    ("DIABETES", "Diabetes"),
    ("NEUROLOGIC", "Doença neurológica"),
    ("PNEUMOPATI", "Pneumopatia"),
    ("IMUNODEPRE", "Imunodepressão"),
    ("RENAL", "Doença renal"),
    ("OBESIDADE", "Obesidade"),
    ("TABAG", "Tabagismo"),
    ("OUT_MORBI", "Outros fatores"),
]


def _odds_ratio_with_ci(a: int, b: int, c: int, d: int) -> tuple[float, float, float]:
    """Odds Ratio with Woolf 95% CI from a 2x2 table.

    Cells: a=exposed+dead, b=exposed+alive, c=unexposed+dead, d=unexposed+alive.
    Applies the Haldane correction (+0.5) when any cell is zero.
    Returns (OR, ci_lower, ci_upper).
    """
    aa, bb, cc, dd = float(a), float(b), float(c), float(d)
    if 0 in (a, b, c, d):
        aa, bb, cc, dd = aa + 0.5, bb + 0.5, cc + 0.5, dd + 0.5
    if cc * bb == 0:
        return (0.0, 0.0, 0.0)

    odds = (aa * dd) / (bb * cc)
    se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    ln_or = math.log(odds)
    return (
        round(odds, 3),
        round(math.exp(ln_or - 1.96 * se), 3),
        round(math.exp(ln_or + 1.96 * se), 3),
    )


def compute_comorbidities_odds_ratio(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Each risk factor with frequency, lethality, Odds Ratio and 95% CI.

    The 2x2 table only uses clinically resolved cases (EVOLUCAO in VALID_OUTCOMES);
    death is EVOLUCAO == 2. Result is sorted by Odds Ratio, descending.
    """
    if df.empty:
        return []

    if "EVOLUCAO" in df.columns:
        evolucao = pd.to_numeric(df["EVOLUCAO"], errors="coerce")
        resolved_mask = evolucao.isin(VALID_OUTCOMES)
        death_mask = outcome_death_mask(df["EVOLUCAO"])
    else:
        resolved_mask = pd.Series(False, index=df.index)
        death_mask = pd.Series(False, index=df.index)

    total_resolved = int(resolved_mask.sum())
    total_deaths = int(death_mask.sum())

    rows: list[dict[str, Any]] = []
    for column, label in _RISK_FIELDS:
        if column not in df.columns:
            rows.append(_empty_risk_row(label))
            continue

        factor_mask = pd.to_numeric(df[column], errors="coerce") == 1
        count = int(factor_mask.sum())
        resolved_with = int((factor_mask & resolved_mask).sum())
        deaths_with = int((factor_mask & death_mask).sum())

        unexposed_deaths = total_deaths - deaths_with
        unexposed_resolved = total_resolved - resolved_with
        unexposed_alive = unexposed_resolved - unexposed_deaths
        # OR is undefined without resolved cases on both sides of the comparison
        # (the Haldane correction would otherwise invent a meaningless value).
        if resolved_with == 0 or unexposed_resolved == 0:
            odds_ratio, ci_lower, ci_upper = 0.0, 0.0, 0.0
        else:
            odds_ratio, ci_lower, ci_upper = _odds_ratio_with_ci(
                deaths_with, resolved_with - deaths_with, unexposed_deaths, unexposed_alive
            )

        rows.append(
            {
                "name": label,
                "value": count,
                "deaths": deaths_with,
                "lethality": round(deaths_with / resolved_with * 100, 2) if resolved_with else 0.0,
                "prevalence": round(count / len(df) * 100, 2),
                "odds_ratio": odds_ratio,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
            }
        )

    rows.sort(key=lambda row: row["odds_ratio"], reverse=True)
    return rows


def _empty_risk_row(label: str) -> dict[str, Any]:
    return {
        "name": label,
        "value": 0,
        "deaths": 0,
        "lethality": 0.0,
        "prevalence": 0.0,
        "odds_ratio": 0.0,
        "ci_lower": 0.0,
        "ci_upper": 0.0,
    }


# ---------------------------------------------------------------------------
# Assinatura clínica de sintomas (COVID-19, Influenza e VSR)
# ---------------------------------------------------------------------------

SIGNATURE_PROFILES = ("all", "crianca", "adolescente", "adulto", "idoso")

_SYMPTOM_LABELS = {
    "febre": "Febre",
    "tosse": "Tosse",
    "garganta": "Dor de garganta",
    "dispneia": "Dispneia",
    "desc_resp": "Desconforto respiratório",
    "saturacao": "Saturação <95%",
    "diarreia": "Diarreia",
    "vomito": "Vômito",
    "dor_abd": "Dor abdominal",
    "fadiga": "Fadiga",
    "perd_olft": "Perda de olfato",
    "perd_pala": "Perda de paladar",
    "outro_sin": "Outros sintomas",
}

# agent label (from infer_etiologic_agent) -> key used in the response
_SIGNATURE_AGENTS = {"COVID-19": "covid", "Influenza": "gripe", "VSR": "vsr"}


def _age_bands(age: pd.Series, profile: str) -> list[tuple[str, pd.Series]]:
    """(label, mask) pairs for the requested age profile."""
    if profile == "crianca":
        return [
            ("<2 anos", age < 2),
            ("2-5 anos", (age >= 2) & (age < 6)),
            ("6-11 anos", (age >= 6) & (age < 12)),
        ]
    if profile == "adolescente":
        return [("12-14 anos", (age >= 12) & (age < 15)), ("15-19 anos", (age >= 15) & (age < 20))]
    if profile == "adulto":
        return [("20-39 anos", (age >= 20) & (age < 40)), ("40-59 anos", (age >= 40) & (age < 60))]
    if profile == "idoso":
        return [
            ("60-69 anos", (age >= 60) & (age < 70)),
            ("70-79 anos", (age >= 70) & (age < 80)),
            ("80+ anos", age >= 80),
        ]
    return [
        ("Criança", age < 12),
        ("Adolescente", (age >= 12) & (age < 20)),
        ("Adulto", (age >= 20) & (age < 60)),
        ("Idoso", age >= 60),
    ]


def _has_symptom(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    return pd.to_numeric(df[column], errors="coerce") == 1


def _prevalence_row(
    has_symptom: pd.Series, agent_mask: pd.Series, band_masks: list[pd.Series]
) -> list[list[float | int]]:
    """[prevalence %, case count] of one symptom, for each age band."""
    row: list[list[float | int]] = []
    for band_mask in band_masks:
        subset = agent_mask & band_mask
        total = int(subset.sum())
        hits = int((has_symptom & subset).sum()) if total else 0
        row.append([round(hits / total * 100, 1) if total else 0.0, hits])
    return row


def _agent_matrix(
    df: pd.DataFrame, agent_mask: pd.Series, band_masks: list[pd.Series]
) -> list[list[list[float | int]]]:
    return [
        _prevalence_row(_has_symptom(df, column), agent_mask, band_masks)
        for column in SYMPTOM_FIELDS.values()
    ]


def _order_by_total_prevalence(
    matrices: dict[str, list[list[list[float | int]]]],
) -> list[int]:
    """Row indexes sorted by the symptom's summed prevalence, most frequent first."""
    count = len(SYMPTOM_FIELDS)
    totals = [
        sum(cell[0] for matrix in matrices.values() for cell in matrix[index])
        for index in range(count)
    ]
    return sorted(range(count), key=lambda index: totals[index], reverse=True)


def compute_symptoms_signature(df: pd.DataFrame, profile: str = "all") -> dict[str, Any]:
    """Symptom prevalence (%) per age band for COVID-19, Influenza and VSR.

    Each case belongs to exactly one agent group (the same ``infer_etiologic_agent``
    used by the agent filter, so VSR positives are not double counted as COVID/Flu).
    Each cell is ``[prevalence_pct, case_count]``; symptoms are ordered by their
    summed prevalence, most frequent first.
    """
    if df.empty:
        return {"labels": [], "bands": [], "matrices": {}}

    profile = profile if profile in SIGNATURE_PROFILES else "all"
    work = df.copy()
    bands = _age_bands(pd.to_numeric(age_years(work), errors="coerce"), profile)
    band_masks = [mask.fillna(False).astype(bool) for _, mask in bands]
    agents = infer_etiologic_agent(work)

    matrices = {
        key: _agent_matrix(work, agents == label, band_masks)
        for label, key in _SIGNATURE_AGENTS.items()
    }
    order = _order_by_total_prevalence(matrices)
    labels = [_SYMPTOM_LABELS[key] for key in SYMPTOM_FIELDS]
    return {
        "labels": [labels[index] for index in order],
        "bands": [label for label, _ in bands],
        "matrices": {key: [matrix[i] for i in order] for key, matrix in matrices.items()},
    }


# ---------------------------------------------------------------------------
# Acesso à UTI: tempo entre a internação e a entrada na UTI
# ---------------------------------------------------------------------------

ICU_GRANULARITIES = ("year", "quarter", "month")
ICU_ACCEPTABLE_DAYS = 3
ICU_MAX_WAIT_DAYS = 30
# Períodos com menos admissões que isso não são exibidos (percentuais instáveis).
_ICU_MIN_CASES = {"year": 50, "quarter": 30, "month": 20}
_ICU_WARN_MEDIAN_DAYS = 2
_ICU_CRITICAL_MEDIAN_DAYS = 4


def _pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total else 0.0


def _icu_waits(df: pd.DataFrame) -> pd.DataFrame:
    """ICU admissions with valid dates: admission date and days waited for the ICU."""
    if df.empty or not {"UTI", "DT_INTERNA", "DT_ENTUTI"} <= set(df.columns):
        return pd.DataFrame(
            {
                "admitted": pd.Series(dtype="datetime64[ns]"),
                "wait_days": pd.Series(dtype="int64"),
            }
        )
    icu = df[pd.to_numeric(df["UTI"], errors="coerce") == 1]
    admitted = pd.to_datetime(icu["DT_INTERNA"], errors="coerce")
    entered = pd.to_datetime(icu["DT_ENTUTI"], errors="coerce")
    wait = (entered - admitted).dt.days
    valid = admitted.notna() & wait.between(0, ICU_MAX_WAIT_DAYS)
    return pd.DataFrame({"admitted": admitted[valid], "wait_days": wait[valid].astype("int64")})


def _period_key(admitted: pd.Series, granularity: str) -> pd.Series:
    if granularity == "year":
        return admitted.dt.strftime("%Y")
    if granularity == "quarter":
        return admitted.dt.year.astype(str) + "-Q" + admitted.dt.quarter.astype(str)
    return admitted.dt.strftime("%Y-%m")


def _icu_wait_stats(waits: pd.Series) -> dict[str, Any]:
    """Wait-time bands and median wait (only among those who waited at all)."""
    waited = waits[waits > 0]
    return {
        "total": len(waits),
        "same_day": int((waits == 0).sum()),
        "d1_3": int(waits.between(1, ICU_ACCEPTABLE_DAYS).sum()),
        "d4_7": int(waits.between(ICU_ACCEPTABLE_DAYS + 1, 7).sum()),
        "d8_plus": int((waits >= 8).sum()),
        "median_wait_days": float(waited.median()) if len(waited) else None,
    }


def _icu_status(median: float | None) -> str | None:
    if median is None:
        return None
    if median <= _ICU_WARN_MEDIAN_DAYS:
        return "adequado"
    if median <= _ICU_CRITICAL_MEDIAN_DAYS:
        return "atencao"
    return "critico"


def compute_icu_access(df: pd.DataFrame, granularity: str = "year") -> dict[str, Any]:
    """How long ICU patients waited between hospital admission and ICU entry.

    Wait = DT_ENTUTI - DT_INTERNA in days, kept when between 0 and 30. Admissions
    are grouped by the hospital admission date (year, quarter or month). The
    summary uses every valid admission; ``periods`` only lists periods with enough
    admissions to be meaningful. ``status`` grades the median wait of those who
    waited: <= 2 days adequate, <= 4 attention, above that critical.
    """
    granularity = granularity if granularity in ICU_GRANULARITIES else "year"
    min_cases = _ICU_MIN_CASES[granularity]
    waits = _icu_waits(df)

    stats = _icu_wait_stats(waits["wait_days"])
    over_limit = int((waits["wait_days"] > ICU_ACCEPTABLE_DAYS).sum())
    summary = {
        **stats,
        "same_day_pct": _pct(stats["same_day"], stats["total"]),
        "over_limit": over_limit,
        "over_limit_pct": _pct(over_limit, stats["total"]),
        "status": _icu_status(stats["median_wait_days"]),
    }

    periods: list[dict[str, Any]] = []
    if len(waits):
        keys = _period_key(waits["admitted"], granularity)
        for key, group in waits.groupby(keys, sort=True):
            if len(group) >= min_cases:
                periods.append({"period": str(key), **_icu_wait_stats(group["wait_days"])})

    return {
        "granularity": granularity,
        "limit_days": ICU_ACCEPTABLE_DAYS,
        "min_cases": min_cases,
        "summary": summary,
        "periods": periods,
    }


# ---------------------------------------------------------------------------
# Confirmação diagnóstica, infecção hospitalar e letalidade por método
# ---------------------------------------------------------------------------

_METHOD_GROUPS = {
    "RT-PCR": "rt_pcr",
    "Antígeno Rápido": "antigeno_outros",
    "Outros Laboratoriais": "antigeno_outros",
    "Clínico-Epidemiológico": "clinico_epi",
    "Clínico": "clinico_outros",
    "Clínico-Imagem": "clinico_outros",
    "Desconhecido": "clinico_outros",
}
_GROUP_KEYS = ("rt_pcr", "antigeno_outros", "clinico_epi", "clinico_outros")
_MIN_RESOLVED_FOR_LETHALITY = 10
_ALERT_MIN_PERIODS = 12  # below this the 3-sigma limit cannot even be exceeded
_ALERT_SIGMAS = 3
_MAX_OUTCOME_DAYS = 365


def _numeric_column(df: pd.DataFrame, name: str) -> pd.Series:
    """Numeric view of a column; NaN everywhere when the column does not exist."""
    if name not in df.columns:
        return pd.Series(float("nan"), index=df.index)
    return pd.to_numeric(df[name], errors="coerce")


def _date_column(df: pd.DataFrame, name: str) -> pd.Series:
    """Datetime view of a column; NaT everywhere when the column does not exist."""
    if name not in df.columns:
        return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    return pd.to_datetime(df[name], errors="coerce")


def _diagnostic_method(df: pd.DataFrame) -> pd.Series:
    """How each case was confirmed, from the closing criterion (CRITERIO).

    Laboratory closure (1) is split into RT-PCR (detectable), rapid antigen
    (positive) and other laboratory methods; RT-PCR wins when both are present.
    """
    method = pd.Series("Desconhecido", index=df.index, dtype="object")

    criterion = _numeric_column(df, "CRITERIO")
    laboratory = criterion == 1
    method[criterion == 2] = "Clínico-Epidemiológico"
    method[criterion == 3] = "Clínico"
    method[criterion == 4] = "Clínico-Imagem"
    method[laboratory] = "Outros Laboratoriais"
    method[laboratory & (_numeric_column(df, "RES_AN") == 1)] = "Antígeno Rápido"
    method[laboratory & (_numeric_column(df, "PCR_RESUL") == 1)] = "RT-PCR"
    return method


def _onset_period(df: pd.DataFrame, granularity: str) -> pd.Series:
    """Period key (year, quarter or month) of the first-symptoms date; NaN if unknown."""
    keys = pd.Series(pd.NA, index=df.index, dtype="object")
    if "DT_SIN_PRI" not in df.columns:
        return keys
    onset = pd.to_datetime(df["DT_SIN_PRI"], errors="coerce")
    valid = onset.notna()
    keys[valid] = _period_key(onset[valid], granularity)
    return keys


def _clean_granularity(granularity: str) -> str:
    return granularity if granularity in ICU_GRANULARITIES else "year"


def compute_diagnostic_methods(df: pd.DataFrame, granularity: str = "year") -> dict[str, Any]:
    """How cases were confirmed (laboratory x clinical), per period of symptom onset.

    Four groups: RT-PCR, antigen and other laboratory methods, clinical-epidemiological,
    and clinical / imaging / unknown. The summary covers every case; ``periods`` only
    lists periods with enough cases.
    """
    granularity = _clean_granularity(granularity)
    min_cases = _ICU_MIN_CASES[granularity]
    groups = _diagnostic_method(df).map(_METHOD_GROUPS)

    totals = groups.value_counts()
    total = len(df)
    summary: dict[str, Any] = {"total": total}
    summary.update({key: int(totals.get(key, 0)) for key in _GROUP_KEYS})
    laboratory = summary["rt_pcr"] + summary["antigeno_outros"]
    summary["laboratory_pct"] = _pct(laboratory, total)
    summary["rt_pcr_pct"] = _pct(summary["rt_pcr"], total)

    periods: list[dict[str, Any]] = []
    frame = pd.DataFrame({"period": _onset_period(df, granularity), "group": groups})
    frame = frame.dropna(subset=["period"])
    if len(frame):
        counts = frame.groupby(["period", "group"]).size().unstack(fill_value=0)
        counts = counts.reindex(columns=list(_GROUP_KEYS), fill_value=0)
        for period, row in counts.iterrows():
            if int(row.sum()) >= min_cases:
                periods.append(
                    {"period": str(period), "total": int(row.sum())}
                    | {key: int(row[key]) for key in _GROUP_KEYS}
                )

    return {
        "granularity": granularity,
        "min_cases": min_cases,
        "summary": summary,
        "periods": periods,
    }


def _alert_limit(rates: list[float]) -> tuple[float | None, float | None]:
    """(mean, upper alert limit = mean + 3 standard deviations) across periods."""
    if not rates:
        return None, None
    mean = statistics.fmean(rates)
    if len(rates) < _ALERT_MIN_PERIODS:
        return round(mean, 1), None
    return round(mean, 1), round(mean + _ALERT_SIGMAS * statistics.stdev(rates), 1)


def _origin_lethality(df: pd.DataFrame, origin: pd.Series, code: int) -> dict[str, Any]:
    if "EVOLUCAO" not in df.columns:
        return {"resolved": 0, "deaths": 0, "pct": None}
    resolved = pd.to_numeric(df["EVOLUCAO"], errors="coerce").isin(VALID_OUTCOMES)
    deaths = outcome_death_mask(df["EVOLUCAO"])
    in_group = origin == code
    resolved_count = int((in_group & resolved).sum())
    death_count = int((in_group & deaths).sum())
    return {
        "resolved": resolved_count,
        "deaths": death_count,
        "pct": _pct(death_count, resolved_count) if resolved_count else None,
    }


def compute_nosocomial_risk(df: pd.DataFrame, granularity: str = "year") -> dict[str, Any]:
    """Share of hospital-acquired infections per period, plus lethality by origin.

    Only cases with known origin (NOSOCOMIAL 1 or 2) count. ``alert_limit`` (mean + 3
    standard deviations across periods) only exists with enough periods, and periods
    above it are flagged with ``alert``.
    """
    granularity = _clean_granularity(granularity)
    min_cases = _ICU_MIN_CASES[granularity]
    if "NOSOCOMIAL" in df.columns:
        origin = pd.to_numeric(df["NOSOCOMIAL"], errors="coerce")
    else:
        origin = pd.Series(float("nan"), index=df.index)
    known = origin.isin([1, 2])

    summary = {
        "known": int(known.sum()),
        "nosocomial": int((origin == 1).sum()),
        "nosocomial_pct": _pct(int((origin == 1).sum()), int(known.sum())),
        "lethality": {
            "nosocomial": _origin_lethality(df, origin, 1),
            "community": _origin_lethality(df, origin, 2),
        },
    }

    frame = pd.DataFrame({"period": _onset_period(df, granularity), "nosocomial": origin == 1})
    frame = frame[known & frame["period"].notna()]
    grouped = frame.groupby("period")["nosocomial"].agg(["size", "sum"])
    rows = [
        (str(period), int(row["size"]), int(row["sum"]))
        for period, row in grouped.iterrows()
        if row["size"] >= min_cases
    ]
    rates = [_pct(nosocomial, known_count) for _, known_count, nosocomial in rows]
    mean, limit = _alert_limit(rates)
    periods = [
        {
            "period": period,
            "known": known_count,
            "nosocomial": nosocomial,
            "pct": rate,
            "alert": limit is not None and rate > limit,
        }
        for (period, known_count, nosocomial), rate in zip(rows, rates, strict=True)
    ]
    return {
        "granularity": granularity,
        "min_cases": min_cases,
        "mean_pct": mean,
        "alert_limit_pct": limit,
        "summary": summary,
        "periods": periods,
    }


def compute_diagnostic_lethality(df: pd.DataFrame) -> dict[str, Any]:
    """Lethality, ICU share and median time to outcome for each confirmation method.

    Lethality = deaths / cases with a known outcome (EVOLUCAO in VALID_OUTCOMES).
    Time to outcome = DT_EVOLUCA - DT_NOTIFIC in days (0 to 365). Methods with fewer
    than 10 resolved cases are listed in ``hidden`` instead of being ranked.
    """
    empty_overall = {"cases": 0, "resolved": 0, "deaths": 0, "cfr": None}
    if df.empty or "EVOLUCAO" not in df.columns:
        return {
            "min_resolved": _MIN_RESOLVED_FOR_LETHALITY,
            "overall": empty_overall,
            "methods": [],
            "hidden": [],
        }

    days = (_date_column(df, "DT_EVOLUCA") - _date_column(df, "DT_NOTIFIC")).dt.days
    frame = pd.DataFrame(
        {
            "method": _diagnostic_method(df),
            "resolved": pd.to_numeric(df["EVOLUCAO"], errors="coerce").isin(VALID_OUTCOMES),
            "death": outcome_death_mask(df["EVOLUCAO"]),
            "icu": _numeric_column(df, "UTI") == 1,
            "days": days.where(days.between(0, _MAX_OUTCOME_DAYS)),
        }
    )

    methods: list[dict[str, Any]] = []
    hidden: list[str] = []
    for name, group in frame.groupby("method"):
        resolved = int(group["resolved"].sum())
        if resolved < _MIN_RESOLVED_FOR_LETHALITY:
            hidden.append(str(name))
            continue
        deaths = int(group["death"].sum())
        median_days = group["days"].median()
        methods.append(
            {
                "method": str(name),
                "cases": len(group),
                "resolved": resolved,
                "deaths": deaths,
                "cfr": _pct(deaths, resolved),
                "median_days": None if pd.isna(median_days) else float(median_days),
                "icu_pct": _pct(int(group["icu"].sum()), len(group)),
            }
        )
    methods.sort(key=lambda row: row["cfr"], reverse=True)

    resolved_total = int(frame["resolved"].sum())
    deaths_total = int(frame["death"].sum())
    overall = {
        "cases": len(frame),
        "resolved": resolved_total,
        "deaths": deaths_total,
        "cfr": _pct(deaths_total, resolved_total) if resolved_total else None,
    }
    return {
        "min_resolved": _MIN_RESOLVED_FOR_LETHALITY,
        "overall": overall,
        "methods": methods,
        "hidden": sorted(hidden),
    }


# ---------------------------------------------------------------------------
# Laboratório: qualidade do diagnóstico, positividade, antiviral e imagem
# ---------------------------------------------------------------------------

# Result codes shared by PCR_RESUL and RES_AN: 1 positive/detectable, 2 negative/not
# detectable, 3 inconclusive. Code 5 means "awaiting result", so it does not count.
_RESULT_CODES = (1, 2, 3)
LAB_TARGET_COVERAGE_PCT = 80
LAB_TARGET_RT_PCR_DAYS = 7
LAB_TARGET_TURNAROUND_DAYS = 2
_MAX_LAB_DAYS = 30
_MAX_ANTIVIRAL_DAYS = 14
_MIN_GROUP_CASES = 10

_SAMPLE_TYPES = {
    1: "Secreção naso/orofaringe",
    2: "Lavado bronco-alveolar",
    3: "Tecido post-mortem",
    4: "Outra",
    5: "LCR",
    9: "Ignorado",
}
_XRAY_FINDINGS = {
    1: "Normal",
    2: "Infiltrado intersticial",
    3: "Consolidação",
    4: "Misto",
    5: "Outro",
}
_CT_FINDINGS = {
    1: "Típico (COVID-19)",
    2: "Indeterminado",
    3: "Atípico",
    4: "Negativo para pneumonia",
    5: "Outro",
}
_ANTIVIRAL_WINDOWS = (
    ("le1", "Até 1 dia"),
    ("d2", "2 dias"),
    ("d3_5", "3 a 5 dias"),
    ("gt5", "Mais de 5 dias"),
    ("none", "Sem antiviral"),
)


def _days_between(df: pd.DataFrame, start: str, end: str, max_days: int) -> pd.Series:
    """Days from ``start`` to ``end`` dates, keeping only values between 0 and ``max_days``."""
    days = (_date_column(df, end) - _date_column(df, start)).dt.days
    return days[days.between(0, max_days)]


def _has_result(df: pd.DataFrame) -> pd.Series:
    """Cases with a lab result available (RT-PCR or antigen)."""
    pcr = _numeric_column(df, "PCR_RESUL").isin(_RESULT_CODES)
    antigen = _numeric_column(df, "RES_AN").isin(_RESULT_CODES)
    return pcr | antigen


def _is_positive(df: pd.DataFrame) -> pd.Series:
    return (_numeric_column(df, "PCR_RESUL") == 1) | (_numeric_column(df, "RES_AN") == 1)


def _wait_distribution(days: pd.Series) -> dict[str, Any]:
    if days.empty:
        return {"count": 0, "mean": None, "median": None, "p90": None, "p95": None}
    return {
        "count": len(days),
        "mean": round(float(days.mean()), 1),
        "median": round(float(days.median()), 1),
        "p90": round(float(days.quantile(0.9)), 1),
        "p95": round(float(days.quantile(0.95)), 1),
    }


def compute_lab_performance(df: pd.DataFrame) -> dict[str, Any]:
    """Operational quality of the diagnostic network, each indicator against its target.

    - result: cases with an RT-PCR or antigen result available (target >= 80%);
    - collection: cases with a sample collected (target >= 80%);
    - RT-PCR latency: days from collection to the RT-PCR result (target <= 7 days);
    - turnaround: days from collection to any lab result, RT-PCR or antigen
      (target: mean <= 2 days). Waits above 30 days are treated as data errors.
    """
    total = len(df)
    has_result = _has_result(df)
    tested = int(has_result.sum())
    collected = int((_numeric_column(df, "AMOSTRA") == 1).sum())

    rt_pcr_days = _days_between(df, "DT_COLETA", "DT_PCR", _MAX_LAB_DAYS)
    antigen_days = _days_between(df, "DT_COLETA", "DT_RES_AN", _MAX_LAB_DAYS)
    rt_pcr = _wait_distribution(rt_pcr_days)
    rt_pcr["within_target_pct"] = (
        _pct(int((rt_pcr_days <= LAB_TARGET_RT_PCR_DAYS).sum()), len(rt_pcr_days))
        if len(rt_pcr_days)
        else None
    )
    positive = int((_is_positive(df) & has_result).sum())

    return {
        "total": total,
        "result": {
            "count": tested,
            "pct": _pct(tested, total),
            "target_pct": LAB_TARGET_COVERAGE_PCT,
        },
        "collection": {
            "count": collected,
            "pct": _pct(collected, total),
            "target_pct": LAB_TARGET_COVERAGE_PCT,
        },
        "rt_pcr_latency": {**rt_pcr, "target_days": LAB_TARGET_RT_PCR_DAYS},
        "turnaround": {
            **_wait_distribution(pd.concat([rt_pcr_days, antigen_days], ignore_index=True)),
            "target_days": LAB_TARGET_TURNAROUND_DAYS,
        },
        "positivity": {
            "tested": tested,
            "positive": positive,
            "pct": _pct(positive, tested) if tested else None,
        },
    }


def compute_sample_positivity(df: pd.DataFrame) -> dict[str, Any]:
    """Positivity (RT-PCR or antigen) per sample type, among cases with a lab result.

    Sample types with fewer than 10 tested cases are listed in ``hidden`` instead of
    being ranked, since their percentages swing wildly.
    """
    has_result = _has_result(df)
    sample = _numeric_column(df, "TP_AMOSTRA").map(_SAMPLE_TYPES).fillna("Não informado")
    frame = pd.DataFrame(
        {"type": sample, "tested": has_result, "positive": _is_positive(df) & has_result}
    )

    types: list[dict[str, Any]] = []
    hidden: list[str] = []
    for name, group in frame.groupby("type"):
        tested = int(group["tested"].sum())
        if tested == 0:
            continue
        if tested < _MIN_GROUP_CASES:
            hidden.append(str(name))
            continue
        positive = int(group["positive"].sum())
        types.append(
            {
                "sample_type": str(name),
                "tested": tested,
                "positive": positive,
                "positivity_pct": _pct(positive, tested),
            }
        )
    types.sort(key=lambda row: row["tested"], reverse=True)

    tested_total = int(has_result.sum())
    positive_total = int(frame["positive"].sum())
    return {
        "min_tested": _MIN_GROUP_CASES,
        "overall": {
            "tested": tested_total,
            "positive": positive_total,
            "pct": _pct(positive_total, tested_total) if tested_total else None,
        },
        "types": types,
        "hidden": sorted(hidden),
    }


def _treatment_window(days: float) -> str:
    if days <= 1:
        return "le1"
    if days <= 2:
        return "d2"
    if days <= 5:
        return "d3_5"
    return "gt5"


def _combined_pct(
    windows: dict[str, dict[str, Any]], keys: tuple[str, ...], field: str
) -> float | None:
    """Share of ``field`` (cure/death) across the given windows; None without cases."""
    total = sum(windows[key]["total"] for key in keys)
    return _pct(sum(windows[key][field] for key in keys), total) if total else None


def compute_antiviral_windows(df: pd.DataFrame) -> dict[str, Any]:
    """Cure and death by how fast antiviral treatment started after the first symptoms.

    Treated = ANTIVIRAL == 1 with a start date 0 to 14 days after symptom onset.
    Windows: up to 1 day, 2 days, 3 to 5 days and over 5 days, compared with the cases
    that did not use antiviral. Only closed outcomes count (cure or death).
    """
    empty: dict[str, Any] = {
        "treated": 0,
        "with_dates": 0,
        "median_days": None,
        "within_2d_pct": None,
        "cure_within_2d_pct": None,
        "cure_without_antiviral_pct": None,
        "death_after_5d_pct": None,
        "windows": [],
    }
    if df.empty or "EVOLUCAO" not in df.columns:
        return empty

    used = _numeric_column(df, "ANTIVIRAL") == 1
    days = (_date_column(df, "DT_ANTIVIR") - _date_column(df, "DT_SIN_PRI")).dt.days
    valid_days = days.where(used & days.between(0, _MAX_ANTIVIRAL_DAYS))

    window = pd.Series(pd.NA, index=df.index, dtype="object")
    window[valid_days.notna()] = valid_days.dropna().map(_treatment_window)
    window[~used] = "none"
    outcome = _numeric_column(df, "EVOLUCAO").map({1: "cure", 2: "death"})
    counts = (
        pd.DataFrame({"window": window, "outcome": outcome})
        .dropna()
        .groupby(["window", "outcome"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["cure", "death"], fill_value=0)
    )

    windows: dict[str, dict[str, Any]] = {}
    for key, label in _ANTIVIRAL_WINDOWS:
        cure = int(counts["cure"].get(key, 0))
        death = int(counts["death"].get(key, 0))
        total = cure + death
        windows[key] = {
            "key": key,
            "label": label,
            "total": total,
            "cure": cure,
            "death": death,
            "cure_pct": _pct(cure, total) if total else None,
            "death_pct": _pct(death, total) if total else None,
        }

    with_dates = int(valid_days.notna().sum())
    median = valid_days.median()
    return {
        "treated": int(used.sum()),
        "with_dates": with_dates,
        "median_days": None if pd.isna(median) else float(median),
        "within_2d_pct": _pct(int((valid_days <= 2).sum()), with_dates) if with_dates else None,
        "cure_within_2d_pct": _combined_pct(windows, ("le1", "d2"), "cure"),
        "cure_without_antiviral_pct": windows["none"]["cure_pct"],
        "death_after_5d_pct": windows["gt5"]["death_pct"],
        "windows": list(windows.values()),
    }


def _imaging_findings(df: pd.DataFrame, column: str, labels: dict[int, str]) -> dict[str, Any]:
    finding = _numeric_column(df, column).map(labels)
    evolucao = _numeric_column(df, "EVOLUCAO")
    frame = pd.DataFrame(
        {
            "finding": finding,
            "resolved": evolucao.isin(VALID_OUTCOMES),
            "death": evolucao == 2,
            "icu": _numeric_column(df, "UTI") == 1,
        }
    ).dropna(subset=["finding"])

    rows: list[dict[str, Any]] = []
    hidden: list[str] = []
    for name, group in frame.groupby("finding"):
        total = len(group)
        if total < _MIN_GROUP_CASES:
            hidden.append(str(name))
            continue
        resolved = int(group["resolved"].sum())
        deaths = int(group["death"].sum())
        rows.append(
            {
                "finding": str(name),
                "total": total,
                "icu_pct": _pct(int(group["icu"].sum()), total),
                "resolved": resolved,
                "deaths": deaths,
                "death_pct": _pct(deaths, resolved) if resolved else None,
            }
        )
    rows.sort(key=lambda row: row["total"], reverse=True)
    return {"rows": rows, "hidden": sorted(hidden)}


def compute_imaging_severity(df: pd.DataFrame) -> dict[str, Any]:
    """ICU admission and lethality by chest X-ray and CT result.

    ICU share = ICU cases / cases with that finding; lethality = deaths / cases with a
    known outcome. Findings with fewer than 10 cases are listed in ``hidden``.
    """
    return {
        "min_cases": _MIN_GROUP_CASES,
        "xray": _imaging_findings(df, "RAIOX_RES", _XRAY_FINDINGS),
        "ct": _imaging_findings(df, "TOMO_RES", _CT_FINDINGS),
    }
