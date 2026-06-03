"""Pulse FastAPI application."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .coach import chat as coach_chat
from .config import get_settings
from .dashboard.routes import router as dashboard_router
from .schemas import ChatRequest, ChatResponse, RetrievedChunk

settings = get_settings()

app = FastAPI(title="Pulse — Design Intelligence Coach", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok", "provider": settings.llm_provider}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = coach_chat.run_turn(
        message=req.message,
        user_id=req.user_id,
        sector=req.sector,
        conversation_id=req.conversation_id,
        history=[t.model_dump() for t in req.history],
    )
    return ChatResponse(
        reply=result.reply,
        conversation_id=result.conversation_id,
        retrieved=[
            RetrievedChunk(
                framework=c.framework,
                pillar=c.pillar,
                phase=c.phase,
                similarity=round(c.similarity, 3),
            )
            for c in result.chunks
        ],
        tag=result.tag,
    )
