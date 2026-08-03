"""Provider registry — one declarative entry per connectable tool.

Adding a future tool (Slack, GitHub, Drive, …) is a new Provider entry here plus the
OAuth client credentials in .env — no new integration code. Each provider points at a
remote MCP server; the coach talks to it through the standard MCP protocol, so we never
hand-write REST wrappers.

Providers differ in transport and in how they authenticate:
- Linear, Jira (Atlassian): remote MCP server that accepts a classic OAuth-app bearer token
  → transport=MCP, auth_mode="classic" (client id/secret from a developer app in .env).
- Notion: remote MCP server that runs its own OAuth authorization server → transport=MCP,
  auth_mode="mcp" (we discover its endpoints and self-register via Dynamic Client
  Registration, the same flow Claude/ChatGPT use — no developer app needed).
- Figma: its hosted MCP gates the `mcp:connect` scope to approved partners, so third-party
  apps can't use it. We drive Figma over its public REST API instead → transport="rest"
  (see figma_rest.py), with standard Figma OAuth (auth_mode="classic", Basic-auth token
  exchange, granular read scopes) and a registered FIGMA_CLIENT_ID/SECRET.
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

    # How the user's token is obtained:
    #   'classic' — a pre-registered OAuth app (client id/secret in .env); the provider's
    #               own OAuth endpoints (below) are used. Works when the MCP server accepts
    #               classic OAuth-app tokens (Linear, Atlassian/Jira).
    #   'mcp'     — the MCP-native OAuth flow: discover the server's auth endpoints and
    #               self-register via Dynamic Client Registration. No developer app, no
    #               client id/secret. Required by servers that reject classic tokens
    #               (Notion, Figma) — the same mechanism Claude/ChatGPT use.
    auth_mode: str = "classic"

    # OAuth 2.0 (authorization-code) — only used in 'classic' mode
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
        """Whether a real connect can run. MCP-native providers self-register (DCR), so
        they need no server-side credentials and are always 'configured'. Classic
        providers need their OAuth app client id/secret in the environment."""
        if self.auth_mode == "mcp":
            return True
        return bool(self.client_id and self.client_secret)


PROVIDERS: dict[str, Provider] = {
    "notion": Provider(
        key="notion",
        label="Notion",
        capability="Read your notes and create or update pages",
        icon="description",
        mcp_url="https://mcp.notion.com/mcp",
        auth_mode="mcp",  # mcp.notion.com rejects classic integration tokens
    ),
    "figma": Provider(
        key="figma",
        label="Figma",
        capability="Read your design files and leave comments",
        icon="brush",
        # Figma's hosted MCP (mcp.figma.com) gates the `mcp:connect` scope to approved
        # partners only — third-party OAuth apps can't use it. So Figma is the one provider
        # we drive over its public REST API instead of MCP (see connections/figma_rest.py),
        # with standard Figma OAuth (Basic-auth token exchange) and granular read scopes.
        mcp_url="",  # unused for REST providers
        transport="rest",
        authorize_url="https://www.figma.com/oauth",
        token_url="https://api.figma.com/v1/oauth/token",
        scopes="file_content:read file_metadata:read file_comments:read file_comments:write current_user:read projects:read",
        token_auth="basic",  # Figma requires Base64(client_id:client_secret) in the header
        uses_pkce=False,      # confidential client (has a secret); Figma's canonical flow omits PKCE
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
