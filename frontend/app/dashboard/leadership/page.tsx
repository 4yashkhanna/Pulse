"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import PillarBars from "@/components/PillarBars";
import { getLeadership } from "@/lib/api";

export default function LeadershipDashboard() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    getLeadership().then(setData);
  }, []);

  if (!data) return <div className="page muted">Loading…</div>;

  const delta = data.delta_vs_baseline;

  return (
    <div className="page">
      <div className="page-title">Organisation Maturity</div>
      <div className="page-sub">
        Live Design Quality score vs baseline · View 03
      </div>

      <div className="grid grid-3" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-label">Live DQ Score</div>
          <div>
            <span className="metric-big">{data.dq_score}</span>
            {delta !== null && (
              <span className={`metric-delta ${delta >= 0 ? "up" : "down"}`}>
                {delta >= 0 ? "▲" : "▼"} {Math.abs(delta)} vs baseline
              </span>
            )}
          </div>
          <div className="muted" style={{ marginTop: 8 }}>
            Baseline at assessment: {data.baseline_dq ?? "—"}
          </div>
        </div>
        <div className="card">
          <div className="card-label">Industry benchmark</div>
          <div className="metric-big">{data.benchmark}</div>
          <div className="muted" style={{ marginTop: 8 }}>
            {data.dq_score >= data.benchmark
              ? "Above benchmark"
              : "Below benchmark — closing the gap"}
          </div>
        </div>
        <div className="card">
          <div className="card-label">Strongest / weakest pillar</div>
          {(() => {
            const entries = Object.entries(data.pillar_scores) as [string, number][];
            const sorted = [...entries].sort((a, b) => b[1] - a[1]);
            const top = sorted[0];
            const bottom = sorted[sorted.length - 1];
            return (
              <div style={{ marginTop: 6 }}>
                <div style={{ textTransform: "capitalize", fontWeight: 700, color: "var(--green)" }}>
                  ↑ {top[0]} ({top[1].toFixed(0)})
                </div>
                <div style={{ textTransform: "capitalize", fontWeight: 700, color: "var(--coral)", marginTop: 4 }}>
                  ↓ {bottom[0]} ({bottom[1].toFixed(0)})
                </div>
              </div>
            );
          })()}
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-label">DQ trajectory (monthly)</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.trajectory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="month" fontSize={11} />
              <YAxis domain={[0, 100]} fontSize={11} />
              <Tooltip />
              {data.baseline_dq !== null && (
                <ReferenceLine
                  y={data.baseline_dq}
                  stroke="#bc204b"
                  strokeDasharray="4 4"
                  label={{ value: "baseline", fontSize: 10, fill: "#bc204b" }}
                />
              )}
              <Line
                type="monotone"
                dataKey="dq"
                stroke="#00338d"
                strokeWidth={2.5}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div className="card-label">Pillar scores vs baseline</div>
          <PillarBars
            scores={data.pillar_scores}
            baseline={data.baseline_pillar_scores}
          />
        </div>
      </div>
    </div>
  );
}
