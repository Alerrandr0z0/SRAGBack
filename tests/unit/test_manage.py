from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from srag.api import auth as auth_module
from srag.api.main import app

if TYPE_CHECKING:
    from collections.abc import Generator

ADMIN_CPF = "123.456.789-09"
USER_CPF = "987.654.321-00"

KNOWN_PROBLEMS = {
    "Data faltando",
    "Bairro faltando",
    "Sexo não informado",
    "Classificação faltando",
    "Evolução não informada",
}


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient]:
    engine = create_engine(f"sqlite:///{tmp_path}/dq_test.db")
    auth_module.set_engine_override(engine)
    try:
        yield TestClient(app)
    finally:
        auth_module.set_engine_override(None)
        engine.dispose()


def _auth_headers(client: TestClient, cpf: str, password: str) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"cpf": cpf, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['jwtToken']}"}


@pytest.fixture()
def admin_headers(client: TestClient) -> dict[str, str]:
    first = client.post(
        "/api/auth/register",
        json={
            "cpf": ADMIN_CPF,
            "fullName": "Admin",
            "password": "secret12",
            "confirmPassword": "secret12",
        },
    )
    assert first.status_code in (200, 201), first.text
    return _auth_headers(client, ADMIN_CPF, "secret12")


@pytest.fixture()
def user_headers(client: TestClient, admin_headers: dict[str, str]) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={
            "cpf": USER_CPF,
            "fullName": "User",
            "password": "secret12",
            "confirmPassword": "secret12",
            "role": "USER",
        },
        headers=admin_headers,
    )
    assert reg.status_code in (200, 201), reg.text
    return _auth_headers(client, USER_CPF, "secret12")


def test_manage_errors_requires_auth(client: TestClient) -> None:
    assert client.get("/api/manage/errors").status_code == 401


def test_manage_errors_forbids_non_admin(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/manage/errors", headers=user_headers)
    assert resp.status_code == 403


def test_manage_errors_lists_rows_with_problems(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    resp = client.get("/api/manage/errors", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    payload: dict[str, Any] = resp.json()
    assert payload["total"] > 0
    assert len(payload["items"]) > 0
    assert payload["page"] == 1
    assert payload["page_size"] == 20
    for item in payload["items"]:
        assert isinstance(item["raw_record"], dict)
        assert item["error_category"] in KNOWN_PROBLEMS
    labels = {c["category"] for c in payload["categories"]}
    assert labels <= KNOWN_PROBLEMS
    assert labels, "expected at least one problem category"


def test_manage_errors_category_filter_narrows(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    resp = client.get(
        "/api/manage/errors",
        params={"category": "Bairro faltando"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    payload: dict[str, Any] = resp.json()
    assert payload["total"] > 0
    for item in payload["items"]:
        assert item["error_category"] == "Bairro faltando"
        assert item["raw_record"].get("NM_BAIRRO") in (None, "")


def test_manage_errors_pagination(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    first = client.get(
        "/api/manage/errors",
        params={"page": 1, "page_size": 5},
        headers=admin_headers,
    )
    second = client.get(
        "/api/manage/errors",
        params={"page": 2, "page_size": 5},
        headers=admin_headers,
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["page_size"] == 5
    assert second.json()["page"] == 2
    ids_first = {i["id"] for i in first.json()["items"]}
    ids_second = {i["id"] for i in second.json()["items"]}
    assert ids_first.isdisjoint(ids_second)


def test_manage_errors_pdf_requires_auth(client: TestClient) -> None:
    assert client.get("/api/manage/errors/pdf").status_code == 401


def test_manage_errors_pdf_returns_pdf(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    resp = client.get("/api/manage/errors/pdf", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
