"use client";

import { useEffect, useState } from "react";
import { getDepts, getManager } from "@/lib/api";

const PILLARS = ["values", "behavior", "climate", "process", "resources", "success"];

function heatColor(v: number): string {
  // 0 → pale, 100 → teal
  const t = Math.max(0, Math.min(1, v / 100));
  const r = Math.round(224 + (0 - 224) * t);
  const g = Math.round(246 + (178 - 246) * t);
  const b = Math.round(245 + (169 - 245) * t);
  return `rgb(${r},${g},${b})`;
}

export default function ManagerDashboard() {
  const [depts, setDepts] = useState<string[]>([]);
  const [dept, setDept] = useState("");
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    getDepts().then((d) => {
      setDepts(d);
      if (d.length) setDept(d[0]);
    });
  }, []);

  useEffect(() => {
    if (dept) getManager(dept).then(setData);
  }, [dept]);

  return (
    <div className="page">
      <div className="page-title">Team &amp; Department</div>
      <div className="page-sub">Where the team is strong, stuck, or skipping · View 02</div>

      <div style={{ marginBottom: 20 }}>
        <select
          className="select"
          value={dept}
          onChange={(e) => setDept(e.target.value)}
        >
          {depts.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>

      {data && (
        <>
          <div className="grid grid-3" style={{ marginBottom: 16 }}>
            <div className="card">
              <div className="card-label">Team DQ Score</div>
              <div className="metric-big">{data.team_dq}</div>
            </div>
            <div className="card">
              <div className="card-label">Most-skipped phase</div>
              <div className="metric-big" style={{ fontSize: 28, textTransform: "capitalize" }}>
                {data.most_skipped_phase ?? "—"}
              </div>
            </div>
            <div className="card">
              <div className="card-label">Stagnation flags (6+ wks)</div>
              <div style={{ marginTop: 6 }}>
                {data.stagnation_flags.length === 0 ? (
                  <span className="muted">None — team is active</span>
                ) : (
                  data.stagnation_flags.map((n: string) => (
                    <span className="flag" key={n}>
                      {n}
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-label">Team heatmap — DQ fluency by pillar</div>
            <table className="heat-table">
              <thead>
                <tr>
                  <th>Member</th>
                  {PILLARS.map((p) => (
                    <th key={p}>{p}</th>
                  ))}
                  <th>DQ</th>
                </tr>
              </thead>
              <tbody>
                {data.heatmap.map((row: any) => (
                  <tr key={row.name}>
                    <td>{row.name}</td>
                    {PILLARS.map((p) => {
                      const v = row.pillar_scores[p] ?? 0;
                      return (
                        <td key={p} style={{ padding: 4 }}>
                          <div
                            className="heat-cell"
                            style={{
                              background: heatColor(v),
                              color: v > 55 ? "#fff" : "var(--ink-2)",
                            }}
                          >
                            {v.toFixed(0)}
                          </div>
                        </td>
                      );
                    })}
                    <td style={{ textAlign: "center", fontWeight: 700, color: "var(--blue)" }}>
                      {row.dq}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
