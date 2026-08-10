"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Guard from "@/components/Guard";
import { Org, createOrg, listOrgs } from "@/lib/api";

const STAGE_LABELS: Record<number, string> = {
  1: "Initial Assessment",
  2: "Foundation",
  3: "Optimization",
  4: "Optimized",
  5: "Target Goal",
};

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function Sparkline({ seed }: { seed: number }) {
  // deterministic pseudo-random bars so each org gets a stable sparkline
  const heights = useMemo(() => {
    const out: number[] = [];
    let x = seed || 1;
    for (let i = 0; i < 6; i++) {
      x = (x * 9301 + 49297) % 233280;
      out.push(4 + Math.floor((x / 233280) * 12));
    }
    return out;
  }, [seed]);
  return (
    <div className="w-16 h-4 flex items-end gap-0.5 mb-1 opacity-80">
      {heights.map((h, i) => (
        <div
          key={i}
          className={i === heights.length - 1 ? "w-2 bg-pulse-teal-vibrant" : "w-2 bg-secondary"}
          style={{ height: h }}
        />
      ))}
    </div>
  );
}

function OrgCard({ org, onOpen }: { org: Org; onOpen: () => void }) {
  return (
    <div
      onClick={onOpen}
      className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-ambient hover:shadow-md transition-shadow duration-300 overflow-hidden group cursor-pointer relative"
    >
      <div className="h-1 w-full bg-pulse-teal-vibrant" />
      <div className="p-stack-md">
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-primary-container text-on-primary flex items-center justify-center text-headline-sm font-bold">
              {initials(org.name)}
            </div>
            <div>
              <h4 className="text-headline-sm text-primary group-hover:text-primary-container transition-colors">{org.name}</h4>
              <p className="text-body-sm text-on-surface-variant">{org.maturity_label || "—"}</p>
            </div>
          </div>
          <span className="material-symbols-outlined text-on-surface-variant">more_vert</span>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4 bg-surface-container-low p-3 rounded">
          <div>
            <p className="text-label-caps text-on-surface-variant mb-1">MATURITY STAGE</p>
            <div className="flex items-end gap-2">
              <span className="text-headline-md text-primary">{org.maturity_stage}</span>
              <Sparkline seed={org.name.length * 7 + org.maturity_stage} />
            </div>
          </div>
          <div>
            <p className="text-label-caps text-on-surface-variant mb-1">PEOPLE</p>
            <p className="text-headline-md text-primary">{org.n_users ?? 0}</p>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-secondary-fixed/20 text-secondary text-label-sm border border-secondary/20">
            <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
            Stage {org.maturity_stage} · {STAGE_LABELS[org.maturity_stage] || "Custom"}
          </span>
          <span className="text-body-sm text-on-surface-variant flex items-center gap-1 group-hover:text-primary transition-colors">
            View Details <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_forward</span>
          </span>
        </div>
      </div>
    </div>
  );
}

function AdminOrgs() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [query, setQuery] = useState("");
  const [stageFilter, setStageFilter] = useState<number | 0>(0);
  const [showNew, setShowNew] = useState(false);
  const [name, setName] = useState("");
  const [stage, setStage] = useState(2);
  const [busy, setBusy] = useState(false);

  function load() { listOrgs().then(setOrgs).catch(() => {}); }
  useEffect(load, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const org = await createOrg({ name, maturity_stage: stage });
      setShowNew(false);
      setName("");
      router.push(`/admin/org/${org.id}`);
    } finally {
      setBusy(false);
    }
  }

  const filtered = orgs.filter(
    (o) =>
      o.name.toLowerCase().includes(query.toLowerCase()) &&
      (stageFilter === 0 || o.maturity_stage === stageFilter),
  );

  const totalUsers = orgs.reduce((s, o) => s + (o.n_users ?? 0), 0);
  const totalChunks = orgs.reduce((s, o) => s + (o.n_chunks ?? 0), 0);

  return (
    <div className="app-main">
      {/* TopNavBar */}
      <header className="topbar">
        <h2 className="text-headline-md font-bold text-primary">Organizations Overview</h2>
        <div className="flex-1 max-w-md mx-8 relative">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">search</span>
          <input
            className="w-full bg-surface-container-low border border-outline-variant text-on-surface text-body-sm rounded pl-10 pr-4 py-2 focus:outline-none focus:border-pulse-teal-vibrant focus:ring-1 focus:ring-pulse-teal-vibrant transition-all"
            placeholder="Search organizations..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
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
      </header>

      <div className="page-canvas">
        {/* Welcome header */}
        <section className="mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <h2 className="text-headline-lg text-primary font-bold mb-2">Good morning, Admin.</h2>
            <p className="text-body-md text-on-surface-variant">Here is the latest intelligence across all active client organizations.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <select
                className="appearance-none bg-surface border border-outline-variant text-on-surface text-body-sm rounded pl-4 pr-10 py-2 focus:outline-none focus:border-pulse-teal-vibrant cursor-pointer shadow-sm"
                value={stageFilter}
                onChange={(e) => setStageFilter(Number(e.target.value))}
              >
                <option value={0}>All Stages</option>
                {[1, 2, 3, 4, 5].map((s) => (
                  <option key={s} value={s}>Stage {s}: {STAGE_LABELS[s]}</option>
                ))}
              </select>
              <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none" style={{ fontSize: 20 }}>expand_more</span>
            </div>
            <button
              className="bg-primary text-on-primary text-label-sm py-2 px-4 rounded hover:bg-primary-container transition-colors shadow-sm flex items-center gap-2"
              onClick={() => setShowNew((s) => !s)}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>
              New Org
            </button>
          </div>
        </section>

        {showNew && (
          <form onSubmit={create} className="card mb-6 flex gap-4 items-end flex-wrap">
            <div className="flex-1" style={{ minWidth: 200 }}>
              <div className="card-label">Organization name</div>
              <input className="input-field w-full" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Northwind Retail" required />
            </div>
            <div>
              <div className="card-label">Maturity stage</div>
              <select className="select" value={stage} onChange={(e) => setStage(Number(e.target.value))}>
                {[1, 2, 3, 4, 5].map((s) => <option key={s} value={s}>Stage {s}</option>)}
              </select>
            </div>
            <button className="btn" style={{ height: 40 }} disabled={busy}>Create</button>
          </form>
        )}

        {/* Key metrics */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-surface-container-lowest rounded-xl p-stack-md border border-outline-variant shadow-ambient flex items-center justify-between">
            <div>
              <p className="text-label-caps text-on-surface-variant mb-1">TOTAL ORGANIZATIONS</p>
              <p className="text-display-lg text-primary">{orgs.length}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-primary-fixed flex items-center justify-center text-primary">
              <span className="material-symbols-outlined icon-fill">corporate_fare</span>
            </div>
          </div>
          <div className="bg-surface-container-lowest rounded-xl p-stack-md border border-outline-variant shadow-ambient flex items-center justify-between">
            <div>
              <p className="text-label-caps text-on-surface-variant mb-1">TOTAL PEOPLE COACHED</p>
              <p className="text-display-lg text-primary">{totalUsers}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-secondary-fixed/20 flex items-center justify-center text-secondary">
              <span className="material-symbols-outlined icon-fill">monitoring</span>
            </div>
          </div>
          <div className="bg-surface-container-lowest rounded-xl p-stack-md border border-outline-variant shadow-ambient flex items-center justify-between">
            <div>
              <p className="text-label-caps text-on-surface-variant mb-1">KNOWLEDGE CHUNKS INDEXED</p>
              <p className="text-display-lg text-primary">{totalChunks}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-tertiary-fixed flex items-center justify-center text-tertiary">
              <span className="material-symbols-outlined icon-fill">database</span>
            </div>
          </div>
        </section>

        {/* Organizations grid */}
        <section>
          <div className="flex items-center justify-between mb-4 border-b border-outline-variant pb-2">
            <h3 className="text-headline-sm text-primary font-medium">Active Organizations</h3>
            <div className="flex items-center gap-2">
              <button className="p-1.5 text-primary bg-surface-container-low rounded">
                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>grid_view</span>
              </button>
              <button className="p-1.5 text-on-surface-variant hover:bg-surface-container-low rounded">
                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>view_list</span>
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {filtered.map((o) => (
              <OrgCard key={o.id} org={o} onOpen={() => router.push(`/admin/org/${o.id}`)} />
            ))}
            {filtered.length === 0 && (
              <div className="muted col-span-full">
                {orgs.length === 0 ? "No organizations yet — create one to begin." : "No organizations match your search."}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Guard role="kpmg_admin">
      <AdminOrgs />
    </Guard>
  );
}
