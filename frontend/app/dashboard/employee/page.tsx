"use client";

import { useEffect, useState } from "react";
import PillarBars from "@/components/PillarBars";
import { User, getEmployee, getUsers } from "@/lib/api";

export default function EmployeeDashboard() {
  const [users, setUsers] = useState<User[]>([]);
  const [userId, setUserId] = useState("");
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    getUsers().then((u) => {
      setUsers(u);
      if (u.length) setUserId(u[0].id);
    });
  }, []);

  useEffect(() => {
    if (userId) getEmployee(userId).then(setData);
  }, [userId]);

  return (
    <div className="page">
      <div className="page-title">My Progress</div>
      <div className="page-sub">Individual design-thinking growth · View 01</div>

      <div style={{ marginBottom: 20 }}>
        <select
          className="select"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        >
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name} · {u.dept}
            </option>
          ))}
        </select>
      </div>

      {data && (
        <>
          <div className="grid grid-3" style={{ marginBottom: 16 }}>
            <div className="card">
              <div className="card-label">My DQ Score</div>
              <div className="metric-big">{data.dq_score}</div>
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

          <div className="grid grid-2">
            <div className="card">
              <div className="card-label">Fluency by pillar</div>
              <PillarBars scores={data.pillar_scores} />
            </div>
            <div className="card">
              <div className="card-label">Phase habits</div>
              {Object.entries(data.phase_counts).map(([ph, n]: any) => (
                <div className="bar-row" key={ph}>
                  <div className="bar-label">{ph}</div>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{
                        width: `${Math.min(100, (n as number) * 18)}%`,
                        background: "var(--blue-mid)",
                      }}
                    />
                  </div>
                  <div className="bar-val">{n as number}</div>
                </div>
              ))}
              {data.skipped_phases.length > 0 && (
                <div className="muted" style={{ marginTop: 10 }}>
                  Phases you tend to skip:{" "}
                  <strong>{data.skipped_phases.join(", ")}</strong>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
