"""MCP session manager for a user's connected tools.

Two concerns, deliberately split so a plain chat message never pays for tools it won't use:

- **Describing** what tools exist (`tool_menu`) — the menu is identical across all users of
  a provider, so it's discovered once and cached process-wide (`_TOOL_MENU_CACHE`). This is
  what we hand to Gemini so the model can *decide* whether a tool is needed.
- **Executing** a tool call (`ToolSessions`) — this is the only thing that actually needs the
  user's token and a live MCP session, so we open one lazily, per provider, only when the
  model genuinely calls a tool. A message like "hello" therefore contacts no tool server.

Sessions are turn-scoped: opened on demand and torn down via the AsyncExitStack when the
turn ends.
"""
from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from . import store
from .registry import PROVIDERS, Provider

log = logging.getLogger("pulse.connections")

# Don't let a slow/broken provider hang the whole chat turn.
_CONNECT_TIMEOUT = 8.0


@dataclass
class ToolDecl:
    """A single tool's Gemini-ready declaration. Cached process-wide (the menu is identical
    across users of a provider); the user's token is only needed to *call* a tool, not to
    describe it."""
    provider: str   # 'notion' | ...
    label: str      # 'Notion'
    name: str
    description: str
    params: dict


# Process-lifetime cache of each provider's tool menu, keyed by provider. Populated on the
# first turn that reaches a provider after a restart, then reused for every later message —
# so a plain "hello" never re-lists tools. Cleared only when the backend restarts.
_TOOL_MENU_CACHE: dict[str, list[ToolDecl]] = {}


@asynccontextmanager
async def _open_one(provider: Provider, token: str) -> AsyncIterator[ClientSession]:
    """Open and initialize a single MCP session for one provider."""
    headers = {"Authorization": f"Bearer {token}"}
    if provider.transport == "sse":
        transport = sse_client(url=provider.mcp_url, headers=headers, timeout=_CONNECT_TIMEOUT)
    else:
        transport = streamablehttp_client(url=provider.mcp_url, headers=headers, timeout=_CONNECT_TIMEOUT)
    async with transport as streams:
        # streamable_http yields (read, write, get_session_id); sse yields (read, write).
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def _refresh_access_token(user_id: str, provider: Provider) -> str | None:
    """Use the stored refresh token to mint a fresh access token, persist it, and return
    it. Works for both auth modes. Returns None if there's no refresh token or it fails."""
    rt = store.get_refresh_token(user_id, provider.key)
    if not rt:
        return None
    try:
        if provider.auth_mode == "mcp":
            from . import mcp_oauth

            reg = store.get_mcp_client(provider.key) or await mcp_oauth.ensure_registration(provider)
            token_json = await mcp_oauth.refresh(provider, reg, rt)
        else:
            from . import oauth

            token_json = await oauth.refresh_token(provider, rt)
    except Exception as exc:  # noqa: BLE001
        log.warning("token refresh failed for %s (user %s): %s", provider.key, user_id, exc)
        return None
    access = token_json.get("access_token")
    if not access:
        return None
    store.update_tokens(
        user_id, provider.key,
        access_token=access,
        refresh_token=token_json.get("refresh_token"),  # rotated refresh tokens kept
    )
    return access


class ToolSessions:
    """Per-turn pool of live MCP sessions, opened lazily and held open until the turn ends.

    A provider is connected at most once per turn, and only when something actually needs it
    — discovery (listing tools on a cache miss) or an actual tool call. Tokens for some
    providers (Notion, Atlassian) expire after ~an hour, so a failure to connect triggers a
    one-time token refresh and retry; a provider that still can't be reached is skipped
    rather than breaking the turn."""

    def __init__(self, user_id: str, stack: AsyncExitStack):
        self._user_id = user_id
        self._stack = stack
        self._sessions: dict[str, ClientSession] = {}

    async def get(self, key: str) -> ClientSession | None:
        if key in self._sessions:
            return self._sessions[key]
        provider = PROVIDERS.get(key)
        if not provider:
            return None
        token = store.get_token(self._user_id, key)
        if not token:
            return None
        for attempt in range(2):
            try:
                session = await self._stack.enter_async_context(_open_one(provider, token))
                self._sessions[key] = session
                return session
            except Exception as exc:  # noqa: BLE001
                # First failure may just be an expired token — refresh once and retry.
                if attempt == 0:
                    refreshed = await _refresh_access_token(self._user_id, provider)
                    if refreshed:
                        token = refreshed
                        continue
                log.warning("MCP connect failed for %s (user %s): %s", key, self._user_id, exc)
                return None
        return None

    async def call_tool(self, provider: str, name: str, args: dict) -> str:
        """Execute one tool call, opening the owning provider's session on first use.
        Returns the flattened text payload (or an error string) for the model."""
        p = PROVIDERS.get(provider)
        if p and p.transport == "rest":
            return await self._rest_call(p, name, dict(args or {}))
        session = await self.get(provider)
        if session is None:
            return f"Tool error: could not connect to {provider}"
        result = await session.call_tool(name, dict(args or {}))
        return _mcp_result_text(result)

    async def _rest_call(self, provider: Provider, name: str, args: dict) -> str:
        """Dispatch a REST-provider (Figma) tool call. Stateless — just the user's token and
        an HTTP call — with the same one-shot refresh-on-401 the MCP path uses for expiry."""
        from . import figma_rest

        token = store.get_token(self._user_id, provider.key)
        if not token:
            return f"Tool error: not connected to {provider.key}"
        for attempt in range(2):
            try:
                return await figma_rest.dispatch(token, name, args)
            except figma_rest._Unauthorized:
                if attempt == 0:
                    refreshed = await _refresh_access_token(self._user_id, provider)
                    if refreshed:
                        token = refreshed
                        continue
                return f"Tool error: {provider.label} access expired — please reconnect it."
            except Exception as exc:  # noqa: BLE001 — report tool failure to the model
                return f"Tool error: {exc}"
        return f"Tool error: could not reach {provider.label}"


@asynccontextmanager
async def tool_sessions(user_id: str) -> AsyncIterator[ToolSessions]:
    """Open a turn-scoped session pool; every session opened through it is torn down on exit."""
    async with AsyncExitStack() as stack:
        yield ToolSessions(user_id, stack)


async def tool_menu(user_id: str, sessions: ToolSessions) -> list[ToolDecl]:
    """Return the Gemini-ready tool declarations for the user's connected providers.

    Cached process-wide per provider; on a cache miss we connect once (via `sessions`) and
    list that provider's tools. A provider we can't reach right now is skipped and not
    cached, so it recovers on a later turn."""
    from ..llm import _sanitize_schema

    out: list[ToolDecl] = []
    for key in store.connected_providers(user_id):
        cached = _TOOL_MENU_CACHE.get(key)
        if cached is not None:
            out.extend(cached)
            continue
        provider = PROVIDERS.get(key)
        if not provider:
            continue
        # REST providers (Figma) have a static, hand-written tool menu — no MCP session.
        if provider.transport == "rest":
            from . import figma_rest

            decls = figma_rest.tool_decls()
            _TOOL_MENU_CACHE[key] = decls
            out.extend(decls)
            continue
        session = await sessions.get(key)
        if session is None:
            continue
        try:
            listed = await session.list_tools()
        except Exception as exc:  # noqa: BLE001
            log.warning("list_tools failed for %s (user %s): %s", key, user_id, exc)
            continue
        decls = [
            ToolDecl(
                provider=key,
                label=provider.label,
                name=tool.name,
                description=(tool.description or "")[:1024],
                params=_sanitize_schema(tool.inputSchema) or {"type": "object", "properties": {}},
            )
            for tool in listed.tools
        ]
        _TOOL_MENU_CACHE[key] = decls
        out.extend(decls)
    return out


def _mcp_result_text(result) -> str:
    """Flatten an MCP call_tool result into text for the model."""
    if getattr(result, "structuredContent", None):
        return json.dumps(result.structuredContent)[:8000]
    chunks: list[str] = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if text:
            chunks.append(text)
    return ("\n".join(chunks) or "(no content)")[:8000]
