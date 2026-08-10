"""Figma over its public REST API — the one provider we don't drive through MCP.

Figma's hosted MCP server gates the `mcp:connect` OAuth scope to approved partners, so a
third-party app like Pulse can't connect to it. Instead we expose a small, hand-picked set
of Figma REST endpoints as "tools" with the same shape the MCP path produces (ToolDecl +
a string-returning dispatch), so the coach's tool loop treats Figma identically to Notion,
Linear, and Jira — it never knows the transport differs.

Scope of the tools, matched to the coaching use case (read design context, leave comments):
  figma_get_me          — who the connected account is
  figma_get_file        — a file's page/frame structure from a Figma URL or key
  figma_get_comments    — comments on a file
  figma_post_comment    — leave a comment (write — gated by the constitution's boundary)

Listing: Figma's REST API has no global "list all my files" (it can't even enumerate the
user's teams), but given a TEAM link it can walk team → projects → files. So the flow is
link-driven: the person shares a team/project/file URL and the coach reads or lists from it.
"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .mcp_client import ToolDecl

_API = "https://api.figma.com/v1"
_TIMEOUT = 15.0
_MAX_OUT = 8000  # mirror the MCP path's payload cap


class _Unauthorized(Exception):
    """Figma returned 401 — the access token is expired; caller should refresh and retry."""


# Tools are static for every user, so the declarations are built once.
_LABEL = "Figma"


def tool_decls() -> list[ToolDecl]:
    """The Gemini-ready Figma tool menu. Static — no live session needed to describe it."""
    return [
        ToolDecl(
            provider="figma", label=_LABEL, name="figma_get_me",
            description="Get the connected Figma account (name, email). Use to confirm whose Figma is connected.",
            params={"type": "object", "properties": {}},
        ),
        ToolDecl(
            provider="figma", label=_LABEL, name="figma_list_team_projects",
            description=(
                "List all projects in a Figma team, given the team's URL or numeric team id. "
                "Use this first when someone asks what's in their Figma — they share their team "
                "link, you list its projects, then drill into a project's files with figma_list_project_files."
            ),
            params={
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "A Figma team URL (https://www.figma.com/files/team/ID/...) or the raw numeric team id."},
                },
                "required": ["team"],
            },
        ),
        ToolDecl(
            provider="figma", label=_LABEL, name="figma_list_project_files",
            description="List all files in a Figma project, given the project's URL or numeric project id (from figma_list_team_projects).",
            params={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "A Figma project URL or the raw numeric project id."},
                },
                "required": ["project"],
            },
        ),
        ToolDecl(
            provider="figma", label=_LABEL, name="figma_get_file",
            description=(
                "Read a Figma file's structure (pages and top-level frames, by name) from a "
                "Figma file URL or key. Use this to understand what a design contains before "
                "coaching on it. Pass the URL the person shared."
            ),
            params={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "A Figma file URL (https://www.figma.com/design/KEY/...) or the raw file key."},
                    "depth": {"type": "integer", "description": "How deep to walk the node tree (default 2: pages + their top-level frames). Increase to see nested frames."},
                },
                "required": ["file"],
            },
        ),
        ToolDecl(
            provider="figma", label=_LABEL, name="figma_get_comments",
            description="List the comments on a Figma file, given its URL or key. Use to see existing design feedback.",
            params={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "A Figma file URL or the raw file key."},
                },
                "required": ["file"],
            },
        ),
        ToolDecl(
            provider="figma", label=_LABEL, name="figma_post_comment",
            description=(
                "Post a comment on a Figma file (a WRITE action — only do this when the person "
                "explicitly asks you to leave a comment). Given the file URL or key and the message text."
            ),
            params={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "A Figma file URL or the raw file key."},
                    "message": {"type": "string", "description": "The comment text to post."},
                },
                "required": ["file", "message"],
            },
        ),
    ]


def _file_key(file: str) -> str | None:
    """Extract a Figma file key from a URL like .../file/KEY/... or .../design/KEY/..., or
    accept a raw key as-is."""
    if not file:
        return None
    m = re.search(r"/(?:file|design)/([A-Za-z0-9]+)", file)
    if m:
        return m.group(1)
    # A bare key: Figma keys are alphanumeric and reasonably long.
    if re.fullmatch(r"[A-Za-z0-9]{10,}", file.strip()):
        return file.strip()
    return None


def _numeric_id(value: str, kind: str) -> str | None:
    """Extract a Figma team/project id (numeric) from a URL like .../team/123/... or
    .../project/123/..., or accept a raw numeric id."""
    if not value:
        return None
    m = re.search(rf"/{kind}/(\d+)", value)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d{4,}", value.strip()):
        return value.strip()
    return None


def _summarize_file(doc: dict) -> dict:
    """Flatten a Figma document tree to {name, type, children} keeping only names/types, so
    the model gets the structure without the megabytes of geometry the REST file payload
    carries."""
    def walk(node: dict) -> dict:
        out: dict[str, Any] = {"name": node.get("name"), "type": node.get("type")}
        kids = node.get("children")
        if kids:
            out["children"] = [walk(k) for k in kids]
        return out

    return walk(doc) if doc else {}


async def _request(method: str, path: str, token: str, **kw) -> Any:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        resp = await c.request(method, f"{_API}{path}", headers=headers, **kw)
    if resp.status_code == 401:
        raise _Unauthorized()
    resp.raise_for_status()
    return resp.json()


async def dispatch(token: str, name: str, args: dict) -> str:
    """Execute one Figma tool call, returning a flattened-text payload for the model. Raises
    _Unauthorized on an expired token so the caller can refresh and retry."""
    args = args or {}

    if name == "figma_get_me":
        me = await _request("GET", "/me", token)
        return json.dumps({k: me.get(k) for k in ("id", "handle", "email", "img_url")})[:_MAX_OUT]

    if name == "figma_list_team_projects":
        team_id = _numeric_id(args.get("team", ""), "team")
        if not team_id:
            return "Tool error: couldn't find a team id — share the Figma team URL (it contains /team/<number>/)."
        data = await _request("GET", f"/teams/{team_id}/projects", token)
        projects = [{"id": p.get("id"), "name": p.get("name")} for p in data.get("projects", [])]
        return json.dumps({"team": data.get("name"), "projects": projects})[:_MAX_OUT]

    if name == "figma_list_project_files":
        project_id = _numeric_id(args.get("project", ""), "project")
        if not project_id:
            return "Tool error: couldn't find a project id — pass a project URL or its numeric id."
        data = await _request("GET", f"/projects/{project_id}/files", token)
        files = [{"key": f.get("key"), "name": f.get("name"), "last_modified": f.get("last_modified")} for f in data.get("files", [])]
        return json.dumps({"files": files})[:_MAX_OUT]

    if name in ("figma_get_file", "figma_get_comments", "figma_post_comment"):
        key = _file_key(args.get("file", ""))
        if not key:
            return "Tool error: couldn't find a Figma file key in that input — share the file's URL."

        if name == "figma_get_file":
            depth = args.get("depth") or 2
            data = await _request("GET", f"/files/{key}", token, params={"depth": depth})
            summary = {
                "name": data.get("name"),
                "lastModified": data.get("lastModified"),
                "structure": _summarize_file(data.get("document", {})),
            }
            return json.dumps(summary)[:_MAX_OUT]

        if name == "figma_get_comments":
            data = await _request("GET", f"/files/{key}/comments", token)
            comments = [
                {
                    "author": (c.get("user") or {}).get("handle"),
                    "message": c.get("message"),
                    "created_at": c.get("created_at"),
                }
                for c in data.get("comments", [])
            ]
            return json.dumps({"comments": comments})[:_MAX_OUT]

        if name == "figma_post_comment":
            message = (args.get("message") or "").strip()
            if not message:
                return "Tool error: no comment message provided."
            data = await _request("POST", f"/files/{key}/comments", token, json={"message": message})
            return json.dumps({"posted": True, "id": data.get("id"), "message": data.get("message")})[:_MAX_OUT]

    return f"Tool error: unknown Figma tool '{name}'"
