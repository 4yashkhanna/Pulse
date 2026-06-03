"""Pydantic request/response models for the API."""
from __future__ import annotations

from pydantic import BaseModel


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    user_id: str
    sector: str | None = None
    conversation_id: str | None = None
    history: list[ChatTurn] = []


class RetrievedChunk(BaseModel):
    framework: str | None
    pillar: str | None
    phase: str | None
    similarity: float


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    retrieved: list[RetrievedChunk]
    tag: dict | None = None
