"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import { dashMe, dashMember, dashTeam } from "@/lib/api";

const PILLAR_ORDER = ["values", "behavior", "climate", "process", "resources", "success"];

function PillarBarsNew({ scores, baseline }: { scores?: Record<string, number>; baseline?: Record<string, number> }) {
  if (!scores) return null;
  const max = Math.max(1, ...Object.values(scores));
  return (
    <div className="space-y-4">
      {PILLAR_ORDER.map((p) => {
        const val = scores[p] ?? 0;
        const base = baseline?.[p];
        const pct = (val / max) * 100;
        const basePct = base != null ? (base / max) * 100 : null;
        return (
          <div key={p}>
            <div className="flex justify-between text-label-sm mb-1">
              <span className="text-on-surface capitalize">{p}</span>
              <span className="text-primary font-medium">{val.toFixed(0)}</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${pct}%` }} />
              {basePct != null && (
                <div className="absolute top-[-3px] bottom-[-3px] w-0.5 bg-outline-variant" style={{ left: `${basePct}%` }} title={`Baseline: ${base}`} />
              )}
            </div>
          </div>
        );
      })}
      {baseline && (
        <div className="flex items-center gap-4 mt-2 text-label-caps text-on-surface-variant">
          <div className="flex items-center gap-1"><div className="w-3 h-2 rounded-sm" style={{ background: "#00E1DE" }} /> Current</div>
          <div className="flex items-center gap-1"><div className="w-0.5 h-3 bg-outline-variant" /> Baseline</div>
        </div>
      )}
    </div>
  );
}

function PhaseBars({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts);
  const max = Math.max(1, ...entries.map(([, n]) => n));
  return (
    <div className="flex items-end justify-between h-40 border-b border-surface-container-high pb-2 px-2 mb-3">
      {entries.map(([ph, n]) => {
        const pct = (n / max) * 100;
        return (
          <div key={ph} className="flex flex-col items-center gap-1 group cursor-pointer" style={{ width: `${100 / entries.length}%` }}>
            <div className="w-8 bg-primary rounded-t-sm transition-opacity group-hover:opacity-80" style={{ height: `${pct}%`, minHeight: 4 }} />
            <span className="text-label-caps text-on-surface-variant truncate w-full text-center" title={ph}>
              {ph.slice(0, 3)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function Breakdown({ data }: { data: { pillar_scores?: Record<string, number>; breakdown?: Record<string, { signal_id: string; polarity: number; example?: string; text: string; count: number }[]> } }) {
  const anyData = PILLAR_ORDER.some((p) => (data.breakdown?.[p] || []).length);
  if (!anyData) return null;
  return (
    <section>
      <h3 className="text-headline-md text-primary mb-4">Coaching Breakdown</h3>
      {PILLAR_ORDER.map((p) => {
        const score = data.pillar_scores?.[p];
        const items = (data.breakdown?.[p] || []);
        if (!items.length) return null;
        return (
          <article key={p} className="card mb-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-3 gap-2">
              <h4 className="text-headline-sm text-primary flex items-center gap-2">
                <span className="w-2 h-2 rounded-full" style={{ background: "#00E1DE" }} />
                <span className="capitalize">{p}</span> Fluency
              </h4>
              <span className="bg-surface-container text-on-surface-variant text-label-caps px-3 py-1 rounded-full">
                {score != null ? `${score.toFixed(0)}/100` : "building…"}
              </span>
            </div>
            <div className="bg-surface border border-outline-variant/30 rounded-lg p-4">
              <div className="card-label border-b border-outline-variant/20 pb-2 mb-3">Evidence Signals</div>
              <ul className="space-y-3">
                {items.map((it) => (
                  <li key={it.signal_id} className="flex items-start gap-3">
                    <div className={`mt-1 shrink-0 text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1 uppercase tracking-wide ${it.polarity > 0 ? "bg-secondary-container text-on-secondary-container" : "bg-error-container text-on-error-container"}`}>
                      <span className="material-symbols-outlined" style={{ fontSize: 12 }}>{it.polarity > 0 ? "arrow_drop_up" : "arrow_drop_down"}</span>
                      {it.polarity > 0 ? "Positive" : "Negative"}
                    </div>
                    <div>
                      <p className="text-body-sm italic text-on-surface">
                        {it.example ? <>&ldquo;{it.example}&rdquo; — {it.text.toLowerCase()}</> : it.text}
                      </p>
                      {it.count > 1 && <p className="text-label-caps text-outline mt-1">Fired {it.count} times</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </article>
        );
      })}
    </section>
  );
}

function Individual({ data }: { data: { name?: string; dq_score?: number; baseline_dq?: number; evidence_rate?: number; total_interactions?: number; pillar_scores?: Record<string, number>; baseline_pillar_scores?: Record<string, number>; phase_counts?: Record<string, number>; skipped_phases?: string[]; breakdown?: Record<string, { signal_id: string; polarity: number; example?: string; text: string; count: number }[]> } }) {
  const delta = data.baseline_dq != null && data.dq_score != null
    ? Math.round((data.dq_score - data.baseline_dq) * 10) / 10
    : null;

  if (data.total_interactions === 0) {
    return (
      <div className="card">
        <div className="card-label">No coaching activity yet</div>
        <p className="muted mt-1">
          {data.name ? `${data.name} hasn't` : "You haven't"} used the coach yet. Scores appear once conversations begin.
          {data.baseline_dq != null && <> Assessment baseline DQ: <strong>{data.baseline_dq}</strong>.</>}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="card-label">{data.name ? `${data.name}'s DQ` : "My DQ Score"}</div>
          <div className="flex items-baseline gap-2">
            <span className="metric-big">{data.dq_score ?? "—"}</span>
            {delta != null && (
              <span className={`metric-delta ${delta >= 0 ? "up" : "down"}`}>
                {delta >= 0 ? "▲" : "▼"} {Math.abs(delta)}
              </span>
            )}
          </div>
          {data.baseline_dq != null && <div className="muted mt-1">baseline {data.baseline_dq}</div>}
        </div>
        <div className="card">
          <div className="card-label">Evidence-Backed Rate</div>
          <div className="metric-big">{data.evidence_rate}%</div>
          <div className="muted mt-1">Supporting data for decisions</div>
        </div>
        <div className="card relative overflow-hidden">
          <span className="material-symbols-outlined absolute right-2 top-2 opacity-5" style={{ fontSize: 80, fontVariationSettings: "'FILL' 1" }}>forum</span>
          <div className="card-label relative z-10">Coaching Turns</div>
          <div className="metric-big relative z-10">{data.total_interactions}</div>
          <div className="muted mt-1 relative z-10">Total sessions analyzed</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-headline-sm text-primary mb-4">Pillar Fluency</h3>
          <PillarBarsNew scores={data.pillar_scores} baseline={data.baseline_pillar_scores} />
        </div>
        <div className="card">
          <h3 className="text-headline-sm text-primary mb-4">Phase Habits</h3>
          {data.phase_counts && <PhaseBars counts={data.phase_counts} />}
          {data.skipped_phases?.length ? (
            <div className="flex items-start gap-2 bg-error-container text-on-error-container border-l-4 border-error p-3 rounded-r text-body-sm">
              <span className="material-symbols-outlined mt-0.5" style={{ fontSize: 18 }}>warning</span>
              <div>
                <strong className="text-label-caps uppercase">Phase Habit Alert</strong>
                <p>Tends to skip: <strong>{data.skipped_phases.join(", ")}</strong></p>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* Breakdown */}
      {data.breakdown && <Breakdown data={data} />}
    </div>
  );
}

function Team() {
  const [data, setData] = useState<{ team_name?: string; team_dq?: number; most_skipped_phase?: string; evidence_rate?: number; team_pillar_scores?: Record<string, number>; members?: { id: string; name: string; total_interactions: number; dq_score: number }[] } | null>(null);
  const [member, setMember] = useState<{ name?: string; dq_score?: number; baseline_dq?: number; evidence_rate?: number; total_interactions?: number; pillar_scores?: Record<string, number>; baseline_pillar_scores?: Record<string, number>; phase_counts?: Record<string, number>; skipped_phases?: string[]; breakdown?: Record<string, { signal_id: string; polarity: number; example?: string; text: string; count: number }[]> } | null>(null);

  useEffect(() => {
    dashTeam().then(setData).catch(() => {});
  }, []);

  if (!data) return <div className="muted">Loading team…</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="card-label">{data.team_name} · Team DQ</div>
          <div className="metric-big">{data.team_dq}</div>
        </div>
        <div className="card">
          <div className="card-label">Most-skipped phase</div>
          <div className="metric-big capitalize" style={{ fontSize: 32 }}>{data.most_skipped_phase ?? "—"}</div>
        </div>
        <div className="card">
          <div className="card-label">Team evidence rate</div>
          <div className="metric-big">{data.evidence_rate}%</div>
        </div>
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-headline-sm text-primary mb-4">Team fluency by pillar</h3>
          <PillarBarsNew scores={data.team_pillar_scores} />
        </div>
        {data.members && (
          <div className="card">
            <h3 className="text-headline-sm text-primary mb-4">Team members</h3>
            {data.members.map((m) => (
              <div key={m.id} onClick={() => dashMember(m.id).then(setMember)}
                className="flex items-center gap-3 py-3 border-b border-surface-container last:border-0 cursor-pointer hover:bg-surface-container-low rounded px-2 -mx-2 transition-colors">
                <div className="w-8 h-8 rounded-full bg-primary-fixed flex items-center justify-center text-on-primary-fixed text-label-sm font-bold shrink-0">
                  {m.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                </div>
                <span className="flex-1 font-medium text-on-surface text-body-sm">{m.name}</span>
                <span className="text-label-sm text-on-surface-variant">{m.total_interactions} turns</span>
                <span className="font-bold text-primary text-body-md w-8 text-right">{m.dq_score}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {member && (
        <div>
          <div className="flex items-center mb-4">
            <h3 className="text-headline-sm text-primary">{member.name}&apos;s dashboard</h3>
            <button className="ml-auto text-on-surface-variant hover:text-primary text-body-sm" onClick={() => setMember(null)}>Close ×</button>
          </div>
          <Individual data={member} />
        </div>
      )}
    </div>
  );
}

function Dashboard() {
  const [me, setMe] = useState<{ can_see_team?: boolean; name?: string; dq_score?: number; baseline_dq?: number; evidence_rate?: number; total_interactions?: number; pillar_scores?: Record<string, number>; baseline_pillar_scores?: Record<string, number>; phase_counts?: Record<string, number>; skipped_phases?: string[]; breakdown?: Record<string, { signal_id: string; polarity: number; example?: string; text: string; count: number }[]> } | null>(null);
  const [tab, setTab] = useState<"me" | "team">("me");

  useEffect(() => {
    dashMe().then(setMe).catch(() => {});
  }, []);

  if (!me) return <div className="app-main"><div className="page-canvas muted">Loading…</div></div>;

  return (
    <div className="app-main">
      <header className="topbar">
        <div className="topbar-tabs">
          {(["me", "team"] as const).filter((t) => t === "me" || me.can_see_team).map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`topbar-tab ${tab === t ? "active" : ""}`}>
              {t === "me" ? "My Progress" : "Team"}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 text-on-surface-variant">
          <button className="btn-teal flex items-center gap-2 text-label-sm" style={{ height: 36 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>bolt</span>
            Generate Report
          </button>
        </div>
      </header>

      <div className="page-canvas">
        <div className="mb-6">
          <h2 className="page-title">Performance Dashboard</h2>
          <p className="page-sub">Your design intelligence metrics and coaching insights.</p>
        </div>
        {tab === "me" ? <Individual data={me} /> : <Team />}
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Guard role={["employee", "manager"]}>
      <Dashboard />
    </Guard>
  );
}
