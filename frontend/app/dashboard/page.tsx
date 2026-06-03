"use client";

import Guard from "@/components/Guard";

export default function Page() {
  return (
    <Guard role={["employee", "manager"]}>
      <div className="page">
        <div className="page-title">Performance</div>
        <div className="page-sub">Coming after the chatbot</div>
        <div className="card muted">
          Individual and team dashboards (permission-gated) are built once conversations
          are flowing through the coach.
        </div>
      </div>
    </Guard>
  );
}
