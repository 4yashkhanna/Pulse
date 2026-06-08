"use client";

import { useEffect, useRef, useState } from "react";
import Guard from "@/components/Guard";
import KnowledgePanel from "@/components/KnowledgePanel";
import MessageContent from "@/components/MessageContent";
import ArtifactPanel, { Artifact, artifactTitle } from "@/components/ArtifactPanel";
import {
  ChatReply,
  Conversation,
  Project,
  ProjectFolders,
  createProject,
  deleteConversation,
  deleteProject,
  deleteProjectDoc,
  getConversation,
  getProjectFolders,
  importFolder,
  listConversations,
  listProjectDocs,
  listProjects,
  sendMessage,
  unimportFolder,
  uploadProjectDocs,
} from "@/lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  handoff?: boolean;
}

function Chat() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastReply, setLastReply] = useState<ChatReply | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [newProj, setNewProj] = useState("");
  const [showManage, setShowManage] = useState(false);
  const [pf, setPf] = useState<ProjectFolders | null>(null);
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadProjects = () => listProjects().then(setProjects);
  const loadConvos = () => listConversations().then(setConversations);
  useEffect(() => {
    listProjects().then((ps) => {
      setProjects(ps);
      if (ps.length && !activeProject) setActiveProject(ps[0].id);
    });
    loadConvos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [messages, loading]);

  const project = projects.find((p) => p.id === activeProject) || null;
  const projectConvos = conversations.filter((c) => c.project_id === activeProject);

  const loadFolders = () => {
    if (activeProject) getProjectFolders(activeProject).then(setPf).catch(() => setPf(null));
  };
  useEffect(() => {
    setShowManage(false);
    newChat();
    if (activeProject) loadFolders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProject]);

  function newChat() {
    setActiveId(null);
    setMessages([]);
    setLastReply(null);
    setInput("");
    setFiles([]);
    setArtifact(null);
  }

  // Pull the first ```html / ```artifact block out of a reply, if any.
  function extractArtifact(reply: string): Artifact | null {
    const m = /```(?:html|artifact)\s*\n?([\s\S]*?)```/i.exec(reply);
    if (!m) return null;
    const html = m[1].trim();
    return html ? { html, title: artifactTitle(html) } : null;
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
    const p = await createProject(name);
    setNewProj("");
    await loadProjects();
    setActiveProject(p.id);
  }

  async function submit() {
    const text = input.trim();
    if ((!text && files.length === 0) || loading || !activeProject) return;
    const attached = files;
    const note = attached.length ? ` 📎 ${attached.map((f) => f.name).join(", ")}` : "";
    setInput("");
    setFiles([]);
    setMessages((m) => [...m, { role: "user", content: (text || "(file)") + note }]);
    setLoading(true);
    try {
      const r = await sendMessage(text, activeId, attached, activeId ? undefined : activeProject);
      setActiveId(r.conversation_id);
      setLastReply(r);
      setMessages((m) => [...m, { role: "assistant", content: r.reply, handoff: r.tag?.handoff }]);
      const art = extractArtifact(r.reply);
      if (art) setArtifact(art); // auto-open the visualization, like Claude
      loadConvos();
    } catch (e: any) {
      const msg = typeof e?.message === "string" && e.message.length < 200 ? e.message : "Could not reach the coach.";
      setMessages((m) => [...m, { role: "assistant", content: `⚠️ ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-shell">
      {/* Sidebar: projects → chats within the open project */}
      <aside className="chat-side" style={{ width: 270 }}>
        <div className="card" style={{ padding: 14 }}>
          <div className="card-label">Projects</div>
          {projects.map((p) => (
            <div
              key={p.id}
              onClick={() => setActiveProject(p.id)}
              className="knowledge-item"
              style={{ cursor: "pointer", marginBottom: 4, background: activeProject === p.id ? "var(--blue-pale)" : "var(--surface)", display: "flex", gap: 6 }}
            >
              <span>📁</span>
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: activeProject === p.id ? 700 : 500 }}>{p.name}</span>
              <span className="muted" style={{ fontSize: 10 }}>{p.n_docs}📄</span>
            </div>
          ))}
          {projects.length === 0 && <div className="muted" style={{ fontSize: 12 }}>Create a project to start.</div>}
          <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
            <input className="select" style={{ flex: 1, fontSize: 12 }} placeholder="New project…" value={newProj}
              onChange={(e) => setNewProj(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addProject()} />
            <button className="btn" style={{ height: 36, padding: "0 12px" }} onClick={addProject}>+</button>
          </div>
        </div>

        {project && (
          <>
            <div style={{ display: "flex", gap: 6 }}>
              <button className="btn" style={{ height: 36, flex: 1 }} onClick={newChat}>+ New chat</button>
              <button
                className="nav-link"
                style={{ background: "var(--white)", border: "0.5px solid var(--border-mid)", borderRadius: 8, padding: "0 12px", cursor: "pointer", fontSize: 12, fontWeight: 600, color: showManage ? "var(--blue)" : "var(--ink-3)" }}
                onClick={() => setShowManage((s) => !s)}
              >
                Manage
              </button>
            </div>
            <div className="card-label" style={{ marginTop: 4 }}>Chats in {project.name}</div>
            <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
              {projectConvos.map((c) => (
                <div key={c.id} onClick={() => openConversation(c.id)} className="knowledge-item"
                  style={{ cursor: "pointer", marginBottom: 0, background: c.id === activeId ? "var(--blue-pale)" : "var(--surface)", display: "flex", gap: 6 }}>
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title}</span>
                  <span onClick={async (e) => { e.stopPropagation(); await deleteConversation(c.id); if (c.id === activeId) newChat(); loadConvos(); }}
                    style={{ color: "var(--ink-3)", fontSize: 14 }}>×</span>
                </div>
              ))}
              {projectConvos.length === 0 && <div className="muted" style={{ fontSize: 12 }}>No chats yet — start one.</div>}
            </div>
          </>
        )}
      </aside>

      {/* Main */}
      <div className="chat-main">
        {!project ? (
          <div className="chat-log" style={{ alignItems: "center", justifyContent: "center" }}>
            <div className="muted" style={{ textAlign: "center" }}>Create or select a project to start chatting.</div>
          </div>
        ) : (
          <>
            <div style={{ padding: "10px 16px", borderBottom: "0.5px solid var(--border)", background: "var(--blue-pale)", display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontWeight: 700, color: "var(--blue)", fontSize: 13 }}>📁 {project.name}</span>
              <span className="muted" style={{ fontSize: 11 }}>the coach uses this project&apos;s files & imported folders</span>
              <span style={{ marginLeft: "auto", color: "var(--coral)", fontSize: 11, cursor: "pointer" }}
                onClick={async () => { if (confirm(`Delete project "${project.name}"?`)) { await deleteProject(project.id); const ps = await listProjects(); setProjects(ps); setActiveProject(ps[0]?.id ?? null); } }}>
                Delete
              </span>
            </div>
            <div className="chat-log" ref={logRef}>
              {messages.length === 0 && <div className="muted" style={{ margin: "auto", textAlign: "center" }}>Chatting in “{project.name}”. Ask Pulse anything.</div>}
              {messages.map((m, i) => (
                <div key={i} className={`bubble ${m.role === "user" ? "user" : "coach"} ${m.handoff ? "handoff" : ""}`}>
                  {m.handoff && <div style={{ marginBottom: 6 }}><span className="chip handoff">Human handoff</span></div>}
                  {m.role === "assistant" ? (
                    <MessageContent content={m.content} onOpenArtifact={(html, title) => setArtifact({ html, title })} />
                  ) : (
                    m.content
                  )}
                </div>
              ))}
              {loading && <div className="bubble coach muted">Coaching…</div>}
            </div>
            {files.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "0 16px 8px" }}>
                {files.map((f, i) => (
                  <span key={i} className="chip" style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>📎 {f.name}
                    <span style={{ cursor: "pointer" }} onClick={() => setFiles((fs) => fs.filter((_, j) => j !== i))}>×</span></span>
                ))}
              </div>
            )}
            <div className="chat-input-row">
              <input ref={fileRef} type="file" hidden multiple accept="image/png,image/jpeg,image/webp,image/gif,application/pdf"
                onChange={(e) => { setFiles((fs) => [...fs, ...Array.from(e.target.files || [])]); if (fileRef.current) fileRef.current.value = ""; }} />
              <button className="btn" style={{ background: "var(--surface)", color: "var(--blue)", border: "0.5px solid var(--border-mid)", padding: "0 14px" }} onClick={() => fileRef.current?.click()} title="Attach image or PDF">📎</button>
              <textarea className="chat-input" rows={1} placeholder="Message Pulse…" value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} />
              <button className="btn" onClick={submit} disabled={loading || (!input.trim() && files.length === 0)}>Send</button>
            </div>
          </>
        )}
      </div>

      {/* Right rail */}
      <aside className="chat-side" style={{ width: 270 }}>
        {project && showManage && (
          <>
            <KnowledgePanel
              title="Project files"
              hint="Files only this project's chats use."
              load={() => listProjectDocs(project.id)}
              upload={(fs) => uploadProjectDocs(project.id, fs).then((r) => { loadProjects(); return r; })}
              remove={(id) => deleteProjectDoc(project.id, id).then((r) => { loadProjects(); return r; })}
            />
            <div className="card">
              <div className="card-label">Imported team folders</div>
              {pf?.imported.length === 0 && <div className="muted" style={{ fontSize: 12 }}>None imported.</div>}
              {pf?.imported.map((f) => (
                <div key={f.id} style={{ display: "flex", gap: 8, padding: "6px 0", borderBottom: "0.5px solid var(--border)", alignItems: "center" }}>
                  <span style={{ flex: 1, fontSize: 13, fontWeight: 600 }}>📚 {f.name}</span>
                  <span className="muted" style={{ fontSize: 11 }}>{f.n_docs}📄</span>
                  <span style={{ color: "var(--coral)", cursor: "pointer", fontSize: 12 }}
                    onClick={async () => { await unimportFolder(project.id, f.id); loadFolders(); }}>remove</span>
                </div>
              ))}
              {pf && pf.available.length > 0 && (
                <>
                  <div className="card-label" style={{ marginTop: 12 }}>Available to import</div>
                  {pf.available.map((f) => (
                    <div key={f.id} style={{ display: "flex", gap: 8, padding: "6px 0", alignItems: "center" }}>
                      <span style={{ flex: 1, fontSize: 13 }}>📚 {f.name}</span>
                      <button className="btn" style={{ height: 28, padding: "0 10px", fontSize: 12 }}
                        onClick={async () => { await importFolder(project.id, f.id); loadFolders(); }}>Import</button>
                    </div>
                  ))}
                </>
              )}
              <div className="muted" style={{ fontSize: 11, marginTop: 8 }}>
                Need a folder you don&apos;t have? Request access on the <strong>Team Knowledge</strong> page.
              </div>
            </div>
          </>
        )}
        {!showManage && lastReply?.tag && (
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
                    <span title={s.text} style={{ fontSize: 11, fontWeight: 600, padding: "2px 7px", borderRadius: 5, background: s.polarity > 0 ? "var(--teal-pale)" : "var(--coral-pale)", color: s.polarity > 0 ? "#0f6e56" : "var(--coral)" }}>
                      {s.polarity > 0 ? "+" : "−"} {s.pillar}
                    </span>
                    {s.evidence && <div className="muted" style={{ fontSize: 11.5, marginTop: 3, fontStyle: "italic" }}>“{s.evidence}” — {s.text}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        {!showManage && (
          <div className="card">
            <div className="card-label">Knowledge retrieved</div>
            {!lastReply?.retrieved?.length && <div className="muted">Knowledge used to ground the reply appears here.</div>}
            {(() => {
              // Collapse multiple chunks from the same document into one row (best match + count).
              const byDoc = new Map<string, { source: string; scope?: string; similarity: number; n: number }>();
              for (const c of lastReply?.retrieved || []) {
                const key = `${c.source}|${c.scope}`;
                const prev = byDoc.get(key);
                if (!prev) byDoc.set(key, { source: c.source || "knowledge", scope: c.scope, similarity: c.similarity, n: 1 });
                else {
                  prev.n += 1;
                  prev.similarity = Math.max(prev.similarity, c.similarity);
                }
              }
              return Array.from(byDoc.values()).map((c, i) => (
                <div className="knowledge-item" key={i}>
                  <span className="kf">{c.source}</span>
                  <div className="ks">
                    <span style={{ textTransform: "uppercase", fontWeight: 700, fontSize: 9, letterSpacing: "0.05em", color: c.scope === "user" ? "var(--purple)" : c.scope === "team" ? "var(--teal)" : "var(--blue-mid)" }}>
                      {c.scope === "user" ? "project" : c.scope || "org"}
                    </span>{" "}· match {(c.similarity * 100).toFixed(0)}%
                    {c.n > 1 && <span className="muted"> · {c.n} passages</span>}
                  </div>
                </div>
              ));
            })()}
          </div>
        )}
      </aside>

      <ArtifactPanel artifact={artifact} onClose={() => setArtifact(null)} />
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
