"""End-to-end smoke + contract tests for the lean FastAPI surface.

These tests boot the FastAPI app, inject a deterministic DataFrame via
the shared _cache fixture, and validate that:

  1. The endpoint returns 200
  2. The response shape matches the TypedDict contract
  3. The body actually contains the expected data

Lean scope (12 tópicos + sociodemográfico + auth): health, summary, trends,
virus, territory_bootstrap, laboratory_network, vaccination_profile,
citizen_bootstrap, comorbidities_pareto.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi.testclient import TestClient

from srag.api.main import app
from srag.api.types import (
    CitizenBootstrapResponse,
    LaboratoryNetworkResponse,
    SummaryResponse,
    TerritoryBootstrapResponse,
    TrendsResponse,
    VaccinationProfileResponse,
)
from tests.integration._helpers import assert_typeddict_keys

if TYPE_CHECKING:
    from httpx import Response

client = TestClient(app)


def _ok(response: Response) -> dict[str, Any]:
    assert response.status_code == 200, response.text
    return response.json()


def test_health() -> None:
    body = _ok(client.get("/health"))
    assert "status" in body


class TestSummary:
    def test_returns_summary(self, mock_srag_df) -> None:
        body = _ok(client.get("/summary"))
        assert_typeddict_keys(body, SummaryResponse)
        assert body["total"] == 15
        assert body["notification_total"] == 15
        assert body["death_count"] == 1
        assert 0.0 <= body["death_rate"] <= 100.0

    def test_empty_returns_zero_totals(self, empty_srag_df) -> None:
        body = _ok(client.get("/summary"))
        assert body["total"] == 0
        assert body["death_count"] == 0
        assert body["uti_total"] == 0


class TestTrends:
    def test_returns_trends(self, mock_srag_df) -> None:
        body = _ok(client.get("/trends"))
        assert_typeddict_keys(body, TrendsResponse)
        assert len(body["history"]) > 0

    def test_empty_returns_no_history(self, empty_srag_df) -> None:
        body = _ok(client.get("/trends"))
        assert body["history"] == []


class TestVirus:
    def test_returns_virus_distribution(self, covid_only_df) -> None:
        body = _ok(client.get("/virus"))
        assert isinstance(body, list)
        assert len(body) > 0


class TestTerritoryBootstrap:
    def test_returns_territory(self, mock_srag_df) -> None:
        body = _ok(client.get("/territory_bootstrap?min_cases=1"))
        assert_typeddict_keys(body, TerritoryBootstrapResponse)
        assert "territory" in body
        assert "bairros" in body["territory"]
        assert "zonas" in body["territory"]
        assert set(body) == {"territory"}


class TestLaboratoryNetwork:
    def test_returns_rt_pcr_summary(self, mock_srag_df) -> None:
        body = _ok(client.get("/laboratory_network"))
        assert_typeddict_keys(body, LaboratoryNetworkResponse)
        assert body["total_cases"] >= 0

    def test_empty_returns_zeros(self, empty_srag_df) -> None:
        body = _ok(client.get("/laboratory_network"))
        assert body == {"total_cases": 0}


class TestVaccinationProfile:
    def test_returns_vaccination(self, mock_srag_df) -> None:
        body = _ok(client.get("/vaccination_profile"))
        assert_typeddict_keys(body, VaccinationProfileResponse)
        assert "gripe_donut" in body
        assert "resumo" in body

    def test_empty(self, empty_srag_df) -> None:
        body = _ok(client.get("/vaccination_profile"))
        assert body == {}


class TestCitizenBootstrap:
    def test_returns_citizen_bootstrap(self, mock_srag_df) -> None:
        body = _ok(client.get("/citizen_bootstrap"))
        assert_typeddict_keys(body, CitizenBootstrapResponse)
        for key in (
            "citizen_pyramid",
            "race_profile",
            "schooling_profile",
            "risk_factors_full",
            "maternal_profile",
        ):
            assert key in body, f"missing {key} in citizen_bootstrap"

    def test_pediatric_profile_via_age_filter(self, pediatric_df) -> None:
        """Pediatric dataset should only populate bands up to 15-19 anos."""
        import re

        body = _ok(client.get("/citizen_bootstrap"))
        bands = [row["age_band"] for row in body["citizen_pyramid"]]
        populated = [
            b
            for b, row in zip(bands, body["citizen_pyramid"], strict=True)
            if row["male"] + row["female"] > 0
        ]
        assert populated, "expected at least one populated band"
        upper_bounds = [int(re.findall(r"\d+", b)[-1]) for b in populated]
        assert max(upper_bounds) <= 19, f"expected pediatric-only bands, got {populated}"


class TestComorbidities:
    def test_returns_pareto(self, mock_srag_df) -> None:
        body = _ok(client.get("/clinical/comorbidities_pareto"))
        assert isinstance(body, list)


class TestBairrosPdf:
    def test_todos_returns_summary_plus_one_page_per_year(self) -> None:
        from datetime import date

        import pandas as pd

        from srag.api.auth import UserRecord, require_admin
        from tests.integration.conftest import _clear, _inject, make_srag_row

        rows = [make_srag_row(i, DT_SIN_PRI=date(2024, 4, 25)) for i in range(4)]
        rows += [make_srag_row(i, DT_SIN_PRI=date(2023, 6, 15)) for i in range(4, 8)]
        _inject(pd.DataFrame(rows))
        app.dependency_overrides[require_admin] = lambda: UserRecord(
            id=1, cpf="00000000000", full_name="Teste", role="ADMIN"
        )
        try:
            resp = client.get("/reports/bairros/pdf")
        finally:
            app.dependency_overrides.clear()
            _clear()
        assert resp.status_code == 200, resp.text
        content = resp.content
        assert content.startswith(b"%PDF")
        pages = content.count(b"/Type /Page") - content.count(b"/Type /Pages")
        assert pages == 3

    def test_single_year_keeps_single_page(self) -> None:
        from datetime import date

        import pandas as pd

        from srag.api.auth import UserRecord, require_admin
        from tests.integration.conftest import _clear, _inject, make_srag_row

        rows = [make_srag_row(i, DT_SIN_PRI=date(2024, 4, 25)) for i in range(4)]
        _inject(pd.DataFrame(rows))
        app.dependency_overrides[require_admin] = lambda: UserRecord(
            id=1, cpf="00000000000", full_name="Teste", role="ADMIN"
        )
        try:
            resp = client.get("/reports/bairros/pdf?years=2024")
        finally:
            app.dependency_overrides.clear()
            _clear()
        assert resp.status_code == 200, resp.text
        content = resp.content
        pages = content.count(b"/Type /Page") - content.count(b"/Type /Pages")
        assert pages == 1
