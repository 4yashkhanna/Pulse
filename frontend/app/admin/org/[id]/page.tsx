"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Guard from "@/components/Guard";
import {
  KDoc,
  KTemplate,
  Org,
  OrgUser,
  Team,
  applyTemplate,
  createTeam,
  createUser,
  deleteDoc,
  getOrg,
  grantSkill,
  listDocs,
  listTeams,
  listTemplates,
  listUsers,
  orgSkillGrants,
  revokeSkill,
  updateOrg,
  uploadDocs,
} from "@/lib/api";

const TABS = ["Overview", "Knowledge", "Pulse Config", "People Access"] as const;
type Tab = (typeof TABS)[number];

const STAGES = [
  { n: 1, label: "Initial Assessment" },
  { n: 2, label: "Foundation" },
  { n: 3, label: "Optimization" },
  { n: 4, label: "Optimized" },
  { n: 5, label: "Target Goal" },
];

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function OrgDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [org, setOrg] = useState<Org | null>(null);
  const [tab, setTab] = useState<Tab>("Overview");

  useEffect(() => {
    getOrg(id).then(setOrg);
  }, [id]);

  if (!org) return <div className="app-main flex items-center justify-center muted">Loading…</div>;

  return (
    <div className="app-main">
      {/* TopNavBar */}
      <header className="topbar" style={{ flexWrap: "wrap", height: "auto", paddingBottom: 0 }}>
        <div className="w-full flex justify-between items-center" style={{ minHeight: 56 }}>
          <div className="flex items-center gap-4">
            <button
              className="flex items-center gap-2 text-primary hover:bg-surface-container-low px-2 py-1 rounded transition-colors"
              onClick={() => router.push("/admin")}
            >
              <span className="material-symbols-outlined">arrow_back</span>
            </button>
            <div className="flex items-center gap-3">
              <h2 className="text-headline-md text-primary font-bold">{org.name}</h2>
              <span className="px-2 py-0.5 bg-surface-tint text-on-primary text-label-caps rounded" style={{ fontSize: 10 }}>
                STAGE {org.maturity_stage}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-2 text-on-surface-variant hover:bg-surface-container-low rounded-full transition-colors relative">
              <span className="material-symbols-outlined">notifications</span>
              <span className="absolute top-1 right-1 w-2 h-2 bg-error rounded-full" />
            </button>
            <button className="p-2 text-on-surface-variant hover:bg-surface-container-low rounded-full transition-colors">
              <span className="material-symbols-outlined">help</span>
            </button>
          </div>
        </div>
        {/* Sub navigation */}
        <nav className="w-full flex gap-8">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`pb-3 border-b-2 text-label-sm transition-colors ${
                tab === t
                  ? "border-pulse-teal-vibrant text-primary font-bold"
                  : "border-transparent text-on-surface-variant hover:text-primary"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>

      <div className="page-canvas">
        {tab === "Overview" && <OverviewTab org={org} />}
        {tab === "Knowledge" && <KnowledgeTab org={org} onSaved={setOrg} />}
        {tab === "Pulse Config" && <ConfigTab org={org} onSaved={setOrg} />}
        {tab === "People Access" && <PeopleTab orgId={id} />}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Overview
// --------------------------------------------------------------------------- //
function OverviewTab({ org }: { org: Org }) {
  const [users, setUsers] = useState<OrgUser[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [docs, setDocs] = useState<KDoc[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    listUsers(org.id).then(setUsers).catch(() => {});
    listTeams(org.id).then(setTeams).catch(() => {});
    listDocs(org.id).then(setDocs).catch(() => {});
  }, [org.id]);

  const managers = users.filter((u) => u.role === "manager");
  const chunks = docs.reduce((s, d) => s + (d.n_chunks || 0), 0);
  const readyDocs = docs.filter((d) => d.status === "ready").length;
  const adoption = docs.length ? Math.round((readyDocs / docs.length) * 100) : 0;

  const teamRows = teams
    .map((t) => {
      const members = users.filter((u) => u.team_id === t.id);
      const lead = users.find((u) => u.id === t.manager_user_id) || members.find((u) => u.role === "manager");
      return { team: t, members, lead };
    })
    .filter((r) => !filter || r.team.name.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div className="flex flex-col gap-8">
      {/* Organization Profile */}
      <section className="bg-surface-container-lowest border border-surface-variant rounded-lg p-stack-lg shadow-ambient flex flex-col gap-4">
        <div className="flex items-center gap-2 border-b border-surface-variant pb-2">
          <span className="material-symbols-outlined text-primary">corporate_fare</span>
          <h3 className="text-headline-sm text-on-surface">Organization Profile</h3>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          <div className="flex flex-col gap-1">
            <span className="text-label-caps text-on-surface-variant">Maturity Stage</span>
            <span className="text-body-md text-on-surface">Stage {org.maturity_stage} · {org.maturity_label || "—"}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-label-caps text-on-surface-variant">Teams</span>
            <span className="text-body-md text-on-surface">{teams.length}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-label-caps text-on-surface-variant">People</span>
            <span className="text-body-md text-on-surface">{users.length}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-label-caps text-on-surface-variant">Description</span>
            <p className="text-body-sm text-on-surface-variant">{org.description || "No description set."}</p>
          </div>
        </div>
      </section>

      {/* Performance Analytics */}
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">analytics</span>
        <h3 className="text-headline-sm text-on-surface">Performance Analytics</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 -mt-4">
        {/* Stage card */}
        <div className="bg-surface-container-lowest border border-surface-variant rounded-lg p-stack-md flex flex-col gap-4 shadow-ambient">
          <div className="flex justify-between items-center">
            <h3 className="text-headline-sm text-on-surface">Maturity Stage</h3>
            <span className="material-symbols-outlined text-pulse-teal-vibrant">speed</span>
          </div>
          <div className="flex items-end gap-4">
            <span className="text-display-lg text-primary">{org.maturity_stage}</span>
            <div className="flex flex-col pb-2">
              <span className="text-label-sm text-secondary bg-secondary-container px-2 py-0.5 rounded w-fit">{org.maturity_label || "—"}</span>
              <span className="text-body-sm text-on-surface-variant mt-1">of 5 stages</span>
            </div>
          </div>
        </div>
        {/* Managers card */}
        <div className="bg-surface-container-lowest border border-surface-variant rounded-lg p-stack-md flex flex-col gap-4 shadow-ambient">
          <div className="flex justify-between items-center">
            <h3 className="text-headline-sm text-on-surface">Active Managers</h3>
            <span className="material-symbols-outlined text-primary">group</span>
          </div>
          <div className="flex items-end gap-4 h-full">
            <span className="text-display-lg text-primary">{managers.length}</span>
            <div className="flex -space-x-3 mb-2">
              {managers.slice(0, 3).map((m) => (
                <div
                  key={m.id}
                  className="w-8 h-8 rounded-full border-2 border-surface-container-lowest bg-tertiary-fixed flex items-center justify-center text-label-sm font-bold text-on-tertiary-fixed"
                  title={m.name}
                >
                  {initials(m.name)}
                </div>
              ))}
              {managers.length > 3 && (
                <div className="w-8 h-8 rounded-full border-2 border-surface-container-lowest bg-surface-container-low flex items-center justify-center text-label-sm text-on-surface-variant">
                  +{managers.length - 3}
                </div>
              )}
            </div>
          </div>
        </div>
        {/* Knowledge card */}
        <div className="bg-surface-container-lowest border border-surface-variant rounded-lg p-stack-md flex flex-col gap-4 shadow-ambient">
          <div className="flex justify-between items-center">
            <h3 className="text-headline-sm text-on-surface">Knowledge Base</h3>
            <span className="material-symbols-outlined text-primary">database</span>
          </div>
          <div className="flex flex-col gap-2 mt-auto">
            <div className="flex justify-between items-end">
              <span className="text-display-lg text-primary">{chunks}</span>
              <span className="text-body-sm text-on-surface-variant pb-2">chunks from {docs.length} docs</span>
            </div>
            <div className="w-full bg-surface-container-highest rounded-full h-2">
              <div className="bg-pulse-teal-vibrant h-2 rounded-full" style={{ width: `${adoption}%` }} />
            </div>
            <span className="text-label-sm text-on-surface-variant text-right">{adoption}% Documents Ready</span>
          </div>
        </div>
      </div>

      {/* Team Management table */}
      <div className="bg-surface-container-lowest border border-surface-variant rounded-lg shadow-ambient overflow-hidden flex flex-col">
        <div className="p-stack-md border-b border-surface-variant flex justify-between items-center">
          <h3 className="text-headline-md text-on-surface">Team Management</h3>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" style={{ fontSize: 18 }}>filter_list</span>
            <input
              className="pl-9 pr-4 py-1.5 bg-surface-container-low border border-outline-variant rounded text-body-sm focus:outline-none focus:ring-1 focus:ring-pulse-teal-vibrant w-48"
              placeholder="Filter teams..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container text-on-surface-variant text-label-sm uppercase border-b border-surface-variant">
                <th className="p-3 pl-stack-md font-medium">Team Name</th>
                <th className="p-3 font-medium">Lead Coach</th>
                <th className="p-3 font-medium">Members</th>
                <th className="p-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="text-body-sm text-on-surface">
              {teamRows.map(({ team, members, lead }) => (
                <tr key={team.id} className="border-b border-surface-variant hover:bg-surface-container-low transition-colors">
                  <td className="p-3 pl-stack-md font-medium">{team.name}</td>
                  <td className="p-3">
                    {lead ? (
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-bold" style={{ fontSize: 10 }}>
                          {initials(lead.name)}
                        </div>
                        <span>{lead.name}</span>
                      </div>
                    ) : (
                      <span className="muted">Unassigned</span>
                    )}
                  </td>
                  <td className="p-3">{members.length}</td>
                  <td className="p-3">
                    {lead ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container text-label-sm" style={{ fontSize: 11 }}>
                        <span className="w-1.5 h-1.5 rounded-full bg-secondary" /> Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-error-container text-on-error-container text-label-sm" style={{ fontSize: 11 }}>
                        <span className="w-1.5 h-1.5 rounded-full bg-error" /> Needs Lead
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {teamRows.length === 0 && (
                <tr><td className="p-4 muted" colSpan={4}>No teams yet — create one in People Access.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Knowledge
// --------------------------------------------------------------------------- //
function ApplyTemplatesPanel({ org, onApplied }: { org: Org; onApplied: () => void }) {
  const [templates, setTemplates] = useState<KTemplate[]>([]);
  const [stageId, setStageId] = useState("");
  const [sectorId, setSectorId] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string>("");

  useEffect(() => {
    listTemplates().then((ts) => {
      setTemplates(ts);
      // preselect the template matching the org's current stage
      const match = ts.find((t) => t.kind === "stage" && t.key === `stage-${org.maturity_stage}`);
      if (match) setStageId(match.id);
    }).catch(() => {});
  }, [org.maturity_stage]);

  const stages = templates.filter((t) => t.kind === "stage");
  const sectors = templates.filter((t) => t.kind === "sector");

  async function apply() {
    setBusy(true);
    const lines: string[] = [];
    try {
      for (const tid of [stageId, sectorId].filter(Boolean)) {
        const r = await applyTemplate(tid, org.id);
        lines.push(
          `${r.template}: ${r.copied.length} added${r.skipped.length ? `, ${r.skipped.length} already present` : ""}`,
        );
      }
      setResult(lines.join(" · ") || "Nothing selected");
      onApplied();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="bg-surface-container-lowest border border-surface-variant rounded-lg shadow-ambient p-stack-md">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-8 h-8 rounded-full bg-secondary/10 flex items-center justify-center text-secondary">
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>library_add</span>
        </div>
        <div>
          <h4 className="text-headline-sm text-on-surface">Apply Knowledge Templates</h4>
          <p className="text-on-surface-variant" style={{ fontSize: 12 }}>
            Route premade stage & sector documents into this organization&apos;s RAG. Copies are instant and editable per-org.
          </p>
        </div>
      </div>
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center">
        <select
          className="flex-1 pl-3 pr-8 py-2 bg-surface-container-low border border-outline-variant rounded text-label-sm focus:outline-none focus:ring-1 focus:ring-pulse-teal-vibrant"
          value={stageId}
          onChange={(e) => setStageId(e.target.value)}
        >
          <option value="">No stage template</option>
          {stages.map((t) => (
            <option key={t.id} value={t.id}>{t.name} ({t.n_docs} docs)</option>
          ))}
        </select>
        <select
          className="flex-1 pl-3 pr-8 py-2 bg-surface-container-low border border-outline-variant rounded text-label-sm focus:outline-none focus:ring-1 focus:ring-pulse-teal-vibrant"
          value={sectorId}
          onChange={(e) => setSectorId(e.target.value)}
        >
          <option value="">No sector template</option>
          {sectors.map((t) => (
            <option key={t.id} value={t.id}>{t.name} ({t.n_docs} docs)</option>
          ))}
        </select>
        <button
          className="bg-secondary text-on-secondary px-5 py-2 rounded-lg text-label-sm font-bold hover:bg-secondary/90 transition-colors disabled:opacity-50 whitespace-nowrap"
          disabled={busy || (!stageId && !sectorId)}
          onClick={apply}
        >
          {busy ? "Applying…" : "Apply to organization"}
        </button>
      </div>
      {result && <p className="text-body-sm text-secondary mt-3 font-medium">✓ {result}</p>}
    </div>
  );
}

function KnowledgeTab({ org, onSaved }: { org: Org; onSaved: (o: Org) => void }) {
  const [docs, setDocs] = useState<KDoc[]>([]);
  const [busy, setBusy] = useState(false);
  const [stageOpen, setStageOpen] = useState(true);
  const [stage, setStage] = useState(org.maturity_stage);
  const [search, setSearch] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const load = () => listDocs(org.id).then(setDocs);
  useEffect(() => {
    load();
  }, [org.id]);

  // Ingestion runs in the background — poll while any document is still processing.
  useEffect(() => {
    if (!docs.some((d) => d.status === "processing")) return;
    const t = setTimeout(load, 2500);
    return () => clearTimeout(t);
  }, [docs]);

  async function handleFiles(files: FileList | null) {
    if (!files || !files.length) return;
    setBusy(true);
    try {
      await uploadDocs(org.id, files);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function saveStage(s: number) {
    setStage(s);
    const updated = await updateOrg(org.id, {
      maturity_stage: s,
      maturity_label: STAGES.find((x) => x.n === s)?.label,
    });
    onSaved(updated);
  }

  const visible = docs.filter((d) => !search || d.filename.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="flex flex-col gap-8">
      <h3 className="text-headline-lg text-on-surface">Knowledge Management</h3>

      {/* Maturity Alignment */}
      <div className="bg-surface-container-lowest border border-surface-variant rounded-lg shadow-ambient overflow-hidden">
        <div
          className="p-stack-md border-b border-surface-variant flex justify-between items-center bg-surface-container-low/30 cursor-pointer"
          onClick={() => setStageOpen((o) => !o)}
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined" style={{ fontSize: 20 }}>account_tree</span>
            </div>
            <div>
              <h4 className="text-headline-sm text-on-surface">Maturity Alignment</h4>
              <p className="text-on-surface-variant" style={{ fontSize: 12 }}>
                Current: <span className="text-primary font-bold">Stage {stage}: {STAGES.find((s) => s.n === stage)?.label}</span>
              </p>
            </div>
          </div>
          <button className="p-2 hover:bg-surface-container-high rounded-full transition-colors">
            <span className="material-symbols-outlined text-on-surface-variant">{stageOpen ? "expand_less" : "expand_more"}</span>
          </button>
        </div>

        {stageOpen && (
          <div className="p-stack-md">
            <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex-1">
                <p className="text-label-sm text-on-surface font-bold mb-1">Current Maturity Stage</p>
                <p className="text-body-sm text-on-surface-variant">Align methodology requirements to the organization&apos;s current level.</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="relative" style={{ minWidth: 220 }}>
                  <select
                    className="w-full pl-3 pr-10 py-2 bg-surface-container-lowest border border-outline-variant rounded text-label-sm appearance-none focus:outline-none focus:ring-1 focus:ring-pulse-teal-vibrant transition-colors"
                    value={stage}
                    onChange={(e) => saveStage(Number(e.target.value))}
                  >
                    {STAGES.map((s) => (
                      <option key={s.n} value={s.n}>Stage {s.n}: {s.label}</option>
                    ))}
                  </select>
                  <span className="material-symbols-outlined absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">expand_more</span>
                </div>
                <button
                  className="bg-primary text-on-primary px-4 py-2 rounded-lg text-label-sm flex items-center gap-2 hover:bg-primary/90 transition-colors shadow-sm font-bold whitespace-nowrap"
                  onClick={() => inputRef.current?.click()}
                  disabled={busy}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>
                  {busy ? "Processing…" : "Add Document"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Apply stage & sector templates */}
      <ApplyTemplatesPanel org={org} onApplied={load} />

      {/* Knowledge Base & RAG Context */}
      <div className="bg-surface-container-lowest border border-surface-variant rounded-lg shadow-ambient overflow-hidden flex flex-col">
        <div className="p-stack-md border-b border-surface-variant flex justify-between items-center flex-wrap gap-3">
          <div>
            <h3 className="text-headline-sm text-on-surface">Organization Knowledge Base &amp; RAG Context</h3>
            <p className="text-body-sm text-on-surface-variant mt-1">Manage foundational documents and broader context for AI processing.</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" style={{ fontSize: 18 }}>search</span>
              <input
                className="pl-9 pr-4 py-1.5 bg-surface-container-low border border-outline-variant rounded text-body-sm focus:outline-none focus:ring-1 focus:ring-pulse-teal-vibrant w-64"
                placeholder="Search documents..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button
              className="bg-primary-container text-on-primary px-4 py-2 rounded text-label-sm flex items-center gap-2 hover:bg-primary/90 transition-colors shadow-sm font-bold"
              onClick={() => inputRef.current?.click()}
              disabled={busy}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>
              {busy ? "Processing…" : "Add Document"}
            </button>
          </div>
        </div>

        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept=".pdf,.docx,.pptx,.txt,.md,.markdown"
          onChange={(e) => handleFiles(e.target.files)}
        />

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container text-on-surface-variant text-label-sm uppercase border-b border-surface-variant">
                <th className="p-3 pl-stack-md font-medium">Document Name</th>
                <th className="p-3 font-medium">Status</th>
                <th className="p-3 font-medium">Chunks</th>
                <th className="p-3 font-medium" />
              </tr>
            </thead>
            <tbody className="text-body-sm text-on-surface">
              {visible.map((d) => (
                <tr key={d.id} className="border-b border-surface-variant hover:bg-surface-container-low transition-colors">
                  <td className="p-3 pl-stack-md font-medium">
                    <span className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-outline-variant">description</span>
                      {d.filename}
                    </span>
                  </td>
                  <td className="p-3">
                    {d.status === "ready" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container text-label-sm" style={{ fontSize: 11 }}>
                        <span className="w-1.5 h-1.5 rounded-full bg-secondary" /> Ready
                      </span>
                    ) : d.status === "error" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-error-container text-on-error-container text-label-sm" style={{ fontSize: 11 }}>
                        <span className="w-1.5 h-1.5 rounded-full bg-error" /> Error
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-tint/10 text-primary text-label-sm" style={{ fontSize: 11 }}>
                        <span className="w-1.5 h-1.5 rounded-full bg-primary" /> {d.status}
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-on-surface-variant">{d.n_chunks || "—"}</td>
                  <td className="p-3 text-right">
                    <button
                      className="text-error hover:bg-error/5 p-1.5 rounded transition-colors"
                      onClick={async () => {
                        await deleteDoc(org.id, d.id);
                        load();
                      }}
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: 18 }}>delete</span>
                    </button>
                  </td>
                </tr>
              ))}
              {visible.length === 0 && (
                <tr><td className="p-4 muted" colSpan={4}>{docs.length === 0 ? "No documents yet — add workshop files to build this org's knowledge." : "No documents match your search."}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Pulse Config
// --------------------------------------------------------------------------- //
function ConfigTab({ org, onSaved }: { org: Org; onSaved: (o: Org) => void }) {
  const [coachPrompt, setCoachPrompt] = useState(org.coach_prompt);
  const [description, setDescription] = useState(org.description);
  const [settings, setSettings] = useState<Record<string, boolean>>(org.settings || {});
  const [saved, setSaved] = useState(false);

  const toggles = [
    { key: "manager_can_see_members", label: "Managers can see each team member's individual dashboard" },
    { key: "employee_can_see_team", label: "Employees can see the combined team dashboard" },
  ];

  async function save() {
    const updated = await updateOrg(org.id, { coach_prompt: coachPrompt, description, settings });
    onSaved(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  const currentIdx = org.maturity_stage;

  return (
    <div className="flex flex-col gap-8" style={{ maxWidth: 1200 }}>
      {/* Maturity Journey Map */}
      <section className="bg-surface border border-outline-variant rounded p-6 shadow-ambient">
        <div className="mb-6">
          <h3 className="text-headline-sm text-on-surface font-semibold">Maturity Journey Map</h3>
          <p className="text-body-sm text-on-surface-variant mt-1">Current coaching trajectory and active stage focus.</p>
        </div>
        <div className="relative flex items-center justify-between w-full pt-4" style={{ paddingBottom: 64 }}>
          <div className="absolute top-1/2 left-0 w-full bg-surface-container-high -translate-y-1/2 z-0" style={{ height: 2 }} />
          <div
            className="absolute top-1/2 left-0 bg-secondary -translate-y-1/2 z-0"
            style={{ height: 2, width: `${((currentIdx - 1) / (STAGES.length - 1)) * 100}%` }}
          />
          {STAGES.map((s) => {
            const done = s.n < currentIdx;
            const active = s.n === currentIdx;
            return (
              <div key={s.n} className={`relative z-10 flex flex-col items-center gap-2 group ${!done && !active ? "opacity-60" : ""}`}>
                {active && <div className="absolute -inset-2 bg-pulse-teal-vibrant/20 rounded-full animate-ping z-0" />}
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border-2 shadow-sm relative z-10 transition-transform group-hover:scale-110 ${
                    done
                      ? "bg-secondary text-on-secondary border-surface"
                      : active
                        ? "bg-surface border-secondary text-secondary"
                        : "bg-surface border-outline-variant text-outline"
                  }`}
                >
                  <span className="material-symbols-outlined icon-fill" style={{ fontSize: 20 }}>
                    {done ? "check" : active ? "play_arrow" : s.n === STAGES.length ? "flag" : "lock"}
                  </span>
                </div>
                <div className="absolute text-center" style={{ top: 56, width: 128 }}>
                  <p className={`text-label-caps ${active ? "text-secondary font-bold" : "text-on-surface-variant"}`}>Stage {s.n}</p>
                  <p className={`text-body-sm ${active ? "text-on-surface font-medium" : "text-on-surface-variant"}`}>{s.label}</p>
                  {active && (
                    <span className="inline-block mt-1 px-2 py-0.5 rounded-sm bg-secondary/10 text-secondary text-label-sm" style={{ fontSize: 10 }}>CURRENT</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Global Coach Prompt */}
        <section className="lg:col-span-7 bg-surface border border-outline-variant rounded p-6 shadow-ambient flex flex-col" style={{ height: 500 }}>
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-headline-sm text-on-surface font-semibold flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">psychology</span>
                Global Coach Prompt
              </h3>
              <p className="text-body-sm text-on-surface-variant mt-1">Master instructions defining the AI&apos;s core behavior for this organization.</p>
            </div>
          </div>
          <textarea
            className="flex-1 w-full resize-none rounded border border-outline-variant bg-surface-bright p-4 text-body-sm text-on-surface focus:border-secondary focus:ring-1 focus:ring-secondary focus:outline-none transition-all shadow-inner mb-4"
            placeholder={`You are the Pulse AI Coach for ${org.name}. Push them from aesthetics toward evidence-backed decisions…`}
            value={coachPrompt}
            onChange={(e) => setCoachPrompt(e.target.value)}
          />
          <div className="flex justify-end gap-3 pt-4 border-t border-outline-variant">
            <button
              className="px-4 py-2 rounded border border-outline-variant text-on-surface text-label-sm hover:bg-surface-variant transition-colors"
              onClick={() => setCoachPrompt(org.coach_prompt)}
            >
              Revert
            </button>
            <button
              className="px-4 py-2 rounded bg-primary text-on-primary text-label-sm hover:bg-primary-container transition-colors flex items-center gap-2"
              onClick={save}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>save</span>
              {saved ? "Saved ✓" : "Save Master Prompt"}
            </button>
          </div>
        </section>

        {/* Org context + visibility */}
        <section className="lg:col-span-5 flex flex-col gap-6">
          <div className="bg-surface border border-outline-variant rounded p-6 shadow-ambient flex flex-col flex-1">
            <h3 className="text-headline-sm text-on-surface font-semibold mb-1">Organization Context</h3>
            <p className="text-body-sm text-on-surface-variant mb-3">Where they are today and the target the coach should push toward.</p>
            <textarea
              className="flex-1 w-full resize-none rounded border border-outline-variant bg-surface-bright p-4 text-body-sm text-on-surface focus:border-secondary focus:ring-1 focus:ring-secondary focus:outline-none transition-all shadow-inner"
              rows={5}
              placeholder="This organization is at Stage 2… designs for aesthetics, target is evidence-backed decision making…"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="bg-surface border border-outline-variant rounded p-6 shadow-ambient">
            <h3 className="text-headline-sm text-on-surface font-semibold mb-1">Dashboard Visibility</h3>
            <p className="text-body-sm text-on-surface-variant mb-3">Control who can see which dashboards.</p>
            {toggles.map((t) => (
              <label key={t.key} className="flex items-center gap-3 py-2.5 border-b border-outline-variant/50 cursor-pointer last:border-0">
                <input
                  type="checkbox"
                  checked={!!settings[t.key]}
                  onChange={(e) => setSettings({ ...settings, [t.key]: e.target.checked })}
                />
                <span className="text-body-sm text-on-surface">{t.label}</span>
              </label>
            ))}
            <button
              className="mt-4 px-4 py-2 rounded bg-primary text-on-primary text-label-sm hover:bg-primary-container transition-colors w-full"
              onClick={save}
            >
              {saved ? "Saved ✓" : "Save Configuration"}
            </button>
          </div>

          <SkillGrantsPanel orgId={org.id} />
        </section>
      </div>
    </div>
  );
}

function SkillGrantsPanel({ orgId }: { orgId: string }) {
  const [rows, setRows] = useState<{ id: string; name: string; command: string; description: string; granted: boolean }[]>([]);
  const load = () => orgSkillGrants(orgId).then(setRows).catch(() => setRows([]));
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  return (
    <div className="bg-surface border border-outline-variant rounded p-6 shadow-ambient">
      <h3 className="text-headline-sm text-on-surface font-semibold mb-1 flex items-center gap-2">
        <span className="material-symbols-outlined text-pulse-teal-vibrant" style={{ fontSize: 20 }}>bolt</span>
        Skills
      </h3>
      <p className="text-body-sm text-on-surface-variant mb-3">
        Slash commands this organization&apos;s users can invoke in chat (e.g. <code className="bg-surface-container px-1 rounded">/design-thinking</code>).
      </p>
      {rows.length === 0 && <p className="text-body-sm text-on-surface-variant">No skills exist yet — create them in Stage Knowledge.</p>}
      {rows.map((s) => (
        <label key={s.id} className="flex items-start gap-3 py-2.5 border-b border-outline-variant/50 cursor-pointer last:border-0">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={s.granted}
            onChange={async (e) => {
              if (e.target.checked) await grantSkill(orgId, s.id);
              else await revokeSkill(orgId, s.id);
              load();
            }}
          />
          <span>
            <span className="text-body-sm text-on-surface font-medium">{s.name}</span>
            <code className="ml-2 text-on-surface-variant bg-surface-container px-1.5 py-0.5 rounded" style={{ fontSize: 11 }}>/{s.command}</code>
            {s.description && <span className="block text-on-surface-variant" style={{ fontSize: 12 }}>{s.description}</span>}
          </span>
        </label>
      ))}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// People Access
// --------------------------------------------------------------------------- //
function PeopleTab({ orgId }: { orgId: string }) {
  const [users, setUsers] = useState<OrgUser[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [teamName, setTeamName] = useState("");
  const [showNewTeam, setShowNewTeam] = useState(false);
  const [addingFor, setAddingFor] = useState<string | null>(null); // team_id or "none"
  const [form, setForm] = useState({ name: "", email: "", role: "employee" });
  const [err, setErr] = useState("");
  const [tempPassword, setTempPassword] = useState<{ email: string; password: string } | null>(null);

  function load() {
    listUsers(orgId).then(setUsers);
    listTeams(orgId).then(setTeams);
  }
  useEffect(load, [orgId]);

  async function addUser(e: React.FormEvent, teamId: string | null) {
    e.preventDefault();
    setErr("");
    try {
      const created = await createUser(orgId, { ...form, team_id: teamId });
      if (created.temp_password) setTempPassword({ email: created.email, password: created.temp_password });
      setForm({ name: "", email: "", role: "employee" });
      setAddingFor(null);
      load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  const unassigned = users.filter((u) => !u.team_id);

  function TeamCard({ team }: { team: Team | null }) {
    const members = team ? users.filter((u) => u.team_id === team.id) : unassigned;
    const lead = team
      ? users.find((u) => u.id === team.manager_user_id) || members.find((u) => u.role === "manager")
      : undefined;
    const key = team ? team.id : "none";

    return (
      <article className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-outline-variant/50 flex justify-between items-start bg-gradient-to-br from-surface-bright to-surface-container-lowest">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-headline-md text-primary font-semibold">{team ? team.name : "Unassigned"}</h3>
              <span className="bg-primary-fixed text-on-primary-fixed-variant px-2 py-0.5 rounded text-label-sm border border-primary-fixed-dim">
                {members.length} Member{members.length === 1 ? "" : "s"}
              </span>
            </div>
            <div className="flex gap-2 flex-wrap mt-2">
              <span className="px-2.5 py-1 rounded-full bg-surface-container text-on-surface-variant text-label-sm border border-outline-variant/30 flex items-center gap-1">
                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>design_services</span>
                {team ? "Team" : "No team assigned"}
              </span>
            </div>
          </div>
          <span className="material-symbols-outlined text-on-surface-variant">more_vert</span>
        </div>

        {/* Body */}
        <div className="p-6 flex-1 flex flex-col gap-6">
          {/* Lead */}
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-label-caps text-on-surface-variant mb-2">TEAM LEAD</span>
              {lead ? (
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-bold text-label-sm border-2 border-white shadow-sm">
                    {initials(lead.name)}
                  </div>
                  <div>
                    <p className="text-body-md font-medium text-on-surface">{lead.name}</p>
                    <p className="text-body-sm text-on-surface-variant">{lead.email}</p>
                  </div>
                </div>
              ) : (
                <span className="muted text-body-sm">No manager assigned</span>
              )}
            </div>
          </div>

          {/* Members */}
          <div className="flex flex-col">
            <div className="flex justify-between items-center mb-3">
              <span className="text-label-caps text-on-surface-variant">MEMBERS ({members.length})</span>
            </div>
            <ul className="flex flex-col gap-2">
              {members.map((m) => (
                <li key={m.id} className="flex items-center justify-between p-2 hover:bg-surface-container-low rounded transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-label-sm font-bold ${m.role === "manager" ? "bg-secondary-container text-on-secondary-container" : "bg-tertiary-fixed text-on-tertiary-fixed"}`}>
                      {initials(m.name)}
                    </div>
                    <div>
                      <span className="text-body-sm text-on-surface">{m.name}</span>
                      <span className="text-label-sm text-on-surface-variant ml-2 capitalize">{m.role}</span>
                    </div>
                  </div>
                </li>
              ))}
              {members.length === 0 && <li className="muted text-body-sm p-2">No members yet.</li>}
            </ul>
          </div>

          {/* Inline add-member form */}
          {addingFor === key && (
            <form onSubmit={(e) => addUser(e, team ? team.id : null)} className="bg-surface-container-low rounded-lg p-4 flex flex-col gap-2 border border-outline-variant/50">
              <div className="card-label">Add person {team ? `to ${team.name}` : ""}</div>
              <input className="input-field w-full" placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              <input className="input-field w-full" placeholder="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
              <select className="select w-full" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="employee">Employee</option>
                <option value="manager">Manager (becomes team lead)</option>
              </select>
              {err && <div className="text-error text-label-sm">{err}</div>}
              <div className="flex gap-2">
                <button className="btn flex-1" style={{ height: 38 }}>Add person</button>
                <button type="button" className="px-4 rounded border border-outline-variant text-label-sm" onClick={() => setAddingFor(null)}>Cancel</button>
              </div>
              <div className="text-label-sm text-on-surface-variant">A one-time temporary password is generated — share it securely.</div>
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-outline-variant/30 bg-surface-container-low flex justify-end gap-3">
          <button
            className="bg-secondary text-white hover:bg-on-secondary-container px-4 py-2 rounded text-label-sm transition-colors flex items-center gap-2"
            onClick={() => { setErr(""); setAddingFor(addingFor === key ? null : key); }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>person_add</span> Add Members
          </button>
        </div>
      </article>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-headline-lg text-primary">People &amp; Teams Management</h2>
          <p className="text-body-md text-on-surface-variant mt-1">Manage organizational structures, roles, and access controls across your enterprise.</p>
        </div>
        <button
          className="bg-primary hover:bg-primary-container text-white px-6 py-2.5 rounded text-label-caps transition-colors flex items-center justify-center gap-2 whitespace-nowrap shadow-sm hover:shadow-md"
          onClick={() => setShowNewTeam((s) => !s)}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>
          Create New Team
        </button>
      </div>

      {showNewTeam && (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (!teamName) return;
            await createTeam(orgId, { name: teamName });
            setTeamName("");
            setShowNewTeam(false);
            load();
          }}
          className="card flex gap-3 items-end"
        >
          <div className="flex-1">
            <div className="card-label">Team name</div>
            <input className="input-field w-full" placeholder="e.g. Core UX Team" value={teamName} onChange={(e) => setTeamName(e.target.value)} required />
          </div>
          <button className="btn" style={{ height: 40 }}>Create</button>
        </form>
      )}

      {tempPassword && (
        <div className="card flex items-center gap-4 border border-secondary/40 bg-secondary-container/20">
          <span className="material-symbols-outlined text-secondary">key</span>
          <div className="flex-1">
            <div className="text-body-sm text-on-surface">
              Temporary password for <strong>{tempPassword.email}</strong>:{" "}
              <code className="px-2 py-0.5 rounded bg-surface-container font-semibold">{tempPassword.password}</code>
            </div>
            <div className="text-label-sm text-on-surface-variant mt-0.5">Shown once — copy it now and share it securely. They can change it after signing in.</div>
          </div>
          <button
            className="px-3 py-1.5 rounded border border-outline-variant text-label-sm hover:bg-surface-container"
            onClick={() => navigator.clipboard.writeText(tempPassword.password)}
          >
            Copy
          </button>
          <button className="p-1.5 text-on-surface-variant hover:text-primary" onClick={() => setTempPassword(null)}>
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>close</span>
          </button>
        </div>
      )}

      {/* Bento grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {teams.map((t) => (
          <TeamCard key={t.id} team={t} />
        ))}
        {unassigned.length > 0 && <TeamCard team={null} />}
        {teams.length === 0 && unassigned.length === 0 && (
          <div className="muted col-span-full">No teams or people yet — create a team to get started.</div>
        )}
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Guard role="kpmg_admin">
      <OrgDetail />
    </Guard>
  );
}
