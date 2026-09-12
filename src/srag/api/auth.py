"""JWT authentication for the SRAG API.

Implements the ``/auth/*`` + ``/user/*`` contract expected by the legacy
frontend (``SRAGFront``): login with CPF + password, access/refresh JWT pair
with rotation, admin-only registration and user management.

Deliberately stdlib-only (HMAC-SHA256 JWT, PBKDF2-HMAC-SHA256 password
hashing) so no new third-party dependency or lockfile change is needed.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Literal, cast

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from srag.data.database import DB_URL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

Role = Literal["USER", "ADMIN"]

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
if JWT_SECRET == "dev-only-change-me":  # pragma: no cover # nosec B105
    logger.warning(
        "JWT_SECRET nao configurado: usando segredo de desenvolvimento. "
        "Defina JWT_SECRET no .env antes de expor este backend."
    )

ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "60")) * 60
REFRESH_TOKEN_EXPIRE_SECONDS = int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "7")) * 86400

_PBKDF2_ITERATIONS = 600_000
_SALT_BYTES = 16
_MAX_PASSWORD_LENGTH = 128

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpf TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'USER',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS refresh_tokens (
    jti TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);
"""


class AuthError(Exception):
    """Raised when a token is missing, invalid, expired or revoked."""


@dataclass
class UserRecord:
    """Authenticated user loaded from the users table."""

    id: int
    cpf: str
    full_name: str
    role: Role


_engine: Engine | None = None


def get_engine() -> Engine:
    """Return the shared SQLAlchemy engine (lazily created)."""
    global _engine
    if _engine is None:
        _engine = create_engine(DB_URL, pool_pre_ping=True)
    return _engine


def set_engine_override(engine: Engine | None) -> None:
    """Override the engine (used by tests to point at a temporary database)."""
    global _engine
    _engine = engine


def ensure_schema() -> None:
    """Create the auth tables if they do not exist yet."""
    engine = get_engine()
    with engine.begin() as conn:
        for statement in _SCHEMA_SQL.strip().split(";"):
            if statement.strip():
                conn.execute(text(statement))


def normalize_cpf(cpf: str) -> str:
    """Strip the display mask, keeping only digits."""
    return "".join(ch for ch in cpf if ch.isdigit())


def mask_cpf(digits: str) -> str:
    """Format 11 digits as XXX.XXX.XXX-XX (the mask the frontend sends)."""
    if len(digits) != 11:
        return digits
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def is_valid_cpf(cpf: str) -> bool:
    """Accept 11 digits, rejecting the trivial all-same-digit sequences."""
    digits = normalize_cpf(cpf)
    return len(digits) == 11 and digits.isdigit() and len(set(digits)) > 1


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and a random salt."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash, tolerating malformed hashes."""
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, binascii.Error):
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, int(iterations)
    )
    return hmac.compare_digest(candidate, expected)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _encode_jwt(payload: dict[str, str | int]) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64url_encode(json.dumps(payload).encode())
    signature = _b64url_encode(
        hmac.new(JWT_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{body}.{signature}"


def _decode_jwt(token: str) -> dict[str, str | int]:
    try:
        header_b64, body_b64, signature_b64 = token.split(".")
        expected = hmac.new(
            JWT_SECRET.encode(), f"{header_b64}.{body_b64}".encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64url_encode(expected), signature_b64):
            raise AuthError("Token inválido")
        payload = json.loads(_b64url_decode(body_b64))
    except (ValueError, binascii.Error, json.JSONDecodeError) as exc:
        raise AuthError("Token inválido") from exc
    if not isinstance(payload, dict):
        raise AuthError("Token inválido")
    return payload


def _new_token(user_id: int, token_type: str, expires_in: int) -> tuple[str, str, int]:
    now = int(time.time())
    jti = secrets.token_hex(16)
    payload: dict[str, str | int] = {
        "sub": user_id,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expires_in,
    }
    return _encode_jwt(payload), jti, now + expires_in


def create_token_pair(user: UserRecord) -> dict[str, str | int]:
    """Create an access + refresh pair and persist the refresh jti."""
    access_token, _, _ = _new_token(user.id, "access", ACCESS_TOKEN_EXPIRE_SECONDS)
    refresh_token, jti, expires_at = _new_token(
        user.id, "refresh", REFRESH_TOKEN_EXPIRE_SECONDS
    )
    ensure_schema()
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO refresh_tokens (jti, user_id, expires_at, revoked)"
                " VALUES (:jti, :user_id, :expires_at, 0)"
            ),
            {"jti": jti, "user_id": user.id, "expires_at": expires_at},
        )
    return {"jwtToken": access_token, "token": refresh_token}


def decode_token(token: str, expected_type: str) -> dict[str, str | int]:
    """Validate signature, expiry and type of a JWT."""
    payload = _decode_jwt(token)
    if payload.get("type") != expected_type:
        raise AuthError("Token inválido")
    try:
        expires_at = int(payload["exp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthError("Token inválido") from exc
    if expires_at < int(time.time()):
        raise AuthError("Sessão expirada")
    return payload


def _row_to_user(row: Sequence[object]) -> UserRecord:
    user_id = cast("int", row[0])
    cpf = cast("str", row[1])
    full_name = cast("str", row[2])
    role = cast("str", row[3])
    return UserRecord(
        id=user_id, cpf=cpf, full_name=full_name, role="ADMIN" if role == "ADMIN" else "USER"
    )


def get_user_by_cpf(cpf_digits: str) -> UserRecord | None:
    """Find an active user by normalized CPF digits."""
    ensure_schema()
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT id, cpf, full_name, role FROM users WHERE cpf = :cpf"),
            {"cpf": cpf_digits},
        ).fetchone()
    return _row_to_user(row) if row is not None else None


def get_user_by_id(user_id: int) -> UserRecord | None:
    """Find a user by id."""
    ensure_schema()
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT id, cpf, full_name, role FROM users WHERE id = :id"),
            {"id": user_id},
        ).fetchone()
    return _row_to_user(row) if row is not None else None


def count_users() -> int:
    """Return the total number of users (used for first-admin bootstrap)."""
    ensure_schema()
    with get_engine().connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0)


def create_user(cpf_digits: str, full_name: str, password: str, role: Role) -> UserRecord:
    """Insert a user and return it. Raises AuthError if the CPF exists."""
    ensure_schema()
    created_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        with get_engine().begin() as conn:
            result = conn.execute(
                text(
                    "INSERT INTO users (cpf, full_name, password_hash, role, created_at)"
                    " VALUES (:cpf, :full_name, :password_hash, :role, :created_at)"
                ),
                {
                    "cpf": cpf_digits,
                    "full_name": full_name,
                    "password_hash": hash_password(password),
                    "role": role,
                    "created_at": created_at,
                },
            )
            user_id = int(result.lastrowid)
    except SQLAlchemyError as exc:
        raise AuthError("CPF já cadastrado") from exc
    created = get_user_by_id(user_id)
    if created is None:  # pragma: no cover - defensive
        raise AuthError("Falha ao criar usuário")
    return created


def update_user(
    user_id: int,
    full_name: str,
    cpf_digits: str,
    password: str | None = None,
) -> UserRecord:
    """Update name/CPF and optionally the password. Raises AuthError on conflict."""
    ensure_schema()
    params: dict[str, object] = {"id": user_id, "cpf": cpf_digits, "full_name": full_name}
    password_set = ""  # nosec B105 - empty default, not a secret
    if password is not None:
        params["password_hash"] = hash_password(password)
        password_set = ", password_hash = :password_hash"  # nosec B105 - SQL fragment, not a secret
    try:
        with get_engine().begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE users SET cpf = :cpf, full_name = :full_name"
                    f"{password_set} WHERE id = :id"  # nosec B608 - interpolated fragment is a constant
                ),
                params,
            )
            if result.rowcount == 0:
                raise AuthError("Usuário não encontrado")
    except SQLAlchemyError as exc:
        raise AuthError("CPF já cadastrado") from exc
    updated = get_user_by_id(user_id)
    if updated is None:  # pragma: no cover - defensive
        raise AuthError("Usuário não encontrado")
    return updated


def list_users() -> list[UserRecord]:
    """List all users ordered by id."""
    ensure_schema()
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT id, cpf, full_name, role FROM users ORDER BY id")
        ).fetchall()
    return [_row_to_user(row) for row in rows]


def delete_user(user_id: int) -> bool:
    """Delete a user and revoke their refresh tokens. Returns False if missing."""
    ensure_schema()
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM refresh_tokens WHERE user_id = :id"), {"id": user_id}
        )
        result = conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        return result.rowcount > 0


def is_refresh_revoked(jti: str) -> bool:
    """Check whether a refresh token jti was revoked (or is unknown)."""
    ensure_schema()
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT revoked FROM refresh_tokens WHERE jti = :jti"), {"jti": jti}
        ).fetchone()
    return row is None or int(row[0]) != 0


def revoke_refresh_token(jti: str) -> None:
    """Mark a refresh token jti as revoked (rotation on refresh)."""
    ensure_schema()
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE refresh_tokens SET revoked = 1 WHERE jti = :jti"), {"jti": jti}
        )


_bearer_scheme = HTTPBearer(auto_error=False)

BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]


def get_current_user(credentials: BearerCredentials) -> UserRecord:
    """Resolve the Bearer access token into the authenticated user (401 if bad)."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Token de acesso ausente")
    try:
        payload = decode_token(credentials.credentials, "access")
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuário não existe ou foi desativado")
    return user


def get_optional_user(credentials: BearerCredentials) -> UserRecord | None:
    """Resolve the Bearer token when present, else None (for bootstrap flows)."""
    if credentials is None:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


def require_admin(user: Annotated[UserRecord, Depends(get_current_user)]) -> UserRecord:
    """Require the authenticated user to have the ADMIN role (403 otherwise)."""
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=403, detail="Você não tem permissão para usar esse recurso!"
        )
    return user
