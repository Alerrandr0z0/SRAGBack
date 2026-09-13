"""Database management for SRAG Mossoró historical data."""

import hashlib
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, Date, Float, Integer, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("SRAG-Database")


def _find_project_root() -> Path:
    """Find the project root by looking for .git directory first, then pyproject.toml."""
    current = Path(__file__).resolve()
    # Check current directory and all parents
    for parent in [current, *list(current.parents)]:
        # Prefer .git as it won't be copied to mutants/ directory
        if (parent / ".git").exists():
            return parent
    # Fallback to pyproject.toml if .git not found
    for parent in [current, *list(current.parents)]:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback to current directory if no marker found
    return current


def _get_db_url() -> str:
    """Get DB URL from environment or auto-detect project root."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    root = _find_project_root()
    return f"sqlite:///{root / 'data' / 'processed' / 'srag_mossoro.db'}"


PROJECT_ROOT = _find_project_root()
DB_URL = _get_db_url()
CASE_HASH_FIELDS = (
    "DT_NOTIFIC",
    "ID_MUNICIP",
    "DT_SIN_PRI",
    "NU_IDADE_N",
    "CS_SEXO",
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class SragRecord(Base):
    """SQLAlchemy model for an anonymized SRAG case."""

    __tablename__ = "casos_srag"

    # unique_hash: MD5 of stable case fields used to prevent duplication.
    # The hash intentionally excludes ID_UNIDADE so corrected unit data can
    # enrich the same case without splitting the series.
    unique_hash = Column(String(32), primary_key=True)

    DT_NOTIFIC = Column(Date, nullable=False)
    ID_MUNICIP = Column(String(10), nullable=False)
    ID_MN_RESI = Column(String(10), nullable=False)
    DT_SIN_PRI = Column(Date, nullable=False)
    ID_UNIDADE = Column(String(30))
    BAIRRO_REF = Column(String(80))
    NM_BAIRRO = Column(String(120))
    ZONA = Column(String(20))
    CS_ZONA = Column(Integer)
    NU_IDADE_N = Column(Integer)
    TP_IDADE = Column(Integer)
    IDADE_ANOS = Column(Float)
    CS_SEXO = Column(String(1))
    CS_RACA = Column(Integer)
    CS_ESCOL_N = Column(Integer)
    PAC_DSCBO = Column(String(150))
    AVE_SUINO = Column(Integer)
    CLASSI_FIN = Column(Integer)
    PCR_VSR = Column(Integer)
    AN_VSR = Column(Integer)
    PCR_SARS2 = Column(Integer)
    AN_SARS2 = Column(Integer)
    TP_FLU_PCR = Column(Integer)
    TP_FLU_AN = Column(Integer)
    PCR_RESUL = Column(Integer)
    RES_AN = Column(Integer)
    DT_PCR = Column(Date)
    DT_RES_AN = Column(Date)
    DT_COLETA = Column(Date)
    LAB_AN = Column(String(120))
    CO_LAB_AN = Column(String(20))
    POS_PCRFLU = Column(Integer)
    PCR_FLUASU = Column(Integer)
    PCR_FLUBLI = Column(Integer)
    PCR_RINO = Column(Integer)
    PCR_METAP = Column(Integer)
    PCR_ADENO = Column(Integer)
    PCR_PARA1 = Column(Integer)
    PCR_PARA2 = Column(Integer)
    PCR_PARA3 = Column(Integer)
    PCR_PARA4 = Column(Integer)
    POS_AN_OUT = Column(Integer)
    AN_ADENO = Column(Integer)
    AN_PARA1 = Column(Integer)
    AN_PARA2 = Column(Integer)
    AN_PARA3 = Column(Integer)
    AMOSTRA = Column(Integer)
    TP_AMOSTRA = Column(Integer)
    DT_INTERNA = Column(Date)
    DT_ENTUTI = Column(Date)
    DT_SAIDUTI = Column(Date)
    EVOLUCAO = Column(Integer)
    DT_EVOLUCA = Column(Date)
    UTI = Column(Integer)
    HOSPITAL = Column(Integer)
    SUPORT_VEN = Column(Integer)
    RAIOX_RES = Column(Integer)
    TOMO_RES = Column(Integer)
    ASMA = Column(Integer)
    HEMATOLOGI = Column(Integer)
    SIND_DOWN = Column(Integer)
    HEPATICA = Column(Integer)
    NEUROLOGIC = Column(Integer)
    PNEUMOPATI = Column(Integer)
    IMUNODEPRE = Column(Integer)
    RENAL = Column(Integer)
    DIABETES = Column(Integer)
    OBESIDADE = Column(Integer)
    TABAG = Column(Integer)
    OUT_MORBI = Column(Integer)
    CARDIOPATI = Column(Integer)
    FEBRE = Column(Integer)
    TOSSE = Column(Integer)
    GARGANTA = Column(Integer)
    DISPNEIA = Column(Integer)
    DESC_RESP = Column(Integer)
    SATURACAO = Column(Integer)
    DIARREIA = Column(Integer)
    VOMITO = Column(Integer)
    DOR_ABD = Column(Integer)
    FADIGA = Column(Integer)
    PERD_OLFT = Column(Integer)
    PERD_PALA = Column(Integer)
    OUTRO_SIN = Column(Integer)
    NOSOCOMIAL = Column(Integer)
    CS_GESTANT = Column(Integer)
    PUERPERA = Column(Integer)
    POV_CT = Column(Integer)
    TP_POV_CT = Column(String(150))
    VACINA_COV = Column(Integer)
    DOSE_1_COV = Column(Date)
    DOSE_2_COV = Column(Date)
    DOSE_REF = Column(Date)
    DOSE_2REF = Column(Date)
    DOSE_ADIC = Column(Date)
    DOS_RE_BI = Column(Date)
    VACINA = Column(Integer)
    DT_UT_DOSE = Column(Date)
    MAE_VAC = Column(Integer)
    DT_VAC_MAE = Column(Date)
    DT_DOSEUNI = Column(Date)
    DT_1_DOSE = Column(Date)
    DT_2_DOSE = Column(Date)
    ANTIVIRAL = Column(Integer)
    CRITERIO = Column(Integer)
    TRAT_COV = Column(Integer)

    # Fabricantes de Vacina
    FAB_COV1 = Column(String(100))
    FAB_COV2 = Column(String(100))
    FAB_COVRF = Column(String(100))
    FAB_COVRF2 = Column(String(100))
    FAB_ADIC = Column(String(100))
    FAB_RE_BI = Column(String(100))

    # Vigilância Genômica e Co-detecção
    VG_OMS = Column(Integer)
    VG_LIN = Column(String(50))
    VG_MET = Column(Integer)
    VG_REINF = Column(Integer)
    CO_DETEC = Column(Integer)

    # Sorologia e Detalhamento de Tratamento
    TP_SOR = Column(Integer)
    RES_IGG = Column(Integer)
    RES_IGM = Column(Integer)
    RES_IGA = Column(Integer)
    TP_ANTIVIR = Column(Integer)
    DT_ANTIVIR = Column(Date)
    OUT_ANTIV = Column(String(100))
    TIPO_TRAT = Column(Integer)
    OUT_TRAT = Column(String(100))
    SURTO_SG = Column(Integer)


def generate_case_hash(record: dict[str, Any]) -> str:
    """Generate a unique hash for a case to prevent duplicates."""
    key_fields = [str(record.get(field)) for field in CASE_HASH_FIELDS]
    hash_input = "|".join(key_fields).encode("utf-8")
    return hashlib.md5(hash_input, usedforsecurity=False).hexdigest()


def build_case_hash_sql(resolve_field: Callable[[str], str]) -> str:
    """Build the DuckDB SQL expression for the case hash."""
    return (
        "md5("
        + " || '|' || ".join(
            f"COALESCE(CAST({resolve_field(field)} AS VARCHAR), '')" for field in CASE_HASH_FIELDS
        )
        + ")"
    )


def init_db() -> None:
    """Initialize the SQLite database and create tables with automated migrations."""
    engine = create_engine(DB_URL)
    Base.metadata.create_all(engine)

    # Automated migration for any newly added model columns
    with engine.begin() as conn:
        cols = conn.execute(text("PRAGMA table_info(casos_srag)")).fetchall()
        col_names = {col[1].upper() for col in cols}

        for column in SragRecord.__table__.columns:
            name = column.name
            if name.upper() == "UNIQUE_HASH" or name.upper() in col_names:
                continue

            sql_type = column.type.compile(dialect=engine.dialect)
            conn.execute(text(f"ALTER TABLE casos_srag ADD COLUMN {name} {sql_type}"))


def _enrich_existing_case(
    existing: SragRecord, case_dict: dict[str, Any], model_columns: set[str]
) -> bool:
    """Fill missing fields on the existing SragRecord with new data.

    Returns:
        True if the record was enriched, False otherwise.
    """
    was_enriched = False
    for col in model_columns:
        val = case_dict.get(col)
        if val is not None and getattr(existing, col) is None:
            setattr(existing, col, val)
            was_enriched = True
    return was_enriched


def _map_case_to_record(
    case_dict: dict[str, Any], case_hash: str, model_columns: set[str]
) -> SragRecord:
    """Automatically map a dict to SragRecord model based on column names."""
    data = {k: v for k, v in case_dict.items() if k in model_columns}

    # Special handling for common SIVEP hyphenated fields
    if "CO-DETEC" in case_dict and "CO_DETEC" not in data:
        data["CO_DETEC"] = case_dict["CO-DETEC"]

    return SragRecord(unique_hash=case_hash, **data)


_ingest_engine = None


def save_cases(cases: list[dict[str, Any]]) -> int:
    """Save a list of cases to the database, skipping duplicates with automated mapping.

    Returns:
        The number of NEW cases added.
    """
    global _ingest_engine
    if _ingest_engine is None:
        _ingest_engine = create_engine(DB_URL)
    # expire_on_commit=False previne o erro e3q8 (ObjectDeletedError) ao acessar/atualizar objetos
    # caso o banco seja alterado por outro processo (ex: DuckDB ingest script)
    session_factory = sessionmaker(bind=_ingest_engine, expire_on_commit=False)

    # Get model columns for automated mapping (excluding primary key)
    model_columns = {c.name for c in SragRecord.__table__.columns if c.name != "unique_hash"}

    new_count = 0
    duplicate_count = 0
    enriched_count = 0
    with session_factory() as session:
        for case_dict in cases:
            case_hash = generate_case_hash(case_dict)
            exists = session.query(SragRecord).filter(SragRecord.unique_hash == case_hash).first()

            if not exists:
                record = _map_case_to_record(case_dict, case_hash, model_columns)
                session.add(record)
                new_count += 1
            else:
                duplicate_count += 1
                if _enrich_existing_case(exists, case_dict, model_columns):
                    enriched_count += 1

        session.commit()
    logger.info(
        "save_cases summary: new=%d, duplicates=%d, enriched=%d",
        new_count,
        duplicate_count,
        enriched_count,
    )
    return new_count
