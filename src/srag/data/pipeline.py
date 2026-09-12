"""Reusable SRAG ingestion pipeline (importable; CLI lives in scripts/ingest_data.py).

DuckDB handles CSV and Parquet; XLSX is loaded via pandas.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Iterable

# Defaults
DB_PATH = Path("data/processed/srag_mossoro.db")
DATA_DIRS = [Path("data/raw")]

# Mossoró normalization constants
MOSSORO_CODES = ("2408003", "240800", "240800.0")
MOSSORO_NAMES = ("MOSSORO", "MOSSORÓ")


def _load_xml_frame(pf: Path) -> pd.DataFrame:
    """Parse a tabular XML file (repeated record elements) into a DataFrame."""
    from defusedxml.ElementTree import parse as safe_parse

    def _tag(name: str) -> str:
        return name.rsplit("}", 1)[-1]

    def _flatten(elem: Any, prefix: str = "") -> dict[str, str | None]:  # noqa: ANN401
        flat: dict[str, str | None] = {}
        children = list(elem)  # type: ignore[call-overload]
        if not children:
            flat[prefix or _tag(elem.tag)] = (elem.text or "").strip() or None
            return flat
        for child in children:
            key = _tag(child.tag) if not prefix else f"{prefix}_{_tag(child.tag)}"
            flat.update(_flatten(child, key))
        return flat

    root = safe_parse(pf).getroot()
    children = list(root)  # type: ignore[call-overload]
    if len(children) == 1:
        grand = list(children[0])
        if len(grand) > 1 and len({g.tag for g in grand}) == 1:
            children = grand  # <root><records><record/>...</records> envelope
    df = pd.DataFrame([_flatten(c) for c in children], dtype=str)
    if len(df.columns):
        # Unwrap single-record envelopes: all cols share one prefix (e.g. record_DT_NOTIFIC).
        segments = [str(c).split("_") for c in df.columns]
        firsts = {parts[0] for parts in segments if len(parts) > 1}
        if len(firsts) == 1:
            df.columns = [
                "_".join(parts[1:]) if len(parts) > 1 else parts[0] for parts in segments
            ]
    return df


def _load_source_frames(pf: Path) -> Iterable[tuple[str, pd.DataFrame]]:
    """Load one file as one or more DataFrames.

    Args:
        pf: Path to the source file.

    Yields:
        Tuples of (source_name, DataFrame).
    """
    ext = pf.suffix.lower()
    if ext == ".xlsx":
        sheets = pd.read_excel(pf, sheet_name=None, dtype=str)
        for sheet_name, df in sheets.items():
            yield f"{pf.name}::{sheet_name}", df
        return

    if ext == ".parquet":
        yield pf.name, pd.read_parquet(pf)
        return

    if ext == ".json":
        yield pf.name, pd.read_json(pf)
        return

    if ext == ".xml":
        yield pf.name, _load_xml_frame(pf)
        return

    yield pf.name, pd.read_csv(pf, sep=None, engine="python", dtype=str)


def _find_ingestion_files(data_dirs: list[Path]) -> list[Path]:
    """Find all matching files in data directories."""
    files: list[Path] = []
    for d in data_dirs:
        if d.exists():
            files.extend(list(d.glob("**/*.parquet")))
            files.extend(list(d.glob("**/*.csv")))
            files.extend(list(d.glob("**/*.xlsx")))
            files.extend(list(d.glob("**/*.json")))
            files.extend(list(d.glob("**/*.xml")))
    return files


def _file_col(file_cols: dict[str, str], name: str) -> str:
    """Resolve a source column name, or "NULL" when absent."""
    return file_cols.get(name.upper(), "NULL")


def _first_present_col(file_cols: dict[str, str], *names: str) -> str:
    """First available source column among aliases, else "NULL"."""
    for name in names:
        hit = _file_col(file_cols, name)
        if hit != "NULL":
            return hit
    return "NULL"


def _coalesce_date_expr(orig: str) -> str:
    """DATE coercion trying native, DD/MM/YYYY then YYYY-MM-DD order."""
    if orig == "NULL":
        return "NULL"
    p1 = f"strptime(SUBSTR(CAST({orig} AS VARCHAR), 1, 10), '%d/%m/%Y')"
    p2 = f"strptime(SUBSTR(CAST({orig} AS VARCHAR), 1, 10), '%Y-%m-%d')"
    return f"""
        COALESCE(
            TRY_CAST({orig} AS DATE),
            TRY_CAST({p1} AS DATE),
            TRY_CAST({p2} AS DATE)
        )
    """


def _resolve_hash_field(file_cols: dict[str, str], source_mun: str, field: str) -> str:
    if field == "ID_MUNICIP":
        return source_mun
    return _file_col(file_cols, field)


def _project_column(
    col: str,
    file_cols: dict[str, str],
    date_cols: set[str],
    source_mun: str,
    source_res: str,
) -> str:
    """SQL projection expression for one target column."""
    from srag.data.database import build_case_hash_sql

    col_up = col.upper()
    if col == "unique_hash":
        # Hash logic MUST match srag.data.database.generate_case_hash.
        return build_case_hash_sql(
            lambda field: _resolve_hash_field(file_cols, source_mun, field)
        )
    if col in ("BAIRRO_REF", "ZONA"):
        return "NULL"
    if col == "ID_MUNICIP":
        return f"CAST({source_mun} AS VARCHAR)"
    if col == "ID_MN_RESI":
        return f"CAST({source_res} AS VARCHAR)"
    if col_up in date_cols:
        return _coalesce_date_expr(_file_col(file_cols, col_up))
    if col_up == "CO_DETEC":
        return _first_present_col(file_cols, "CO-DETEC", "CO_DETEC")
    if col_up == "FAB_COV1":
        return _first_present_col(file_cols, "FAB_COV_1", "FAB_COV1")
    if col_up == "FAB_COV2":
        return _first_present_col(file_cols, "FAB_COV_2", "FAB_COV2")
    if col_up == "ID_UNIDADE":
        return _first_present_col(file_cols, "CO_UNI_NOT", "ID_UNIDADE")
    return _file_col(file_cols, col_up)


def _build_projection_select(
    target_cols: list[str],
    date_cols: set[str],
    file_cols: dict[str, str],
    source_mun: str,
    source_res: str,
) -> list[str]:
    """Build SQL projection expressions for each target column."""
    return [
        _project_column(col, file_cols, date_cols, source_mun, source_res)
        for col in target_cols
    ]


def _ingest_source_frame(
    con: duckdb.DuckDBPyConnection,
    source_name: str,
    source_df: pd.DataFrame,
    target_cols: list[str],
    date_cols: set[str],
) -> None:
    """Ingest a single dataframe source into temp_cases."""
    print(f"  -> {source_name}")
    file_cols = {str(c).upper(): c for c in source_df.columns}

    source_mun = _first_present_col(file_cols, "CO_MUN_NOT", "ID_MUNICIP")
    source_res = _first_present_col(file_cols, "CO_MUN_RES", "ID_MN_RESI")

    select_parts = _build_projection_select(
        target_cols, date_cols, file_cols, source_mun, source_res
    )

    con.register("source_frame", source_df)
    # FILTRO AMPLIADO: Garante captura de códigos IBGE curtos e longos + nomes
    con.execute(f"""
        INSERT INTO temp_cases ({", ".join(target_cols)})
        SELECT {", ".join(select_parts)} FROM source_frame
        WHERE
            CAST({source_mun} AS VARCHAR) LIKE '240800%' OR
            CAST({source_res} AS VARCHAR) LIKE '240800%' OR
            UPPER(CAST({source_mun} AS VARCHAR)) IN {MOSSORO_NAMES} OR
            UPPER(CAST({source_res} AS VARCHAR)) IN {MOSSORO_NAMES}
    """)  # nosec B608


def _run_ingest_geo_pass(db_path: Path) -> None:
    """Apply geographic intelligence to cases_srag table."""
    from srag.data.loader import _infer_zone_from_bairro, _normalize_bairro_name, _normalize_zone

    print("🧪 Aplicando inteligência geográfica...")
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql("SELECT rowid, NM_BAIRRO, CS_ZONA FROM casos_srag", conn)
        df["BAIRRO_REF"] = df["NM_BAIRRO"].apply(_normalize_bairro_name)
        zona_from_code = df["CS_ZONA"].apply(
            lambda value: _normalize_zone(int(value)) if pd.notna(value) else None
        )
        zona_from_bairro = df["BAIRRO_REF"].apply(_infer_zone_from_bairro)
        df["ZONA"] = zona_from_code.combine_first(zona_from_bairro).fillna("Nao informado")
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE casos_srag SET BAIRRO_REF = ?, ZONA = ? WHERE rowid = ?",
            df[["BAIRRO_REF", "ZONA", "rowid"]].values.tolist(),
        )
        conn.commit()


def run_ingest(
    db_path_override: Path | None = None,
    data_dirs_override: list[Path] | None = None,
    batch: str | None = None,
) -> dict[str, Any]:
    """Run the master ingestion pipeline.

    Args:
        db_path_override: Optional path to the SQLite database.
        data_dirs_override: Optional list of directories to search for data.
        batch: Tag identifying this upload batch for the error quarantine
            (defaults to a timestamp).

    Returns:
        Stats dict with temp_cases, unique_cases, duplicates_removed, sources,
        quarantined.
    """
    from srag.data.database import init_db

    db_path = db_path_override or DB_PATH
    data_dirs = data_dirs_override or DATA_DIRS

    print(f"🚀 Iniciando motor universal de ingestão (DB: {db_path})...")

    init_db()
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"ATTACH '{db_path}' AS sqlite_db (TYPE SQLITE);")

    print("🧹 Limpando dados antigos...")
    con.execute("DELETE FROM sqlite_db.casos_srag;")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("PRAGMA table_info('casos_srag')")
        target_cols = [c[1] for c in cursor.fetchall()]

    date_cols = {
        "DT_NOTIFIC",
        "DT_SIN_PRI",
        "DT_NASC",
        "DT_INTERNA",
        "DT_ENTUTI",
        "DT_SAIDUTI",
        "DT_EVOLUCA",
        "DT_PCR",
        "DT_RES_AN",
        "DT_COLETA",
        "DOSE_1_COV",
        "DOSE_2_COV",
        "DOSE_REF",
        "DOSE_2REF",
        "DOSE_ADIC",
        "DOS_RE_BI",
        "DT_UT_DOSE",
        "DT_1_DOSE",
        "DT_2_DOSE",
        "DT_DOSEUNI",
        "DT_VAC_MAE",
        "DT_ANTIVIR",
    }

    # Tabela temporária para consolidação
    con.execute("CREATE TABLE temp_cases AS SELECT * FROM sqlite_db.casos_srag WHERE 1=0;")

    # 1. Localizar arquivos
    files = _find_ingestion_files(data_dirs)

    if not files:
        print(f"⚠️ Nenhum dado encontrado em {data_dirs}.")
        empty_stats = {
            "temp_cases": 0,
            "unique_cases": 0,
            "duplicates_removed": 0,
            "sources": 0,
            "quarantined": 0,
        }
        return empty_stats

    print(f"📦 Processando {len(files)} fontes de dados...")

    for pf in files:
        try:
            for source_name, source_df in _load_source_frames(pf):
                _ingest_source_frame(con, source_name, source_df, target_cols, date_cols)
        except Exception as e:
            print(f"  ❌ Erro em {pf.name}: {e}")

    # 2. Desduplicação e Carga Final
    print("💎 Removendo duplicatas e salvando no banco final...")
    temp_row = con.execute("SELECT count(*) FROM temp_cases").fetchone()
    assert temp_row is not None
    temp_count = temp_row[0]
    con.execute(f"""
        INSERT INTO sqlite_db.casos_srag ({", ".join(target_cols)})
        SELECT {", ".join(target_cols)} FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY unique_hash ORDER BY DT_NOTIFIC DESC) as rn
            FROM temp_cases
        ) WHERE rn = 1
    """)  # nosec B608
    final_row = con.execute("SELECT count(*) FROM sqlite_db.casos_srag").fetchone()
    assert final_row is not None
    final_count = final_row[0]
    duplicates = temp_count - final_count
    print(
        "📊 Ingestão consolidada: "
        f"temp_cases={temp_count}, unique_cases={final_count}, duplicates_removed={duplicates}"
    )

    # 3. Normalização Inteligente (Pandas Pass)
    _run_ingest_geo_pass(db_path)

    # Quarentena desativada: a base mantém todas as notificações.
    quarantine_stats = {"quarantined": 0, "by_category": {}}

    print(f"✅ Ingestão finalizada: {final_count} registros únicos.")
    return {
        "temp_cases": temp_count,
        "unique_cases": final_count,
        "duplicates_removed": duplicates,
        "sources": len(files),
        "quarantined": quarantine_stats["quarantined"],
    }


if __name__ == "__main__":
    run_ingest()
