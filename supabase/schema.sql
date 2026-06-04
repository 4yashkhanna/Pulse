-- Pulse — multi-tenant schema (Postgres + pgvector)
-- Embedding dimension 768 (Gemini gemini-embedding-001 @ 768).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Tenants
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    maturity_stage  INT  DEFAULT 2,             -- 1..5
    maturity_label  TEXT DEFAULT 'Designs for aesthetics',
    description     TEXT DEFAULT '',            -- where they are / target
    coach_prompt    TEXT DEFAULT '',            -- org-level config injected into the coach
    settings        JSONB NOT NULL DEFAULT
                      '{"employee_can_see_team": false, "manager_can_see_members": true}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Teams (manager_user_id set after users exist; no hard FK to avoid cycles)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS teams (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    manager_user_id  UUID,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Users (org_id NULL only for KPMG admins)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email          TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    name           TEXT NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('kpmg_admin','manager','employee')),
    team_id        UUID REFERENCES teams(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Knowledge layer (per-org). Documents track each uploaded file.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    filename     TEXT NOT NULL,
    mime         TEXT,
    status       TEXT NOT NULL DEFAULT 'processing',  -- processing|ready|error
    n_chunks     INT  NOT NULL DEFAULT 0,
    error        TEXT,
    uploaded_by  UUID REFERENCES users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    document_id  UUID REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    content      TEXT NOT NULL,
    source       TEXT,
    chunk_index  INT,
    active       BOOLEAN NOT NULL DEFAULT TRUE,
    embedding    vector(768),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_chunks_org_idx ON knowledge_chunks(org_id);
CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- Conversations + messages (chat history)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL DEFAULT 'New chat',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role             TEXT NOT NULL,        -- user|assistant
    content          TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Passive measurement
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interactions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id  UUID REFERENCES conversations(id) ON DELETE CASCADE,
    message_id       UUID REFERENCES messages(id) ON DELETE CASCADE,
    pillar           TEXT,
    phase            TEXT,
    usage_type       TEXT,
    evidence_backed  BOOLEAN DEFAULT FALSE,
    quality_score    INT DEFAULT 3,
    handoff          BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS interactions_org_idx ON interactions(org_id);
CREATE INDEX IF NOT EXISTS interactions_user_idx ON interactions(user_id);

-- ---------------------------------------------------------------------------
-- Fired signals: the audit trail behind every pillar score. One row per
-- behavioural signal the tagger observed in a turn (see app/coach/signals.py).
-- org_id / user_id are denormalised so the dashboard can aggregate without joins.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interaction_signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interaction_id  UUID REFERENCES interactions(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    signal_id       TEXT NOT NULL,        -- e.g. "VAL-5"
    pillar          TEXT NOT NULL,
    polarity        INT  NOT NULL,        -- +1 or -1
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS interaction_signals_org_pillar_idx ON interaction_signals(org_id, pillar);
CREATE INDEX IF NOT EXISTS interaction_signals_user_idx ON interaction_signals(user_id);

-- ---------------------------------------------------------------------------
-- Mocked assessment baseline (per org)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS baseline (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    scope   TEXT NOT NULL,        -- 'org' or a team name
    pillar  TEXT NOT NULL,
    score   NUMERIC NOT NULL
);

-- ---------------------------------------------------------------------------
-- Org-scoped vector search.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_chunks(
    p_org_id        UUID,
    query_embedding vector(768),
    match_count     INT DEFAULT 6
)
RETURNS TABLE (id UUID, content TEXT, source TEXT, similarity FLOAT)
LANGUAGE sql STABLE AS $$
    SELECT kc.id, kc.content, kc.source,
           1 - (kc.embedding <=> query_embedding) AS similarity
    FROM knowledge_chunks kc
    WHERE kc.org_id = p_org_id AND kc.active
    ORDER BY kc.embedding <=> query_embedding
    LIMIT match_count;
$$;
