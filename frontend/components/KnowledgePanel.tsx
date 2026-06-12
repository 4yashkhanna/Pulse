"use client";

import { useEffect, useRef, useState } from "react";
import { KDoc } from "@/lib/api";

export default function KnowledgePanel({
  title,
  hint,
  canEdit = true,
  load,
  upload,
  remove,
}: {
  title: string;
  hint: string;
  canEdit?: boolean;
  load: () => Promise<KDoc[]>;
  upload: (files: FileList | File[]) => Promise<any>;
  remove: (id: string) => Promise<any>;
}) {
  const [docs, setDocs] = useState<KDoc[]>([]);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const refresh = () => load().then(setDocs).catch(() => setDocs([]));
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title]);

  // Ingestion runs in the background — poll while any document is still processing.
  useEffect(() => {
    if (!docs.some((d) => d.status === "processing")) return;
    const t = setTimeout(refresh, 2500);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs]);

  async function handle(files: FileList | null) {
    if (!files || !files.length) return;
    setBusy(true);
    try {
      await upload(files);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-label">{title}</div>
      <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>{hint}</div>
      {canEdit && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            handle(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          style={{
            border: `1.5px dashed ${drag ? "var(--blue-mid)" : "var(--border-mid)"}`,
            background: drag ? "var(--blue-pale)" : "var(--surface)",
            borderRadius: 10,
            textAlign: "center",
            padding: 20,
            cursor: "pointer",
            marginBottom: 12,
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--blue)", fontSize: 13 }}>
            {busy ? "Processing…" : "Drop files or click to add"}
          </div>
          <div className="muted" style={{ fontSize: 11 }}>PDF · Word · PowerPoint · text / markdown</div>
          <input
            ref={inputRef}
            type="file"
            multiple
            hidden
            accept=".pdf,.docx,.pptx,.txt,.md,.markdown"
            onChange={(e) => handle(e.target.files)}
          />
        </div>
      )}
      {docs.length === 0 && <div className="muted" style={{ fontSize: 12 }}>No documents yet.</div>}
      {docs.map((d) => (
        <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: "0.5px solid var(--border)" }}>
          <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: "var(--ink-2)" }}>{d.filename}</span>
          <span className={`chip ${d.status === "error" ? "handoff" : ""}`}>
            {d.status === "ready" ? `${d.n_chunks} chunks` : d.status}
          </span>
          {canEdit && (
            <span
              style={{ color: "var(--coral)", cursor: "pointer", fontSize: 13 }}
              onClick={async () => {
                await remove(d.id);
                refresh();
              }}
            >
              Remove
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
