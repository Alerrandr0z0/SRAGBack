"""Data filtering: bairro display filter plus shared masks and age helpers."""

import pandas as pd

from srag.data.loader import (
    MISSING_BAIRRO_LABEL,
    OFFICIAL_BAIRROS,
    RURAL_AGGREGATE_LABEL,
    SUB_BAIRRO_TO_BAIRRO_MAP,
)
from srag.data.references import (
    CONFIRMED_CLASSI_FIN,
    DEATH_OUTCOMES,
    SYMPTOM_FIELDS,
    SYMPTOM_PRESENT_CODE,
    VENTILACAO_CODES,
)


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
    mask = df["BAIRRO_REF"].fillna("").astype(str).str.upper().str.strip().isin(bairro_norm)
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


def _filter_by_base_analise(df: pd.DataFrame, base: str | None) -> pd.DataFrame:
    """Apply the "Base de análise" filter: notificados / confirmados / obitos.

    - notificados (default/None): universo completo, sem filtro extra.
    - confirmados: CLASSI_FIN ∈ {1, 5} — classificação final etiológica
      (Influenza ou COVID-19). Não é confirmação laboratorial isolada.
    - obitos: EVOLUCAO == 2.
    """
    if not base or base == "notificados":
        return df
    if base == "confirmados":
        if "CLASSI_FIN" not in df.columns:
            return df.iloc[0:0]
        classi = pd.to_numeric(df["CLASSI_FIN"], errors="coerce")
        return df[classi.isin(CONFIRMED_CLASSI_FIN)]
    if base == "obitos":
        if "EVOLUCAO" not in df.columns:
            return df.iloc[0:0]
        evolucao = pd.to_numeric(df["EVOLUCAO"], errors="coerce")
        return df[evolucao.isin(DEATH_OUTCOMES)]
    return df


def _filter_by_gravidade(df: pd.DataFrame, gravidade: str | None) -> pd.DataFrame:
    """Apply the "Gravidade" filter: uti / internacao / ventilacao.

    Each option is independent (not mutually exclusive in the data — a case
    can have gone through both UTI and regular hospitalization). Cases with
    the relevant field unfilled are excluded from that specific option.
    """
    if not gravidade or gravidade == "todos":
        return df
    if gravidade == "uti":
        if "UTI" not in df.columns:
            return df.iloc[0:0]
        return df[pd.to_numeric(df["UTI"], errors="coerce") == 1]
    if gravidade == "internacao":
        if "HOSPITAL" not in df.columns:
            return df.iloc[0:0]
        return df[pd.to_numeric(df["HOSPITAL"], errors="coerce") == 1]
    if gravidade == "ventilacao":
        if "SUPORT_VEN" not in df.columns:
            return df.iloc[0:0]
        suport_ven = pd.to_numeric(df["SUPORT_VEN"], errors="coerce")
        return df[suport_ven.isin(VENTILACAO_CODES)]
    return df


def _filter_by_sintomas(df: pd.DataFrame, sintomas: list[str] | None) -> pd.DataFrame:
    """Apply the "Sintomatologia" filter: AND across every selected symptom.

    A case only matches if it has code 1 (Sim) in every selected symptom
    column. Unknown keys are ignored defensively (validated upstream too).
    """
    if not sintomas:
        return df
    out = df
    for key in sintomas:
        column = SYMPTOM_FIELDS.get(key)
        if column is None or column not in out.columns:
            continue
        out = out[pd.to_numeric(out[column], errors="coerce") == SYMPTOM_PRESENT_CODE]
    return out


def apply_global_filters(
    df: pd.DataFrame,
    bairros: list[str] | None = None,
    base: str | None = None,
    gravidade: str | None = None,
    sintomas: list[str] | None = None,
) -> pd.DataFrame:
    """Apply the row-level display filters shared by every surveillance view.

    Years/agents/classi (the pre-existing "quem/onde/quando" filters) go
    through ``apply_surveillance_filters`` in ``srag.api.core``; this function
    covers bairro plus the three newer filters (base de análise, gravidade,
    sintomatologia), all of which narrow the row universe the same way.
    """
    if df.empty:
        return df
    out = _filter_by_bairros(df.copy(), [b for b in (bairros or []) if b])
    out = _filter_by_base_analise(out, base)
    out = _filter_by_gravidade(out, gravidade)
    out = _filter_by_sintomas(out, sintomas)
    return out


def outcome_death_mask(values: pd.Series) -> pd.Series:
    """Return a boolean mask for fatal outcomes."""
    return pd.to_numeric(values, errors="coerce").isin(DEATH_OUTCOMES)
