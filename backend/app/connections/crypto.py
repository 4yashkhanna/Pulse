"""Token encryption for stored tool connections.

Connection tokens (Notion/Figma/Linear/Jira OAuth) are never stored in plaintext.
We encrypt them with Fernet (symmetric, authenticated). In prod the key comes from
CONNECTIONS_SECRET; in dev we derive a stable key from JWT_SECRET so the prototype
works with zero extra setup.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from ..config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    raw = settings.connections_secret
    if raw:
        # A real Fernet key (44-char urlsafe base64). Use as-is.
        try:
            return Fernet(raw.encode())
        except (ValueError, TypeError):
            pass  # not a valid Fernet key — fall through to derive one from it
    # Derive a deterministic 32-byte key from whatever secret we have. This keeps
    # dev frictionless; prod is required to set a proper CONNECTIONS_SECRET (see config).
    seed = (raw or settings.jwt_secret or "pulse-dev").encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
    return Fernet(key)


def encrypt(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str | None) -> str | None:
    if token is None:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        # Key rotated or corrupt value — treat as no token so the user reconnects.
        return None
