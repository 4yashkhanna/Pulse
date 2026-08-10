# Pulse — Platform Architecture

Pulse is a **multi-tenant** design-intelligence platform. A KPMG consultant sets up an
organization (tenant), uploads that org's knowledge, and provisions its people. The org's
employees then use the Pulse coach and watch their design quality improve.

## Roles

| Role | Who | Can do |
|---|---|---|
| `kpmg_admin` | KPMG consultant | Everything in the Admin Portal: create orgs, upload knowledge, write the org coach prompt, provision users, assign managers, set visibility |
| `manager` | A team lead inside an org | Use the chatbot; see own dashboard + each team member's dashboard + the combined team dashboard |
| `employee` | An org member | Use the chatbot; see own dashboard |

## The three surfaces

1. **Admin Portal** (`/admin/*`, kpmg_admin only)
   - Organizations: create/manage; set maturity stage + description + **org coach prompt**.
   - **No-code knowledge manager**: drag-drop PDF / DOCX / PPTX / TXT / MD → parsed,
     chunked, embedded into *that org's* private knowledge base. No terminal.
   - Users & teams: invite users, assign roles, group into teams, set a team manager.
   - Visibility: toggles for what employees / managers may see on dashboards.

2. **Pulse Chatbot** (`/chat`, org users) — *next step*
   - Familiar chat UI: conversation list, new chat, search, persisted history.
   - Coach grounded in the org's uploaded knowledge + org coach prompt.

3. **Performance Dashboards** (`/dashboard/*`, org users) — *next step*
   - Individual view; manager view (team members + combined team), permission-gated.

## Tenancy rule

Every domain row carries `org_id`. Knowledge retrieval, conversations, interactions, and
dashboards are **always** filtered by the caller's org. KPMG admins operate across orgs.

## Stack (unchanged seam)

FastAPI · Postgres + pgvector · Gemini behind `app/llm.py` (Azure swap = config only).
Auth: email + password, JWT bearer, three roles. Frontend: Next.js.

## Build order

1. **Foundation** — schema (orgs/users/teams/knowledge/conversations/interactions) + auth + roles.
2. **Admin Portal** — provisioning + no-code ingestion + org prompt.  ← current
3. **Chatbot** — history + search, per-org knowledge.
4. **Dashboards** — individual + manager/team, permission-gated.
