# Pulse — Design Intelligence Coach

AI coaching prototype for KPMG: a chat coach that RAGs KPMG's design methodology (Gemini + pgvector) and passively scores every conversation turn into a live Design Quality (DQ) dashboard (employee / manager / leadership views). See README.md for full architecture.

## Stack
- `frontend/` — Next.js 14 + Tailwind + Recharts (port 3000)
- `backend/` — FastAPI + Gemini + Postgres/pgvector (port 8000)
- `docker-compose.yml` — local Postgres + pgvector (port 5432); `supabase/schema.sql` auto-applied on first boot
- `scripts/seed.py` — ingests knowledge + seeds synthetic dashboard data (run once after DB is up)

## Run locally (in order)
```bash
docker compose up -d
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev        # http://localhost:3000
```
Backend needs `backend/.env` with `GEMINI_API_KEY` (copy from `.env.example`). If the venv is missing: `python -m venv .venv && pip install -r requirements.txt`, then `python ../scripts/seed.py`.

There is also `.claude/launch.json` — prefer `preview_start` with the `pulse-frontend` / `pulse-backend` configs over ad-hoc Bash servers.

## Smoke test
- http://localhost:3000/chat — "We already know the solution, let's just build it" should get Socratic pushback
- http://localhost:3000/dashboard/leadership — DQ score renders

## Gotchas / current state
- Deploy target: Cloudflare/Render experiments exist (`render.yaml`); production plan is Azure (env-var swap only, see README table)
- Notion/Figma connector data-pull was a recurring pain point in past sessions — check `backend/app/` integrations before assuming they work
