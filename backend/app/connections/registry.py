"""Provider registry — one declarative entry per connectable tool.

Adding a future tool (Slack, GitHub, Drive, …) is a new Provider entry here plus the
OAuth client credentials in .env — no new integration code. Each provider points at a
remote MCP server; the coach talks to it through the standard MCP protocol, so we never
hand-write REST wrappers.

OAuth note: Notion, Linear and Atlassian run hosted MCP servers with their own OAuth.
Figma's MCP is primarily a local desktop server today, so it's the most likely to need
adjustment for a hosted multi-user deployment — flagged with `experimental=True`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Provider:
    key: str                       # 'notion' | 'figma' | 'linear' | 'jira'
    label: str                     # display name
    capability: str                # short human description of what the coach can do
    icon: str                      # material-symbol name for the UI card

    # MCP transport
    mcp_url: str                   # remote MCP server endpoint
    transport: str = "streamable_http"  # 'streamable_http' | 'sse'

    # OAuth 2.0 (authorization-code)
    authorize_url: str = ""
    token_url: str = ""
    scopes: str = ""               # space-separated
    extra_authorize_params: dict[str, str] = field(default_factory=dict)
    uses_pkce: bool = True

    # token-exchange shape: how client creds are sent ('basic' header vs 'body' params)
    # and the request encoding ('form' vs 'json').
    token_auth: str = "body"       # 'basic' | 'body'
    token_format: str = "form"     # 'form' | 'json'

    # env var names holding this provider's OAuth client credentials
    client_id_env: str = ""
    client_secret_env: str = ""

    experimental: bool = False

    # ---- runtime helpers ---------------------------------------------------
    @property
    def client_id(self) -> str:
        return os.getenv(self.client_id_env, "")

    @property
    def client_secret(self) -> str:
        return os.getenv(self.client_secret_env, "")

    @property
    def configured(self) -> bool:
        """True when OAuth client credentials are present, so a real connect can run."""
        return bool(self.client_id and self.client_secret)


PROVIDERS: dict[str, Provider] = {
    "notion": Provider(
        key="notion",
        label="Notion",
        capability="Read your notes and create or update pages",
        icon="description",
        mcp_url="https://mcp.notion.com/mcp",
        authorize_url="https://api.notion.com/v1/oauth/authorize",
        token_url="https://api.notion.com/v1/oauth/token",
        scopes="",  # Notion grants are page-level at consent time, not scope strings
        extra_authorize_params={"owner": "user"},
        uses_pkce=False,  # Notion uses HTTP Basic client auth on the token exchange
        token_auth="basic",
        token_format="json",
        client_id_env="NOTION_CLIENT_ID",
        client_secret_env="NOTION_CLIENT_SECRET",
    ),
    "figma": Provider(
        key="figma",
        label="Figma",
        capability="Read your design files and leave comments",
        icon="brush",
        mcp_url="https://mcp.figma.com/mcp",
        authorize_url="https://www.figma.com/oauth",
        token_url="https://api.figma.com/v1/oauth/token",
        scopes="file_read file_comments:write",
        client_id_env="FIGMA_CLIENT_ID",
        client_secret_env="FIGMA_CLIENT_SECRET",
        experimental=True,
    ),
    "linear": Provider(
        key="linear",
        label="Linear",
        capability="Read your issues and projects",
        icon="checklist",
        mcp_url="https://mcp.linear.app/mcp",
        authorize_url="https://linear.app/oauth/authorize",
        token_url="https://api.linear.app/oauth/token",
        scopes="read",
        client_id_env="LINEAR_CLIENT_ID",
        client_secret_env="LINEAR_CLIENT_SECRET",
    ),
    "jira": Provider(
        key="jira",
        label="Jira",
        capability="Read your issues and project context",
        icon="task_alt",
        mcp_url="https://mcp.atlassian.com/v1/sse",
        transport="sse",
        authorize_url="https://auth.atlassian.com/authorize",
        token_url="https://auth.atlassian.com/oauth/token",
        scopes="read:jira-work offline_access",
        extra_authorize_params={"audience": "api.atlassian.com", "prompt": "consent"},
        client_id_env="JIRA_CLIENT_ID",
        client_secret_env="JIRA_CLIENT_SECRET",
    ),
}


def get_provider(key: str) -> Provider | None:
    return PROVIDERS.get(key)
