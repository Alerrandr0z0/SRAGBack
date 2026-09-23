"""Data filtering: bairro display filter plus shared masks and age helpers."""

import pandas as pd

from srag.data.loader import (
    MISSING_BAIRRO_LABEL,
    OFFICIAL_BAIRROS,
    RURAL_AGGREGATE_LABEL,
    SUB_BAIRRO_TO_BAIRRO_MAP,
)
from srag.data.references import DEATH_OUTCOMES


def age_years(df: pd.DataFrame) -> pd.Series:
    """Normalize age into years whenever possible."""
    if "IDADE_ANOS" in df.columns and df["IDADE_ANOS"].notna().any():
        return pd.to_numeric(df["IDADE_ANOS"], errors="coerce")

    nu_idade = df.get("NU_IDADE_N", pd.Series(index=df.index))
    idade_bruta = pd.to_numeric(nu_idade, errors="coerce").fillna(0)
    tp = pd.to_numeric(df.get("TP_IDADE", pd.Series(index=df.index)), errors="coerce")

    idade_anos = pd.Series(pd.NA, index=df.index, dtype="Float64")
    idade_anos = idade_anos.mask(tp == 3, idade_bruta)
    idade_anos = idade_anos.mask(tp == 2, idade_bruta / 12.0)
    idade_anos = idade_anos.mask(tp == 1, idade_bruta / 365.25)
    idade_anos = idade_anos.mask(tp.isna(), idade_bruta)

    return pd.to_numeric(idade_anos, errors="coerce")


def epi_week_year(dt_series: pd.Series) -> pd.Series:
    """Return the epidemiological year for a datetime Series (SIVEP convention)."""
    idx = (dt_series.dt.weekday + 1) % 7
    sun = dt_series - pd.to_timedelta(idx, unit="D")
    return (sun + pd.to_timedelta(3, unit="D")).dt.year


def _filter_by_bairros(df: pd.DataFrame, bairros: list[str] | None) -> pd.DataFrame:
    """Filter by bairro display label (mirrors normalize_territory_labels)."""
    if not bairros:
        return df
    bairro_norm = [str(b).strip().upper() for b in bairros]
    mask = (
        df["BAIRRO_REF"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
        .isin(bairro_norm)
    )
    # "NAO INFORMADO" tem linha própria, nunca fundido no agregado rural.
    if RURAL_AGGREGATE_LABEL in bairro_norm:
        official = (
            frozenset(OFFICIAL_BAIRROS)
            | frozenset(SUB_BAIRRO_TO_BAIRRO_MAP.values())
            | {RURAL_AGGREGATE_LABEL}
        )
        names = df["BAIRRO_REF"].fillna("").astype(str).str.upper().str.strip()
        mask = (
            mask
            | (names == "ZONA RURAL")
            | ((~names.isin(official)) & (~names.isin({MISSING_BAIRRO_LABEL, ""})))
        )
    return df[mask]


def apply_global_filters(
    df: pd.DataFrame,
    bairros: list[str] | None = None,
) -> pd.DataFrame:
    """Apply the display (bairro) filter. Years/agents/classi go through core."""
    if df.empty:
        return df
    return _filter_by_bairros(df.copy(), [b for b in (bairros or []) if b])


def outcome_death_mask(values: pd.Series) -> pd.Series:
    """Return a boolean mask for fatal outcomes."""
    return pd.to_numeric(values, errors="coerce").isin(DEATH_OUTCOMES)
