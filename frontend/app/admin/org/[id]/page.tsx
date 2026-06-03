"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Guard from "@/components/Guard";
import {
  KDoc,
  Org,
  OrgUser,
  Team,
  createTeam,
  createUser,
  deleteDoc,
  getOrg,
  listDocs,
  listTeams,
  listUsers,
  updateOrg,
  uploadDocs,
} from "@/lib/api";

const TABS = ["Knowledge", "Config", "People", "Visibility"] as const;
type Tab = (typeof TABS)[number];

function OrgDetail() {
  const { id } = useParams<{ id: string }>();
  const [org, setOrg] = useState<Org | null>(null);
  const [tab, setTab] = useState<Tab>("Knowledge");

  useEffect(() => {
    getOrg(id).then(setOrg);
  }, [id]);

  if (!org) return <div className="page muted">Loading…</div>;

  return (
    <div className="page">
      <div className="page-title">{org.name}</div>
      <div className="page-sub">
        Stage {org.maturity_stage} · {org.maturity_label}
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 20, borderBottom: "0.5px solid var(--border)" }}>
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="nav-link"
            style={{
              background: "none",
              border: "none",
              borderBottom: tab === t ? "2px solid var(--blue)" : "2px solid transparent",
              color: tab === t ? "var(--blue)" : "var(--ink-3)",
              fontWeight: 600,
              padding: "8px 14px",
              cursor: "pointer",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Knowledge" && <KnowledgeTab orgId={id} />}
      {tab === "Config" && <ConfigTab org={org} onSaved={setOrg} />}
      {tab === "People" && <PeopleTab orgId={id} />}
      {tab === "Visibility" && <VisibilityTab org={org} onSaved={setOrg} />}
    </div>
  );
}

// --------------------------------------------------------------------------- //
function KnowledgeTab({ orgId }: { orgId: string }) {
  const [docs, setDocs] = useState<KDoc[]>([]);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = () => listDocs(orgId).then(setDocs);
  useEffect(() => {
    load();
  }, [orgId]);

  async function handleFiles(files: FileList | null) {
    if (!files || !files.length) return;
    setBusy(true);
    try {
      await uploadDocs(orgId, files);
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className="card"
        style={{
          border: `1.5px dashed ${drag ? "var(--blue-mid)" : "var(--border-mid)"}`,
          background: drag ? "var(--blue-pale)" : "var(--white)",
          textAlign: "center",
          padding: 36,
          cursor: "pointer",
          marginBottom: 16,
        }}
      >
        <div style={{ fontWeight: 700, color: "var(--blue)", marginBottom: 4 }}>
          {busy ? "Processing…" : "Drop workshop files here, or click to browse"}
        </div>
        <div className="muted">PDF · Word · PowerPoint · text / markdown — parsed, chunked & embedded into this org&apos;s knowledge</div>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept=".pdf,.docx,.pptx,.txt,.md,.markdown"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <div className="card">
        <div className="card-label">Knowledge documents ({docs.length})</div>
        {docs.length === 0 && <div className="muted">No documents yet.</div>}
        {docs.map((d) => (
          <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "0.5px solid var(--border)" }}>
            <span style={{ flex: 1, fontWeight: 600, color: "var(--ink-2)" }}>{d.filename}</span>
            <span className={`chip ${d.status === "error" ? "handoff" : ""}`}>
              {d.status === "ready" ? `${d.n_chunks} chunks` : d.status}
            </span>
            <button
              className="nav-link"
              style={{ color: "var(--coral)", background: "none", border: "none", cursor: "pointer" }}
              onClick={async () => {
                await deleteDoc(orgId, d.id);
                load();
              }}
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
function ConfigTab({ org, onSaved }: { org: Org; onSaved: (o: Org) => void }) {
  const [stage, setStage] = useState(org.maturity_stage);
  const [label, setLabel] = useState(org.maturity_label);
  const [description, setDescription] = useState(org.description);
  const [coachPrompt, setCoachPrompt] = useState(org.coach_prompt);
  const [saved, setSaved] = useState(false);

  async function save() {
    const updated = await updateOrg(org.id, {
      maturity_stage: stage,
      maturity_label: label,
      description,
      coach_prompt: coachPrompt,
    });
    onSaved(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="card">
      <div className="card-label">Maturity stage</div>
      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <select className="select" value={stage} onChange={(e) => setStage(Number(e.target.value))}>
          {[1, 2, 3, 4, 5].map((s) => (
            <option key={s} value={s}>Stage {s}</option>
          ))}
        </select>
        <input className="chat-input" style={{ flex: 1 }} value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Designs for aesthetics" />
      </div>

      <div className="card-label">Where they are / target</div>
      <textarea className="chat-input" style={{ width: "100%", marginBottom: 16 }} rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />

      <div className="card-label">Coach prompt — how Pulse should coach this org</div>
      <textarea
        className="chat-input"
        style={{ width: "100%", marginBottom: 16 }}
        rows={5}
        value={coachPrompt}
        onChange={(e) => setCoachPrompt(e.target.value)}
        placeholder="This organization is at Stage 2… push them from aesthetics toward evidence-backed decisions…"
      />
      <button className="btn" style={{ height: 42 }} onClick={save}>
        {saved ? "Saved ✓" : "Save configuration"}
      </button>
    </div>
  );
}

// --------------------------------------------------------------------------- //
function PeopleTab({ orgId }: { orgId: string }) {
  const [users, setUsers] = useState<OrgUser[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [form, setForm] = useState({ name: "", email: "", password: "pulse1234", role: "employee", team_id: "" });
  const [teamName, setTeamName] = useState("");
  const [err, setErr] = useState("");

  function load() {
    listUsers(orgId).then(setUsers);
    listTeams(orgId).then(setTeams);
  }
  useEffect(load, [orgId]);

  async function addUser(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await createUser(orgId, { ...form, team_id: form.team_id || null });
      setForm({ name: "", email: "", password: "pulse1234", role: "employee", team_id: "" });
      load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <div className="grid grid-2">
      <div className="card">
        <div className="card-label">People ({users.length})</div>
        {users.map((u) => (
          <div key={u.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 0", borderBottom: "0.5px solid var(--border)" }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: "var(--ink-2)" }}>{u.name}</div>
              <div className="muted" style={{ fontSize: 11 }}>{u.email}</div>
            </div>
            <span className={`chip ${u.role === "manager" ? "phase" : ""}`}>{u.role}</span>
            {u.team_name && <span className="chip">{u.team_name}</span>}
          </div>
        ))}
      </div>

      <div>
        <form onSubmit={addUser} className="card" style={{ marginBottom: 14 }}>
          <div className="card-label">Add person</div>
          <input className="chat-input" style={{ width: "100%", marginBottom: 8 }} placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <input className="chat-input" style={{ width: "100%", marginBottom: 8 }} placeholder="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <select className="select" style={{ flex: 1 }} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="employee">Employee</option>
              <option value="manager">Manager</option>
            </select>
            <select className="select" style={{ flex: 1 }} value={form.team_id} onChange={(e) => setForm({ ...form, team_id: e.target.value })}>
              <option value="">No team</option>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          {err && <div style={{ color: "var(--coral)", fontSize: 12, marginBottom: 8 }}>{err}</div>}
          <button className="btn" style={{ height: 40, width: "100%" }}>Add person (pw: pulse1234)</button>
        </form>

        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (!teamName) return;
            await createTeam(orgId, { name: teamName });
            setTeamName("");
            load();
          }}
          className="card"
        >
          <div className="card-label">Teams ({teams.length})</div>
          <div style={{ marginBottom: 8 }}>
            {teams.map((t) => (
              <span key={t.id} className="chip" style={{ marginRight: 6 }}>{t.name}</span>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <input className="chat-input" style={{ flex: 1 }} placeholder="New team name" value={teamName} onChange={(e) => setTeamName(e.target.value)} />
            <button className="btn" style={{ height: 44 }}>Add</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
function VisibilityTab({ org, onSaved }: { org: Org; onSaved: (o: Org) => void }) {
  const [settings, setSettings] = useState<Record<string, boolean>>(org.settings || {});
  const [saved, setSaved] = useState(false);

  const toggles = [
    { key: "manager_can_see_members", label: "Managers can see each team member's individual dashboard" },
    { key: "employee_can_see_team", label: "Employees can see the combined team dashboard" },
  ];

  async function save() {
    const updated = await updateOrg(org.id, { settings });
    onSaved(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="card">
      <div className="card-label">Dashboard visibility</div>
      {toggles.map((t) => (
        <label key={t.key} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 0", borderBottom: "0.5px solid var(--border)", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={!!settings[t.key]}
            onChange={(e) => setSettings({ ...settings, [t.key]: e.target.checked })}
          />
          <span style={{ color: "var(--ink-2)", fontSize: 14 }}>{t.label}</span>
        </label>
      ))}
      <button className="btn" style={{ height: 42, marginTop: 16 }} onClick={save}>
        {saved ? "Saved ✓" : "Save visibility"}
      </button>
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
