"""Unit tests for the auth helpers (pure functions, no DB/FastAPI needed)."""

import datetime

import jwt
import pytest

from src.core.auth import AuthError, decode_jwt, extract_bearer_token

# >= 32 bytes to satisfy PyJWT's HS256 key-length recommendation.
SECRET = "test-secret-key-0123456789abcdef-0123456789"


def _make_token(claims: dict, secret: str = SECRET, algorithm: str = "HS256") -> str:
    return jwt.encode(claims, secret, algorithm=algorithm)


def test_extract_bearer_token_ok():
    assert extract_bearer_token("Bearer abc.def.ghi") == "abc.def.ghi"
    assert extract_bearer_token("bearer TOKEN") == "TOKEN"


@pytest.mark.parametrize("header", [None, "", "Token abc", "Bearer ", "abc"])
def test_extract_bearer_token_rejects_bad_headers(header):
    with pytest.raises(AuthError):
        extract_bearer_token(header)


def test_decode_jwt_valid_email_claim():
    token = _make_token({"email": "a@b.com"})
    assert decode_jwt(token, SECRET) == "a@b.com"


def test_decode_jwt_falls_back_to_sub():
    token = _make_token({"sub": "user-123"})
    assert decode_jwt(token, SECRET) == "user-123"


def test_decode_jwt_missing_secret():
    token = _make_token({"email": "a@b.com"})
    with pytest.raises(AuthError):
        decode_jwt(token, None)


def test_decode_jwt_bad_signature():
    token = _make_token({"email": "a@b.com"}, secret="other-secret")
    with pytest.raises(AuthError):
        decode_jwt(token, SECRET)


def test_decode_jwt_expired():
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    token = _make_token({"email": "a@b.com", "exp": past})
    with pytest.raises(AuthError):
        decode_jwt(token, SECRET)


def test_decode_jwt_missing_identity_claim():
    token = _make_token({"role": "admin"})
    with pytest.raises(AuthError):
        decode_jwt(token, SECRET)
