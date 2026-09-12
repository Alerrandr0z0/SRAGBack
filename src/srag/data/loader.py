"""Data loading and anonymization utilities for Mossoró SRAG data."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import TYPE_CHECKING

import pandas as pd
from pydantic import ValidationError
from rapidfuzz import process

from srag.data.schema import SragCase, is_mossoro_case

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# List of sensitive fields that MUST be dropped for LGPD compliance.
# Address fields are intentionally kept because the application uses
# territorial data for analysis and geospatial views.
SENSITIVE_FIELDS = [
    "NM_PACIENT",  # Nome do Paciente
    "NU_CPF",  # CPF
    "NU_CNS",  # Cartão Nacional de Saúde
    "NM_MAE_PAC",  # Nome da Mãe
    "NU_DDD_TEL",  # DDD Telefone
    "NU_TELEFON",  # Telefone
    "ID_RG_RESI",  # Registro de Residência
]

COLUMN_ALIASES = {
    "CO_MUN_NOT": "ID_MUNICIP",
    "CO_MUN_RES": "ID_MN_RESI",
    "CO_UNI_NOT": "ID_UNIDADE",
    "CO-DETEC": "CO_DETEC",
    "FAB_COV_1": "FAB_COV1",
    "FAB_COV_2": "FAB_COV2",
}

OFFICIAL_BAIRROS = {
    "ABOLICAO",
    "ABOLICOES",
    "AEROPORTO",
    "ALAGADOS",
    "ALTO DA CONCEICAO",
    "ALTO DE SAO MANOEL",
    "ALTO DO SUMARE",
    "ALTO DA BELA VISTA",
    "BELA VISTA",
    "BARROCAS",
    "BELO HORIZONTE",
    "BOA VISTA",
    "BOM JARDIM",
    "BOM JESUS",
    "CENTRO",
    "DIX-SEPT ROSADO",
    "GOV DIX SEPT ROSADO",
    "DOM JAIME CAMARA",
    "DOZE ANOS",
    "ILHA DE SANTA LUZIA",
    "ITAPETINGA",
    "LAGOA DO MATO",
    "MONS ALFREDO SIMONETI",
    "MONSENHOR ALFREDO SIMONETI",
    "NOVA BETANIA",
    "PAREDOES",
    "PINTOS",
    "PLANALTO TREZE DE MAIO",
    "PLANALTO 13 DE MAIO",
    "PRESIDENTE COSTA E SILVA",
    "COSTA E SILVA",
    "REDENCAO",
    "RINCAO",
    "SANTA DELMIRA",
    "SANTO ANTONIO",
    "SANTA JULIA",
    "AREA RURAL DE MOSSORO",
    "ZONA RURAL",
}

SUB_BAIRRO_TO_BAIRRO_MAP = {
    # 01. ABOLICOES (Maps to official Abolição in GeoJSON)
    "ABOLICOES": "ABOLICAO",
    "CIGANO": "ABOLICAO",
    "TRES VINTENS": "ABOLICAO",
    "SEM TERRA": "ABOLICAO",
    "POUSADA DOS TERMAS": "ABOLICAO",
    # 02. AEROPORTO
    "MACARRAO": "AEROPORTO",
    "IPASA": "AEROPORTO",
    "QUIXABEIRINHA": "AEROPORTO",
    # 03. ALTO DE SAO MANOEL
    "WALFREDO GURGEL": "ALTO DE SAO MANOEL",
    "URICK GRAFF": "ALTO DE SAO MANOEL",
    "COAB": "ALTO DE SAO MANOEL",
    # 04. ALTO DO SUMARE
    "CIDADE JARDIM": "ALTO DO SUMARE",
    "MONTE OLIMPO": "ALTO DO SUMARE",
    # 05. ALTO DA CONCEICAO
    "PEREIROS": "ALTO DA CONCEICAO",
    "PANTANAL": "ALTO DA CONCEICAO",
    # 06. ALTO DA BELA VISTA
    "MARCIO MARINHO": "ALTO DA BELA VISTA",
    "QUINTAS ALPHAVILLE": "ALTO DA BELA VISTA",
    "ALPHAVILLE": "ALTO DA BELA VISTA",
    "SANVILLE": "ALTO DA BELA VISTA",
    # 08. BARROCAS
    "FREITAS NOBRE": "BARROCAS",
    # 10. BELO HORIZONTE
    "CARNAUBAL": "BELO HORIZONTE",
    # 14. COSTA E SILVA (Maps to official Presidente Costa e Silva in GeoJSON)
    "COSTA E SILVA": "PRESIDENTE COSTA E SILVA",
    "TEIMOSOS": "PRESIDENTE COSTA E SILVA",
    "GERALDO MELO": "PRESIDENTE COSTA E SILVA",
    # 15. DOM JAIME CAMARA
    "MALVINAS": "DOM JAIME CAMARA",
    "NOVA VIDA": "DOM JAIME CAMARA",
    "TRAQUILIM": "DOM JAIME CAMARA",
    "JARDIM DAS PALMEIRAS": "DOM JAIME CAMARA",
    # 17. GOV DIX SEPT ROSADO (Maps to official Dix-Sept Rosado in GeoJSON)
    "GOV DIX SEPT ROSADO": "DIX-SEPT ROSADO",
    "GOVERNADOR DIX SEPT ROSADO": "DIX-SEPT ROSADO",
    "FORNO VELHO": "DIX-SEPT ROSADO",
    "BOM PASTOR": "DIX-SEPT ROSADO",
    "VERONIQUE": "DIX-SEPT ROSADO",
    "BOULEVARD": "DIX-SEPT ROSADO",
    # 18. ITAPETINGA
    "CIDADA OESTE": "ITAPETINGA",
    # 20. LAGOA DO MATO
    "ALTO DO XEREM": "LAGOA DO MATO",
    # 21. MONS ALFREDO SIMONNETI (Maps to MONS ALFREDO SIMONETI)
    "ALFREDO SIMONETI": "MONS ALFREDO SIMONETI",
    "AMERICO": "MONS ALFREDO SIMONETI",
    # 22. NOVA BETANIA
    "OURO NEGRO": "NOVA BETANIA",
    "PORTAL DO SOL": "NOVA BETANIA",
    # 24. PAREDOES
    "SAO JOSE": "PAREDOES",
    # 25. PLANALTO 13 DE MAIO (Maps to official Planalto Treze de Maio in GeoJSON)
    "PLANALTO 13 DE MAIO": "PLANALTO TREZE DE MAIO",
    "ALAMEDA DOS CAJUEIROS": "PLANALTO TREZE DE MAIO",
    "LIBERDADE": "PLANALTO TREZE DE MAIO",
    "PAPOCO": "PLANALTO TREZE DE MAIO",
    "INOCOOP": "PLANALTO TREZE DE MAIO",
    # 26. REDENCAO
    "INTEGRACAO": "REDENCAO",
    "INDEPENDENCIA": "REDENCAO",
    "JARDINS": "REDENCAO",
    # 27. RINCAO
    "VINGT ROSADO": "RINCAO",
    "ALTO DA PELONHA": "RINCAO",
    "ODETE ROSADO": "RINCAO",
    "ALTO DAS BRISAS": "RINCAO",
    "PARQUE UNIVERSITARIO": "RINCAO",
    # 28. SANTO ANTONIO
    "SANTA HELENA": "SANTO ANTONIO",
    "WILSON ROSADO": "SANTO ANTONIO",
    "ESTRADA DA RAIZ": "SANTO ANTONIO",
    "SANDRA ROSADO": "SANTO ANTONIO",
    "JOSE AGRIPINO": "SANTO ANTONIO",
    # 29. SANTA DELMIRA
    "PARQUE DAS ROSAS": "SANTA DELMIRA",
    "NOVA ESPERANCA": "SANTA DELMIRA",
    "ROSILANDIA": "SANTA DELMIRA",
    "BOA ESPERANCA": "SANTA DELMIRA",
    "RESISTENCIA": "SANTA DELMIRA",
    "PROMORAR": "SANTA DELMIRA",
    # 30. SANTA JULIA
    "NOVA MOSSORO": "SANTA JULIA",
    "ROYALVILLE": "SANTA JULIA",
}

VARIANT_SUFFIX_RE = re.compile(r"\s+(?:\d+|[IVXLCDM]+)$")
COMPOUND_VARIANT_SUFFIX_RE = re.compile(r"\s+[IVXLCDM]+(?:\s+E\s+[IVXLCDM]+)+$")

RURAL_KEYWORDS = [
    "RURAL",
    "SITIO",
    "ASSENTAMENTO",
    "FAZENDA",
    "PROJETO DE ASSENTAMENTO",
    "VILA RURAL",
]


def _normalize_bairro_name(value: str | None) -> str | None:
    """Normalize bairro values to a stable, privacy-preserving category."""
    if value is None:
        return None

    text = str(value).strip().upper()
    if not text or text in {"NAN", "NONE", "NULL", "IGNORADO", "SEM INFORMACAO"}:
        return None

    text = "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )
    text = " ".join(text.split())

    # Strip generic sub-bairro prefixes to allow a clean dictionary mapping
    prefixes_to_strip = [
        "COMUNIDADE DO ",
        "COMUNIDADE DA ",
        "COMUNIDADE DE ",
        "COMUNIDADE ",
        "CONJUNTO DO ",
        "CONJUNTO DA ",
        "CONJUNTO DE ",
        "CONJUNTO ",
        "CONJ. DO ",
        "CONJ. DA ",
        "CONJ. DE ",
        "CONJ. ",
        "CONJ ",
        "LOTEAMENTO ",
        "LOTEAM. ",
        "LOT. ",
        "VILA DO ",
        "VILA ",
        "MONSENHOR ",
        "MONS. ",
        "MONS ",
    ]
    for prefix in prefixes_to_strip:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break

    text = _strip_compound_variant_suffix(text)
    text = _strip_variant_suffix(text)

    # Look for exact match in map
    if text in SUB_BAIRRO_TO_BAIRRO_MAP:
        return SUB_BAIRRO_TO_BAIRRO_MAP[text]

    # If it is already an official neighborhood name or known parent, preserve it
    if text in OFFICIAL_BAIRROS or text in SUB_BAIRRO_TO_BAIRRO_MAP.values():
        return text

    # Fuzzy fallback on a relaxed variant-stripped form so typos like
    # "LEBERDADE 1" can still resolve to the intended sub-bairro key.
    relaxed_text = _relaxed_variant_text(text)
    if relaxed_text != text:
        relaxed_match = process.extractOne(
            relaxed_text, list(SUB_BAIRRO_TO_BAIRRO_MAP.keys()), score_cutoff=85.0
        )
        if relaxed_match:
            return SUB_BAIRRO_TO_BAIRRO_MAP[relaxed_match[0]]

    # Fuzzy match with score_cutoff=85.0 for spelling typos (e.g. URIC GRAF -> URICK GRAFF)
    match = process.extractOne(text, list(SUB_BAIRRO_TO_BAIRRO_MAP.keys()), score_cutoff=85.0)
    if match:
        matched_key = match[0]
        return SUB_BAIRRO_TO_BAIRRO_MAP[matched_key]

    official_match = process.extractOne(text, list(OFFICIAL_BAIRROS), score_cutoff=85.0)
    if official_match:
        return official_match[0]

    return text


def _strip_variant_suffix(text: str) -> str:
    """Collapse numbered or Roman-numeral variants when the base name is official."""
    candidate = VARIANT_SUFFIX_RE.sub("", text).strip()
    if candidate != text and (
        candidate in OFFICIAL_BAIRROS or candidate in SUB_BAIRRO_TO_BAIRRO_MAP.values()
    ):
        return candidate
    return text


def _strip_compound_variant_suffix(text: str) -> str:
    """Collapse compound Roman numeral variants like 'I E II' when the base is official."""
    candidate = COMPOUND_VARIANT_SUFFIX_RE.sub("", text).strip()
    if candidate != text and (
        candidate in OFFICIAL_BAIRROS
        or candidate in SUB_BAIRRO_TO_BAIRRO_MAP.values()
        or candidate in SUB_BAIRRO_TO_BAIRRO_MAP
    ):
        return candidate
    return text


def _relaxed_variant_text(text: str) -> str:
    """Remove trailing numeric/Roman suffixes before fuzzy matching only."""
    return VARIANT_SUFFIX_RE.sub("", text).strip()


def _infer_zone_from_bairro(bairro_ref: str | None) -> str | None:
    """Infer territorial zone from bairro text using simple heuristics."""
    if bairro_ref is None:
        return None

    if any(keyword in bairro_ref for keyword in RURAL_KEYWORDS):
        return "Rural"
    return "Urbana"


def _normalize_zone(cs_zona: int | None) -> str | None:
    """Map official CS_ZONA coding to human-readable labels."""
    if cs_zona is None:
        return None
    zone_map = {
        1: "Urbana",
        2: "Rural",
        3: "Periurbana",
    }
    return zone_map.get(cs_zona)


def _normalize_age_to_years(nu_idade_n: int | None, tp_idade: int | None) -> float | None:
    """Convert SIVEP age representation into decimal years.

    SIVEP stores age value (NU_IDADE_N) with a separate type code (TP_IDADE):
    1=days, 2=months, 3=years.
    """
    if nu_idade_n is None or nu_idade_n < 0:
        return None

    if tp_idade == 1:
        return round(nu_idade_n / 365.25, 4)
    if tp_idade == 2:
        return round(nu_idade_n / 12.0, 4)
    if tp_idade == 3 or tp_idade is None:
        return float(nu_idade_n)

    return None


def _read_file(file_path: Path) -> pd.DataFrame:
    """Detect format (CSV/Excel/JSON/XML/Parquet) and load the file into a DataFrame."""
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(file_path, sep=None, engine="python", dtype=str)
        except Exception:
            return pd.read_csv(file_path, sep=";", dtype=str)
    if suffix in [".xls", ".xlsx"]:
        return pd.read_excel(file_path, dtype=str)
    if suffix == ".json":
        # dtype=str keeps codes (leading zeros); stubs mistype read_json's dtype.
        return pd.read_json(file_path, dtype=str)  # type: ignore[arg-type]
    if suffix == ".xml":
        from srag.data.pipeline import _load_xml_frame

        return _load_xml_frame(file_path)
    if suffix == ".parquet":
        return pd.read_parquet(file_path)
    raise ValueError(f"Unsupported file format: {file_path.suffix}")


def _derive_territorial_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize known alternate SIVEP column names and derive territorial fields."""
    out = df.copy()
    rename_map = {
        source: target
        for source, target in COLUMN_ALIASES.items()
        if source in out.columns and target not in out.columns
    }
    if rename_map:
        out = out.rename(columns=rename_map)
        logger.info(f"Normalized {len(rename_map)} alternate SIVEP column names.")

    if "NM_BAIRRO" in out.columns and "BAIRRO_REF" not in out.columns:
        out["BAIRRO_REF"] = out["NM_BAIRRO"].apply(_normalize_bairro_name)

    if "CS_ZONA" in out.columns:
        cs_zona_num = pd.to_numeric(out["CS_ZONA"], errors="coerce").astype("Int64")
        out["ZONA"] = cs_zona_num.apply(lambda v: _normalize_zone(int(v)) if pd.notna(v) else None)

    if "BAIRRO_REF" in out.columns and "ZONA" not in out.columns:
        out["ZONA"] = out["BAIRRO_REF"].apply(_infer_zone_from_bairro)

    if "BAIRRO_REF" in out.columns and "ZONA" in out.columns:
        missing_zone = out["ZONA"].isna()
        out.loc[missing_zone, "ZONA"] = out.loc[missing_zone, "BAIRRO_REF"].apply(
            _infer_zone_from_bairro
        )

    return out


def _validate_and_normalize(
    df: pd.DataFrame,
    filter_mossoro: bool = True,
    drop_sensitive: bool = True,
) -> pd.DataFrame:
    """Drop sensitive fields, validate records with Pydantic, and normalize age."""
    out = df.copy()
    if drop_sensitive:
        cols_to_drop = [c for c in SENSITIVE_FIELDS if c in out.columns]
        out = out.drop(columns=cols_to_drop)
        logger.info(f"Dropped {len(cols_to_drop)} sensitive columns for LGPD compliance.")

    valid_records = []
    invalid_count = 0
    records = out.to_dict(orient="records")

    for record in records:
        try:
            cleaned_record = {
                k: (v if str(v).strip() != "" and pd.notna(v) else None) for k, v in record.items()
            }
            case = SragCase.model_validate(cleaned_record)

            if filter_mossoro and not is_mossoro_case(case):
                continue

            normalized_case = case.model_dump()
            normalized_case["IDADE_ANOS"] = _normalize_age_to_years(
                normalized_case.get("NU_IDADE_N"),
                normalized_case.get("TP_IDADE"),
            )
            valid_records.append(normalized_case)
        except ValidationError as e:
            invalid_count += 1
            if invalid_count < 3:
                logger.debug(f"Validation error in record: {e}")

    if invalid_count > 0:
        logger.warning(
            f"Skipped {invalid_count} records due to validation errors (dates, types, etc)."
        )

    logger.info(f"Processed {len(valid_records)} valid records for Mossoró.")
    return pd.DataFrame(valid_records)


def load_and_clean_srag_data(
    file_path: Path,
    filter_mossoro: bool = True,
    drop_sensitive: bool = True,
) -> pd.DataFrame:
    """Load SRAG data from CSV, Excel, JSON, XML, or Parquet, validate, and clean it.

    Args:
        file_path: Path to the input file (CSV, Excel, JSON, XML, or Parquet).
        filter_mossoro: If True, only keeps cases related to Mossoró/RN.
        drop_sensitive: If True, removes LGPD-sensitive columns.

    Returns:
        A cleaned and validated pandas DataFrame.
    """
    logger.info(f"Loading data from {file_path}")

    try:
        df = _read_file(file_path)
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise

    df = _derive_territorial_fields(df)
    return _validate_and_normalize(df, filter_mossoro, drop_sensitive)


def export_secure_dataset(input_path: Path, output_path: Path) -> None:
    """Read a raw dataset and export a filtered, anonymized version for Mossoró.

    This function is designed to be the main entry point for the Mossoró health sector.
    """
    df_clean = load_and_clean_srag_data(input_path, filter_mossoro=True, drop_sensitive=True)

    if df_clean.empty:
        logger.warning("No valid Mossoró records found to export.")
        return

    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as Parquet for efficiency or CSV as fallback
    if output_path.suffix == ".parquet":
        df_clean.to_parquet(output_path, index=False)
    else:
        df_clean.to_csv(output_path, index=False, encoding="utf-8")

    logger.info(f"Secure dataset exported successfully to {output_path}")
