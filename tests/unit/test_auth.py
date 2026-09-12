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
ADMIN_PASSWORD = "admin123"
USER_CPF = "987.654.321-00"
USER_PASSWORD = "user1234"


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient]:
    engine = create_engine(f"sqlite:///{tmp_path}/auth_test.db")
    auth_module.set_engine_override(engine)
    try:
        yield TestClient(app)
    finally:
        auth_module.set_engine_override(None)
        engine.dispose()


def _register(client: TestClient, cpf: str, role: str = "USER", token: str | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post(
        "/api/auth/register",
        json={
            "cpf": cpf,
            "fullName": "Nome Teste",
            "password": "secret12",
            "confirmPassword": "secret12",
            "role": role,
        },
        headers=headers,
    )


def _login(client: TestClient, cpf: str, password: str):
    return client.post("/api/auth/login", json={"cpf": cpf, "password": password})


def test_bootstrap_first_user_becomes_admin(client: TestClient) -> None:
    response = _register(client, ADMIN_CPF, role="USER")

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADMIN"


def test_register_duplicate_cpf_returns_message(client: TestClient) -> None:
    _register(client, ADMIN_CPF)
    admin = _login(client, ADMIN_CPF, "secret12").json()

    response = _register(client, ADMIN_CPF, token=admin["jwtToken"])

    assert response.status_code == 400
    assert "message" in response.json()


def test_register_validations(client: TestClient) -> None:
    _register(client, ADMIN_CPF)
    admin = _login(client, ADMIN_CPF, "secret12").json()
    headers = {"Authorization": f"Bearer {admin['jwtToken']}"}

    mismatch = client.post(
        "/api/auth/register",
        json={
            "cpf": USER_CPF,
            "fullName": "X",
            "password": "secret12",
            "confirmPassword": "other12",
            "role": "USER",
        },
        headers=headers,
    )
    assert mismatch.status_code == 400

    short = client.post(
        "/api/auth/register",
        json={
            "cpf": USER_CPF,
            "fullName": "X",
            "password": "123",
            "confirmPassword": "123",
            "role": "USER",
        },
        headers=headers,
    )
    assert short.status_code == 400

    bad_cpf = client.post(
        "/api/auth/register",
        json={
            "cpf": "111",
            "fullName": "X",
            "password": "secret12",
            "confirmPassword": "secret12",
            "role": "USER",
        },
        headers=headers,
    )
    assert bad_cpf.status_code == 400


def test_register_requires_admin_after_bootstrap(client: TestClient) -> None:
    _register(client, ADMIN_CPF)

    response = _register(client, USER_CPF)

    assert response.status_code == 403


def test_login_contract_matches_frontend(client: TestClient) -> None:
    _register(client, ADMIN_CPF)

    response = _login(client, ADMIN_CPF, "secret12")

    assert response.status_code == 200
    body = response.json()
    assert {"jwtToken", "token", "fullName", "cpf", "role"} <= set(body)
    assert body["cpf"] == ADMIN_CPF
    assert body["role"] == "ADMIN"


def test_login_wrong_password_is_401(client: TestClient) -> None:
    _register(client, ADMIN_CPF)

    assert _login(client, ADMIN_CPF, "wrongpass").status_code == 401
    assert _login(client, USER_CPF, "secret12").status_code == 401


def test_refresh_rotates_and_revokes_old(client: TestClient) -> None:
    _register(client, ADMIN_CPF)
    first = _login(client, ADMIN_CPF, "secret12").json()

    response = client.post("/api/auth/refreshToken", json={"token": first["token"]})

    assert response.status_code == 200
    body = response.json()
    assert body["jwtToken"] != first["jwtToken"]
    assert body["token"] != first["token"]

    replay = client.post("/api/auth/refreshToken", json={"token": first["token"]})
    assert replay.status_code == 401


def test_refresh_invalid_token_is_401(client: TestClient) -> None:
    assert client.post("/api/auth/refreshToken", json={"token": "bogus"}).status_code == 401


def test_manage_requires_admin(client: TestClient) -> None:
    _register(client, ADMIN_CPF)
    admin = _login(client, ADMIN_CPF, "secret12").json()
    _register(client, USER_CPF, token=admin["jwtToken"])
    user = _login(client, USER_CPF, "secret12").json()

    assert client.get("/api/user/manage").status_code == 401

    forbidden = client.get(
        "/api/user/manage", headers={"Authorization": f"Bearer {user['jwtToken']}"}
    )
    assert forbidden.status_code == 403

    response = client.get(
        "/api/user/manage", headers={"Authorization": f"Bearer {admin['jwtToken']}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert {(u["cpf"], u["role"]) for u in users} == {(ADMIN_CPF, "ADMIN"), (USER_CPF, "USER")}
    assert all({"id", "name", "cpf", "role"} <= set(u) for u in users)


def test_admin_can_delete_user_but_not_self(client: TestClient) -> None:
    _register(client, ADMIN_CPF)
    admin = _login(client, ADMIN_CPF, "secret12").json()
    headers = {"Authorization": f"Bearer {admin['jwtToken']}"}
    target_id = _register(client, USER_CPF, token=admin["jwtToken"]).json()["user"]["id"]
    admin_id = admin_id_of(client, headers)

    assert client.delete(f"/api/user/{admin_id}", headers=headers).status_code == 400
    assert client.delete("/api/user/999999", headers=headers).status_code == 404

    deleted = client.delete(f"/api/user/{target_id}", headers=headers)
    assert deleted.status_code == 200
    assert _login(client, USER_CPF, "secret12").status_code == 401


def admin_id_of(client: TestClient, headers: dict[str, str]) -> int:
    users = client.get("/api/user/manage", headers=headers).json()
    return next(u["id"] for u in users if u["cpf"] == ADMIN_CPF)


def test_protected_with_tampered_token_is_401(client: TestClient) -> None:
    _register(client, ADMIN_CPF)
    admin = _login(client, ADMIN_CPF, "secret12").json()
    tampered = admin["jwtToken"][:-2] + "xx"

    response = client.get(
        "/api/user/manage", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert response.status_code == 401


def test_update_profile_name_and_password(client: TestClient) -> None:
    _register(client, ADMIN_CPF)
    admin = _login(client, ADMIN_CPF, "secret12").json()
    headers = {"Authorization": f"Bearer {admin['jwtToken']}"}

    response = client.put(
        "/api/user/me",
        json={
            "fullName": "Novo Nome",
            "cpf": ADMIN_CPF,
            "currentPassword": "secret12",
            "newPassword": "novaSenha1",
            "confirmNewPassword": "novaSenha1",
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fullName"] == "Novo Nome"

    assert _login(client, ADMIN_CPF, "secret12").status_code == 401
    assert _login(client, ADMIN_CPF, "novaSenha1").status_code == 200


def test_update_profile_rejects_bad_input(client: TestClient) -> None:
    _register(client, ADMIN_CPF)
    admin = _login(client, ADMIN_CPF, "secret12").json()
    admin_headers = {"Authorization": f"Bearer {admin['jwtToken']}"}
    _register(client, USER_CPF, token=admin["jwtToken"])

    assert client.put("/api/user/me", json={"fullName": "X", "cpf": ADMIN_CPF}).status_code == 401

    bad_password = client.put(
        "/api/user/me",
        json={
            "fullName": "Novo Nome",
            "cpf": ADMIN_CPF,
            "currentPassword": "errada",
            "newPassword": "novaSenha1",
            "confirmNewPassword": "novaSenha1",
        },
        headers=admin_headers,
    )
    assert bad_password.status_code == 401

    duplicate_cpf = client.put(
        "/api/user/me", json={"fullName": "Novo Nome", "cpf": USER_CPF}, headers=admin_headers
    )
    assert duplicate_cpf.status_code == 400
