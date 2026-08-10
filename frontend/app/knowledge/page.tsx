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
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [folderId]);
  return (
    <div className="mt-4">
      <div className="card-label">Who can use this folder</div>
      {rows.length === 0 && <div className="muted">No other team members.</div>}
      {rows.map((m) => (
        <div key={m.id} className="flex items-center gap-3 py-2 border-b border-surface-container last:border-0">
          <div className="w-7 h-7 rounded-full bg-primary-fixed flex items-center justify-center text-on-primary-fixed text-label-sm font-bold shrink-0">
            {m.name[0]}
          </div>
          <span className="flex-1 text-body-sm font-medium">{m.name}</span>
          {m.status === "requested" && <span className="chip handoff">requested</span>}
          {m.status === "granted" ? (
            <button className="text-error text-label-sm hover:underline" onClick={async () => { await folderAccessChange(folderId, m.id, "revoke"); load(); }}>Revoke</button>
          ) : (
            <button className="btn" style={{ height: 28, padding: "0 10px" }} onClick={async () => { await folderAccessChange(folderId, m.id, "grant"); load(); }}>Grant</button>
          )}
        </div>
      ))}
    </div>
  );
}

function ManagerFolder({ folder, onChange }: { folder: Folder; onChange: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card mb-4">
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => setOpen((o) => !o)}>
        <span className="material-symbols-outlined text-primary" style={{ fontSize: 20 }}>library_books</span>
        <span className="flex-1 font-semibold text-primary">{folder.name}</span>
        <span className="muted">{folder.n_docs} files · {folder.n_granted} with access</span>
        {!!folder.n_requests && <span className="chip handoff">{folder.n_requests} request{folder.n_requests > 1 ? "s" : ""}</span>}
        <span className="material-symbols-outlined text-on-surface-variant" style={{ fontSize: 20 }}>{open ? "expand_less" : "expand_more"}</span>
        <button
          className="text-error text-label-sm hover:underline"
          onClick={async (e) => { e.stopPropagation(); if (confirm(`Delete folder "${folder.name}"?`)) { await deleteFolder(folder.id); onChange(); } }}
        >
          Delete
        </button>
      </div>
      {open && (
        <div className="mt-4 border-t border-surface-container pt-4">
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
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  return (
    <div className="mt-8">
      <h3 className="text-headline-sm text-primary mb-1">Knowledge folders</h3>
      <p className="muted mb-5">
        {isManager
          ? "Curated knowledge sets you share with specific people. Grant access, and they can import a folder into their projects."
          : "Knowledge sets your manager curates. Request access, then import a folder into one of your projects."}
      </p>

      {isManager && (
        <form onSubmit={async (e) => { e.preventDefault(); if (!name.trim()) return; await createFolder(name); setName(""); load(); }}
          className="flex gap-3 mb-6">
          <input className="input-field flex-1" placeholder="New folder name (e.g. Sustainability Research)" value={name} onChange={(e) => setName(e.target.value)} />
          <button className="btn" style={{ height: 40 }}>Create folder</button>
        </form>
      )}

      {folders.length === 0 && <div className="muted">No knowledge folders yet.</div>}

      {isManager
        ? folders.map((f) => <ManagerFolder key={f.id} folder={f} onChange={load} />)
        : folders.map((f) => (
            <div key={f.id} className="card mb-4 flex items-center gap-3">
              <span className="material-symbols-outlined text-primary" style={{ fontSize: 20 }}>library_books</span>
              <span className="flex-1 font-semibold text-primary">{f.name}</span>
              <span className="muted">{f.n_docs} files</span>
              <span>
                {f.my_status === "granted" ? (
                  <span className="chip">✓ access — import in a project</span>
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
    <div className="app-main">
      <header className="topbar">
        <h2 className="text-headline-md font-semibold text-primary">Team Knowledge</h2>
      </header>
      <div className="page-canvas">
        <p className="page-sub" style={{ marginTop: 0 }}>Knowledge shared across the team — general documents and curated folders.</p>
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
