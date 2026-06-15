"""MCP session manager — opens live MCP sessions for a user's connected tools.

At chat time we look up which providers the user has connected, open an MCP session to
each remote server (injecting that user's decrypted OAuth token as a bearer), and hand
the initialized sessions to Gemini as tools. The google-genai SDK natively accepts an
MCP ClientSession in `tools=[...]` and translates the tool calls for us.

Everything here is async and request-scoped: sessions are opened for one turn and torn
down via the AsyncExitStack when the turn ends.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
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
class LiveTool:
    provider: str          # 'notion' | ...
    label: str             # 'Notion'
    session: ClientSession


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


@asynccontextmanager
async def open_user_tools(user_id: str) -> AsyncIterator[list[LiveTool]]:
    """Yield live MCP sessions for every provider this user has connected.

    A provider that fails to connect (expired token, server down) is skipped with a log
    line rather than breaking the chat turn — the coach simply works without that tool.
    """
    from contextlib import AsyncExitStack

    providers = store.connected_providers(user_id)
    tools: list[LiveTool] = []
    async with AsyncExitStack() as stack:
        for key in providers:
            provider = PROVIDERS.get(key)
            if not provider:
                continue
            token = store.get_token(user_id, key)
            if not token:
                continue
            try:
                session = await stack.enter_async_context(_open_one(provider, token))
                tools.append(LiveTool(provider=key, label=provider.label, session=session))
            except Exception as exc:  # noqa: BLE001
                log.warning("MCP connect failed for %s (user %s): %s", key, user_id, exc)
        yield tools
