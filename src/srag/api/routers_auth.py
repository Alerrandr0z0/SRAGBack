"""Auth routers: ``/auth/*`` login/refresh/register and ``/user/*`` management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from srag.api.auth import (
    AuthError,
    Role,
    UserRecord,
    count_users,
    create_token_pair,
    create_user,
    decode_token,
    delete_user,
    ensure_schema,
    get_current_user,
    get_engine,
    get_optional_user,
    get_user_by_cpf,
    get_user_by_id,
    is_refresh_revoked,
    is_valid_cpf,
    list_users,
    mask_cpf,
    normalize_cpf,
    require_admin,
    revoke_refresh_token,
    update_user,
    verify_password,
)
from srag.api.rate_limit import limiter

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    """Login payload sent by the frontend (masked CPF + password)."""

    cpf: str
    password: str


class RefreshRequest(BaseModel):
    """Refresh payload: the stored refresh token under the ``token`` key."""

    token: str


class RegisterRequest(BaseModel):
    """Registration payload sent by UserRegistrationForm."""

    cpf: str
    fullName: str  # noqa: N815 - camelCase required by the frontend contract
    password: str
    confirmPassword: str  # noqa: N815 - camelCase required by the frontend contract
    role: str = "USER"


class UpdateProfileRequest(BaseModel):
    """Profile payload sent by Profile (password change is optional)."""

    fullName: str  # noqa: N815 - camelCase required by the frontend contract
    cpf: str
    currentPassword: str | None = None  # noqa: N815
    newPassword: str | None = None  # noqa: N815
    confirmNewPassword: str | None = None  # noqa: N815


def _user_payload(user: UserRecord) -> dict[str, str | int]:
    return {
        "id": user.id,
        "name": user.full_name,
        "cpf": mask_cpf(user.cpf),
        "role": user.role,
    }


def _session_payload(user: UserRecord) -> dict[str, str | int | None]:
    tokens = create_token_pair(user)
    return {
        **tokens,
        "fullName": user.full_name,
        "cpf": mask_cpf(user.cpf),
        "role": user.role,
    }


def _validate_register(body: RegisterRequest) -> tuple[str, str, str, Role] | JSONResponse:
    if not is_valid_cpf(body.cpf):
        return JSONResponse(status_code=400, content={"message": "CPF inválido"})
    full_name = body.fullName.strip()
    if not full_name or len(full_name) > 120:
        return JSONResponse(status_code=400, content={"message": "Nome inválido"})
    if len(body.password) < 6:
        return JSONResponse(
            status_code=400, content={"message": "Senha deve ter pelo menos 6 caracteres"}
        )
    if len(body.password) > 128:
        return JSONResponse(status_code=400, content={"message": "Senha muito longa"})
    if body.password != body.confirmPassword:
        return JSONResponse(status_code=400, content={"message": "Senhas não conferem"})
    role: Role = "ADMIN" if body.role == "ADMIN" else "USER"
    return normalize_cpf(body.cpf), full_name, body.password, role


@router.post("/auth/register")
def register(
    body: RegisterRequest, caller: Annotated[UserRecord | None, Depends(get_optional_user)]
) -> JSONResponse:
    """Register a user. Admin-only, except the very first user (bootstrap ADMIN)."""
    validated = _validate_register(body)
    if isinstance(validated, JSONResponse):
        return validated
    cpf_digits, full_name, password, role = validated

    if count_users() == 0:
        role = "ADMIN"
        bootstrap = True
    else:
        bootstrap = False
        if caller is None or caller.role != "ADMIN":
            return JSONResponse(
                status_code=403,
                content={"message": "Você não tem permissão para usar esse recurso!"},
            )
    try:
        user = create_user(cpf_digits, full_name, password, role)
    except AuthError as exc:
        return JSONResponse(status_code=400, content={"message": str(exc)})
    content: dict[str, object] = {
        "message": "Registro realizado com sucesso!",
        "user": _user_payload(user),
    }
    if bootstrap:
        content["message"] = "Primeiro administrador criado com sucesso!"
    return JSONResponse(status_code=200, content=content)


def _login_rate_key(cpf: str, client_host: str | None) -> str:
    """Rate-limit key: normalized CPF when valid, else the client host."""
    if is_valid_cpf(cpf):
        return normalize_cpf(cpf)
    return client_host or "unknown"


@router.post("/auth/login")
def login(body: LoginRequest, request: Request) -> JSONResponse:
    """Authenticate with CPF + password and return the access/refresh pair."""
    key = _login_rate_key(body.cpf, request.client.host if request.client else None)
    if limiter.is_locked(key):
        return JSONResponse(
            status_code=429,
            content={
                "message": (
                    "Muitas tentativas de login. Aguarde alguns minutos e tente novamente."
                )
            },
        )
    user = get_user_by_cpf(normalize_cpf(body.cpf)) if is_valid_cpf(body.cpf) else None
    stored_hash = _password_hash_for(user.cpf) if user is not None else None
    if user is None or stored_hash is None or not verify_password(body.password, stored_hash):
        limiter.record_failure(key)
        return JSONResponse(status_code=401, content={"message": "Credenciais inválidas"})
    limiter.record_success(key)
    return JSONResponse(status_code=200, content=_session_payload(user))


@router.post("/auth/refreshToken")
def refresh_token(body: RefreshRequest) -> JSONResponse:
    """Rotate a refresh token into a new access/refresh pair."""
    try:
        payload = decode_token(body.token, "refresh")
    except AuthError as exc:
        return JSONResponse(status_code=401, content={"message": str(exc)})
    jti = str(payload.get("jti", ""))
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return JSONResponse(status_code=401, content={"message": "Token inválido"})
    if not jti or is_refresh_revoked(jti):
        return JSONResponse(status_code=401, content={"message": "Sessão expirada"})
    user = get_user_by_id(user_id)
    if user is None:
        return JSONResponse(
            status_code=401, content={"message": "Usuário não existe ou foi desativado"}
        )
    revoke_refresh_token(jti)
    return JSONResponse(status_code=200, content=_session_payload(user))


def _validate_password_change(
    body: UpdateProfileRequest, user: UserRecord
) -> str | None | JSONResponse:
    """Validate an optional password change; returns the new password (or None)."""
    if not body.newPassword and not body.confirmNewPassword:
        return None
    stored_hash = _password_hash_for(user.cpf)
    if (
        not body.currentPassword
        or stored_hash is None
        or not verify_password(body.currentPassword, stored_hash)
    ):
        return JSONResponse(status_code=401, content={"message": "Senha atual inválida"})
    if len(body.newPassword or "") < 6:
        return JSONResponse(
            status_code=400, content={"message": "Senha deve ter pelo menos 6 caracteres"}
        )
    if len(body.newPassword or "") > 128:
        return JSONResponse(status_code=400, content={"message": "Senha muito longa"})
    if body.newPassword != body.confirmNewPassword:
        return JSONResponse(status_code=400, content={"message": "Senhas não conferem"})
    return body.newPassword


@router.put("/user/me")
def update_profile(
    body: UpdateProfileRequest,
    user: Annotated[UserRecord, Depends(get_current_user)],
) -> JSONResponse:
    """Update own name/CPF and optionally the password; returns a fresh session."""
    full_name = body.fullName.strip()
    if not full_name or len(full_name) > 120:
        return JSONResponse(status_code=400, content={"message": "Nome inválido"})
    if not is_valid_cpf(body.cpf):
        return JSONResponse(status_code=400, content={"message": "CPF inválido"})
    cpf_digits = normalize_cpf(body.cpf)
    if cpf_digits != user.cpf and get_user_by_cpf(cpf_digits) is not None:
        return JSONResponse(status_code=400, content={"message": "CPF já cadastrado"})

    checked = _validate_password_change(body, user)
    if isinstance(checked, JSONResponse):
        return checked

    try:
        updated = update_user(user.id, full_name, cpf_digits, checked)
    except AuthError as exc:
        return JSONResponse(status_code=400, content={"message": str(exc)})
    return JSONResponse(status_code=200, content=_session_payload(updated))


@router.get("/user/manage")
def manage_users(
    admin: Annotated[UserRecord, Depends(require_admin)],
) -> list[dict[str, str | int]]:
    """List users for the admin ManageUsers screen."""
    del admin
    return [_user_payload(user) for user in list_users()]


@router.delete("/user/{user_id}")
def remove_user(
    user_id: int, admin: Annotated[UserRecord, Depends(require_admin)]
) -> JSONResponse:
    """Delete a user. Admins cannot delete themselves (this also protects the last admin)."""
    if user_id == admin.id:
        return JSONResponse(
            status_code=400, content={"message": "Você não pode remover a própria conta"}
        )
    target = get_user_by_id(user_id)
    if target is None:
        return JSONResponse(status_code=404, content={"message": "Usuário não encontrado"})
    delete_user(user_id)
    return JSONResponse(status_code=200, content={"message": "Usuário removido com sucesso."})


def _password_hash_for(cpf_digits: str) -> str | None:
    """Fetch the stored password hash for a CPF (kept out of UserRecord)."""
    ensure_schema()
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT password_hash FROM users WHERE cpf = :cpf"), {"cpf": cpf_digits}
        ).fetchone()
    return str(row[0]) if row is not None else None
