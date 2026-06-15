"""Generic OAuth 2.0 authorization-code flow for tool connections.

One implementation drives every provider; per-provider quirks (PKCE, Basic vs body
client auth, form vs JSON token requests) come from the registry. The `state` parameter
is a short-lived signed JWT that carries the user id, provider, and (for PKCE) the code
verifier across the redirect, so the flow stays stateless.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
import jwt

from ..config import get_settings
from .registry import Provider

_STATE_TTL_SECONDS = 600  # 10 min to complete the consent screen


def redirect_uri(provider: Provider) -> str:
    base = get_settings().backend_base_url.rstrip("/")
    return f"{base}/connections/{provider.key}/callback"


def _pkce_pair() -> tuple[str, str]:
    """(verifier, challenge) using S256."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def build_authorize_url(provider: Provider, user_id: str) -> str:
    """Authorize URL plus a signed state carrying user_id (+ PKCE verifier if used)."""
    settings = get_settings()
    state_payload: dict = {
        "uid": user_id,
        "provider": provider.key,
        "nonce": secrets.token_urlsafe(8),
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=_STATE_TTL_SECONDS),
    }
    params: dict[str, str] = {
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri(provider),
        "response_type": "code",
        **provider.extra_authorize_params,
    }
    if provider.scopes:
        params["scope"] = provider.scopes
    if provider.uses_pkce:
        verifier, challenge = _pkce_pair()
        state_payload["pkce"] = verifier
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"

    params["state"] = jwt.encode(state_payload, settings.jwt_secret, algorithm="HS256")
    return f"{provider.authorize_url}?{urlencode(params)}"


def decode_state(state: str) -> dict:
    settings = get_settings()
    return jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])


async def exchange_code(provider: Provider, code: str, state_payload: dict) -> dict:
    """Swap the authorization code for tokens. Returns the provider's raw token JSON."""
    data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri(provider),
    }
    if provider.uses_pkce and state_payload.get("pkce"):
        data["code_verifier"] = state_payload["pkce"]

    headers = {"Accept": "application/json"}
    auth = None
    if provider.token_auth == "basic":
        auth = (provider.client_id, provider.client_secret)
    else:
        data["client_id"] = provider.client_id
        data["client_secret"] = provider.client_secret

    async with httpx.AsyncClient(timeout=15.0) as client:
        if provider.token_format == "json":
            resp = await client.post(provider.token_url, json=data, headers=headers, auth=auth)
        else:
            resp = await client.post(provider.token_url, data=data, headers=headers, auth=auth)
    resp.raise_for_status()
    return resp.json()


def account_label(provider: Provider, token_json: dict) -> str | None:
    """A friendly 'connected as …' label pulled from the provider's token response."""
    if provider.key == "notion":
        ws = token_json.get("workspace_name")
        owner = (token_json.get("owner") or {}).get("user", {})
        return ws or owner.get("name")
    if provider.key == "figma":
        return token_json.get("email") or token_json.get("user_id")
    # Linear/Jira return little identifying info in the token response itself.
    return None
