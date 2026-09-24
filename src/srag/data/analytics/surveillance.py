"""Lean surveillance analytics: agent, vaccines, series, virus, thresholds, RT-PCR."""

from __future__ import annotations

from contextlib import suppress
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from srag.utils.epi_weeks import compute_epi_week_columns


def _ensure_epi_week(df: pd.DataFrame) -> pd.DataFrame:
    if "_epi_week" not in df.columns and "DT_SIN_PRI" in df.columns:
        epi = compute_epi_week_columns(df["DT_SIN_PRI"])
        return pd.concat([df, epi], axis=1)
    return df


ETIOLOGIC_AGENT_PRIORITY = [
    "VSR",
    "Influenza",
    "COVID-19",
    "Outros Vírus",
    "Outro Agente",
    "Não Especificada",
]

CAMPANHAS_GRIPE = {
    2019: pd.to_datetime("2019-04-10").date(),
    2020: pd.to_datetime("2020-03-23").date(),
    2021: pd.to_datetime("2021-04-12").date(),
    2022: pd.to_datetime("2022-04-04").date(),
    2023: pd.to_datetime("2023-04-10").date(),
    2024: pd.to_datetime("2024-03-25").date(),
    2025: pd.to_datetime("2025-03-20").date(),
}


def infer_etiologic_agent(df: pd.DataFrame) -> pd.Series:
    """Infer the etiologic agent label used across surveillance views."""
    if df.empty:
        return pd.Series(dtype="object")

    out = df.copy()
    col = out.get("CLASSI_FIN")
    if col is None:
        return pd.Series(["Não Especificada"] * len(out), index=out.index)

    classi = pd.to_numeric(col, errors="coerce")
    agent = classi.map(
        {
            1: "Influenza",
            2: "Outros Vírus",
            3: "Outro Agente",
            4: "Não Especificada",
            5: "COVID-19",
        }
    ).fillna("Não Especificada")

    has_vsr_cols = {"PCR_VSR", "AN_VSR"}.intersection(set(out.columns))
    if has_vsr_cols:
        pcr_vsr = pd.to_numeric(out.get("PCR_VSR"), errors="coerce")  # type: ignore[arg-type]
        an_vsr = pd.to_numeric(out.get("AN_VSR"), errors="coerce")  # type: ignore[arg-type]
        agent.loc[(pcr_vsr == 1) | (an_vsr == 1)] = "VSR"

    return agent.astype(str)


# Aliases accepted in the `?agents=` filter (frontend shorthand -> canonical label).
AGENT_FILTER_ALIASES = {
    "OUTRO_VIRUS": "OUTROS VÍRUS",
    "OUTROS_VIRUS": "OUTROS VÍRUS",
    "OUTROS VIRUS": "OUTROS VÍRUS",
    "OUTRO_AGENTE": "OUTRO AGENTE",
    "NAO_ESPECIFICADO": "NÃO ESPECIFICADA",
    "NAO ESPECIFICADA": "NÃO ESPECIFICADA",
    "NAO_ESPECIFICADA": "NÃO ESPECIFICADA",
    "COVID": "COVID-19",
    "COVID19": "COVID-19",
    "INFLUENZA A": "INFLUENZA",
    "INFLUENZA B": "INFLUENZA",
}


def normalize_agent_values(values: list[str] | None) -> set[str]:
    """Normalize `?agents=` filter values to canonical upper-case labels."""
    if not values:
        return set()
    normalized = set()
    for raw in values:
        upper = str(raw).strip().upper()
        if upper:
            normalized.add(AGENT_FILTER_ALIASES.get(upper, upper))
    return normalized


def _is_baby_under_6m(nu_idade: float, tp_idade: float | str | None) -> bool:
    """Determine if patient is under 6 months old."""
    if pd.notna(tp_idade):
        return tp_idade == 1 or (tp_idade == 2 and nu_idade < 6)
    return (1000 <= nu_idade <= 1365) or (2000 <= nu_idade < 2006)


def _is_child_under_8y(nu_idade: float, tp_idade: float | str | None) -> bool:
    """Determine if patient is a child aged 6 months to 8 years."""
    if pd.notna(tp_idade):
        return (tp_idade == 2 and nu_idade >= 6) or (tp_idade == 3 and nu_idade <= 8)
    return (2006 <= nu_idade <= 2011) or (3000 <= nu_idade <= 3008)


def _classify_age_group(row: pd.Series | dict[str, Any]) -> tuple[bool, bool]:
    """Determine if patient is menor_6m or is_crianca_8y."""
    nu_idade = float(row.get("NU_IDADE_N", 0)) if pd.notna(row.get("NU_IDADE_N")) else 0
    tp_idade = row.get("TP_IDADE")
    return _is_baby_under_6m(nu_idade, tp_idade), _is_child_under_8y(nu_idade, tp_idade)


def _resolve_flu_dose_and_vacina(
    row: pd.Series | dict[str, Any],
    is_menor_6m: bool,
    is_crianca_8y: bool,
    vacina: float,
    dt_dose: str | date | pd.Timestamp | float | None,
) -> tuple[str | date | pd.Timestamp | float | None, float, str]:
    """Resolve vacina, dt_dose, and label_prefix based on age group."""
    label_prefix = "protegido"

    if is_menor_6m:
        mae_vac = row.get("MAE_VAC")
        dt_vac_mae = row.get("DT_VAC_MAE")
        with suppress(TypeError, ValueError):
            vacina = float(mae_vac) if pd.notna(mae_vac) else vacina
        dt_dose = dt_vac_mae if pd.notna(dt_vac_mae) else dt_dose
    elif is_crianca_8y:
        if pd.notna(row.get("DT_2_DOSE")):
            dt_dose = row.get("DT_2_DOSE")
            label_prefix = "dose_2"
        elif pd.notna(row.get("DT_1_DOSE")):
            dt_dose = row.get("DT_1_DOSE")
            label_prefix = "dose_1"
        elif pd.notna(row.get("DT_DOSEUNI")):
            dt_dose = row.get("DT_DOSEUNI")
            label_prefix = "dose_unica"

    return dt_dose, vacina, label_prefix


def _parse_date_safe(value: str | date | pd.Timestamp | float | None) -> date | None:
    """Parse safely and return a date or None/NaT."""
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return pd.to_datetime(value, dayfirst=True, format="mixed").date()
        except TypeError, ValueError:
            return None
    return None


def _evaluate_vax_status_active(
    dt_dose_val: date,
    dt_sintoma_val: date,
    label_prefix: str,
    is_crianca_8y: bool,
) -> str:
    """Evaluate vaccination status logic when both dates are present and valid."""
    if dt_dose_val > dt_sintoma_val:
        return "inconsistencia"

    ano_sintoma = getattr(dt_sintoma_val, "year", None)
    if not ano_sintoma:
        return "ignorado"

    inicio_campanha = CAMPANHAS_GRIPE.get(
        ano_sintoma, pd.to_datetime(f"{ano_sintoma}-04-01").date()
    )

    if dt_dose_val >= inicio_campanha:
        return label_prefix if is_crianca_8y else "protegido"
    return "vencida"


def _parse_vacina_code(value: float | str | None) -> float:
    """Safely parse vaccination status code to float."""
    try:
        return float(value) if pd.notna(value) else np.nan
    except TypeError, ValueError:
        return np.nan


def _handle_vacina_status(
    vacina: float,
    dt_dose: str | date | pd.Timestamp | float | None,
    dt_sintoma: str | date | pd.Timestamp | float | None,
    label_prefix: str,
    is_crianca_8y: bool,
) -> str:
    """Handle vaccination status resolution for known vacina codes."""
    if vacina == 2:
        if pd.notna(dt_dose):
            return "inconsistencia"
        return "nao_vacinado"

    if vacina == 1:
        if pd.isna(dt_dose):
            return "ignorado"

        dt_dose_val = _parse_date_safe(dt_dose)
        dt_sintoma_val = _parse_date_safe(dt_sintoma)

        if dt_sintoma_val is None or dt_dose_val is None:
            return "ignorado"

        if not hasattr(dt_dose_val, "year") or not hasattr(dt_sintoma_val, "year"):
            return "ignorado"

        return _evaluate_vax_status_active(
            dt_dose_val, dt_sintoma_val, label_prefix, is_crianca_8y
        )

    return "ignorado"


def classificar_status_gripe(row: pd.Series | dict[str, Any]) -> str:
    """Determine epidemiological status for Flu based on vaccination date and symptoms."""
    vacina = _parse_vacina_code(row.get("VACINA"))
    dt_dose: str | date | pd.Timestamp | float | None = row.get("DT_UT_DOSE")
    dt_sintoma: str | date | pd.Timestamp | float | None = row.get("DT_SIN_PRI")

    is_menor_6m, is_crianca_8y = _classify_age_group(row)
    dt_dose, vacina, label_prefix = _resolve_flu_dose_and_vacina(
        row, is_menor_6m, is_crianca_8y, vacina, dt_dose
    )

    if pd.isna(vacina) or vacina == 9:
        return "ignorado"

    return _handle_vacina_status(vacina, dt_dose, dt_sintoma, label_prefix, is_crianca_8y)


def classificar_status_gripe_vectorized(df: pd.DataFrame) -> pd.Series:
    """Vectorized batch classification of flu vaccination status.

    Fast path: handles the vast majority of records (adults, VACINA ∈ {1,2,NaN,9})
    with boolean masks avoiding row-by-row Python iteration.
    Complex edge cases (babies < 6 months, children 6m-8y) fall back to the
    scalar function only for those rows, which are typically a small fraction.
    """
    n = len(df)
    if n == 0:
        return pd.Series(dtype="object")

    result = pd.Series("ignorado", index=df.index, dtype="object")

    vacina = pd.to_numeric(df.get("VACINA", pd.Series(dtype=float)), errors="coerce")  # type: ignore[call-overload]
    tp_idade = pd.to_numeric(df.get("TP_IDADE", pd.Series(dtype=float)), errors="coerce")  # type: ignore[call-overload]
    nu_idade = pd.to_numeric(df.get("NU_IDADE_N", pd.Series(dtype=float)), errors="coerce")  # type: ignore[call-overload]

    # Identify edge-case rows that require multi-column date logic
    is_menor_6m_mask = (tp_idade == 1) | ((tp_idade == 2) & (nu_idade < 6))
    is_crianca_8y_mask = ((tp_idade == 2) & (nu_idade >= 6)) | ((tp_idade == 3) & (nu_idade <= 8))
    edge_case_mask = is_menor_6m_mask | is_crianca_8y_mask

    # --- Fast path: standard adults (no edge-case age groups) ---
    std_mask = ~edge_case_mask

    # Ignorado: vacina is NaN or 9
    ignorado_mask = std_mask & (vacina.isna() | (vacina == 9))
    result[ignorado_mask] = "ignorado"

    # Não vacinado: vacina == 2 with no dose date
    nao_vac_mask = std_mask & (vacina == 2)
    result[nao_vac_mask] = "nao_vacinado"

    # Vacinado: vacina == 1 - needs date comparison
    vac1_mask = std_mask & (vacina == 1)
    if vac1_mask.any():
        dt_dose_raw = df.get("DT_UT_DOSE", pd.Series(dtype=object))
        dt_sin_raw = df.get("DT_SIN_PRI", pd.Series(dtype=object))
        dt_dose = pd.to_datetime(dt_dose_raw, errors="coerce", dayfirst=True)
        dt_sin = pd.to_datetime(dt_sin_raw, errors="coerce", dayfirst=True)

        vac1_rows = df[vac1_mask].index

        has_dose = dt_dose[vac1_rows].notna()
        has_sin = dt_sin[vac1_rows].notna()
        both = has_dose & has_sin

        # No dose date → ignorado (already set as default)
        result[vac1_rows[~has_dose]] = "ignorado"

        # Has dose but no symptom → ignorado
        result[vac1_rows[has_dose & ~has_sin]] = "ignorado"

        # Has both: check ordering and campaign date
        both_idx = vac1_rows[both]
        d_dose = dt_dose[both_idx]
        d_sin = dt_sin[both_idx]

        # Inconsistência: dose after symptoms
        incons = d_dose > d_sin
        result[both_idx[incons]] = "inconsistencia"

        # For valid rows, check if dose is within the campaign year
        valid_idx = both_idx[~incons]
        if len(valid_idx):
            d_dose_v = d_dose[valid_idx]
            d_sin_v = d_sin[valid_idx]
            ano_v = d_sin_v.dt.year

            campaign_start = ano_v.map(
                lambda y: pd.Timestamp(CAMPANHAS_GRIPE.get(y, date(y, 4, 1)))
            )
            within_campaign = d_dose_v >= campaign_start
            result[valid_idx[within_campaign]] = "protegido"
            result[valid_idx[~within_campaign]] = "vencida"

    # --- Slow path: edge-case rows (babies / young children) ---
    if edge_case_mask.any():
        edge_results = df[edge_case_mask].apply(classificar_status_gripe, axis=1)
        result[edge_case_mask] = edge_results

    return result


def compute_time_series(df: pd.DataFrame) -> pd.DataFrame:
    """Group cases by epidemiological week for trend analysis."""
    if df.empty:
        return pd.DataFrame(columns=["epi_week", "total"])

    out = df.copy()
    out = _ensure_epi_week(out)
    out["epi_week"] = out["_epi_week"]

    ts = out.groupby("epi_week").size().reset_index(name="total")
    return ts.sort_values("epi_week")


def compute_virus_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Group cases by final classification (Influenza, COVID, etc.)."""
    if df.empty:
        return pd.DataFrame()

    out = df.copy()
    out["virus"] = infer_etiologic_agent(out)

    result = out.groupby("virus").size().reset_index(name="count")
    priority = {label: idx for idx, label in enumerate(ETIOLOGIC_AGENT_PRIORITY)}
    result["_prio"] = result["virus"].map(priority).fillna(99)
    result = result.sort_values(["_prio", "count"], ascending=[True, False]).drop(
        columns=["_prio"]
    )
    return result.reset_index(drop=True)


def compute_rt_pcr_summary(df: pd.DataFrame) -> dict[str, float | int]:
    """RT-PCR summary (tópico 70): detectáveis (PCR_RESUL==1)."""
    if df.empty:
        return {"total_cases": 0}
    has_pcr = "PCR_RESUL" in df.columns
    pcr_res = (
        pd.to_numeric(df["PCR_RESUL"], errors="coerce") if has_pcr else pd.Series(dtype=float)
    )
    positives = int((pcr_res == 1).sum())
    return {"total_cases": positives}
