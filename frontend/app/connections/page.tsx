"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Guard from "@/components/Guard";
import {
  ConnectionStatus,
  disconnectConnection,
  listConnections,
  startConnection,
} from "@/lib/api";

function Banner({ kind, text }: { kind: "ok" | "error"; text: string }) {
  return (
    <div
      className="card mb-5 flex items-center gap-3"
      style={{
        borderLeft: `3px solid var(${kind === "ok" ? "--md-sys-color-primary" : "--md-sys-color-error"})`,
      }}
    >
      <span
        className={`material-symbols-outlined ${kind === "ok" ? "text-primary" : "text-error"}`}
        style={{ fontSize: 20 }}
      >
        {kind === "ok" ? "check_circle" : "error"}
      </span>
      <span className="text-body-sm text-on-surface">{text}</span>
    </div>
  );
}

function ConnectionCard({
  c,
  onChange,
}: {
  c: ConnectionStatus;
  onChange: () => void;
}) {
  const [busy, setBusy] = useState(false);

  async function connect() {
    setBusy(true);
    try {
      const { authorize_url } = await startConnection(c.provider);
      window.location.href = authorize_url; // hand off to the provider's consent screen
    } catch (e: any) {
      alert(e.message || "Couldn't start the connection.");
      setBusy(false);
    }
  }

  async function disconnect() {
    if (!confirm(`Disconnect ${c.label}? Pulse will no longer access it.`)) return;
    setBusy(true);
    try {
      await disconnectConnection(c.provider);
      onChange();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary-fixed flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-on-primary-fixed" style={{ fontSize: 22 }}>
            {c.icon}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-on-surface">{c.label}</span>
            {c.experimental && <span className="chip handoff">beta</span>}
            {c.connected && (
              <span className="material-symbols-outlined text-primary" style={{ fontSize: 18 }}>
                check_circle
              </span>
            )}
          </div>
          <p className="text-body-sm text-on-surface-variant mt-0.5">{c.capability}</p>
        </div>
      </div>

      {c.connected && c.account && (
        <div className="text-label-caps text-on-surface-variant">
          Connected as <span className="text-on-surface font-medium">{c.account}</span>
        </div>
      )}

      <div className="mt-auto pt-1">
        {!c.configured ? (
          <span className="text-label-sm text-on-surface-variant italic">
            Not set up on this server yet
          </span>
        ) : c.connected ? (
          <button
            className="text-error text-label-sm hover:underline disabled:opacity-50"
            onClick={disconnect}
            disabled={busy}
          >
            Disconnect
          </button>
        ) : (
          <button className="btn" onClick={connect} disabled={busy}>
            {busy ? "Connecting…" : "Connect"}
          </button>
        )}
      </div>
    </div>
  );
}

function Connections() {
  const params = useSearchParams();
  const [rows, setRows] = useState<ConnectionStatus[] | null>(null);
  const [banner, setBanner] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const load = () => listConnections().then(setRows).catch(() => setRows([]));
  useEffect(() => {
    load();
  }, []);

  // Surface the result of an OAuth round-trip (backend redirects back with these).
  useEffect(() => {
    const connected = params.get("connected");
    const error = params.get("error");
    if (connected) {
      setBanner({ kind: "ok", text: `${connected[0].toUpperCase()}${connected.slice(1)} connected.` });
      window.history.replaceState({}, "", "/connections");
    } else if (error) {
      setBanner({
        kind: "error",
        text: `Couldn't connect ${error}. Please try again.`,
      });
      window.history.replaceState({}, "", "/connections");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="app-main">
      <header className="topbar">
        <h2 className="text-headline-md font-semibold text-primary">Connections</h2>
      </header>
      <div className="page-canvas">
        <p className="page-sub" style={{ marginTop: 0 }}>
          Connect your own tools so Pulse can coach you with your real notes, designs, and
          tickets. Each connection is personal to you and can be removed any time.
        </p>

        {banner && <Banner kind={banner.kind} text={banner.text} />}

        {rows === null ? (
          <div className="muted">Loading…</div>
        ) : (
          <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
            {rows.map((c) => (
              <ConnectionCard key={c.provider} c={c} onChange={load} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Guard role={["employee", "manager"]}>
      <Connections />
    </Guard>
  );
}
