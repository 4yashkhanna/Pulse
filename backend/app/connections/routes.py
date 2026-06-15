"""Connection routes — per-user OAuth connect/disconnect for tool integrations.

Flow:
  GET  /connections                     → list providers + this user's status
  GET  /connections/{provider}/start    → returns the provider authorize URL (XHR)
  GET  /connections/{provider}/callback → provider redirects here; we store the token
  DELETE /connections/{provider}        → disconnect

The callback is identified by the signed `state` (which carries the user id), not a
bearer token — the browser redirect from the provider can't send our auth header.
"""
from __future__ import annotations

import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from ..auth.security import CurrentUser, get_current_user
from ..config import get_settings
from ..db import get_conn
from . import mcp_oauth, oauth, store
from .registry import PROVIDERS, get_provider

log = logging.getLogger("pulse.connections")
router = APIRouter(prefix="/connections", tags=["connections"])


def _require_org_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Connections are for organization users")
    return user


@router.get("")
def list_connections(user: CurrentUser = Depends(_require_org_user)):
    """Every available provider with whether this user has connected it and whether the
    server has OAuth credentials configured for it (so the UI can disable unconfigured)."""
    connected = {c.provider: c for c in store.list_for_user(user.id)}
    out = []
    for key, p in PROVIDERS.items():
        c = connected.get(key)
        out.append(
            {
                "provider": key,
                "label": p.label,
                "capability": p.capability,
                "icon": p.icon,
                "experimental": p.experimental,
                "configured": p.configured,
                "connected": c is not None,
                "account": c.external_account if c else None,
            }
        )
    return out


@router.get("/{provider}/start")
async def start(provider: str, user: CurrentUser = Depends(_require_org_user)):
    p = get_provider(provider)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown provider")
    if not p.configured:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{p.label} isn't set up yet — add {p.client_id_env} and {p.client_secret_env} to the server.",
        )
    # MCP-native providers (Notion, Figma): discover endpoints + self-register (DCR), then
    # build the authorize URL against the server's own OAuth. Classic providers use the
    # pre-registered developer-app OAuth.
    if p.auth_mode == "mcp":
        try:
            reg = await mcp_oauth.ensure_registration(p)
        except Exception as exc:  # noqa: BLE001
            log.warning("MCP OAuth registration failed for %s: %s", provider, exc)
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Couldn't set up {p.label}'s connection. Please try again.",
            )
        return {"authorize_url": mcp_oauth.build_authorize_url(p, reg, user.id)}
    return {"authorize_url": oauth.build_authorize_url(p, user.id)}


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
):
    settings = get_settings()
    front = settings.frontend_origin.rstrip("/")
    p = get_provider(provider)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown provider")

    def _back(qs: str) -> RedirectResponse:
        return RedirectResponse(url=f"{front}/connections?{qs}")

    if error:
        return _back(f"error={provider}")
    if not code or not state:
        return _back(f"error={provider}")

    try:
        payload = oauth.decode_state(state)
    except jwt.PyJWTError:
        return _back(f"error={provider}")
    if payload.get("provider") != provider:
        return _back(f"error={provider}")
    user_id = payload.get("uid")
    if not user_id:
        return _back(f"error={provider}")

    try:
        if p.auth_mode == "mcp":
            reg = store.get_mcp_client(provider)
            if not reg:
                raise RuntimeError("missing client registration")
            token_json = await mcp_oauth.exchange_code(p, reg, code, payload.get("pkce"))
            account = None  # MCP token responses carry no friendly account label
        else:
            token_json = await oauth.exchange_code(p, code, payload)
            account = oauth.account_label(p, token_json)
    except Exception as exc:  # noqa: BLE001
        log.warning("OAuth token exchange failed for %s: %s", provider, exc)
        return _back(f"error={provider}")

    access = token_json.get("access_token")
    if not access:
        return _back(f"error={provider}")

    with get_conn() as conn:
        row = conn.execute("SELECT org_id FROM users WHERE id = %s", (user_id,)).fetchone()
    org_id = str(row["org_id"]) if row and row["org_id"] else None

    store.upsert(
        user_id=user_id,
        org_id=org_id,
        provider=provider,
        access_token=access,
        refresh_token=token_json.get("refresh_token"),
        scopes=token_json.get("scope") or p.scopes or None,
        external_account=account,
    )
    return _back(f"connected={provider}")


@router.delete("/{provider}")
def disconnect(provider: str, user: CurrentUser = Depends(_require_org_user)):
    if not get_provider(provider):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown provider")
    store.delete(user.id, provider)
    return {"disconnected": provider}
