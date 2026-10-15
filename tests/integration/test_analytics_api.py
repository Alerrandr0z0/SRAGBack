"""API tests for the "Gráficos analíticos" endpoints (/analytics/*)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from srag.api.main import app

client = TestClient(app)


class TestClinicalFlowEndpoint:
    def test_returns_nodes_and_links(self, mock_srag_df) -> None:
        resp = client.get("/analytics/clinical_flow")
        assert resp.status_code == 200
        body = resp.json()
        assert body["nodes"] and body["links"]
        assert {"source", "target", "value", "pct"} <= set(body["links"][0])

    def test_api_prefix_is_also_registered(self, mock_srag_df) -> None:
        assert client.get("/api/analytics/clinical_flow").status_code == 200

    def test_empty_data(self, empty_srag_df) -> None:
        resp = client.get("/analytics/clinical_flow")
        assert resp.status_code == 200
        assert resp.json() == {"nodes": [], "links": []}

    def test_base_filter_narrows_the_flow_to_deaths(self, mock_srag_df) -> None:
        body = client.get("/analytics/clinical_flow", params={"base": "obitos"}).json()
        final_nodes = {link["target"] for link in body["links"]} & {"Cura", "Óbito", "Em Aberto"}
        assert final_nodes == {"Óbito"}

    def test_invalid_filter_value_is_rejected(self, mock_srag_df) -> None:
        assert client.get("/analytics/clinical_flow", params={"base": "x"}).status_code == 422


class TestOddsRatioEndpoint:
    def test_returns_one_row_per_risk_factor(self, mock_srag_df) -> None:
        resp = client.get("/analytics/comorbidities_odds_ratio")
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 14
        assert {"name", "value", "deaths", "lethality", "odds_ratio"} <= set(rows[0])

    def test_empty_data(self, empty_srag_df) -> None:
        resp = client.get("/analytics/comorbidities_odds_ratio")
        assert resp.status_code == 200
        assert resp.json() == []


class TestSymptomsSignatureEndpoint:
    def test_default_profile(self, mock_srag_df) -> None:
        resp = client.get("/analytics/symptoms_signature")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body["matrices"]) == {"covid", "gripe", "vsr"}
        assert body["bands"] == ["Criança", "Adolescente", "Adulto", "Idoso"]

    def test_profile_param(self, mock_srag_df) -> None:
        body = client.get("/analytics/symptoms_signature", params={"profile": "idoso"}).json()
        assert body["bands"] == ["60-69 anos", "70-79 anos", "80+ anos"]

    def test_invalid_profile_is_rejected(self, mock_srag_df) -> None:
        resp = client.get("/analytics/symptoms_signature", params={"profile": "bebe"})
        assert resp.status_code == 422

    def test_empty_data(self, empty_srag_df) -> None:
        resp = client.get("/analytics/symptoms_signature")
        assert resp.status_code == 200
        assert resp.json() == {"labels": [], "bands": [], "matrices": {}}


class TestIcuAccessEndpoint:
    def test_response_shape(self, mock_srag_df) -> None:
        resp = client.get("/analytics/icu_access")
        assert resp.status_code == 200
        body = resp.json()
        assert {"granularity", "limit_days", "min_cases", "summary", "periods"} <= set(body)
        assert body["granularity"] == "year"
        assert body["limit_days"] == 3

    def test_granularity_param(self, mock_srag_df) -> None:
        body = client.get("/analytics/icu_access", params={"granularity": "month"}).json()
        assert body["granularity"] == "month"

    def test_invalid_granularity_is_rejected(self, mock_srag_df) -> None:
        resp = client.get("/analytics/icu_access", params={"granularity": "semana"})
        assert resp.status_code == 422

    def test_empty_data(self, empty_srag_df) -> None:
        body = client.get("/analytics/icu_access").json()
        assert body["summary"]["total"] == 0
        assert body["periods"] == []


class TestDiagnosticMethodsEndpoint:
    def test_response_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/diagnostic_methods").json()
        assert {"granularity", "min_cases", "summary", "periods"} <= set(body)
        assert {"total", "rt_pcr", "laboratory_pct"} <= set(body["summary"])

    def test_invalid_granularity_is_rejected(self, mock_srag_df) -> None:
        params = {"granularity": "semana"}
        assert client.get("/analytics/diagnostic_methods", params=params).status_code == 422

    def test_empty_data(self, empty_srag_df) -> None:
        body = client.get("/analytics/diagnostic_methods").json()
        assert body["summary"]["total"] == 0
        assert body["periods"] == []


class TestNosocomialRiskEndpoint:
    def test_response_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/nosocomial_risk", params={"granularity": "quarter"}).json()
        assert body["granularity"] == "quarter"
        assert {"mean_pct", "alert_limit_pct", "summary", "periods"} <= set(body)
        assert {"nosocomial", "community"} == set(body["summary"]["lethality"])

    def test_invalid_granularity_is_rejected(self, mock_srag_df) -> None:
        params = {"granularity": "dia"}
        assert client.get("/analytics/nosocomial_risk", params=params).status_code == 422

    def test_empty_data(self, empty_srag_df) -> None:
        body = client.get("/analytics/nosocomial_risk").json()
        assert body["summary"]["known"] == 0
        assert body["periods"] == []


class TestDiagnosticLethalityEndpoint:
    def test_response_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/diagnostic_lethality").json()
        assert {"min_resolved", "overall", "methods", "hidden"} <= set(body)

    def test_empty_data(self, empty_srag_df) -> None:
        body = client.get("/analytics/diagnostic_lethality").json()
        assert body["methods"] == []
        assert body["overall"]["cfr"] is None


class TestLabEndpoints:
    def test_lab_performance_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/lab_performance").json()
        assert {"total", "result", "collection", "rt_pcr_latency", "turnaround"} <= set(body)
        assert body["rt_pcr_latency"]["target_days"] == 7

    def test_sample_positivity_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/sample_positivity").json()
        assert {"min_tested", "overall", "types", "hidden"} <= set(body)

    def test_antiviral_windows_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/antiviral_windows").json()
        assert {"treated", "with_dates", "median_days", "windows"} <= set(body)

    def test_imaging_severity_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/imaging_severity").json()
        assert {"min_cases", "xray", "ct"} <= set(body)
        assert {"rows", "hidden"} == set(body["xray"])

    def test_empty_data(self, empty_srag_df) -> None:
        assert client.get("/analytics/lab_performance").json()["total"] == 0
        assert client.get("/analytics/sample_positivity").json()["types"] == []
        assert client.get("/analytics/antiviral_windows").json()["windows"] == []
        assert client.get("/analytics/imaging_severity").json()["ct"]["rows"] == []

    def test_filters_are_validated(self, mock_srag_df) -> None:
        for path in ("lab_performance", "sample_positivity", "antiviral_windows"):
            assert client.get(f"/analytics/{path}", params={"base": "x"}).status_code == 422


class TestNotificationDelayEndpoint:
    def test_response_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/notification_delay").json()
        assert {"limit_days", "overall", "bairros", "hidden_count", "min_cases"} <= set(body)
        assert body["limit_days"] == 7

    def test_empty_data(self, empty_srag_df) -> None:
        body = client.get("/analytics/notification_delay").json()
        assert body["bairros"] == []
        assert body["overall"]["median_days"] is None

    def test_filters_are_validated(self, mock_srag_df) -> None:
        assert client.get("/analytics/notification_delay", params={"base": "x"}).status_code == 422
