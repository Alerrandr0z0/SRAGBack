"""Ingest management routers (ADMIN only): upload new data and inspect DB status."""

import contextlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from srag.api.auth import UserRecord, require_admin
from srag.api.core import get_df, refresh_df, sanitize_data
from srag.data.pipeline import DATA_DIRS, DB_PATH, run_ingest

router = APIRouter(tags=["ingest"])


def _make_db_shared(db_file: Path) -> None:
    """Best-effort chmod so host (uid 1000) and container (uid 1001) can both use the DB."""
    with contextlib.suppress(OSError):
        db_file.chmod(0o666)


MAX_UPLOAD_BYTES = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = {".xlsx", ".csv", ".json", ".xml", ".parquet"}

# In-memory ingestion job state (mirrors the reference async-upload pattern:
# 202 Accepted + background processing + status polling).
_JOB: dict[str, Any] = {"state": "idle"}


def _run_ingest_job(db_file: Path, batch: str) -> None:
    """Background ingestion: full pipeline + quarantine over all raw sources."""
    backup = db_file.with_suffix(".upload_bak")
    try:
        if db_file.exists():
            backup.write_bytes(db_file.read_bytes())
        stats = run_ingest(batch=batch)
        _make_db_shared(db_file)
        refresh_df()
        _JOB.update(
            {
                "state": "done",
                "stats": stats,
                "error": None,
            }
        )
    except Exception as e:
        if backup.exists():
            backup.replace(db_file)
            _make_db_shared(db_file)
            refresh_df()
        _JOB.update(
            {
                "state": "error",
                "stats": None,
                "error": f"Falha na ingestão: {e}",
            }
        )
    finally:
        if backup.exists():
            backup.unlink(missing_ok=True)


@router.get("/ingest/status")
def ingest_status(admin: Annotated[UserRecord, Depends(require_admin)]) -> dict[str, Any]:
    """Current database status: totals, years, latest notification."""
    del admin
    df = get_df()
    latest: str | None = None
    years: list[int] = []
    if not df.empty and "DT_NOTIFIC" in df.columns:
        dt_s = pd.to_datetime(df["DT_NOTIFIC"], errors="coerce").dropna()
        if not dt_s.empty:
            latest = dt_s.max().strftime("%Y-%m-%d")
            years = sorted({int(y) for y in dt_s.dt.year})
    return sanitize_data(
        {
            "total": len(df),
            "available_years": years,
            "latest_notific": latest,
        }
    )


@router.get("/ingest/job")
def ingest_job(admin: Annotated[UserRecord, Depends(require_admin)]) -> dict[str, Any]:
    """Current background ingestion job state (ADMIN only)."""
    del admin
    return sanitize_data(dict(_JOB))


@router.post("/ingest/upload", status_code=202)
def ingest_upload(
    admin: Annotated[UserRecord, Depends(require_admin)],
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    """Upload a new SIVEP file and ingest in background (ADMIN only).

    Accepts .xlsx/.csv/.json/.xml/.parquet. Returns 202 Accepted immediately;
    the file is stored in data/raw and the
    full pipeline runs over all raw sources (deduplicated by unique_hash).
    Poll ``GET /ingest/job`` for completion. The API cache is invalidated after.
    """
    del admin
    if _JOB.get("state") == "processing":
        raise HTTPException(
            status_code=409, detail="Já existe uma ingestão em andamento."
        )
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Aceitos: .xlsx, .csv, .json, .xml, .parquet.",
        )
    raw_dir = DATA_DIRS[0]
    raw_dir.mkdir(parents=True, exist_ok=True)

    content = file.file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo excede 100MB.")
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dest = raw_dir / f"upload_{stamp}{ext}"
    dest.write_bytes(content)

    db_file = DB_PATH if DB_PATH.is_absolute() else Path.cwd() / DB_PATH
    _JOB.update(
        {
            "state": "processing",
            "file": dest.name,
            "stats": None,
            "error": None,
        }
    )
    background_tasks.add_task(_run_ingest_job, db_file, dest.name)

    return sanitize_data(
        {"message": "Processamento iniciado.", "file": dest.name, "status": "processing"}
    )
