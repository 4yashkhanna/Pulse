"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Guard from "@/components/Guard";
import {
  KTemplate,
  Skill,
  createSector,
  createSkill,
  deleteSkill,
  listSkills,
  listTemplates,
  updateSkill,
} from "@/lib/api";

const STAGE_META: Record<string, { icon: string; desc: string }> = {
  "stage-1": { icon: "assessment", desc: "Ad-hoc processes and siloed design initiatives." },
  "stage-2": { icon: "foundation", desc: "Establishing shared libraries and initial AI-assisted workflows." },
  "stage-3": { icon: "tune", desc: "Scaled design systems and integrated performance metrics." },
  "stage-4": { icon: "speed", desc: "AI deeply integrated into generative design and automated compliance." },
  "stage-5": { icon: "flag", desc: "Continuous autonomous improvement and strategic design leadership." },
};

const SECTOR_ICONS: Record<string, string> = {
  tech: "memory",
  fmcg: "shopping_cart",
  banking: "account_balance",
  healthcare: "monitor_heart",
  government: "account_balance_wallet",
};

function TemplateCard({ tpl }: { tpl: KTemplate }) {
  const router = useRouter();
  const meta = tpl.kind === "stage" ? STAGE_META[tpl.key] : undefined;
  const icon = meta?.icon || SECTOR_ICONS[tpl.key] || "category";
  return (
    <div
      className="bg-surface-container-lowest rounded-xl p-stack-md border border-outline-variant shadow-ambient flex flex-col transition-all hover:-translate-y-0.5 hover:shadow-md hover:border-pulse-teal-vibrant"
      style={tpl.kind === "stage" ? { minWidth: 300, width: 300, flexShrink: 0 } : undefined}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="w-11 h-11 rounded bg-surface-container-highest text-primary flex items-center justify-center">
          <span className="material-symbols-outlined">{icon}</span>
        </div>
        <span className="text-label-caps text-on-surface-variant">{tpl.n_docs} docs · {tpl.n_chunks} chunks</span>
      </div>
      {tpl.kind === "stage" && (
        <div className="text-label-caps text-on-surface-variant mb-1">{tpl.key.replace("-", " ").toUpperCase()}</div>
      )}
      <h3 className="text-headline-sm text-primary font-semibold mb-2">{tpl.name}</h3>
      <p className="text-body-sm text-on-surface-variant flex-1">{meta?.desc || tpl.description || "Sector coaching context and premade RAG documents."}</p>
      <button
        onClick={() => router.push(`/admin/knowledge/${tpl.id}`)}
        className="mt-4 text-label-sm py-2 rounded transition-colors font-medium bg-surface-container text-primary hover:bg-primary/10"
      >
        Manage documents
      </button>
    </div>
  );
}

function SkillEditor({ skill, onSaved, onDeleted }: { skill: Skill; onSaved: () => void; onDeleted: () => void }) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState(skill.body);
  const [description, setDescription] = useState(skill.description);
  const [saved, setSaved] = useState(false);
  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 mb-3">
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => setOpen((o) => !o)}>
        <span className="material-symbols-outlined text-pulse-teal-vibrant">bolt</span>
        <div className="flex-1">
          <span className="text-headline-sm text-primary font-semibold">{skill.name}</span>
          <code className="ml-3 text-body-sm bg-surface-container px-2 py-0.5 rounded text-secondary">/{skill.command}</code>
        </div>
        <span className="text-body-sm text-on-surface-variant">{skill.n_orgs ?? 0} org{(skill.n_orgs ?? 0) === 1 ? "" : "s"} granted</span>
        <span className="material-symbols-outlined text-on-surface-variant">{open ? "expand_less" : "expand_more"}</span>
      </div>
      {open && (
        <div className="mt-4 flex flex-col gap-3">
          <div>
            <label className="text-label-caps text-on-surface-variant block mb-1">Description (shown in the / autocomplete)</label>
            <input className="w-full bg-surface-container-low border border-outline-variant rounded px-3 py-2 text-body-sm focus:outline-none focus:border-pulse-teal-vibrant" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div>
            <label className="text-label-caps text-on-surface-variant block mb-1">Instructions (injected into the coach for the whole chat)</label>
            <textarea className="w-full bg-surface-container-low border border-outline-variant rounded px-3 py-2 text-body-sm focus:outline-none focus:border-pulse-teal-vibrant font-mono" rows={10} value={body} onChange={(e) => setBody(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <button
              className="bg-primary text-white text-label-sm px-4 py-2 rounded hover:bg-primary/90"
              onClick={async () => { await updateSkill(skill.id, { description, body }); setSaved(true); setTimeout(() => setSaved(false), 1500); onSaved(); }}
            >
              {saved ? "Saved ✓" : "Save"}
            </button>
            <button
              className="text-error text-label-sm px-4 py-2 rounded hover:bg-error/10"
              onClick={async () => { if (confirm(`Delete skill /${skill.command}?`)) { await deleteSkill(skill.id); onDeleted(); } }}
            >
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StageKnowledge() {
  const [templates, setTemplates] = useState<KTemplate[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [showNewSkill, setShowNewSkill] = useState(false);
  const [ns, setNs] = useState({ name: "", command: "", description: "", body: "" });

  const load = () => { listTemplates().then(setTemplates).catch(() => {}); listSkills().then(setSkills).catch(() => {}); };
  useEffect(load, []);

  const stages = templates.filter((t) => t.kind === "stage");
  const sectors = templates.filter((t) => t.kind === "sector");

  async function addSector() {
    const name = prompt("Sector name (e.g. Energy & Utilities):");
    if (!name) return;
    await createSector(name.toLowerCase().replace(/[^a-z0-9]+/g, "-"), name);
    load();
  }

  return (
    <div className="app-main">
      <header className="topbar">
        <div className="text-headline-md font-bold text-primary">Stage Knowledge</div>
        <div />
      </header>

      <div className="page-canvas">
        <div className="mb-8 max-w-4xl">
          <p className="text-body-lg text-on-surface-variant">
            Premade RAG templates per maturity stage and sector, plus the skills users can invoke in chat.
            Apply templates to an organization from its Knowledge tab.
          </p>
        </div>

        {/* Stage templates */}
        <section className="mb-12">
          <h2 className="text-headline-md text-on-surface border-l-4 border-primary pl-3 mb-6">Maturity Stage Templates</h2>
          <div className="flex gap-6 overflow-x-auto pb-4">
            {stages.map((t) => (
              <TemplateCard key={t.id} tpl={t} />
            ))}
          </div>
        </section>

        {/* Sector templates */}
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-headline-md text-on-surface border-l-4 border-secondary pl-3">Industry Sector Templates</h2>
            <button className="bg-primary text-white text-label-sm px-4 py-2 rounded hover:bg-primary/90 transition-colors" onClick={addSector}>
              Add New Sector
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {sectors.map((t) => (
              <TemplateCard key={t.id} tpl={t} />
            ))}
          </div>
        </section>

        {/* Skills */}
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-headline-md text-on-surface border-l-4 border-pulse-teal-vibrant pl-3">Skills</h2>
            <button className="bg-primary text-white text-label-sm px-4 py-2 rounded hover:bg-primary/90 transition-colors" onClick={() => setShowNewSkill((s) => !s)}>
              {showNewSkill ? "Cancel" : "New Skill"}
            </button>
          </div>
          <p className="text-body-sm text-on-surface-variant mb-4 max-w-3xl">
            A skill is a strict process the coach follows when a user starts a chat with its slash command
            (e.g. <code className="bg-surface-container px-1 rounded">/design-thinking</code>). Grant skills per organization
            from the org&apos;s Pulse Config tab.
          </p>

          {showNewSkill && (
            <div className="bg-surface-container-lowest border border-pulse-teal-vibrant rounded-lg p-4 mb-4 flex flex-col gap-3 max-w-3xl">
              <div className="grid grid-cols-2 gap-3">
                <input className="bg-surface-container-low border border-outline-variant rounded px-3 py-2 text-body-sm focus:outline-none focus:border-pulse-teal-vibrant" placeholder="Skill name (e.g. Lean Experiments)" value={ns.name} onChange={(e) => setNs({ ...ns, name: e.target.value })} />
                <input className="bg-surface-container-low border border-outline-variant rounded px-3 py-2 text-body-sm focus:outline-none focus:border-pulse-teal-vibrant" placeholder="command (e.g. lean-experiments)" value={ns.command} onChange={(e) => setNs({ ...ns, command: e.target.value })} />
              </div>
              <input className="bg-surface-container-low border border-outline-variant rounded px-3 py-2 text-body-sm focus:outline-none focus:border-pulse-teal-vibrant" placeholder="Short description for the / autocomplete" value={ns.description} onChange={(e) => setNs({ ...ns, description: e.target.value })} />
              <textarea className="bg-surface-container-low border border-outline-variant rounded px-3 py-2 text-body-sm focus:outline-none focus:border-pulse-teal-vibrant font-mono" rows={8} placeholder="Instructions the coach must follow for the whole conversation…" value={ns.body} onChange={(e) => setNs({ ...ns, body: e.target.value })} />
              <button
                className="bg-primary text-white text-label-sm px-4 py-2 rounded hover:bg-primary/90 self-start disabled:opacity-50"
                disabled={!ns.name || !ns.command || !ns.body}
                onClick={async () => { await createSkill(ns); setNs({ name: "", command: "", description: "", body: "" }); setShowNewSkill(false); load(); }}
              >
                Create skill
              </button>
            </div>
          )}

          <div className="max-w-3xl">
            {skills.map((s) => (
              <SkillEditor key={s.id} skill={s} onSaved={load} onDeleted={load} />
            ))}
            {skills.length === 0 && <p className="text-body-sm text-on-surface-variant">No skills yet.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Guard role="kpmg_admin">
      <StageKnowledge />
    </Guard>
  );
}
