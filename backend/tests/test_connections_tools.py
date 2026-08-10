"""Tests for the tool-menu cache + lazy MCP session pool.

These cover the core latency fix: the tool *menu* is discovered once and cached process-wide
(so a plain message never re-lists tools), and a provider's MCP session is opened only when a
tool is actually called (so "hello" contacts no tool server).
"""
import asyncio
from contextlib import asynccontextmanager

import pytest

from app.connections import mcp_client
from app.connections.mcp_client import ToolSessions, ToolDecl, tool_menu, _mcp_result_text


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _clear_cache():
    mcp_client._TOOL_MENU_CACHE.clear()
    yield
    mcp_client._TOOL_MENU_CACHE.clear()


# --- fakes -------------------------------------------------------------------

class _FakeListed:
    def __init__(self, tools):
        self.tools = tools


class _FakeTool:
    def __init__(self, name):
        self.name = name
        self.description = f"{name} tool"
        self.inputSchema = {"type": "object", "properties": {"q": {"type": "string"}}}


class _FakeSession:
    def __init__(self):
        self.list_calls = 0
        self.tool_calls = []

    async def list_tools(self):
        self.list_calls += 1
        return _FakeListed([_FakeTool("search"), _FakeTool("create")])

    async def call_tool(self, name, args):
        self.tool_calls.append((name, args))
        class _R:
            structuredContent = {"ok": True, "name": name}
        return _R()


class _FakeSessions:
    """Stand-in for ToolSessions: counts how often a provider is opened via get()."""
    def __init__(self):
        self.session = _FakeSession()
        self.get_calls = []

    async def get(self, key):
        self.get_calls.append(key)
        return self.session

    async def call_tool(self, provider, name, args):
        return await ToolSessions.call_tool(self, provider, name, args)  # reuse real flatten path


# --- tool_menu caching -------------------------------------------------------

def test_tool_menu_discovers_then_caches(monkeypatch):
    monkeypatch.setattr(mcp_client.store, "connected_providers", lambda uid: ["notion"])
    sessions = _FakeSessions()

    decls = run(tool_menu("u1", sessions))
    assert [d.name for d in decls] == ["search", "create"]
    assert all(d.provider == "notion" and d.label == "Notion" for d in decls)
    assert sessions.session.list_calls == 1          # discovered once
    assert sessions.get_calls == ["notion"]          # connected once for discovery

    # Second call (even a different user/session) is a pure cache hit: no new connect/list.
    sessions2 = _FakeSessions()
    decls2 = run(tool_menu("u2", sessions2))
    assert [d.name for d in decls2] == ["search", "create"]
    assert sessions2.get_calls == []                 # never opened a session
    assert sessions2.session.list_calls == 0


def test_tool_menu_skips_unreachable_provider_without_caching(monkeypatch):
    monkeypatch.setattr(mcp_client.store, "connected_providers", lambda uid: ["notion"])

    class _DeadSessions:
        async def get(self, key):
            return None  # can't connect right now

    decls = run(tool_menu("u1", _DeadSessions()))
    assert decls == []
    assert "notion" not in mcp_client._TOOL_MENU_CACHE  # failure not cached → recovers later


# --- lazy session pool -------------------------------------------------------

def test_toolsessions_opens_once_and_reuses(monkeypatch):
    fake = _FakeSession()
    opens = []

    @asynccontextmanager
    async def _fake_open_one(provider, token):
        opens.append(provider.key)
        yield fake

    monkeypatch.setattr(mcp_client, "_open_one", _fake_open_one)
    monkeypatch.setattr(mcp_client.store, "get_token", lambda uid, key: "tok")

    async def _scenario():
        async with mcp_client.tool_sessions("u1") as sessions:
            a = await sessions.get("notion")
            b = await sessions.get("notion")          # cached within the turn
            assert a is b
            payload = await sessions.call_tool("notion", "search", {"q": "x"})
            return payload

    payload = run(_scenario())
    assert opens == ["notion"]                        # connected exactly once
    assert fake.tool_calls == [("search", {"q": "x"})]
    assert '"ok": true' in payload.lower()


def test_mcp_result_text_flattens_text_content():
    class _Item:
        text = "hello world"
    class _R:
        structuredContent = None
        content = [_Item()]
    assert _mcp_result_text(_R()) == "hello world"
