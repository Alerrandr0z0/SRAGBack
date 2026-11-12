"""API tests for the "Gráficos analíticos" endpoints (/analytics/*)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from srag.api.main import app

client = TestClient(app)


class TestSeverityCascadeEndpoint:
    def test_returns_the_four_steps(self, mock_srag_df) -> None:
        resp = client.get("/analytics/severity_cascade")
        assert resp.status_code == 200
        body = resp.json()
        assert [step["key"] for step in body["steps"]] == [
            "notified",
            "hospitalized",
            "icu",
            "invasive_ventilation",
        ]
        assert body["steps"][0]["pct"] == 100.0
        assert {"cases", "deaths", "lethality", "reliable"} <= set(body["steps"][0])

    def test_api_prefix_is_also_registered(self, mock_srag_df) -> None:
        assert client.get("/api/analytics/severity_cascade").status_code == 200

    def test_empty_data(self, empty_srag_df) -> None:
        resp = client.get("/analytics/severity_cascade")
        assert resp.status_code == 200
        assert resp.json() == {"total": 0, "steps": []}

    def test_base_filter_narrows_the_cascade(self, mock_srag_df) -> None:
        everyone = client.get("/analytics/severity_cascade").json()["total"]
        deaths = client.get("/analytics/severity_cascade", params={"base": "obitos"}).json()
        assert deaths["total"] <= everyone

    def test_invalid_filter_value_is_rejected(self, mock_srag_df) -> None:
        assert client.get("/analytics/severity_cascade", params={"base": "x"}).status_code == 422


class TestWarningSignsEndpoint:
    def test_returns_signs_with_and_without(self, mock_srag_df) -> None:
        resp = client.get("/analytics/warning_signs")
        assert resp.status_code == 200
        body = resp.json()
        assert {sign["key"] for sign in body["signs"]} == {"dispneia", "desc_resp", "saturacao"}
        assert {"lethality", "lethality_without", "reliable"} <= set(body["signs"][0])

    def test_empty_data(self, empty_srag_df) -> None:
        resp = client.get("/analytics/warning_signs")
        assert resp.status_code == 200
        assert resp.json() == {"baseline": None, "signs": []}


class TestRiskFactorLoadEndpoint:
    def test_returns_four_buckets(self, mock_srag_df) -> None:
        resp = client.get("/analytics/risk_factor_load")
        assert resp.status_code == 200
        body = resp.json()
        assert [bucket["key"] for bucket in body["buckets"]] == ["0", "1", "2", "3+"]
        assert body["factors"]

    def test_empty_data(self, empty_srag_df) -> None:
        resp = client.get("/analytics/risk_factor_load")
        assert resp.status_code == 200
        assert resp.json() == {"baseline": None, "factors": [], "buckets": []}


class TestSymptomsByAgentEndpoint:
    def test_default_profile(self, mock_srag_df) -> None:
        resp = client.get("/analytics/symptoms_by_agent")
        assert resp.status_code == 200
        body = resp.json()
        assert [agent["key"] for agent in body["agents"]] == ["covid", "gripe", "vsr"]
        assert len(body["symptoms"]) == len(body["agents"][0]["pct"])

    def test_profile_param(self, mock_srag_df) -> None:
        resp = client.get("/analytics/symptoms_by_agent", params={"profile": "idoso"})
        assert resp.status_code == 200

    def test_invalid_profile_is_rejected(self, mock_srag_df) -> None:
        resp = client.get("/analytics/symptoms_by_agent", params={"profile": "bebe"})
        assert resp.status_code == 422

    def test_empty_data(self, empty_srag_df) -> None:
        resp = client.get("/analytics/symptoms_by_agent")
        assert resp.status_code == 200
        assert resp.json() == {"symptoms": [], "agents": []}


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


class TestCitizenEndpoints:
    def test_maternal_outcomes_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/maternal_outcomes").json()
        assert {"gestantes_total", "puerperas_total", "min_cases", "groups"} <= set(body)

    def test_occupation_profile_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/occupation_profile").json()
        assert {"total", "informed", "items"} <= set(body)

    def test_animal_contact_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/animal_contact").json()
        assert {"total", "ignored", "items"} <= set(body)

    def test_covid_immunization_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/covid_immunization").json()
        assert {"manufacturers", "dose_stages"} <= set(body)

    def test_empty_data(self, empty_srag_df) -> None:
        assert client.get("/analytics/maternal_outcomes").json()["groups"] == []
        assert client.get("/analytics/occupation_profile").json()["items"] == []
        assert client.get("/analytics/covid_immunization").json()["manufacturers"] == []

    def test_filters_are_validated(self, mock_srag_df) -> None:
        for path in ("maternal_outcomes", "occupation_profile", "animal_contact"):
            assert client.get(f"/analytics/{path}", params={"base": "x"}).status_code == 422


class TestUnitEndpoints:
    def test_notifying_units_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/notifying_units").json()
        assert {"total", "unidentified", "items"} <= set(body)

    def test_unit_notification_delay_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/unit_notification_delay").json()
        assert {"limit_days", "min_cases", "units", "hidden_count"} <= set(body)
        assert body["limit_days"] == 7

    def test_hospital_stay_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/hospital_stay").json()
        assert {"closed", "median_days", "bed_days", "curve"} <= set(body)

    def test_vaccine_journey_shape(self, mock_srag_df) -> None:
        body = client.get("/analytics/vaccine_journey").json()
        assert {"min_cases", "stages"} <= set(body)

    def test_empty_data(self, empty_srag_df) -> None:
        assert client.get("/analytics/notifying_units").json()["items"] == []
        assert client.get("/analytics/unit_notification_delay").json()["units"] == []
        assert client.get("/analytics/hospital_stay").json()["closed"] == 0
        assert client.get("/analytics/vaccine_journey").json()["stages"] == []

    def test_filters_are_validated(self, mock_srag_df) -> None:
        for path in ("notifying_units", "unit_notification_delay", "hospital_stay"):
            assert client.get(f"/analytics/{path}", params={"base": "x"}).status_code == 422
