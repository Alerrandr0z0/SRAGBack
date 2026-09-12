"""PDF report generators (port of the reference report services).

Mirrors ``NeighborhoodWeeklyPdfReportService`` and ``ErrorsPdfReportService``
(OpenPDF) using fpdf2: A4 landscape, 24pt margins, Helvetica titles,
white-on-``(41, 76, 122)`` headers, and the same subtitles/column layouts.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from fpdf import FPDF

if TYPE_CHECKING:
    from collections.abc import Sequence

HEADER_BG = (41, 76, 122)
_MARGIN_MM = 24 / 2.8346  # 24pt, like the reference
_PT = 1 / 2.8346


def pdf_text(value: object) -> str:
    """Sanitize text to latin-1 (built-in PDF core fonts)."""
    return str(value if value is not None else "—").encode("latin-1", "replace").decode(
        "latin-1"
    )


def _new_pdf_landscape(width_mm: float | None = None) -> FPDF:
    # NOTE: fpdf2 swaps tuple dimensions under orientation="L", so wide
    # custom pages must use orientation="P" with (width, height) order.
    if width_mm is None:
        pdf = FPDF(orientation="L", unit="mm", format="A4")
    else:
        pdf = FPDF(orientation="P", unit="mm", format=(width_mm, 210))
    pdf.set_margins(_MARGIN_MM, _MARGIN_MM, _MARGIN_MM)
    pdf.set_auto_page_break(True, _MARGIN_MM)
    pdf.add_page()
    return pdf


def _title_block(pdf: FPDF, title: str, subtitle: str, subtitle_size: int = 9) -> None:
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, pdf_text(title), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", subtitle_size)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 5, pdf_text(subtitle), align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(12 * _PT)


def _header_row(pdf: FPDF, headers: Sequence[str], widths: Sequence[float], size: float) -> None:
    pdf.set_font("Helvetica", "B", size)
    pdf.set_fill_color(*HEADER_BG)
    pdf.set_text_color(255, 255, 255)
    for width, header in zip(widths, headers, strict=True):
        pdf.cell(width, 8, pdf_text(header), border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)


def _body_row(
    pdf: FPDF,
    values: Sequence[Any],
    widths: Sequence[float],
    aligns: Sequence[str],
    size: int,
    height: float = 7,
    bold_first: bool = False,
) -> None:
    pdf.set_font("Helvetica", "B" if bold_first else "", size)
    for index, (width, value, align) in enumerate(
        zip(widths, values, aligns, strict=True)
    ):
        if index == 0 and bold_first:
            pdf.set_font("Helvetica", "B", size)
        elif bold_first:
            pdf.set_font("Helvetica", "", size)
        pdf.cell(width, height, pdf_text(value), border=1, align=align)
    pdf.ln()


def _proportional_widths(weights: Sequence[float], usable_mm: float) -> list[float]:
    total = sum(weights)
    return [w / total * usable_mm for w in weights]


def usable_width_mm(pdf: FPDF) -> float:
    """Usable page width in mm (page width minus left/right margins)."""
    return pdf.w - pdf.l_margin - pdf.r_margin


# ------------------------------------------------------- errors report ---


def build_errors_pdf(
    records: Sequence[dict[str, Any]],
    subtitle: str,
) -> bytes:
    """Port of ``ErrorsPdfReportService``.

    records: dicts with keys ``agente, data_notif, bairro, sexo,
    classificacao, evolucao, semana, problema`` (pre-formatted strings).
    """
    pdf = _new_pdf_landscape()
    _title_block(pdf, "Relatório — Notificações com Erros", subtitle, subtitle_size=9)

    headers = [
        "Agente",
        "Data Notif.",
        "Bairro",
        "Sexo",
        "Classificação",
        "Evolução",
        "Sem. Epid.",
        "Problema",
    ]
    widths = _proportional_widths([2, 2, 2.5, 1.5, 2.5, 2, 1.5, 3], usable_width_mm(pdf))
    aligns = ["LEFT", "CENTER", "LEFT", "CENTER", "LEFT", "LEFT", "CENTER", "LEFT"]
    _header_row(pdf, headers, widths, size=8)

    if not records:
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(sum(widths), 8, pdf_text("Sem registros para os filtros selecionados."), border=1)
        pdf.ln()
    for record in records:
        _body_row(
            pdf,
            [
                record.get("agente"),
                record.get("data_notif"),
                record.get("bairro"),
                record.get("sexo"),
                record.get("classificacao"),
                record.get("evolucao"),
                record.get("semana"),
                record.get("problema"),
            ],
            widths,
            aligns,
            size=8,
        )
    return bytes(pdf.output())


def format_br_date(iso: object) -> str:
    """Format an ISO ``YYYY-MM-DD`` value as ``DD/MM/YYYY`` (passthrough otherwise)."""
    text = str(iso or "")
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return f"{text[8:10]}/{text[5:7]}/{text[0:4]}"
    return text or "—"


def today_br() -> str:
    """Today's date as ``DD/MM/YYYY`` (report subtitle stamp)."""
    return datetime.now().strftime("%d/%m/%Y")


# ------------------------------------------- neighborhood weekly report ---


def _matrix_page_width_mm(num_semanas: int) -> float:
    # Dynamic page width, like the reference: max(A4-landscape, 230 + n*34 pt).
    return max(297.0, (230 + num_semanas * 34) / 2.8346)


def _render_matrix_page(
    pdf: FPDF,
    title: str,
    rows: Sequence[tuple[str, Sequence[int], int]],
    week_headers: Sequence[str],
    subtitle: str,
) -> None:
    num_semanas = len(week_headers)
    body_size = 7 if num_semanas > 20 else 8
    header_size = 7.5 if num_semanas > 20 else 9

    _title_block(pdf, title, subtitle, subtitle_size=10)

    weights: list[float] = [5.2, *([1.8] * num_semanas), 2.0]
    widths = _proportional_widths(weights, usable_width_mm(pdf))
    headers = ["Bairro", *week_headers, "Total"]
    _header_row(pdf, headers, widths, size=header_size)

    aligns = ["LEFT", *(["CENTER"] * num_semanas), "CENTER"]
    for bairro, counts, total in rows:
        _body_row(
            pdf,
            [bairro, *counts, total],
            widths,
            aligns,
            size=body_size,
        )


def build_neighborhood_weekly_pdf(
    rows: Sequence[tuple[str, Sequence[int], int]],
    week_headers: Sequence[str],
    subtitle: str,
) -> bytes:
    """Port of ``NeighborhoodWeeklyPdfReportService``.

    rows: ``(bairro, [counts aligned with week_headers], total)`` sorted
    alphabetically.
    """
    pdf = _new_pdf_landscape(width_mm=_matrix_page_width_mm(len(week_headers)))
    _render_matrix_page(
        pdf, "Relatório por bairro e semana epidemiológica", rows, week_headers, subtitle
    )
    return bytes(pdf.output())


def build_neighborhood_report_pdf(pages: Sequence[dict[str, Any]]) -> bytes:
    """Multi-page neighborhood report (summary + one page per year).

    pages: dicts with ``title, rows, week_headers, subtitle``. Each page is
    sized for its own matrix (fpdf2 allows per-page formats).
    """
    if not pages:
        raise ValueError("pages must not be empty")
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(_MARGIN_MM, _MARGIN_MM, _MARGIN_MM)
    pdf.set_auto_page_break(True, _MARGIN_MM)
    for page in pages:
        headers = page["week_headers"]
        pdf.add_page(format=(_matrix_page_width_mm(len(headers)), 210))
        _render_matrix_page(
            pdf, page["title"], page["rows"], headers, page["subtitle"]
        )
    return bytes(pdf.output())
