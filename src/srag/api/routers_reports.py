"""Report routers: PDF exports (ADMIN only).

Port of the reference ``NeighborhoodWeeklyPdfReportService``: per-bairro
weekly matrix honoring the common dashboard filters plus week range/scope.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from srag.api.auth import UserRecord, require_admin
from srag.api.core import apply_surveillance_filters, get_df
from srag.api.dependencies import CommonFiltersDep  # noqa: TC001 - FastAPI resolves at runtime
from srag.data.analytics import apply_global_filters, normalize_territory_labels
from srag.reporting import (
    build_neighborhood_report_pdf,
    build_neighborhood_weekly_pdf,
)
from srag.utils.epi_weeks import compute_epi_week_columns

router = APIRouter(tags=["reports"])

AGENT_LABELS = {
    "INFLUENZA": "Influenza",
    "COVID-19": "Covid-19",
    "VSR": "VSR",
    "OUTRO_VIRUS": "Outro vírus",
    "NAO_ESPECIFICADO": "Não especificado",
}


@router.get("/reports/semanas")
def report_weeks(
    admin: Annotated[UserRecord, Depends(require_admin)],
    years: Annotated[list[int] | None, Query()] = None,
) -> dict[str, int]:
    """Min/max epidemiological week available (ADMIN only).

    Single year → ``{"year": Y, "min_week": 1, "max_week": 52|53}`` from the
    data (SIVEP years may have 53 weeks). Used to bound the report range.
    """
    df = get_df()
    if years:
        df = apply_surveillance_filters(df, years=years)
    if df.empty or "DT_SIN_PRI" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma semana epidemiológica foi encontrada para os filtros informados.",
        )
    epi = compute_epi_week_columns(pd.to_datetime(df["DT_SIN_PRI"], errors="coerce"))
    weeks = epi.loc[epi["_epi_week_int"] > 0, "_epi_week_int"].astype(int)
    if weeks.empty:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma semana epidemiológica foi encontrada para os filtros informados.",
        )
    year = int(years[0]) if years and len(years) == 1 else 0
    return {"year": year, "min_week": int(weeks.min()), "max_week": int(weeks.max())}


@router.get("/reports/bairros/pdf")
def bairros_pdf(
    admin: Annotated[UserRecord, Depends(require_admin)],
    filters: CommonFiltersDep,
    semana_inicial: int | None = Query(None, ge=1, le=53),
    semana_final: int | None = Query(None, ge=1, le=53),
) -> Response:
    """Per-bairro weekly-matrix PDF (port of the reference neighborhood report)."""
    del admin
    if semana_final is not None and semana_final < 1:
        raise HTTPException(
            status_code=400,
            detail="Informe uma semana epidemiológica final maior ou igual a 1.",
        )
    start_week = semana_inicial if semana_inicial is not None else 1
    if semana_final is not None and start_week > semana_final:
        raise HTTPException(
            status_code=400,
            detail="A semana inicial deve ser menor ou igual à semana final.",
        )
    df = get_df()
    df = apply_global_filters(df, filters.bairros)
    df = apply_surveillance_filters(df, filters.years, filters.agents, filters.classi)

    # Regra do bairro oficial (mesma da tabela): só OFFICIAL_BAIRROS é bairro.
    df = normalize_territory_labels(df)

    if df.empty or "DT_SIN_PRI" not in df.columns or "BAIRRO_REF" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma semana epidemiológica foi encontrada para os filtros informados.",
        )
    scoped = df.copy()
    epi = compute_epi_week_columns(pd.to_datetime(scoped["DT_SIN_PRI"], errors="coerce"))
    scoped["_epi_year"] = epi["_epi_year"].to_numpy()
    scoped["_epi_week_int"] = epi["_epi_week_int"].to_numpy()
    scoped = scoped[(scoped["_epi_year"] > 0) & (scoped["_epi_week_int"] > 0)]
    if scoped.empty:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma semana epidemiológica foi encontrada para os filtros informados.",
        )

    max_available_week = int(scoped["_epi_week_int"].max())
    end_week = semana_final if semana_final is not None else max_available_week
    if end_week > max_available_week:
        raise HTTPException(
            status_code=400,
            detail=(
                "A semana epidemiológica solicitada deve ser menor ou igual à maior "
                "semana disponível no banco para os filtros informados. "
                f"Semana disponível até: {max_available_week}."
            ),
        )
    scoped = scoped[
        (scoped["_epi_week_int"] >= start_week) & (scoped["_epi_week_int"] <= end_week)
    ]

    base_parts: list[str] = []
    if filters.agents:
        base_parts.append(
            "Agente(s) " + ", ".join(AGENT_LABELS.get(a, a) for a in filters.agents)
        )
    base_parts.append("Escopo Dados notificados")
    base_suffix = " | ".join(base_parts)

    years_in_data = sorted({int(y) for y in scoped["_epi_year"].unique()})
    if len(years_in_data) == 1:
        content = _single_year_pdf(scoped, start_week, end_week, filters, base_suffix)
    else:
        content = _all_years_pdf(
            scoped, start_week, end_week, filters, base_suffix, years_in_data
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio-bairros-{stamp}.pdf"
        },
    )


def _clean_bairro_name(raw: object) -> str | None:
    name = str(raw).strip()
    if not name or name.upper() in ("NAN", "NONE", "NULL"):
        return None
    return name


def _counts_by_bairro_week(frame: pd.DataFrame) -> dict[str, dict[int, int]]:
    """Sum cases per (bairro, epi week).

    Pure helper (unit-testable): backs both the all-years summary page and
    the per-year pages.
    """
    counts: dict[str, dict[int, int]] = {}
    for bairro, sub in frame.groupby("BAIRRO_REF"):
        name = _clean_bairro_name(bairro)
        if name is None:
            continue
        per_week = counts.setdefault(name, {})
        week_counts = sub["_epi_week_int"].value_counts()
        weeks = week_counts.index.tolist()
        totals = week_counts.tolist()
        for w, total in zip(weeks, totals, strict=True):
            per_week[int(w)] = per_week.get(int(w), 0) + int(total)
    return counts


def _matrix_rows(
    counts: dict[str, dict[int, int]], weeks: list[int]
) -> list[tuple[str, list[int], int]]:
    rows: list[tuple[str, list[int], int]] = []
    for bairro in sorted(counts, key=str.lower):
        values = [counts[bairro].get(w, 0) for w in weeks]
        rows.append((bairro, values, sum(values)))
    return rows


def _single_year_pdf(
    scoped: pd.DataFrame,
    start_week: int,
    end_week: int,
    filters: CommonFiltersDep,
    base_suffix: str,
) -> bytes:
    """Single-year matrix (legacy behavior, observed SE columns)."""
    columns = sorted(
        {
            (int(y), int(w))
            for y, w in zip(
                scoped["_epi_year"], scoped["_epi_week_int"], strict=True
            )
        }
    )
    if not columns:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma semana epidemiológica foi encontrada para os filtros informados.",
        )
    grouped = scoped.groupby("BAIRRO_REF")
    counts: dict[str, dict[int, int]] = {}
    for bairro, sub in grouped:
        name = _clean_bairro_name(bairro)
        if name is None:
            continue
        week_counts = sub["_epi_week_int"].value_counts()
        weeks = week_counts.index.tolist()
        totals = week_counts.tolist()
        counts[name] = {
            int(w): int(c) for w, c in zip(weeks, totals, strict=True)
        }
    weeks = [w for _, w in columns]
    week_headers = [f"SE {w}" for w in weeks]
    subtitle_parts = [f"Semanas {start_week} a {end_week}"]
    if filters.years:
        subtitle_parts.append(
            "Ano(s) " + ", ".join(str(y) for y in sorted(filters.years))
        )
    subtitle_parts.append(base_suffix)
    return build_neighborhood_weekly_pdf(
        _matrix_rows(counts, weeks), week_headers, " | ".join(subtitle_parts)
    )


def _all_years_pdf(
    scoped: pd.DataFrame,
    start_week: int,
    end_week: int,
    filters: CommonFiltersDep,
    base_suffix: str,
    years_in_data: list[int],
) -> bytes:
    """Multi-year mode: summary page plus one page per year (same week range)."""
    del filters
    title = "Relatório por bairro e semana epidemiológica"
    weeks = list(range(start_week, end_week + 1))
    week_headers = [f"SE {w}" for w in weeks]

    summary_counts = _counts_by_bairro_week(scoped)
    year_span = f"{years_in_data[0]}-{years_in_data[-1]}"
    pages: list[dict[str, object]] = [
        {
            "title": title,
            "rows": _matrix_rows(summary_counts, weeks),
            "week_headers": week_headers,
            "subtitle": (
                f"Somatório de todos os anos ({year_span}) por semana epidemiológica"
                f" | Semanas {start_week} a {end_week} | {base_suffix}"
            ),
        }
    ]
    for year in years_in_data:
        frame = scoped[scoped["_epi_year"] == year]
        pages.append(
            {
                "title": title,
                "rows": _matrix_rows(_counts_by_bairro_week(frame), weeks),
                "week_headers": week_headers,
                "subtitle": (
                    f"Ano {year} | Semanas {start_week} a {end_week} | {base_suffix}"
                ),
            }
        )
    return build_neighborhood_report_pdf(pages)
