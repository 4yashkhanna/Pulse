"""Central configuration. All environment access lives here so the
prototype → production swap is a matter of changing env values, not code."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

# The 6 KPMG design-maturity pillars and their weights (sum = 1.0).
PILLAR_WEIGHTS: dict[str, float] = {
    "values": 0.25,
    "behavior": 0.20,
    "climate": 0.20,
    "process": 0.10,
    "resources": 0.10,
    "success": 0.15,
}

DT_PHASES = ["empathy", "define", "ideate", "prototype", "test"]
USAGE_TYPES = ["ideation", "poc-scoping", "evidence-check", "synthesis", "reframing"]


class Settings:
    def __init__(self) -> None:
        self.env: str = os.getenv("PULSE_ENV", "dev").lower()  # dev | prod
        self.database_url: str = os.getenv(
            "DATABASE_URL", "postgresql://pulse:pulse@localhost:5432/pulse"
        )
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.embed_model: str = os.getenv("EMBED_MODEL", "gemini-embedding-001")
        self.chat_model: str = os.getenv("CHAT_MODEL", "gemini-3.5-flash")
        self.tag_model: str = os.getenv("TAG_MODEL", "gemini-3.5-flash")
        self.embed_dim: int = 768
        # Chunks below this cosine similarity are dropped from the coach's context
        # rather than injected as irrelevant "knowledge".
        self.min_similarity: float = float(os.getenv("MIN_SIMILARITY", "0.30"))
        self.synchronous_tagging: bool = (
            os.getenv("SYNCHRONOUS_TAGGING", "true").lower() == "true"
        )
        self.frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
        # Public base URL of THIS backend — used to build OAuth redirect URIs for
        # tool connections (Notion/Figma/Linear/Jira). Must match what you register
        # in each provider's developer console.
        self.backend_base_url: str = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
        # Secret used to encrypt stored connection tokens at rest. In dev we derive a
        # stable key from JWT_SECRET so no extra setup is needed; in prod set a real
        # Fernet key (CONNECTIONS_SECRET) — `python -c "from cryptography.fernet import
        # Fernet; print(Fernet.generate_key().decode())"`.
        self.connections_secret: str = os.getenv("CONNECTIONS_SECRET", "")

        # Auth
        self.jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
        self.jwt_ttl_hours: int = int(os.getenv("JWT_TTL_HOURS", "24"))
        if self.env == "prod" and self.jwt_secret == "dev-secret-change-me":
            raise RuntimeError(
                "JWT_SECRET must be set to a strong random value when PULSE_ENV=prod."
            )
        if self.env == "prod" and not self.connections_secret:
            raise RuntimeError(
                "CONNECTIONS_SECRET (a Fernet key) must be set when PULSE_ENV=prod."
            )

        # Invite emails, sent via Brevo's HTTP API (not SMTP — Render's free tier
        # blocks outbound SMTP ports 25/465/587, but HTTPS/443 is unrestricted).
        # Get an API key from Brevo dashboard -> Settings -> SMTP & API -> API Keys.
        self.brevo_api_key: str = os.getenv("BREVO_API_KEY", "")
        self.brevo_sender_email: str = os.getenv("BREVO_SENDER_EMAIL", "")
        self.brevo_sender_name: str = os.getenv("BREVO_SENDER_NAME", "Pulse")
        self.invite_ttl_hours: int = int(os.getenv("INVITE_TTL_HOURS", "168"))
        self.reset_ttl_hours: int = int(os.getenv("RESET_TTL_HOURS", "1"))

        # Azure (production) — read but unused in the prototype.
        self.azure_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.azure_key: str = os.getenv("AZURE_OPENAI_KEY", "")
        self.azure_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")


@lru_cache
def get_settings() -> Settings:
    return Settings()
