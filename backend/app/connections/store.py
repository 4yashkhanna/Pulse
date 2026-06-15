"""CRUD for user_connections — encrypted token storage, org-scoped to the user.

Tokens are encrypted on the way in (crypto.encrypt) and decrypted only when the coach
needs to open an MCP session (get_token). The rest of the app sees connection *status*,
never the raw secret.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..db import get_conn
from . import crypto


@dataclass
class Connection:
    provider: str
    external_account: str | None
    scopes: str | None
    expires_at: datetime | None
    created_at: datetime


def upsert(
    *,
    user_id: str,
    org_id: str | None,
    provider: str,
    access_token: str,
    refresh_token: str | None = None,
    scopes: str | None = None,
    external_account: str | None = None,
    expires_at: datetime | None = None,
) -> None:
    """Store (or replace) a user's grant for one provider. Tokens are encrypted."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO user_connections
                (user_id, org_id, provider, access_token_enc, refresh_token_enc,
                 scopes, external_account, expires_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (user_id, provider) DO UPDATE SET
                access_token_enc  = EXCLUDED.access_token_enc,
                refresh_token_enc = EXCLUDED.refresh_token_enc,
                scopes            = EXCLUDED.scopes,
                external_account  = EXCLUDED.external_account,
                expires_at        = EXCLUDED.expires_at,
                updated_at        = now()
            """,
            (
                user_id, org_id, provider,
                crypto.encrypt(access_token), crypto.encrypt(refresh_token),
                scopes, external_account, expires_at,
            ),
        )
        conn.commit()


def list_for_user(user_id: str) -> list[Connection]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT provider, external_account, scopes, expires_at, created_at
            FROM user_connections WHERE user_id = %s ORDER BY created_at
            """,
            (user_id,),
        ).fetchall()
    return [
        Connection(
            provider=r["provider"],
            external_account=r["external_account"],
            scopes=r["scopes"],
            expires_at=r["expires_at"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def connected_providers(user_id: str) -> set[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT provider FROM user_connections WHERE user_id = %s", (user_id,)
        ).fetchall()
    return {r["provider"] for r in rows}


def get_token(user_id: str, provider: str) -> str | None:
    """Decrypted access token for one (user, provider), or None if not connected."""
    with get_conn() as conn:
        r = conn.execute(
            "SELECT access_token_enc FROM user_connections WHERE user_id=%s AND provider=%s",
            (user_id, provider),
        ).fetchone()
    return crypto.decrypt(r["access_token_enc"]) if r else None


def delete(user_id: str, provider: str) -> bool:
    with get_conn() as conn:
        r = conn.execute(
            "DELETE FROM user_connections WHERE user_id=%s AND provider=%s RETURNING id",
            (user_id, provider),
        ).fetchone()
        conn.commit()
    return r is not None
