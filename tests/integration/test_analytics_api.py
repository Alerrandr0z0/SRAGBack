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
