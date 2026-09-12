from srag.reporting import (
    _new_pdf_landscape,
    build_errors_pdf,
    build_neighborhood_weekly_pdf,
    format_br_date,
)


def test_build_errors_pdf_starts_with_pdf_header() -> None:
    records = [
        {
            "agente": "Covid-19",
            "data_notif": "02/03/2024",
            "bairro": "CENTRO",
            "sexo": "M",
            "classificacao": 5,
            "evolucao": 1,
            "semana": 9,
            "problema": "Bairro faltando",
        }
    ]
    subtitle = "Problema: Todos   |   Agente: Todos   |   Gerado em: 01/01/2026   |   Total: 1 registro(s)"
    content = build_errors_pdf(records, subtitle)
    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_build_errors_pdf_empty() -> None:
    content = build_errors_pdf([], "Problema: Todos")
    assert content.startswith(b"%PDF")


def test_build_neighborhood_weekly_pdf_matrix() -> None:
    rows = [
        ("AEROPORTO", [0, 3, 1], 4),
        ("CENTRO", [2, 0, 5], 7),
    ]
    content = build_neighborhood_weekly_pdf(rows, ["SE 1", "SE 2", "SE 3"], "Semanas 1 a 3")
    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_landscape_helper_keeps_dimensions() -> None:
    # Regression: fpdf2 swaps tuple sizes under orientation="L".
    default = _new_pdf_landscape()
    assert round(default.w, 1) == 297.0
    assert round(default.h, 1) == 210.0
    wide = _new_pdf_landscape(width_mm=705.0)
    assert round(wide.w, 1) == 705.0
    assert round(wide.h, 1) == 210.0


def test_format_br_date() -> None:
    assert format_br_date("2024-03-02") == "02/03/2024"
    assert format_br_date(None) == "—"
    assert format_br_date("") == "—"


def _page_count(content: bytes) -> int:
    return content.count(b"/Type /Page") - content.count(b"/Type /Pages")


def test_build_neighborhood_report_pdf_multi_page() -> None:
    from srag.reporting import build_neighborhood_report_pdf

    pages = [
        {
            "title": "T",
            "rows": [("A", [1, 2], 3)],
            "week_headers": ["SE 1", "SE 2"],
            "subtitle": "sumario",
        },
        {
            "title": "T",
            "rows": [("A", [1, 0], 1)],
            "week_headers": ["SE 1", "SE 2"],
            "subtitle": "ano",
        },
    ]
    content = build_neighborhood_report_pdf(pages)
    assert content.startswith(b"%PDF")
    assert _page_count(content) == 2


def test_counts_by_bairro_week_sums_across_years() -> None:
    import pandas as pd

    from srag.api.routers_reports import _counts_by_bairro_week

    df = pd.DataFrame(
        {
            "BAIRRO_REF": ["CENTRO", "CENTRO", "ALTO"],
            "_epi_year": [2023, 2024, 2024],
            "_epi_week_int": [10, 10, 10],
        }
    )
    assert _counts_by_bairro_week(df) == {"CENTRO": {10: 2}, "ALTO": {10: 1}}
