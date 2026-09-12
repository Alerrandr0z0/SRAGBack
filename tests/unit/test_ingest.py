from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from srag.api import auth as auth_module
from srag.api.main import app

if TYPE_CHECKING:
    from collections.abc import Generator

ADMIN_CPF = "123.456.789-09"
USER_CPF = "987.654.321-00"


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient]:
    engine = create_engine(f"sqlite:///{tmp_path}/ingest_test.db")
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


def test_status_requires_auth(client: TestClient) -> None:
    assert client.get("/api/ingest/status").status_code == 401


def test_status_forbids_non_admin(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get("/api/ingest/status", headers=user_headers)
    assert resp.status_code == 403


def test_upload_rejects_unsupported_format(client: TestClient, admin_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/ingest/upload",
        files={"file": ("dados.txt", b"a,b\n1,2\n", "text/plain")},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_upload_requires_admin(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/ingest/upload",
        files={
            "file": (
                "dados.xlsx",
                b"fake",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=user_headers,
    )
    assert resp.status_code == 403
