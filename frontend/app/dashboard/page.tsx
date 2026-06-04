"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import PillarBars from "@/components/PillarBars";
import { dashMe, dashMember, dashTeam } from "@/lib/api";

function PhaseBars({ counts }: { counts: Record<string, number> }) {
  const max = Math.max(1, ...Object.values(counts));
  return (
    <div>
      {Object.entries(counts).map(([ph, n]) => (
        <div className="bar-row" key={ph}>
          <div className="bar-label">{ph}</div>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(n / max) * 100}%`, background: "var(--blue-mid)" }} />
          </div>
          <div className="bar-val">{n}</div>
        </div>
      ))}
    </div>
  );
}

const PILLAR_ORDER = ["values", "behavior", "climate", "process", "resources", "success"];

function Breakdown({ data }: { data: any }) {
  // Lead with concrete, human-readable reasons (a real quote + what it means), per pillar.
  const anyData = PILLAR_ORDER.some((p) => (data.breakdown?.[p] || []).length);
  if (!anyData) return null;
  return (
    <div className="card">
      <div className="card-label">Why these scores — what was actually observed</div>
      {PILLAR_ORDER.map((p) => {
        const score = data.pillar_scores?.[p];
        const items = (data.breakdown?.[p] || []) as any[];
        if (!items.length) return null;
        return (
          <div key={p} style={{ padding: "12px 0", borderBottom: "0.5px solid var(--border)" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 8 }}>
              <span style={{ textTransform: "capitalize", fontWeight: 700, color: "var(--blue)" }}>{p}</span>
              <span style={{ fontWeight: 700 }}>
                {score != null ? `${score.toFixed(0)}/100` : "building…"}
              </span>
            </div>
            {items.map((it) => (
              <div key={it.signal_id} style={{ display: "flex", gap: 8, marginBottom: 6, fontSize: 13 }}>
                <span style={{ color: it.polarity > 0 ? "var(--green)" : "var(--coral)", fontWeight: 700 }}>
                  {it.polarity > 0 ? "▲" : "▼"}
                </span>
                <span style={{ color: "var(--ink-2)", lineHeight: 1.5 }}>
                  {it.example ? (
                    <>
                      “<em>{it.example}</em>” — {it.text.toLowerCase()}
                    </>
                  ) : (
                    it.text
                  )}
                  {it.count > 1 && <span className="muted"> (×{it.count})</span>}
                </span>
              </div>
            ))}
          </div>
        );
      })}
      <div className="muted" style={{ marginTop: 10, fontSize: 11 }}>
        Each line is a behaviour observed in the coaching conversations. A pillar scores once
        it has enough observations; score = positive ÷ all observations for that pillar.
      </div>
    </div>
  );
}

function Individual({ data }: { data: any }) {
  const delta =
    data.baseline_dq != null && data.dq_score != null
      ? Math.round((data.dq_score - data.baseline_dq) * 10) / 10
      : null;
  if (data.total_interactions === 0) {
    return (
      <div className="card">
        <div className="card-label">No coaching activity yet</div>
        <p className="muted" style={{ marginTop: 4 }}>
          {data.name ? `${data.name} hasn't` : "You haven't"} used the coach yet. Scores are
          measured from real coaching conversations and will appear here as soon as there are
          any.{" "}
          {data.baseline_dq != null && (
            <>Assessment baseline DQ: <strong>{data.baseline_dq}</strong>.</>
          )}
        </p>
      </div>
    );
  }
  return (
    <>
      <div className="grid grid-3" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-label">{data.name ? `${data.name}'s DQ` : "My DQ Score"}</div>
          <div>
            <span className="metric-big">{data.dq_score ?? "—"}</span>
            {delta != null && (
              <span className={`metric-delta ${delta >= 0 ? "up" : "down"}`}>
                {delta >= 0 ? "▲" : "▼"} {Math.abs(delta)}
              </span>
            )}
          </div>
          {data.baseline_dq != null && (
            <div className="muted" style={{ marginTop: 6 }}>baseline {data.baseline_dq}</div>
          )}
        </div>
        <div className="card">
          <div className="card-label">Evidence-backed rate</div>
          <div className="metric-big">{data.evidence_rate}%</div>
        </div>
        <div className="card">
          <div className="card-label">Coaching turns</div>
          <div className="metric-big">{data.total_interactions}</div>
        </div>
      </div>
      <div className="grid grid-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-label">Fluency by pillar (vs baseline)</div>
          <PillarBars scores={data.pillar_scores} baseline={data.baseline_pillar_scores} />
        </div>
        <div className="card">
          <div className="card-label">Phase habits</div>
          <PhaseBars counts={data.phase_counts} />
          {data.skipped_phases?.length > 0 && (
            <div className="muted" style={{ marginTop: 10 }}>
              Tends to skip: <strong>{data.skipped_phases.join(", ")}</strong>
            </div>
          )}
        </div>
      </div>
      {data.breakdown && <Breakdown data={data} />}
    </>
  );
}

function Team() {
  const [data, setData] = useState<any>(null);
  const [member, setMember] = useState<any>(null);
  useEffect(() => {
    dashTeam().then(setData).catch(() => {});
  }, []);
  if (!data) return <div className="muted">Loading team…</div>;
  return (
    <>
      <div className="grid grid-3" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-label">{data.team_name} · Team DQ</div>
          <div className="metric-big">{data.team_dq}</div>
        </div>
        <div className="card">
          <div className="card-label">Most-skipped phase</div>
          <div className="metric-big" style={{ fontSize: 26, textTransform: "capitalize" }}>{data.most_skipped_phase ?? "—"}</div>
        </div>
        <div className="card">
          <div className="card-label">Team evidence rate</div>
          <div className="metric-big">{data.evidence_rate}%</div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-label">Team fluency by pillar</div>
          <PillarBars scores={data.team_pillar_scores} />
        </div>
        {data.members && (
          <div className="card">
            <div className="card-label">Team members — click to drill in</div>
            {data.members.map((m: any) => (
              <div
                key={m.id}
                onClick={() => dashMember(m.id).then(setMember)}
                style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 0", borderBottom: "0.5px solid var(--border)", cursor: "pointer" }}
              >
                <span style={{ flex: 1, fontWeight: 600, color: "var(--ink-2)" }}>{m.name}</span>
                <span className="muted">{m.total_interactions} turns</span>
                <span style={{ fontWeight: 700, color: "var(--blue)", width: 40, textAlign: "right" }}>{m.dq_score}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {member && (
        <div style={{ marginTop: 20 }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
            <div className="page-sub" style={{ margin: 0 }}>{member.name}&apos;s dashboard</div>
            <span style={{ flex: 1 }} />
            <button className="nav-link" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ink-3)" }} onClick={() => setMember(null)}>
              Close ×
            </button>
          </div>
          <Individual data={member} />
        </div>
      )}
    </>
  );
}

function Dashboard() {
  const [me, setMe] = useState<any>(null);
  const [tab, setTab] = useState<"me" | "team">("me");
  useEffect(() => {
    dashMe().then(setMe).catch(() => {});
  }, []);
  if (!me) return <div className="page muted">Loading…</div>;

  return (
    <div className="page">
      <div className="page-title">Performance</div>
      <div className="page-sub">Measured passively from your coaching conversations</div>

      {me.can_see_team && (
        <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          {(["me", "team"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className="nav-link"
              style={{
                background: tab === t ? "var(--blue)" : "var(--white)",
                color: tab === t ? "#fff" : "var(--ink-2)",
                border: "0.5px solid var(--border-mid)",
                borderRadius: 8,
                padding: "8px 16px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {t === "me" ? "My progress" : "Team"}
            </button>
          ))}
        </div>
      )}

      {tab === "me" ? <Individual data={me} /> : <Team />}
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
