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
        self.database_url: str = os.getenv(
            "DATABASE_URL", "postgresql://pulse:pulse@localhost:5432/pulse"
        )
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.embed_model: str = os.getenv("EMBED_MODEL", "gemini-embedding-001")
        self.chat_model: str = os.getenv("CHAT_MODEL", "gemini-3.5-flash")
        self.tag_model: str = os.getenv("TAG_MODEL", "gemini-3.5-flash")
        self.embed_dim: int = 768
        self.synchronous_tagging: bool = (
            os.getenv("SYNCHRONOUS_TAGGING", "true").lower() == "true"
        )
        self.frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

        # Auth
        self.jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
        self.jwt_ttl_hours: int = int(os.getenv("JWT_TTL_HOURS", "24"))

        # Azure (production) — read but unused in the prototype.
        self.azure_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.azure_key: str = os.getenv("AZURE_OPENAI_KEY", "")
        self.azure_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")


@lru_cache
def get_settings() -> Settings:
    return Settings()
