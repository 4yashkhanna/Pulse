"""Auth primitives: bcrypt round-trip, JWT round-trip, login rate limiter."""
import pytest

from app.auth.routes import MAX_ATTEMPTS, _attempts, _rate_limited
from app.auth.security import _decode, create_token, hash_password, verify_password
from fastapi import HTTPException


def test_password_roundtrip():
    h = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)


def test_verify_handles_garbage_hash():
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_token_roundtrip():
    token = create_token("user-123")
    assert _decode(token) == "user-123"


def test_tampered_token_rejected():
    token = create_token("user-123") + "x"
    with pytest.raises(HTTPException):
        _decode(token)


def test_rate_limiter_blocks_after_max_attempts():
    _attempts.clear()
    key = "email:test@example.com"
    for _ in range(MAX_ATTEMPTS):
        assert not _rate_limited(key)
    assert _rate_limited(key)
