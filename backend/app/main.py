"""Pulse FastAPI application (multi-tenant)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.routes import router as auth_router
from .coach.routes import router as coach_router
from .config import get_settings
from .dashboard.routes import router as dashboard_router
from .knowledge.routes import router as knowledge_router
from .knowledge.scoped_routes import router as scoped_knowledge_router
from .orgs.routes import router as orgs_router

settings = get_settings()

app = FastAPI(title="Pulse — Design Intelligence Platform", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(orgs_router)
app.include_router(knowledge_router)
app.include_router(scoped_knowledge_router)
app.include_router(coach_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok", "provider": settings.llm_provider}
