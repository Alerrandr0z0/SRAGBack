"""Manage routers (ADMIN only): review quarantined errors (read-only)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from srag.api.auth import UserRecord, require_admin
from srag.api.core import sanitize_data
from srag.data.pipeline import DB_PATH

router = APIRouter(tags=["manage"])

# Agente viral derivado da CLASSI_FIN (equivale à dimensão "doença" da referência:
# SRAG é a síndrome; o agente — Influenza, Covid-19, VSR… — é a doença).
AGENT_BY_CLASSI = {
    1: "INFLUENZA",
    2: "OUTRO_VIRUS",
    3: "OUTRO_AGENTE",
    4: "NAO_ESPECIFICADO",
    5: "COVID-19",
}


def _agent_of(raw: dict[str, Any]) -> str:
    value = raw.get("CLASSI_FIN")
    if value in (None, ""):
        return "NAO_ESPECIFICADO"
    try:
        code = int(value)
    except (TypeError, ValueError):
        return "NAO_ESPECIFICADO"
    return AGENT_BY_CLASSI.get(code, "NAO_ESPECIFICADO")


def _db_path() -> Path:
    return DB_PATH if DB_PATH.is_absolute() else Path.cwd() / DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _latest_batch(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT batch FROM srag_quarantine ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row["batch"] if row else None


def _error_clauses(
    category: str | None,
    batch: str | None,
    start_date: str | None,
    end_date: str | None,
    agent: str | None = None,
) -> tuple[str, list[Any]]:
    """Shared WHERE builder for the errors list and its PDF export."""
    clauses: list[str] = []
    params: list[Any] = []
    if batch:
        clauses.append("batch = ?")
        params.append(batch)
    if category:
        clauses.append("error_category = ?")
        params.append(category)
    if start_date:
        clauses.append("json_extract(raw_record, '$.DT_NOTIFIC') >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("json_extract(raw_record, '$.DT_NOTIFIC') <= ?")
        params.append(end_date)
    if agent:
        codes = [code for code, name in AGENT_BY_CLASSI.items() if name == agent]
        if codes:
            placeholders = ",".join("?" for _ in codes)
            agent_clause = (
                f"CAST(json_extract(raw_record, '$.CLASSI_FIN') AS INTEGER) "
                f"IN ({placeholders})"
            )
            if agent == "NAO_ESPECIFICADO":
                agent_clause = (
                    f"({agent_clause} OR json_extract(raw_record, '$.CLASSI_FIN') IS NULL)"
                )
            clauses.append(agent_clause)
            params.extend(codes)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def _epi_week_of(raw: dict[str, Any]) -> int | None:
    """Epidemiological week from the raw record (DT_SIN_PRI, fallback DT_NOTIFIC)."""
    from datetime import date as _date

    from srag.utils.epi_weeks import get_epi_week

    for key in ("DT_SIN_PRI", "DT_NOTIFIC"):
        value = raw.get(key)
        if value in (None, ""):
            continue
        try:
            moment = (
                value
                if isinstance(value, _date)
                else _date.fromisoformat(str(value)[:10])
            )
            _year, week = get_epi_week(moment)
            return week or None
        except (ValueError, TypeError):
            continue
    return None


# ---------------------------------------------------------------- errors ---


@router.get("/manage/errors")
def manage_errors(
    admin: Annotated[UserRecord, Depends(require_admin)],
    category: str | None = Query(None, max_length=80),
    start_date: str | None = Query(None, max_length=10),
    end_date: str | None = Query(None, max_length=10),
    agent: str | None = Query(None, max_length=20),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Paginated quarantined-error list with category counts (ADMIN only)."""
    del admin
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS srag_quarantine (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch VARCHAR(64),
                source_file VARCHAR(255),
                row_index INTEGER,
                raw_record TEXT,
                error_category VARCHAR(80),
                error_detail VARCHAR(500),
                created_at DATETIME
            )"""
        )
        active_batch = _latest_batch(conn)
        where, params = _error_clauses(category, active_batch, start_date, end_date, agent)
        total = conn.execute(
            f"SELECT count(*) AS n FROM srag_quarantine {where}", params  # nosec B608
        ).fetchone()["n"]
        rows = conn.execute(
            "SELECT id, batch, source_file, row_index, raw_record, "  # nosec B608
            f"error_category, error_detail, created_at FROM srag_quarantine {where} "
            "ORDER BY id LIMIT ? OFFSET ?",
            [*params, page_size, (page - 1) * page_size],
        ).fetchall()
        cat_where, cat_params = _error_clauses(None, active_batch, start_date, end_date)
        categories = conn.execute(
            "SELECT error_category AS category, count(*) AS count "  # nosec B608
            f"FROM srag_quarantine {cat_where} GROUP BY error_category ORDER BY count DESC",
            cat_params,
        ).fetchall()
    items = []
    for r in rows:
        item = dict(r)
        try:
            raw = json.loads(item["raw_record"] or "{}")
        except (TypeError, json.JSONDecodeError):
            raw = {}
        item["raw_record"] = raw if isinstance(raw, dict) else {}
        item["semana_epidemiologica"] = _epi_week_of(item["raw_record"])
        item["agente"] = _agent_of(item["raw_record"])
        items.append(item)
    return sanitize_data(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "categories": [dict(c) for c in categories],
        }
    )


@router.get("/manage/errors/pdf")
def errors_pdf(
    admin: Annotated[UserRecord, Depends(require_admin)],
    category: str | None = Query(None, max_length=80),
    start_date: str | None = Query(None, max_length=10),
    end_date: str | None = Query(None, max_length=10),
    agent: str | None = Query(None, max_length=20),
) -> Response:
    """Quarantined-error report PDF honoring the active filters (ADMIN only).

    Port of the reference ``ErrorsPdfReportService``: same layout, subtitle
    format and 8-column table (Agente in place of Doença).
    """
    del admin
    from datetime import datetime

    from srag.reporting import build_errors_pdf, format_br_date, today_br

    with _connect() as conn:
        active_batch = _latest_batch(conn)
        where, params = _error_clauses(category, active_batch, start_date, end_date, agent)
        rows = conn.execute(
            "SELECT id, batch, source_file, row_index, raw_record, "  # nosec B608
            f"error_category, error_detail, created_at FROM srag_quarantine {where} "
            "ORDER BY id LIMIT 2000",
            params,
        ).fetchall()

    agent_labels = {
        "INFLUENZA": "Influenza",
        "COVID-19": "Covid-19",
        "OUTRO_VIRUS": "Outro vírus",
        "OUTRO_AGENTE": "Outro agente",
        "NAO_ESPECIFICADO": "Não especificado",
    }
    records: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        try:
            raw = json.loads(item["raw_record"] or "{}")
        except (TypeError, json.JSONDecodeError):
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        records.append(
            {
                "agente": agent_labels.get(_agent_of(raw), "Não especificado"),
                "data_notif": format_br_date(raw.get("DT_NOTIFIC")),
                "bairro": raw.get("NM_BAIRRO") or raw.get("BAIRRO_REF") or "—",
                "sexo": raw.get("CS_SEXO") or "—",
                "classificacao": raw.get("CLASSI_FIN")
                if raw.get("CLASSI_FIN") not in (None, "")
                else "—",
                "evolucao": raw.get("EVOLUCAO")
                if raw.get("EVOLUCAO") not in (None, "")
                else "—",
                "semana": _epi_week_of(raw) or "—",
                "problema": item.get("error_category") or "Outros",
            }
        )

    filter_parts = [
        f"Problema: {category or 'Todos'}",
        f"Agente: {agent_labels.get(agent, 'Todos') if agent else 'Todos'}",
    ]
    if start_date:
        filter_parts.append(f"De: {format_br_date(start_date)}")
    if end_date:
        filter_parts.append(f"Até: {format_br_date(end_date)}")
    filter_parts.append(f"Gerado em: {today_br()}")
    filter_parts.append(f"Total: {len(records)} registro(s)")
    subtitle = "   |   ".join(filter_parts)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    content = build_errors_pdf(records, subtitle)
    filename = (
        f"erros-{category.lower().replace(' ', '-')}-{stamp}.pdf"
        if category
        else f"erros-todos-{stamp}.pdf"
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
