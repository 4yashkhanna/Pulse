-- Pulse — database schema (Postgres + pgvector)
-- Embedding dimension 768 matches Gemini text-embedding-004.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Knowledge layer (the RAG store / differentiator)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content     TEXT        NOT NULL,
    source      TEXT,                       -- file the chunk came from
    framework   TEXT,                       -- e.g. "Journey Map", "JTBD"
    pillar      TEXT,                       -- one of the 6 pillars (nullable)
    phase       TEXT,                       -- empathy|define|ideate|prototype|test
    industry    TEXT,                       -- it|fmcg|generic
    active      BOOLEAN     NOT NULL DEFAULT TRUE,   -- soft delete / rollback
    embedding   vector(768),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Approximate nearest-neighbour index (cosine).
CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- People (mocked cohort in the prototype; Entra ID in production)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name    TEXT NOT NULL,
    dept    TEXT,
    role    TEXT,
    sector  TEXT          -- it|fmcg|... drives industry calibration
);

-- ---------------------------------------------------------------------------
-- Conversations + raw turns (stay server-side; only metrics roll up)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    sector      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role             TEXT NOT NULL,        -- user|assistant
    content          TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Passive measurement: one row per tagged user turn. Drives the dashboard.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interactions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID REFERENCES conversations(id) ON DELETE CASCADE,
    message_id       UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id          UUID REFERENCES users(id),
    pillar           TEXT,     -- values|behavior|climate|process|resources|success
    phase            TEXT,     -- empathy|define|ideate|prototype|test
    usage_type       TEXT,     -- ideation|poc-scoping|evidence-check|synthesis|reframing
    evidence_backed  BOOLEAN   DEFAULT FALSE,
    quality_score    INT       DEFAULT 3,   -- 1..5 sophistication
    handoff          BOOLEAN   DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS interactions_user_idx ON interactions(user_id);
CREATE INDEX IF NOT EXISTS interactions_created_idx ON interactions(created_at);

-- ---------------------------------------------------------------------------
-- Mocked assessment baseline (per scope = dept or "org", per pillar)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS baseline (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope   TEXT NOT NULL,        -- "org" or a department name
    pillar  TEXT NOT NULL,
    score   NUMERIC NOT NULL      -- 0..100 baseline pillar score
);

-- ---------------------------------------------------------------------------
-- Vector search function used by retrieval.
-- Returns the most similar ACTIVE chunks, optionally filtered by industry.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(768),
    match_count     INT DEFAULT 6,
    filter_industry TEXT DEFAULT NULL
)
RETURNS TABLE (
    id         UUID,
    content    TEXT,
    framework  TEXT,
    pillar     TEXT,
    phase      TEXT,
    industry   TEXT,
    similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        kc.id,
        kc.content,
        kc.framework,
        kc.pillar,
        kc.phase,
        kc.industry,
        1 - (kc.embedding <=> query_embedding) AS similarity
    FROM knowledge_chunks kc
    WHERE kc.active
      AND (
            filter_industry IS NULL
            OR kc.industry = filter_industry
            OR kc.industry = 'generic'
          )
    ORDER BY kc.embedding <=> query_embedding
    LIMIT match_count;
$$;
