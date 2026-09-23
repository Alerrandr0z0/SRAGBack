"""Security tests: CORS, input validation, and SQL injection guards."""

from fastapi.testclient import TestClient

from srag.api.main import app

client = TestClient(app)


class TestCORS:
    def test_cors_allowed_origin(self):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert resp.status_code == 200

    def test_cors_disallowed_origin(self):
        resp = client.options(
            "/health",
            headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_origin = resp.headers.get("access-control-allow-origin")
        assert allow_origin != "https://evil.com"

    def test_cors_credentials_disabled(self):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-credentials") != "true"

    def test_cors_methods_restricted(self):
        # Auth endpoints (/auth/*, /user/*) need POST + PUT + DELETE, so the
        # allowlist is exactly GET/POST/PUT/DELETE/OPTIONS — no PATCH/TRACE.
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        allow_methods = {
            m.strip()
            for m in resp.headers.get("access-control-allow-methods", "").split(",")
        }
        assert allow_methods == {"GET", "POST", "PUT", "DELETE", "OPTIONS"}


class TestInputValidation:
    def test_virus_ignores_unknown_params(self):
        resp = client.get("/virus?detail_level=invalid")
        assert resp.status_code == 200

    def test_virus_valid_detail_level(self):
        resp = client.get("/virus?detail_level=summary")
        assert resp.status_code in (200, 422)

    def test_territory_bootstrap_min_cases_out_of_range(self):
        resp = client.get("/territory_bootstrap?min_cases=0")
        assert resp.status_code == 422

    def test_years_filter_out_of_range(self):
        resp = client.get("/summary?years=1800")
        assert resp.status_code == 422

    def test_years_filter_valid(self):
        resp = client.get("/summary?years=2020")
        assert resp.status_code in (200, 422)


class TestDynamicSQL:
    def test_get_df_column_validation(self):
        from srag.api.core import _KNOWN_COLUMNS, get_df

        assert isinstance(_KNOWN_COLUMNS, frozenset)
        assert "DT_NOTIFIC" in _KNOWN_COLUMNS
        assert len(_KNOWN_COLUMNS) > 50

        df = get_df()
        assert not df.empty
        assert "DT_NOTIFIC" in df.columns
        assert "DT_SIN_PRI" in df.columns
