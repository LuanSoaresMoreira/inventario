"""Autenticação, sessões e autorização no servidor.

As sessões são opacas: o cookie contém somente um valor aleatório e o banco
guarda apenas o seu hash. O papel é sempre carregado do usuário persistido,
nunca de dados enviados pelo cliente.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from inventario_backend.config import get_settings
from inventario_backend.database import get_db
from inventario_backend.models import AuditEvent, InternalUser, UserSession

SESSION_COOKIE = "inventario_session"
CSRF_COOKIE = "inventario_csrf"
VALID_ROLES = frozenset({"it", "management", "administration"})

# Matriz única usada pela API. A documentação pública deve refletir este mapa.
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "it": frozenset(
        {
            "auth:read_self",
            "environment:read",
            "environment:write",
            "equipment:read",
            "equipment:write",
            "movement:read",
            "movement:write",
            "occurrence:read",
            "occurrence:write",
            "maintenance:read",
            "maintenance:write",
            "planning:read",
            "planning:write",
            "alert:read",
            "alert:write",
            "dashboard:read",
            "report:read",
            "report:export",
            "prediction:read",
            "prediction:write",
            "prediction:manage",
            "audit:read",
        }
    ),
    "management": frozenset(
        {
            "auth:read_self",
            "environment:read",
            "equipment:read",
            "movement:read",
            "occurrence:read",
            "maintenance:read",
            "planning:read",
            "alert:read",
            "dashboard:read",
            "report:read",
            "report:export",
            "prediction:read",
            "audit:read",
        }
    ),
    "administration": frozenset(
        {
            "auth:read_self",
            "environment:read",
            "environment:write",
            "users:read",
            "users:manage",
            "equipment:read",
            "equipment:write",
            "movement:read",
            "movement:write",
            "occurrence:read",
            "occurrence:write",
            "maintenance:read",
            "maintenance:write",
            "planning:read",
            "planning:write",
            "alert:read",
            "alert:write",
            "dashboard:read",
            "report:read",
            "report:export",
            "prediction:read",
            "prediction:write",
            "prediction:manage",
            "warranty:read",
            "warranty:write",
            "cost:read",
            "cost:write",
            "audit:read",
        }
    ),
}


@dataclass(frozen=True)
class AuthContext:
    user: InternalUser
    session: UserSession

    @property
    def permissions(self) -> frozenset[str]:
        return ROLE_PERMISSIONS.get(self.user.role, frozenset())


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Gera um hash scrypt adequado para provisionamento local controlado."""

    if not password or len(password) > 1024:
        raise ValueError("password must contain between 1 and 1024 characters")

    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
    return f"scrypt$16384$8$1${encode(salt)}${encode(derived)}"


def verify_password(password: str, encoded_hash: str | None) -> bool:
    if not encoded_hash:
        return False

    try:
        algorithm, n_value, r_value, p_value, salt_value, digest_value = (
            encoded_hash.split("$")
        )
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_value.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_value),
            r=int(r_value),
            p=int(p_value),
            dklen=len(expected),
        )
    except (ValueError, TypeError, UnicodeError):
        return False

    return hmac.compare_digest(actual, expected)


def _auth_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _request_token(request: Request) -> str | None:
    cookie_token = request.cookies.get(SESSION_COOKIE)
    if cookie_token:
        return cookie_token

    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_session(db: Session, user: InternalUser) -> tuple[str, str, datetime]:
    settings = get_settings()
    now = _now()
    expires_at = now + timedelta(minutes=settings.session_ttl_minutes)
    raw_token = secrets.token_urlsafe(32)
    raw_csrf_token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=_digest(raw_token),
            csrf_token_hash=_digest(raw_csrf_token),
            expires_at=expires_at,
        )
    )
    return raw_token, raw_csrf_token, expires_at


def get_auth_context(
    request: Request, db: Session = Depends(get_db)
) -> AuthContext:
    token = _request_token(request)
    if not token:
        raise _auth_error()

    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == _digest(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > _now(),
        )
    )
    if session is None:
        raise _auth_error()

    user = db.get(InternalUser, session.user_id)
    if user is None or not user.active:
        raise _auth_error()

    return AuthContext(user=user, session=session)


def _commit_security_audit(
    db: Session,
    *,
    actor_id,
    entity_id,
    action: str,
    reason: str,
    previous_state: dict[str, object] | None = None,
    new_state: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_id=actor_id,
            entity_type="authorization",
            entity_id=entity_id,
            action=action,
            reason=reason,
            previous_state=previous_state,
            new_state=new_state,
        )
    )
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="audit unavailable",
        ) from error


def require_permission(permission: str) -> Callable:
    """Cria uma dependência que nega por padrão e audita 403."""

    if not any(permission in permissions for permissions in ROLE_PERMISSIONS.values()):
        raise ValueError(f"unknown permission: {permission}")

    def dependency(
        request: Request,
        context: AuthContext = Depends(get_auth_context),
        db: Session = Depends(get_db),
    ) -> AuthContext:
        if permission not in context.permissions:
            _commit_security_audit(
                db,
                actor_id=context.user.id,
                entity_id=context.user.id,
                action="authorization.denied",
                reason="permission denied",
                new_state={
                    "path": request.url.path,
                    "permission": permission,
                    "role": context.user.role,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="forbidden",
            )
        return context

    return dependency


def require_csrf(
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Exige o par cookie legível + cabeçalho para operações com sessão."""

    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get("X-CSRF-Token")
    valid = bool(cookie_token and header_token)
    if valid:
        valid = hmac.compare_digest(cookie_token, header_token) and hmac.compare_digest(
            _digest(header_token), context.session.csrf_token_hash
        )

    if not valid:
        _commit_security_audit(
            db,
            actor_id=context.user.id,
            entity_id=context.user.id,
            action="authorization.csrf_denied",
            reason="missing or invalid csrf token",
            new_state={"path": request.url.path},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="csrf validation failed",
        )
    return context


def revoke_session(db: Session, context: AuthContext) -> None:
    context.session.revoked_at = _now()
    db.add(context.session)
