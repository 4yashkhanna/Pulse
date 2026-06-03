"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Guard from "@/components/Guard";
import { Org, createOrg, listOrgs } from "@/lib/api";

function AdminOrgs() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [showNew, setShowNew] = useState(false);
  const [name, setName] = useState("");
  const [stage, setStage] = useState(2);
  const [busy, setBusy] = useState(false);

  function load() {
    listOrgs().then(setOrgs).catch(() => {});
  }
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

  return (
    <div className="page">
      <div style={{ display: "flex", alignItems: "center" }}>
        <div>
          <div className="page-title">Organizations</div>
          <div className="page-sub">Set up and manage client engagements</div>
        </div>
        <span style={{ flex: 1 }} />
        <button className="btn" style={{ height: 40 }} onClick={() => setShowNew((s) => !s)}>
          + New organization
        </button>
      </div>

      {showNew && (
        <form onSubmit={create} className="card" style={{ marginBottom: 16, display: "flex", gap: 10, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <div className="card-label">Organization name</div>
            <input className="chat-input" style={{ width: "100%" }} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Northwind Retail" required />
          </div>
          <div>
            <div className="card-label">Maturity stage</div>
            <select className="select" value={stage} onChange={(e) => setStage(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((s) => (
                <option key={s} value={s}>Stage {s}</option>
              ))}
            </select>
          </div>
          <button className="btn" style={{ height: 44 }} disabled={busy}>Create</button>
        </form>
      )}

      <div className="grid grid-3">
        {orgs.map((o) => (
          <div key={o.id} className="card" style={{ cursor: "pointer" }} onClick={() => router.push(`/admin/org/${o.id}`)}>
            <div className="card-label">Stage {o.maturity_stage} · {o.maturity_label}</div>
            <h3 style={{ color: "var(--blue)", marginBottom: 10 }}>{o.name}</h3>
            <div className="muted">
              {o.n_users ?? 0} users · {o.n_chunks ?? 0} knowledge chunks
            </div>
          </div>
        ))}
        {orgs.length === 0 && <div className="muted">No organizations yet. Create one to begin.</div>}
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
