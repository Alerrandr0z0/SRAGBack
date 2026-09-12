import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from srag.data.analytics import infer_etiologic_agent, normalize_agent_values
from srag.data.analytics.filters import epi_week_year
from srag.data.database import DB_URL
from srag.utils.epi_weeks import compute_epi_week_columns

logger = logging.getLogger(__name__)

engine = create_engine(DB_URL, pool_pre_ping=True)

_cache: dict[str, Any] = {"df": None, "loaded_at": None}  # Cache invalidated at 2026-05-09


def refresh_df() -> None:
    """Invalidate the cached working dataframe (call after ingestion)."""
    _cache["df"] = None
    _cache["loaded_at"] = None


def sanitize_data(obj: Any) -> Any:  # noqa: ANN401
    """Recursively convert numpy types to native python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: sanitize_data(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_data(i) for i in obj]
    if isinstance(obj, (np.integer, np.int64, np.int32)):  # type: ignore[arg-type]
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):  # type: ignore[arg-type]
        return float(obj)
    if isinstance(obj, np.ndarray):
        return sanitize_data(obj.tolist())
    if obj is None:
        return None
    try:
        if pd.isna(obj):  # type: ignore[call-overload]
            return None
    except TypeError:
        pass
    return obj


def apply_surveillance_filters(
    df: pd.DataFrame,
    years: list[int] | None = None,
    agents: list[str] | None = None,
    classi: list[int] | None = None,
) -> pd.DataFrame:
    """Apply temporal, etiologic-agent and final-classification filters.

    Shared by all surveillance endpoints so ``years/agents/classi`` behave
    identically everywhere.
    """
    out = df
    if years and "DT_SIN_PRI" in out.columns:
        year_values = set(years)
        dt_s = pd.to_datetime(out["DT_SIN_PRI"], errors="coerce")
        se_years = epi_week_year(dt_s)
        out = out[se_years.isin(year_values)]
    if agents:
        agent_norm = normalize_agent_values(agents)
        out = out[infer_etiologic_agent(out).str.upper().isin(agent_norm)]
    if classi and "CLASSI_FIN" in out.columns:
        out = out[pd.to_numeric(out["CLASSI_FIN"], errors="coerce").isin(set(classi))]
    return out


_KNOWN_COLUMNS = frozenset(
    {
        "DT_NOTIFIC",
        "DT_SIN_PRI",
        "ID_MUNICIP",
        "ID_MN_RESI",
        "CLASSI_FIN",
        "ID_UNIDADE",
        "BAIRRO_REF",
        "NM_BAIRRO",
        "ZONA",
        "CS_ZONA",
        "NU_IDADE_N",
        "TP_IDADE",
        "IDADE_ANOS",
        "CS_SEXO",
        "CS_RACA",
        "CS_ESCOL_N",
        "PAC_DSCBO",
        "AVE_SUINO",
        "EVOLUCAO",
        "UTI",
        "HOSPITAL",
        "SUPORT_VEN",
        "NOSOCOMIAL",
        "CS_GESTANT",
        "PUERPERA",
        "POV_CT",
        "TP_POV_CT",
        "FEBRE",
        "TOSSE",
        "GARGANTA",
        "DISPNEIA",
        "DESC_RESP",
        "SATURACAO",
        "DIARREIA",
        "VOMITO",
        "DOR_ABD",
        "FADIGA",
        "PERD_OLFT",
        "PERD_PALA",
        "OUTRO_SIN",
        "PCR_VSR",
        "AN_VSR",
        "PCR_SARS2",
        "AN_SARS2",
        "TP_FLU_PCR",
        "TP_FLU_AN",
        "PCR_RESUL",
        "RES_AN",
        "DT_PCR",
        "DT_RES_AN",
        "DT_COLETA",
        "CO_LAB_AN",
        "LAB_AN",
        "ASMA",
        "DIABETES",
        "OBESIDADE",
        "CARDIOPATI",
        "PNEUMOPATI",
        "RENAL",
        "IMUNODEPRE",
        "NEUROLOGIC",
        "HEMATOLOGI",
        "HEPATICA",
        "SIND_DOWN",
        "TABAG",
        "OUT_MORBI",
        "VACINA",
        "DT_UT_DOSE",
        "DT_1_DOSE",
        "MAE_VAC",
        "DT_VAC_MAE",
        "DT_DOSEUNI",
        "ANTIVIRAL",
        "CRITERIO",
        "DT_2_DOSE",
        "DT_INTERNA",
        "DT_ENTUTI",
        "VACINA_COV",
        "DOSE_1_COV",
        "DOSE_2_COV",
        "DOSE_REF",
        "DOSE_2REF",
        "DOSE_ADIC",
        "DOS_RE_BI",
        "FAB_COV1",
        "FAB_COV2",
        "FAB_COVRF",
        "FAB_COVRF2",
        "FAB_ADIC",
        "FAB_RE_BI",
        "VG_OMS",
        "VG_LIN",
        "VG_MET",
        "VG_REINF",
        "PCR_PARA4",
        "CO_DETEC",
        "PCR_FLUASU",
        "PCR_FLUBLI",
        "AMOSTRA",
        "TP_AMOSTRA",
        "RAIOX_RES",
        "TOMO_RES",
        "TP_SOR",
        "RES_IGG",
        "RES_IGM",
        "RES_IGA",
        "TP_ANTIVIR",
        "TIPO_TRAT",
        "SURTO_SG",
        "DT_ANTIVIR",
        "DT_EVOLUCA",
    }
)


def get_df() -> pd.DataFrame:
    """Load and cache the working SRAG dataframe from the database."""
    now = datetime.now(UTC)
    if (
        _cache["df"] is not None
        and _cache["loaded_at"]
        and (now - _cache["loaded_at"]) < timedelta(minutes=30)
    ):
        return _cache["df"]  # type: ignore[no-any-return]

    try:
        core_cols = [
            "DT_NOTIFIC",
            "DT_SIN_PRI",
            "ID_MUNICIP",
            "ID_MN_RESI",
            "CLASSI_FIN",
            "ID_UNIDADE",
            "BAIRRO_REF",
            "NM_BAIRRO",
            "ZONA",
            "CS_ZONA",
            "NU_IDADE_N",
            "TP_IDADE",
            "IDADE_ANOS",
            "CS_SEXO",
            "CS_RACA",
            "CS_ESCOL_N",
            "PAC_DSCBO",
            "AVE_SUINO",
            "EVOLUCAO",
            "UTI",
            "HOSPITAL",
            "SUPORT_VEN",
            "NOSOCOMIAL",
            "CS_GESTANT",
            "PUERPERA",
            "POV_CT",
            "TP_POV_CT",
            "FEBRE",
            "TOSSE",
            "GARGANTA",
            "DISPNEIA",
            "DESC_RESP",
            "SATURACAO",
            "DIARREIA",
            "VOMITO",
            "DOR_ABD",
            "FADIGA",
            "PERD_OLFT",
            "PERD_PALA",
            "OUTRO_SIN",
            "PCR_VSR",
            "AN_VSR",
            "PCR_SARS2",
            "AN_SARS2",
            "TP_FLU_PCR",
            "TP_FLU_AN",
            "PCR_RESUL",
            "RES_AN",
            "DT_PCR",
            "DT_RES_AN",
            "DT_COLETA",
            "CO_LAB_AN",
            "LAB_AN",
            "ASMA",
            "DIABETES",
            "OBESIDADE",
            "CARDIOPATI",
            "PNEUMOPATI",
            "RENAL",
            "IMUNODEPRE",
            "NEUROLOGIC",
            "HEMATOLOGI",
            "HEPATICA",
            "SIND_DOWN",
            "TABAG",
            "OUT_MORBI",
            "VACINA",
            "DT_UT_DOSE",
            "DT_1_DOSE",
            "DT_2_DOSE",
            "MAE_VAC",
            "DT_VAC_MAE",
            "DT_DOSEUNI",
            "ANTIVIRAL",
            "CRITERIO",
            "DT_INTERNA",
            "DT_ENTUTI",
            "VACINA_COV",
            "DOSE_1_COV",
            "DOSE_2_COV",
            "DOSE_REF",
            "DOSE_2REF",
            "DOSE_ADIC",
            "DOS_RE_BI",
            "FAB_COV1",
            "FAB_COV2",
            "FAB_COVRF",
            "FAB_COVRF2",
            "FAB_ADIC",
            "FAB_RE_BI",
            "VG_OMS",
            "VG_LIN",
            "VG_MET",
            "VG_REINF",
            "PCR_PARA4",
            "CO_DETEC",
            "PCR_FLUASU",
            "PCR_FLUBLI",
            "AMOSTRA",
            "TP_AMOSTRA",
            "RAIOX_RES",
            "TOMO_RES",
            "TP_SOR",
            "RES_IGG",
            "RES_IGM",
            "RES_IGA",
            "TP_ANTIVIR",
            "TIPO_TRAT",
            "SURTO_SG",
            "DT_ANTIVIR",
            "DT_EVOLUCA",
        ]
        unique_cols = list(dict.fromkeys(core_cols))
        invalid = [c for c in unique_cols if c not in _KNOWN_COLUMNS]
        if invalid:
            raise ValueError(f"Invalid column names: {invalid}")
        cols_str = ", ".join(unique_cols)
        # Safe: column names are validated against hardcoded allowlist (_KNOWN_COLUMNS)
        df = pd.read_sql(f"SELECT {cols_str} FROM casos_srag", engine)  # nosec: B608
        df = df.reset_index(drop=True)
        for col in [
            "DT_NOTIFIC",
            "DT_SIN_PRI",
            "DT_INTERNA",
            "DT_ENTUTI",
            "DT_EVOLUCA",
            "DT_COLETA",
            "DT_PCR",
            "DT_RES_AN",
            "DT_UT_DOSE",
            "DT_1_DOSE",
            "DT_ANTIVIR",
            "DOSE_1_COV",
            "DOSE_2_COV",
            "DOSE_REF",
            "DOSE_2REF",
            "DOS_RE_BI",
        ]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        df = df[df["DT_SIN_PRI"].notna()]
        epi = compute_epi_week_columns(df["DT_SIN_PRI"])
        df = pd.concat([df, epi], axis=1)
        _cache["df"] = df
        _cache["loaded_at"] = now
        return df
    except Exception:
        logger.exception("Backend query failed")
        cached = _cache["df"]
        if cached is not None:
            return cast("pd.DataFrame", cached)
        return pd.DataFrame()
