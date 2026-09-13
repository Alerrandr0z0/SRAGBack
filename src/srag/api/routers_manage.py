"""Manage routers (ADMIN only): data-quality review (read-only)."""

from __future__ import annotations

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


DQ_PROBLEMS: tuple[str, ...] = (
    "Data faltando",
    "Bairro faltando",
    "Sexo não informado",
    "Classificação faltando",
    "Evolução não informada",
)

DQ_CONDITIONS: dict[str, str] = {
    "Data faltando": "(DT_NOTIFIC IS NULL OR DT_NOTIFIC = '')",
    "Bairro faltando": "(NM_BAIRRO IS NULL OR NM_BAIRRO = '')",
    "Sexo não informado": "(CS_SEXO IS NULL OR CS_SEXO = '' OR CS_SEXO IN ('I', '9'))",
    "Classificação faltando": "(CLASSI_FIN IS NULL OR CLASSI_FIN = '')",
    "Evolução não informada": "(EVOLUCAO IS NULL OR EVOLUCAO = '')",
}

DQ_DETAIL: dict[str, str] = {
    "Data faltando": "DT_NOTIFIC ausente",
    "Bairro faltando": "NM_BAIRRO ausente",
    "Sexo não informado": "CS_SEXO não informado ou ignorado",
    "Classificação faltando": "CLASSI_FIN ausente",
    "Evolução não informada": "EVOLUCAO não informada",
}


def _dq_problems_of(raw: dict[str, Any]) -> list[str]:
    found: list[str] = []
    if raw.get("DT_NOTIFIC") in (None, ""):
        found.append("Data faltando")
    if raw.get("NM_BAIRRO") in (None, ""):
        found.append("Bairro faltando")
    if raw.get("CS_SEXO") in (None, "", "I", "9"):
        found.append("Sexo não informado")
    if raw.get("CLASSI_FIN") in (None, ""):
        found.append("Classificação faltando")
    if raw.get("EVOLUCAO") in (None, ""):
        found.append("Evolução não informada")
    return found


def _dq_clauses(
    category: str | None,
    start_date: str | None,
    end_date: str | None,
    agent: str | None = None,
) -> tuple[str, list[Any]]:
    has_any = " OR ".join(DQ_CONDITIONS[label] for label in DQ_PROBLEMS)
    clauses: list[str] = [f"({has_any})"]
    params: list[Any] = []
    if category and category in DQ_CONDITIONS:
        clauses.append(DQ_CONDITIONS[category])
    if start_date:
        clauses.append("DT_NOTIFIC >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("DT_NOTIFIC <= ?")
        params.append(end_date)
    if agent:
        codes = [code for code, name in AGENT_BY_CLASSI.items() if name == agent]
        if codes:
            placeholders = ",".join("?" for _ in codes)
            agent_clause = f"CAST(CLASSI_FIN AS INTEGER) IN ({placeholders})"
            if agent == "NAO_ESPECIFICADO":
                agent_clause = f"({agent_clause} OR CLASSI_FIN IS NULL)"
            clauses.append(agent_clause)
            params.extend(codes)
    return f"WHERE {' AND '.join(clauses)}", params


def _dq_categories(
    conn: sqlite3.Connection, start_date: str | None, end_date: str | None
) -> list[dict[str, Any]]:
    sums = ", ".join(
        f"SUM(CASE WHEN {DQ_CONDITIONS[label]} THEN 1 ELSE 0 END)"
        for label in DQ_PROBLEMS
    )
    clauses: list[str] = []
    params: list[Any] = []
    if start_date:
        clauses.append("DT_NOTIFIC >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("DT_NOTIFIC <= ?")
        params.append(end_date)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    row = conn.execute(
        f"SELECT {sums} FROM casos_srag {where}",  # nosec B608
        params,
    ).fetchone()
    values = list(row) if row else [0] * len(DQ_PROBLEMS)
    return [
        {"category": label, "count": int(values[i] or 0)}
        for i, label in enumerate(DQ_PROBLEMS)
        if int(values[i] or 0) > 0
    ]


def _dq_row_to_item(row: sqlite3.Row, category: str | None) -> dict[str, Any]:
    raw = dict(row)
    raw.pop("rowid", None)
    problems = _dq_problems_of(raw)
    label = category if category in problems else (problems[0] if problems else "Outros")
    return {
        "id": row["rowid"],
        "raw_record": raw,
        "error_category": label,
        "error_detail": DQ_DETAIL.get(label, label),
        "semana_epidemiologica": _epi_week_of(raw),
        "agente": _agent_of(raw),
    }


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
    """Paginated data-quality list from casos_srag (ADMIN only, read-only)."""
    del admin
    with _connect() as conn:
        where, params = _dq_clauses(category, start_date, end_date, agent)
        total = conn.execute(
            f"SELECT count(*) AS n FROM casos_srag {where}",  # nosec B608
            params,
        ).fetchone()["n"]
        cursor = conn.execute(
            "SELECT rowid, * "  # nosec B608
            f"FROM casos_srag {where} "
            "ORDER BY rowid LIMIT ? OFFSET ?",
            [*params, page_size, (page - 1) * page_size],
        )
        items = [_dq_row_to_item(r, category) for r in cursor.fetchall()]
        categories = _dq_categories(conn, start_date, end_date)
    return sanitize_data(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "categories": categories,
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
    """Data-quality report PDF honoring the active filters (ADMIN only)."""
    del admin
    from datetime import datetime

    from srag.reporting import build_errors_pdf, format_br_date, today_br

    with _connect() as conn:
        where, params = _dq_clauses(category, start_date, end_date, agent)
        cursor = conn.execute(
            "SELECT rowid, * "  # nosec B608
            f"FROM casos_srag {where} "
            "ORDER BY rowid LIMIT 2000",
            params,
        )
        items = [_dq_row_to_item(r, category) for r in cursor.fetchall()]

    agent_labels = {
        "INFLUENZA": "Influenza",
        "COVID-19": "Covid-19",
        "OUTRO_VIRUS": "Outro vírus",
        "OUTRO_AGENTE": "Outro agente",
        "NAO_ESPECIFICADO": "Não especificado",
    }
    records: list[dict[str, Any]] = []
    for item in items:
        raw = item["raw_record"]
        records.append(
            {
                "agente": agent_labels.get(str(item["agente"]), "Não especificado"),
                "data_notif": format_br_date(raw.get("DT_NOTIFIC")),
                "bairro": raw.get("NM_BAIRRO") or raw.get("BAIRRO_REF") or "—",
                "sexo": raw.get("CS_SEXO") or "—",
                "classificacao": raw.get("CLASSI_FIN")
                if raw.get("CLASSI_FIN") not in (None, "")
                else "—",
                "evolucao": raw.get("EVOLUCAO")
                if raw.get("EVOLUCAO") not in (None, "")
                else "—",
                "semana": item["semana_epidemiologica"] or "—",
                "problema": item["error_category"],
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
