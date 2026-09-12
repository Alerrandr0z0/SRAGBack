"""Territory distribution metrics (lean: bairro + zona)."""

import pandas as pd

from srag.data.analytics.filters import outcome_death_mask
from srag.data.loader import OFFICIAL_BAIRROS, SUB_BAIRRO_TO_BAIRRO_MAP

RURAL_AGGREGATE_LABEL = "AREA RURAL DE MOSSORO"

# Bairro ausente na notificação: linha própria (convenção da referência),
# nunca fundido no agregado rural.
MISSING_BAIRRO_LABEL = "NAO INFORMADO"

# Tudo que é bairro: oficiais + pais canônicos do mapa de sub-bairros.
# O resto (sítio, assentamento, localidade não-oficial) é área rural.
BAIRRO_LABELS = frozenset(OFFICIAL_BAIRROS) | frozenset(SUB_BAIRRO_TO_BAIRRO_MAP.values())


def normalize_territory_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Map non-official BAIRRO_REF to the rural aggregate.

    "ZONA RURAL" merges into "AREA RURAL DE MOSSORO"; missing names stay
    "NAO INFORMADO"; official bairros keep their name (urban zone).
    """
    if df.empty or "BAIRRO_REF" not in df.columns:
        return df
    out = df.copy()
    names = out["BAIRRO_REF"].fillna("").astype(str).str.strip().str.upper()
    names = names.mask(names == "", MISSING_BAIRRO_LABEL)
    out["BAIRRO_REF"] = names.mask(names == "ZONA RURAL", RURAL_AGGREGATE_LABEL)
    names = out["BAIRRO_REF"].fillna("").astype(str).str.strip().str.upper()
    is_official = names.isin(BAIRRO_LABELS) | (names == MISSING_BAIRRO_LABEL)
    out.loc[~is_official, "BAIRRO_REF"] = RURAL_AGGREGATE_LABEL
    if "ZONA" in out.columns:
        zona = out["ZONA"].astype(str).str.upper().str.strip()
        official_rural = (
            is_official
            & (zona == "RURAL")
            & (names != RURAL_AGGREGATE_LABEL)
            & (names != MISSING_BAIRRO_LABEL)
        )
        out.loc[official_rural, "ZONA"] = "Urbana"
    return out


def _status_counts(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    out = df.copy()
    out[group_col] = out[group_col].fillna("NAO INFORMADO")
    if "EVOLUCAO" in out.columns:
        evolucao = pd.to_numeric(out["EVOLUCAO"], errors="coerce")
    else:
        evolucao = pd.Series(pd.NA, index=out.index, dtype="Float64")
    out["_is_cura"] = evolucao == 1
    out["_is_obito"] = outcome_death_mask(evolucao)
    out["_is_ignorado"] = evolucao == 3
    return (
        out.groupby(group_col)
        .agg(
            count=(group_col, "size"),
            curados=("_is_cura", "sum"),
            obitos=("_is_obito", "sum"),
            ignorados=("_is_ignorado", "sum"),
        )
        .reset_index()
    )


def compute_territory_distribution(
    df: pd.DataFrame,
    min_cases: int = 5,
) -> pd.DataFrame:
    """Aggregate cases by neighborhood reference with privacy threshold."""
    if df.empty or "BAIRRO_REF" not in df.columns:
        return pd.DataFrame(columns=["bairro", "count", "curados", "obitos", "ignorados"])

    grouped = _status_counts(df, "BAIRRO_REF")
    grouped = grouped[grouped["count"] >= min_cases]
    grouped = grouped.rename(columns={"BAIRRO_REF": "bairro"})
    return grouped.sort_values("count", ascending=False).reset_index(drop=True)


def compute_zone_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate cases by inferred urban/rural zone."""
    if df.empty or "ZONA" not in df.columns:
        return pd.DataFrame(columns=["zona", "count"])

    out = df.copy()
    out["ZONA"] = out["ZONA"].fillna("Nao informado")
    grouped = out.groupby("ZONA").size().reset_index(name="count")
    grouped = grouped.rename(columns={"ZONA": "zona"})
    return grouped.sort_values("count", ascending=False).reset_index(drop=True)


