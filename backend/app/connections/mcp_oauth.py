"""MCP-native OAuth (auth_mode='mcp') — for servers that run their own OAuth.

Notion and Figma's MCP servers reject classic OAuth-app tokens; they expose their own
OAuth 2.1 authorization server and expect the client to **self-register** via Dynamic
Client Registration (DCR). This is the same mechanism Claude/ChatGPT use when you "add a
connector by URL" — no developer app, no client id/secret to manage.

This module drives that flow across our two existing routes:
  /start    → ensure_registration() (discover + DCR, cached) → build_authorize_url()
  /callback → exchange_code()

It reuses the MCP SDK's spec-compliant helpers for discovery/registration so we don't
hand-roll the RFCs, and the signed-JWT `state` (shared with the classic flow) carries the
user id and PKCE verifier across the redirect.
"""
from __future__ import annotations

import datetime as dt
import secrets
from urllib.parse import urlencode

import httpx
from mcp.client.auth import oauth2 as o
from mcp.shared.auth import OAuthClientMetadata

from . import store
from .oauth import _pkce_pair, redirect_uri  # reuse PKCE + redirect-uri helpers
from .registry import Provider
from .store import McpClient

_DISCOVERY_TIMEOUT = 15.0


async def ensure_registration(provider: Provider) -> McpClient:
    """Return this provider's cached DCR registration, performing discovery + Dynamic
    Client Registration on first use and persisting the result."""
    cached = store.get_mcp_client(provider.key)
    if cached:
        return cached

    redirect = redirect_uri(provider)
    async with httpx.AsyncClient(follow_redirects=True, timeout=_DISCOVERY_TIMEOUT) as c:
        # 1. Unauthenticated probe → the WWW-Authenticate header points at the server's
        #    protected-resource metadata.
        probe = await c.get(provider.mcp_url)
        rm_url = o.extract_resource_metadata_from_www_auth(probe)

        # 2. Protected-resource metadata → which authorization server to use.
        prm = None
        for url in o.build_protected_resource_metadata_discovery_urls(rm_url, provider.mcp_url):
            resp = await c.send(o.create_oauth_metadata_request(url))
            if resp.status_code == 200:
                prm = await o.handle_protected_resource_response(resp)
                if prm:
                    break
        if not prm or not prm.authorization_servers:
            raise RuntimeError(f"{provider.label}: could not discover authorization server")
        auth_server = str(prm.authorization_servers[0])

        # 3. Authorization-server metadata → authorize/token/registration endpoints.
        meta = None
        for url in o.build_oauth_authorization_server_metadata_discovery_urls(auth_server, auth_server):
            resp = await c.send(o.create_oauth_metadata_request(url))
            if resp.status_code == 200:
                ok, m = await o.handle_auth_metadata_response(resp)
                if m:
                    meta = m
                    break
        if not meta:
            raise RuntimeError(f"{provider.label}: could not discover OAuth metadata")

        # 4. Self-register a public client (PKCE, no secret) bound to our callback URL.
        client_metadata = OAuthClientMetadata(
            redirect_uris=[redirect],
            client_name="Pulse",
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="none",
        )
        resp = await c.send(o.create_client_registration_request(meta, client_metadata, auth_server))
        info = await o.handle_registration_response(resp)

    # Scopes: prefer what the registry pins, else advertise the server's supported scopes.
    scopes = provider.scopes or " ".join(
        prm.scopes_supported or meta.scopes_supported or []
    ).strip() or None

    reg = McpClient(
        provider=provider.key,
        resource=str(prm.resource) if prm.resource else o.resource_url_from_server_url(provider.mcp_url),
        authorization_endpoint=str(meta.authorization_endpoint),
        token_endpoint=str(meta.token_endpoint),
        registration_endpoint=str(meta.registration_endpoint) if meta.registration_endpoint else None,
        client_id=info.client_id,
        client_secret=info.client_secret,
        scopes=scopes,
    )
    store.save_mcp_client(reg)
    return reg


def build_authorize_url(provider: Provider, reg: McpClient, user_id: str) -> str:
    """Authorize URL (PKCE + RFC 8707 resource indicator) plus a signed state carrying the
    user id and the PKCE verifier."""
    import jwt

    from ..config import get_settings

    verifier, challenge = _pkce_pair()
    state = jwt.encode(
        {
            "uid": user_id,
            "provider": provider.key,
            "pkce": verifier,
            "nonce": secrets.token_urlsafe(8),
            "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=600),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    params = {
        "response_type": "code",
        "client_id": reg.client_id,
        "redirect_uri": redirect_uri(provider),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": reg.resource,
        "state": state,
    }
    if reg.scopes:
        params["scope"] = reg.scopes
    return f"{reg.authorization_endpoint}?{urlencode(params)}"


async def exchange_code(provider: Provider, reg: McpClient, code: str, verifier: str) -> dict:
    """Swap the authorization code for tokens at the discovered token endpoint."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri(provider),
        "client_id": reg.client_id,
        "code_verifier": verifier,
        "resource": reg.resource,
    }
    if reg.client_secret:
        data["client_secret"] = reg.client_secret
    async with httpx.AsyncClient(timeout=_DISCOVERY_TIMEOUT) as c:
        resp = await c.post(reg.token_endpoint, data=data, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


async def refresh(provider: Provider, reg: McpClient, refresh_token: str) -> dict:
    """Use a refresh token to obtain a fresh access token (best-effort)."""
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": reg.client_id,
        "resource": reg.resource,
    }
    if reg.client_secret:
        data["client_secret"] = reg.client_secret
    async with httpx.AsyncClient(timeout=_DISCOVERY_TIMEOUT) as c:
        resp = await c.post(reg.token_endpoint, data=data, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()
