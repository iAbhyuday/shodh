"""Authentication seam.

Resolves the current user for a request. Two modes, selected by ``AUTH_MODE``:

  - ``single_user`` (default): every request maps to the built-in default
    tenant, preserving the app's original single-user behavior.
  - ``jwt``: requests must present a ``Bearer`` JWT signed with
    ``AUTH_JWT_SECRET``; the user is resolved (get-or-create) from its email claim.

The token-decoding helpers are pure functions so they can be unit-tested
without FastAPI or a database. ``get_current_user`` is the FastAPI dependency
routers depend on.
"""

from __future__ import annotations

from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.db.sql_db import User, get_db, get_or_create_default_user


class AuthError(Exception):
    """Raised for any authentication problem (bad header, invalid/expired token)."""


def extract_bearer_token(authorization: Optional[str]) -> str:
    """Pull the token out of an ``Authorization: Bearer <token>`` header."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing or malformed Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AuthError("Empty bearer token.")
    return token


def decode_jwt(
    token: str,
    secret: Optional[str],
    algorithm: str = "HS256",
    email_claim: str = "email",
) -> str:
    """Decode and verify a JWT; return the user's email/identifier.

    Raises ``AuthError`` on a missing secret, an invalid or expired token, or a
    token that carries no identity claim.
    """
    if not secret:
        raise AuthError("JWT auth is not configured (missing AUTH_JWT_SECRET).")
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.PyJWTError as exc:  # invalid signature, expired, malformed, ...
        raise AuthError(f"Invalid token: {exc}") from exc
    identity = payload.get(email_claim) or payload.get("sub")
    if not identity:
        raise AuthError("Token is missing a user identity claim.")
    return str(identity)


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency resolving the request's ``User``.

    In ``single_user`` mode this is always the default tenant; in ``jwt`` mode it
    is the user named by a valid bearer token (created on first sight).
    """
    settings = get_settings()
    mode = settings.AUTH_MODE

    if mode == "single_user":
        return get_or_create_default_user(db)

    if mode == "jwt":
        try:
            token = extract_bearer_token(authorization)
            email = decode_jwt(
                token,
                settings.AUTH_JWT_SECRET,
                settings.AUTH_JWT_ALGORITHM,
                settings.AUTH_JWT_EMAIL_CLAIM,
            )
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    raise HTTPException(status_code=500, detail=f"Unknown AUTH_MODE: {mode!r}")
