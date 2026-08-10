# Pulse — The Design Intelligence Coach

An always-on AI coaching system that keeps design thinking alive after the consultant
leaves the room. Pulse does two things at once:

1. **Coaches in the moment** — a chat partner that retrieves KPMG's design methodology
   (RAG) before every answer, asks Socratic questions, is phase- and sector-aware, and
   hands off to a human when empathy fieldwork / real testing / ethical judgment is needed.
2. **Measures passively** — every conversation turn is tagged against the 6 KPMG pillars
   and the design-thinking phase, and aggregated into a live Design Quality (DQ) score
   across three dashboard views (employee / manager / leadership). No surveys.

This repo is the **online prototype**: a web app (Next.js + FastAPI) backed by a central
Postgres + pgvector knowledge store, using Google Gemini for inference. The same code
moves to a private KPMG Azure deployment by swapping environment variables.

---

## Architecture (prototype)

```
Browser → Next.js (chat + dashboard)
            │ POST /chat
            ▼
        FastAPI backend
          1. embed user message (Gemini)
          2. retrieve top-k knowledge chunks (pgvector cosine)
          3. build coaching system prompt + inject chunks
          4. Gemini → coached reply
          5. store raw turn
          6. tag the turn (pillar, phase, evidence, quality)
            ▼
        Postgres + pgvector (knowledge + conversations + interactions)
            ▼
        Dashboard endpoints → weighted DQ score (pure arithmetic, no AI)
```

**Why online:** the knowledge layer is updated regularly. A central vector store means you
update once and every user gets the new knowledge on their next message — no per-device sync.

---

## Quick start

### 1. Prerequisites
- Python 3.11+
- Node 18+
- Docker (for local Postgres + pgvector) **or** a Supabase project
- A Google Gemini API key (free tier): https://aistudio.google.com/apikey

### 2. Database
```bash
docker compose up -d          # starts Postgres + pgvector on localhost:5432
```
The schema in `supabase/schema.sql` is applied automatically on first boot.

### 3. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in GEMINI_API_KEY
python ../scripts/seed.py     # ingest knowledge + seed synthetic dashboard data
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000
```

### 5. Try it
- Open http://localhost:3000/chat
- Send: *"We already know the solution, let's just build it"* → the coach pushes back
- Send: *"Can you tell me how our users will react to this screen?"* → the coach hands off to real testing
- Open http://localhost:3000/dashboard/leadership → watch the DQ score

---

## Prototype → Production (KPMG pilot)

The application code does not change. Swap infrastructure via environment variables:

| Layer | Prototype | Production |
|---|---|---|
| Inference | Gemini free tier | Azure OpenAI (in-tenant) |
| Database | Supabase / local Postgres | Azure Database for PostgreSQL |
| Hosting | Vercel + Railway | Azure Static Web Apps + Container Apps |
| Auth | none (demo user) | Azure Entra ID (SSO) |
