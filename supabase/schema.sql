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
-- ---------------------------------------------------------------------------
-- Projects: a personal project (owner_kind='user') or a team project
-- (owner_kind='team'). Knowledge and conversations can belong to a project.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    owner_kind  TEXT NOT NULL,        -- 'user' | 'team'
    owner_id    UUID NOT NULL,        -- user_id or team_id
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS projects_owner_idx ON projects(owner_kind, owner_id);

-- ---------------------------------------------------------------------------
-- Knowledge folders: manager-curated RAG sets for a team, shareable per person.
-- A member with granted access can import a folder into one of their projects.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_folders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    team_id     UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-member access to a folder: 'granted' or 'requested'.
CREATE TABLE IF NOT EXISTS folder_access (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folder_id   UUID NOT NULL REFERENCES knowledge_folders(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'requested',  -- granted | requested
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (folder_id, user_id)
);

-- A folder imported into a personal project (its knowledge joins that project's RAG).
CREATE TABLE IF NOT EXISTS project_folder_imports (
    project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    folder_id   UUID NOT NULL REFERENCES knowledge_folders(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, folder_id)
);

-- ---------------------------------------------------------------------------
-- Knowledge templates: global (no org) premade RAG sets per maturity stage or
-- sector, curated by KPMG admins. Applying one to an org COPIES its documents
-- (chunks + embeddings included) into that org's knowledge.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_templates (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind        TEXT NOT NULL CHECK (kind IN ('stage','sector')),
    key         TEXT NOT NULL,        -- 'stage-1'..'stage-5' or sector slug e.g. 'tech'
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (kind, key)
);

-- ---------------------------------------------------------------------------
-- Skills: admin-authored slash-command behaviours (like /design-thinking).
-- Granted per-org; a user pins one to a conversation by starting it with /command.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    command     TEXT UNIQUE NOT NULL,  -- without the slash, e.g. 'design-thinking'
    description TEXT DEFAULT '',
    body        TEXT NOT NULL,         -- instructions injected into the system prompt
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS org_skills (
    org_id    UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    skill_id  UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (org_id, skill_id)
);

-- scope ∈ ('org','team','user','template'); scope_id is the org/team/user/template id.
-- project_id is set when the document belongs to a specific project (NULL = general bucket).
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,  -- NULL for templates
    scope        TEXT NOT NULL DEFAULT 'org',
    scope_id     UUID,
    filename     TEXT NOT NULL,
    mime         TEXT,
    status       TEXT NOT NULL DEFAULT 'processing',  -- processing|ready|error
    n_chunks     INT  NOT NULL DEFAULT 0,
    error        TEXT,
    uploaded_by  UUID REFERENCES users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'org';
ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS scope_id UUID;
ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS project_id UUID;
ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS folder_id UUID;
ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS from_template_id UUID;  -- provenance
ALTER TABLE knowledge_documents ALTER COLUMN org_id DROP NOT NULL;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,  -- NULL for templates
    document_id  UUID REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    scope        TEXT NOT NULL DEFAULT 'org',
    scope_id     UUID,
    content      TEXT NOT NULL,
    source       TEXT,
    chunk_index  INT,
    active       BOOLEAN NOT NULL DEFAULT TRUE,
    embedding    vector(768),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'org';
ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS scope_id UUID;
ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS project_id UUID;
ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS folder_id UUID;
ALTER TABLE knowledge_chunks ALTER COLUMN org_id DROP NOT NULL;

CREATE INDEX IF NOT EXISTS knowledge_chunks_org_idx ON knowledge_chunks(org_id);
CREATE INDEX IF NOT EXISTS knowledge_chunks_scope_idx ON knowledge_chunks(scope, scope_id);
CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- Conversations + messages (chat history)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id  UUID REFERENCES projects(id) ON DELETE SET NULL,
    title       TEXT NOT NULL DEFAULT 'New chat',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS skill_id UUID REFERENCES skills(id) ON DELETE SET NULL;

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
    evidence        TEXT,                 -- short quote/paraphrase that triggered the signal
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- For databases created before `evidence` existed:
ALTER TABLE interaction_signals ADD COLUMN IF NOT EXISTS evidence TEXT;

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
-- Layered vector search: org knowledge + the caller's team knowledge + their
-- personal/project knowledge, all merged and ranked by similarity.
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS match_chunks(UUID, vector, INT);
DROP FUNCTION IF EXISTS match_chunks(UUID, UUID, UUID, vector, INT);
DROP FUNCTION IF EXISTS match_chunks(UUID, UUID, UUID, UUID[], vector, INT);

-- Always: org-general + the caller's team-general. Plus, when chatting inside a
-- project: that project's own knowledge AND any imported folders (p_folder_ids =
-- folders imported into the project that the caller has been granted access to).
CREATE OR REPLACE FUNCTION match_chunks(
    p_org_id        UUID,
    p_team_id       UUID,
    p_project_id    UUID,
    p_folder_ids    UUID[],
    query_embedding vector(768),
    match_count     INT DEFAULT 6
)
RETURNS TABLE (id UUID, content TEXT, source TEXT, scope TEXT, similarity FLOAT)
LANGUAGE sql STABLE AS $$
    SELECT kc.id, kc.content, kc.source, kc.scope,
           1 - (kc.embedding <=> query_embedding) AS similarity
    FROM knowledge_chunks kc
    WHERE kc.org_id = p_org_id AND kc.active
      AND (
            (kc.scope = 'org' AND kc.project_id IS NULL AND kc.folder_id IS NULL)
            OR (kc.scope = 'team' AND kc.scope_id = p_team_id AND kc.project_id IS NULL AND kc.folder_id IS NULL)
            OR (kc.project_id = p_project_id)
            OR (kc.folder_id = ANY(p_folder_ids))
          )
    ORDER BY kc.embedding <=> query_embedding
    LIMIT match_count;
$$;
