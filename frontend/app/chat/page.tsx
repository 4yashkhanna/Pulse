"use client";

import { useEffect, useRef, useState } from "react";
import Guard from "@/components/Guard";
import KnowledgePanel from "@/components/KnowledgePanel";
import { useAuth } from "@/lib/auth";
import {
  ChatReply,
  Conversation,
  Project,
  createProject,
  deleteConversation,
  deleteProject,
  deleteProjectDoc,
  getConversation,
  listConversations,
  listProjectDocs,
  listProjects,
  sendMessage,
  uploadProjectDocs,
} from "@/lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  handoff?: boolean;
}

function Chat() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<string | null>(null); // null = General
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [lastReply, setLastReply] = useState<ChatReply | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [newProj, setNewProj] = useState("");
  const [showFiles, setShowFiles] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadConvos = (q?: string) => listConversations(q).then(setConversations);
  const loadProjects = () => listProjects().then(setProjects);
  useEffect(() => {
    loadConvos();
    loadProjects();
  }, []);
  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [messages, loading]);
  useEffect(() => {
    const t = setTimeout(() => loadConvos(search || undefined), 250);
    return () => clearTimeout(t);
  }, [search]);

  const project = projects.find((p) => p.id === activeProject) || null;
  const visibleConvos = conversations.filter((c) => (c.project_id || null) === activeProject);

  function selectProject(id: string | null) {
    setActiveProject(id);
    setShowFiles(false);
    newChat();
  }

  function newChat() {
    setActiveId(null);
    setMessages([]);
    setLastReply(null);
    setInput("");
    setFiles([]);
  }

  async function openConversation(id: string) {
    setActiveId(id);
    setLastReply(null);
    const c = await getConversation(id);
    setMessages(c.messages as Msg[]);
  }

  async function addProject() {
    const name = newProj.trim();
    if (!name) return;
    const p = await createProject(name, "user");
    setNewProj("");
    await loadProjects();
    selectProject(p.id);
  }

  async function addTeamProject() {
    const name = prompt("Name this team project:");
    if (!name) return;
    const p = await createProject(name, "team");
    await loadProjects();
    selectProject(p.id);
  }

  async function submit() {
    const text = input.trim();
    if ((!text && files.length === 0) || loading) return;
    const attached = files;
    const note = attached.length ? ` 📎 ${attached.map((f) => f.name).join(", ")}` : "";
    setInput("");
    setFiles([]);
    setMessages((m) => [...m, { role: "user", content: (text || "(file)") + note }]);
    setLoading(true);
    try {
      // project only matters when starting a NEW conversation
      const r = await sendMessage(text, activeId, attached, activeId ? undefined : activeProject);
      setActiveId(r.conversation_id);
      setLastReply(r);
      setMessages((m) => [...m, { role: "assistant", content: r.reply, handoff: r.tag?.handoff }]);
      loadConvos(search || undefined);
    } catch (e: any) {
      const msg =
        typeof e?.message === "string" && e.message.length < 200
          ? e.message
          : "Could not reach the coach. Is the backend running?";
      setMessages((m) => [...m, { role: "assistant", content: `⚠️ ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-shell">
      {/* Sidebar: projects + conversations */}
      <aside className="chat-side" style={{ width: 270 }}>
        <div className="card" style={{ padding: 14 }}>
          <div className="card-label">Projects</div>
          <div
            onClick={() => selectProject(null)}
            className="knowledge-item"
            style={{ cursor: "pointer", marginBottom: 4, background: activeProject === null ? "var(--blue-pale)" : "var(--surface)" }}
          >
            💬 General chat
          </div>
          {projects.map((p) => (
            <div
              key={p.id}
              onClick={() => selectProject(p.id)}
              className="knowledge-item"
              style={{ cursor: "pointer", marginBottom: 4, background: activeProject === p.id ? "var(--blue-pale)" : "var(--surface)", display: "flex", gap: 6 }}
            >
              <span>{p.kind === "team" ? "👥" : "📁"}</span>
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.name}</span>
              <span className="muted" style={{ fontSize: 10 }}>{p.n_docs}</span>
            </div>
          ))}
          <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
            <input
              className="select"
              style={{ flex: 1, fontSize: 12 }}
              placeholder="New project…"
              value={newProj}
              onChange={(e) => setNewProj(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addProject()}
            />
            <button className="btn" style={{ height: 36, padding: "0 12px" }} onClick={addProject}>+</button>
          </div>
          {user?.role === "manager" && (
            <button
              onClick={addTeamProject}
              className="nav-link"
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--teal)", fontSize: 12, marginTop: 6, padding: 0 }}
            >
              + New team project
            </button>
          )}
        </div>

        <button className="btn" style={{ height: 38 }} onClick={newChat}>
          + New chat {project ? `in ${project.name}` : ""}
        </button>
        {project && (
          <button
            className="nav-link"
            style={{ background: "var(--white)", border: "0.5px solid var(--border-mid)", borderRadius: 8, padding: "7px", cursor: "pointer", fontSize: 12, fontWeight: 600, color: "var(--blue)" }}
            onClick={() => setShowFiles((s) => !s)}
          >
            {showFiles ? "Hide" : "Manage"} project files ({project.n_docs})
          </button>
        )}
        <input className="select" placeholder="Search chats…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
          {visibleConvos.map((c) => (
            <div
              key={c.id}
              onClick={() => openConversation(c.id)}
              className="knowledge-item"
              style={{ cursor: "pointer", marginBottom: 0, background: c.id === activeId ? "var(--blue-pale)" : "var(--surface)", display: "flex", gap: 6 }}
            >
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title}</span>
              <span
                onClick={async (e) => {
                  e.stopPropagation();
                  await deleteConversation(c.id);
                  if (c.id === activeId) newChat();
                  loadConvos(search || undefined);
                }}
                style={{ color: "var(--ink-3)", fontSize: 14 }}
              >
                ×
              </span>
            </div>
          ))}
          {visibleConvos.length === 0 && <div className="muted" style={{ fontSize: 12 }}>No chats here yet.</div>}
        </div>
      </aside>

      {/* Main chat */}
      <div className="chat-main">
        {project && (
          <div style={{ padding: "10px 16px", borderBottom: "0.5px solid var(--border)", background: "var(--blue-pale)", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontWeight: 700, color: "var(--blue)", fontSize: 13 }}>
              {project.kind === "team" ? "👥" : "📁"} {project.name}
            </span>
            <span className="muted" style={{ fontSize: 11 }}>
              the coach uses this project&apos;s files{project.kind === "team" ? " (team project)" : ""}
            </span>
            {project.can_edit && (
              <span
                style={{ marginLeft: "auto", color: "var(--coral)", fontSize: 11, cursor: "pointer" }}
                onClick={async () => {
                  if (confirm(`Delete project "${project.name}"?`)) {
                    await deleteProject(project.id);
                    await loadProjects();
                    selectProject(null);
                  }
                }}
              >
                Delete project
              </span>
            )}
          </div>
        )}
        <div className="chat-log" ref={logRef}>
          {messages.length === 0 && (
            <div className="muted" style={{ margin: "auto", textAlign: "center" }}>
              {project ? `Chatting in “${project.name}”. ` : ""}Ask Pulse about a design challenge.
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`bubble ${m.role === "user" ? "user" : "coach"} ${m.handoff ? "handoff" : ""}`}>
              {m.handoff && (
                <div style={{ marginBottom: 6 }}>
                  <span className="chip handoff">Human handoff</span>
                </div>
              )}
              {m.content}
            </div>
          ))}
          {loading && <div className="bubble coach muted">Coaching…</div>}
        </div>
        {files.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "0 16px 8px" }}>
            {files.map((f, i) => (
              <span key={i} className="chip" style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                📎 {f.name}
                <span style={{ cursor: "pointer" }} onClick={() => setFiles((fs) => fs.filter((_, j) => j !== i))}>×</span>
              </span>
            ))}
          </div>
        )}
        <div className="chat-input-row">
          <input
            ref={fileRef}
            type="file"
            hidden
            multiple
            accept="image/png,image/jpeg,image/webp,image/gif,application/pdf"
            onChange={(e) => {
              setFiles((fs) => [...fs, ...Array.from(e.target.files || [])]);
              if (fileRef.current) fileRef.current.value = "";
            }}
          />
          <button
            className="btn"
            style={{ background: "var(--surface)", color: "var(--blue)", border: "0.5px solid var(--border-mid)", padding: "0 14px" }}
            onClick={() => fileRef.current?.click()}
            title="Attach image or PDF to this message"
          >
            📎
          </button>
          <textarea
            className="chat-input"
            rows={1}
            placeholder="Message Pulse…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <button className="btn" onClick={submit} disabled={loading || (!input.trim() && files.length === 0)}>
            Send
          </button>
        </div>
      </div>

      {/* Right rail: project files (when managing) + measurement + retrieved */}
      <aside className="chat-side" style={{ width: 260 }}>
        {project && showFiles && (
          <KnowledgePanel
            title={`${project.name} — files`}
            hint={
              project.can_edit
                ? "Documents the coach uses whenever you chat in this project."
                : "Files added by your manager for this team project."
            }
            canEdit={project.can_edit}
            load={() => listProjectDocs(project.id)}
            upload={(fs) => uploadProjectDocs(project.id, fs).then((r) => { loadProjects(); return r; })}
            remove={(id) => deleteProjectDoc(project.id, id).then((r) => { loadProjects(); return r; })}
          />
        )}
        {lastReply?.tag && (
          <div className="card">
            <div className="card-label">How this turn was measured</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              <span className="chip phase">{lastReply.tag.phase}</span>
              <span className="chip">{lastReply.tag.usage_type}</span>
            </div>
            {lastReply.tag.fired_signals && lastReply.tag.fired_signals.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div className="muted" style={{ fontSize: 11, marginBottom: 6 }}>Signals observed</div>
                {lastReply.tag.fired_signals.map((s) => (
                  <div key={s.id} style={{ marginBottom: 8 }}>
                    <span
                      title={s.text}
                      style={{ fontSize: 11, fontWeight: 600, padding: "2px 7px", borderRadius: 5, background: s.polarity > 0 ? "var(--teal-pale)" : "var(--coral-pale)", color: s.polarity > 0 ? "#0f6e56" : "var(--coral)" }}
                    >
                      {s.polarity > 0 ? "+" : "−"} {s.pillar}
                    </span>
                    {s.evidence && (
                      <div className="muted" style={{ fontSize: 11.5, marginTop: 3, fontStyle: "italic" }}>
                        “{s.evidence}” — {s.text}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        <div className="card">
          <div className="card-label">Knowledge retrieved</div>
          {!lastReply?.retrieved?.length && (
            <div className="muted">Knowledge used to ground the reply appears here.</div>
          )}
          {lastReply?.retrieved?.map((c, i) => (
            <div className="knowledge-item" key={i}>
              <span className="kf">{c.source || "knowledge"}</span>
              <div className="ks">
                <span
                  style={{ textTransform: "uppercase", fontWeight: 700, fontSize: 9, letterSpacing: "0.05em", color: c.scope === "user" ? "var(--purple)" : c.scope === "team" ? "var(--teal)" : "var(--blue-mid)" }}
                >
                  {c.scope === "user" ? "project" : c.scope || "org"}
                </span>{" "}
                · match {(c.similarity * 100).toFixed(0)}%
              </div>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}

export default function Page() {
  return (
    <Guard role={["employee", "manager"]}>
      <Chat />
    </Guard>
  );
}
