"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import KnowledgePanel from "@/components/KnowledgePanel";
import { useAuth } from "@/lib/auth";
import {
  Folder,
  createFolder,
  deleteFolder,
  deleteFolderDoc,
  deleteTeamDoc,
  folderAccess,
  folderAccessChange,
  getTeamDocs,
  listFolderDocs,
  listFolders,
  requestFolderAccess,
  uploadFolderDocs,
  uploadTeamDocs,
} from "@/lib/api";

function AccessList({ folderId }: { folderId: string }) {
  const [rows, setRows] = useState<{ id: string; name: string; status: string }[]>([]);
  const load = () => folderAccess(folderId).then(setRows).catch(() => setRows([]));
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [folderId]);
  return (
    <div style={{ marginTop: 10 }}>
      <div className="card-label">Who can use this folder</div>
      {rows.length === 0 && <div className="muted" style={{ fontSize: 12 }}>No other team members.</div>}
      {rows.map((m) => (
        <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: "0.5px solid var(--border)" }}>
          <span style={{ flex: 1, fontSize: 13, fontWeight: 600 }}>{m.name}</span>
          {m.status === "requested" && <span className="chip handoff">requested</span>}
          {m.status === "granted" ? (
            <button className="nav-link" style={{ background: "none", border: "none", color: "var(--coral)", cursor: "pointer", fontSize: 12 }}
              onClick={async () => { await folderAccessChange(folderId, m.id, "revoke"); load(); }}>Revoke</button>
          ) : (
            <button className="btn" style={{ height: 28, padding: "0 10px", fontSize: 12 }}
              onClick={async () => { await folderAccessChange(folderId, m.id, "grant"); load(); }}>Grant</button>
          )}
        </div>
      ))}
    </div>
  );
}

function ManagerFolder({ folder, onChange }: { folder: Folder; onChange: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }} onClick={() => setOpen((o) => !o)}>
        <span style={{ fontWeight: 700, color: "var(--blue)" }}>📚 {folder.name}</span>
        <span className="muted" style={{ fontSize: 12 }}>{folder.n_docs} files · {folder.n_granted} with access</span>
        {!!folder.n_requests && <span className="chip handoff">{folder.n_requests} request{folder.n_requests > 1 ? "s" : ""}</span>}
        <span style={{ marginLeft: "auto", color: "var(--coral)", fontSize: 12 }}
          onClick={async (e) => { e.stopPropagation(); if (confirm(`Delete folder "${folder.name}"?`)) { await deleteFolder(folder.id); onChange(); } }}>Delete</span>
      </div>
      {open && (
        <div style={{ marginTop: 12 }}>
          <KnowledgePanel
            title="Folder files"
            hint="Documents in this shareable knowledge set."
            load={() => listFolderDocs(folder.id)}
            upload={(fs) => uploadFolderDocs(folder.id, fs).then((r) => { onChange(); return r; })}
            remove={(id) => deleteFolderDoc(folder.id, id).then((r) => { onChange(); return r; })}
          />
          <AccessList folderId={folder.id} />
        </div>
      )}
    </div>
  );
}

function FolderSection() {
  const { user } = useAuth();
  const isManager = user?.role === "manager";
  const [folders, setFolders] = useState<Folder[]>([]);
  const [name, setName] = useState("");
  const load = () => listFolders().then(setFolders).catch(() => setFolders([]));
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ marginTop: 24 }}>
      <div className="page-sub" style={{ marginBottom: 12 }}>Knowledge folders</div>
      <p className="muted" style={{ marginBottom: 16 }}>
        {isManager
          ? "Curated knowledge sets you share with specific people. Grant access, and they can import a folder into their own projects."
          : "Knowledge sets your manager curates. Request access, then import a folder into one of your projects from the Coach."}
      </p>

      {isManager && (
        <form onSubmit={async (e) => { e.preventDefault(); if (!name.trim()) return; await createFolder(name); setName(""); load(); }}
          className="card" style={{ marginBottom: 16, display: "flex", gap: 10 }}>
          <input className="chat-input" style={{ flex: 1 }} placeholder="New folder name (e.g. Sustainability Research)" value={name} onChange={(e) => setName(e.target.value)} />
          <button className="btn" style={{ height: 44 }}>Create folder</button>
        </form>
      )}

      {folders.length === 0 && <div className="muted">No knowledge folders yet.</div>}

      {isManager
        ? folders.map((f) => <ManagerFolder key={f.id} folder={f} onChange={load} />)
        : folders.map((f) => (
            <div key={f.id} className="card" style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontWeight: 700, color: "var(--blue)" }}>📚 {f.name}</span>
              <span className="muted" style={{ fontSize: 12 }}>{f.n_docs} files</span>
              <span style={{ marginLeft: "auto" }}>
                {f.my_status === "granted" ? (
                  <span className="chip">✓ access — import it in a project</span>
                ) : f.my_status === "requested" ? (
                  <span className="chip handoff">access requested</span>
                ) : (
                  <button className="btn" style={{ height: 32, fontSize: 13 }} onClick={async () => { await requestFolderAccess(f.id); load(); }}>Request access</button>
                )}
              </span>
            </div>
          ))}
    </div>
  );
}

function TeamKnowledge() {
  const { user } = useAuth();
  const isManager = user?.role === "manager";
  return (
    <div className="page">
      <div className="page-title">Team Knowledge</div>
      <div className="page-sub">Knowledge shared across the team — general and curated folders.</div>

      <KnowledgePanel
        title={isManager ? "General team knowledge" : "General team knowledge (read-only)"}
        hint={
          isManager
            ? "Files every team member's coach uses in every chat. Only you (the manager) can edit these."
            : "Documents your manager shared with the whole team — used in all your chats automatically."
        }
        canEdit={isManager}
        load={getTeamDocs}
        upload={uploadTeamDocs}
        remove={deleteTeamDoc}
      />

      <FolderSection />
    </div>
  );
}

export default function Page() {
  return (
    <Guard role={["employee", "manager"]}>
      <TeamKnowledge />
    </Guard>
  );
}
