"use client";

import { useEffect, useRef, useState } from "react";
import Guard from "@/components/Guard";
import MessageContent from "@/components/MessageContent";
import ArtifactPanel, { Artifact, artifactTitle } from "@/components/ArtifactPanel";
import KnowledgePanel from "@/components/KnowledgePanel";
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
  mySkills,
  sendMessageStream,
  unimportFolder,
  uploadProjectDocs,
} from "@/lib/api";

interface SkillInfo {
  id?: string;
  name: string;
  command: string;
  description?: string;
}

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
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [activeSkill, setActiveSkill] = useState<SkillInfo | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Slash autocomplete: only when starting a NEW chat with "/"
  const slashQuery = !activeId && input.startsWith("/") ? input.slice(1).split(/\s/)[0].toLowerCase() : null;
  const slashMatches =
    slashQuery !== null && !input.includes(" ")
      ? skills.filter((s) => s.command.startsWith(slashQuery))
      : [];

  const loadProjects = () => listProjects().then(setProjects);
  const loadConvos  = () => listConversations().then(setConversations);

  useEffect(() => {
    listProjects().then((ps) => {
      setProjects(ps);
      if (ps.length && !activeProject) setActiveProject(ps[0].id);
    });
    loadConvos();
    mySkills().then(setSkills).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
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
    setActiveSkill(null);
  }

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
    setActiveSkill(c.skill || null);
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
    if (textareaRef.current) textareaRef.current.style.height = "";
    setMessages((m) => [...m, { role: "user", content: (text || "(file)") + note }]);
    setLoading(true);
    // Stream the reply: tokens render as they arrive, the tag (fired signals)
    // lands as a final event after the reply is complete.
    let acc = "";
    let started = false;
    let convId = activeId;
    let convTitle = "";
    let retrieved: ChatReply["retrieved"] = [];
    try {
      await sendMessageStream(text, activeId, attached, activeId ? undefined : activeProject, {
        onMeta: (meta) => {
          convId = meta.conversation_id;
          convTitle = meta.title;
          retrieved = meta.retrieved;
          setActiveId(meta.conversation_id);
          if (meta.skill) setActiveSkill(meta.skill);
        },
        onDelta: (t) => {
          acc += t;
          if (!started) {
            started = true;
            setLoading(false);
            setMessages((m) => [...m, { role: "assistant", content: acc }]);
          } else {
            setMessages((m) => {
              const copy = m.slice();
              copy[copy.length - 1] = { ...copy[copy.length - 1], content: acc };
              return copy;
            });
          }
        },
        onTag: (tag) => {
          setLastReply({ reply: acc, conversation_id: convId!, title: convTitle, retrieved, tag });
          if (tag?.handoff) {
            setMessages((m) => {
              const copy = m.slice();
              copy[copy.length - 1] = { ...copy[copy.length - 1], handoff: true };
              return copy;
            });
          }
        },
      });
      setLastReply((prev) =>
        prev && prev.conversation_id === convId && prev.reply === acc
          ? prev
          : { reply: acc, conversation_id: convId!, title: convTitle, retrieved, tag: prev?.tag ?? null },
      );
      const art = extractArtifact(acc);
      if (art) setArtifact(art);
      loadConvos();
    } catch (e: unknown) {
      const msg = e instanceof Error && e.message.length < 200 ? e.message : "Could not reach the coach.";
      setMessages((m) => {
        // Replace a half-streamed bubble with the error, or append one.
        const copy = m.slice();
        const errLine = `⚠️ ${msg}`;
        if (started && copy.length && copy[copy.length - 1].role === "assistant") {
          copy[copy.length - 1] = { ...copy[copy.length - 1], content: acc ? `${acc}\n\n${errLine}` : errLine };
          return copy;
        }
        return [...copy, { role: "assistant", content: errLine }];
      });
    } finally {
      setLoading(false);
    }
  }

  const activeConvo = conversations.find((c) => c.id === activeId);

  return (
    <div className="app-main">
      {/* Top bar */}
      <header className="topbar">
        <div className="flex items-center gap-3">
          <h2 className="text-headline-md font-semibold text-primary">
            {activeConvo ? activeConvo.title : project ? `${project.name}` : "AI Coaching Portal"}
          </h2>
          {activeConvo && (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-surface-container-low border border-surface-container-high">
              <span className="w-2 h-2 rounded-full bg-pulse-teal-vibrant animate-pulse" />
              <span className="text-label-sm text-on-surface-variant">Active Session</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowManage((s) => !s)}
            className={`text-label-sm px-3 py-1.5 rounded-lg border transition-colors ${showManage ? "border-primary-container bg-primary-fixed/30 text-primary" : "border-outline-variant text-on-surface-variant hover:bg-surface-container"}`}
          >
            <span className="flex items-center gap-1">
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>folder_managed</span>
              Manage
            </span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar: projects + threads */}
        <aside className="w-[260px] shrink-0 border-r border-surface-container-high bg-surface-container-lowest flex flex-col overflow-hidden">
          {/* Projects */}
          <div className="p-4 border-b border-surface-container-high">
            <div className="card-label">Projects</div>
            <div className="flex flex-col gap-1">
              {projects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setActiveProject(p.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-body-sm text-left w-full transition-colors ${activeProject === p.id ? "bg-primary-fixed/40 text-primary font-semibold" : "text-on-surface hover:bg-surface-container"}`}
                >
                  <span className="material-symbols-outlined text-on-surface-variant" style={{ fontSize: 16 }}>folder</span>
                  <span className="flex-1 truncate">{p.name}</span>
                  <span className="text-label-caps text-on-surface-variant">{p.n_docs}</span>
                </button>
              ))}
            </div>
            <div className="flex gap-2 mt-3">
              <input
                className="input-field flex-1 text-body-sm"
                style={{ padding: "6px 10px" }}
                placeholder="New project…"
                value={newProj}
                onChange={(e) => setNewProj(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addProject()}
              />
              <button className="btn" style={{ height: 34, padding: "0 12px", fontSize: 18 }} onClick={addProject}>+</button>
            </div>
          </div>

          {/* Threads */}
          {project && (
            <div className="flex-1 overflow-y-auto p-3">
              <div className="flex items-center justify-between mb-2 px-1">
                <div className="card-label mb-0">Active Threads</div>
                <button onClick={newChat} className="text-label-sm text-primary hover:underline">+ New</button>
              </div>
              <div className="flex flex-col gap-1">
                {projectConvos.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => openConversation(c.id)}
                    className={`sidebar-thread ${c.id === activeId ? "active" : ""}`}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 16, marginTop: 2 }}>chat_bubble</span>
                    <span className="flex-1 truncate">{c.title}</span>
                    <span
                      onClick={async (e) => {
                        e.stopPropagation();
                        await deleteConversation(c.id);
                        if (c.id === activeId) newChat();
                        loadConvos();
                      }}
                      className="opacity-0 group-hover:opacity-100 text-on-surface-variant hover:text-error text-sm cursor-pointer"
                      style={{ fontSize: 14 }}
                    >
                      ×
                    </span>
                  </div>
                ))}
                {projectConvos.length === 0 && (
                  <div className="muted text-center py-4">No chats yet</div>
                )}
              </div>
            </div>
          )}
        </aside>

        {/* Main chat area */}
        <div className="flex-1 flex flex-col overflow-hidden relative bg-surface">
          {!project ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <span className="material-symbols-outlined text-on-surface-variant mb-3" style={{ fontSize: 48 }}>folder_open</span>
                <div className="muted">Create or select a project to start chatting.</div>
              </div>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div ref={scrollRef} className="chat-scroll relative">
                {messages.length === 0 && (
                  <div className="m-auto text-center">
                    <span className="material-symbols-outlined text-on-surface-variant mb-2" style={{ fontSize: 40 }}>robot_2</span>
                    <div className="muted">Ask Pulse anything about {project.name}.</div>
                  </div>
                )}

                {messages.map((m, i) => (
                  <div key={i} className={m.role === "user" ? "bubble-user" : "bubble-coach"}>
                    <div className="bubble-meta">
                      {m.role === "user" ? (
                        <>
                          <div className="bubble-avatar bg-primary-container text-on-primary ml-auto">ME</div>
                          <span className="text-label-sm text-on-surface-variant">You</span>
                        </>
                      ) : (
                        <>
                          <div className="bubble-avatar bg-secondary-container text-on-secondary-container">
                            <span className="material-symbols-outlined icon-fill" style={{ fontSize: 14 }}>robot_2</span>
                          </div>
                          <span className="text-label-sm font-semibold text-primary">AI Coach</span>
                        </>
                      )}
                    </div>
                    <div className={`bubble-body ${m.handoff ? "handoff" : ""}`}>
                      {m.handoff && (
                        <div className="mb-3">
                          <span className="inline-flex items-center gap-1.5 bg-error-container/30 text-error border border-error/20 px-3 py-1.5 rounded-full text-label-sm font-semibold">
                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>record_voice_over</span>
                            Human Handoff Recommended
                          </span>
                        </div>
                      )}
                      {m.role === "assistant" ? (
                        <MessageContent content={m.content} onOpenArtifact={(html, title) => setArtifact({ html, title })} />
                      ) : (
                        m.content
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="bubble-coach">
                    <div className="bubble-meta">
                      <div className="bubble-avatar bg-secondary-container text-on-secondary-container">
                        <span className="material-symbols-outlined icon-fill" style={{ fontSize: 14 }}>robot_2</span>
                      </div>
                      <span className="text-label-sm font-semibold text-primary">AI Coach</span>
                    </div>
                    <div className="bubble-body">
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Attached files preview */}
              {files.length > 0 && (
                <div className="flex flex-wrap gap-2 px-8 pb-2">
                  {files.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 bg-surface-container-low border border-surface-container-high px-3 py-1.5 rounded-lg text-label-sm">
                      <span className="material-symbols-outlined text-on-surface-variant" style={{ fontSize: 16 }}>picture_as_pdf</span>
                      <span>{f.name}</span>
                      <button onClick={() => setFiles((fs) => fs.filter((_, j) => j !== i))} className="text-on-surface-variant hover:text-error ml-1">×</button>
                    </div>
                  ))}
                </div>
              )}

              {/* Input */}
              <div className="chat-input-wrap">
                <div className="max-w-4xl mx-auto relative">
                  {/* Active skill chip */}
                  {activeSkill && (
                    <div className="flex justify-center mb-2">
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-pulse-teal-vibrant/10 border border-pulse-teal-vibrant/40 text-label-sm text-primary font-medium">
                        <span className="material-symbols-outlined text-pulse-teal-vibrant" style={{ fontSize: 16 }}>bolt</span>
                        {activeSkill.name} active — the coach follows this process for the whole chat
                      </span>
                    </div>
                  )}
                  {/* Slash-command autocomplete */}
                  {slashMatches.length > 0 && (
                    <div className="absolute bottom-full left-0 right-0 mb-2 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-md overflow-hidden z-20">
                      {slashMatches.map((s) => (
                        <button
                          key={s.command}
                          className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-surface-container-low transition-colors border-b border-outline-variant/40 last:border-0"
                          onClick={() => {
                            setInput(`/${s.command} `);
                            textareaRef.current?.focus();
                          }}
                        >
                          <span className="material-symbols-outlined text-pulse-teal-vibrant mt-0.5" style={{ fontSize: 18 }}>bolt</span>
                          <span>
                            <span className="text-body-sm font-bold text-primary">/{s.command}</span>
                            <span className="ml-2 text-body-sm text-on-surface">{s.name}</span>
                            {s.description && <span className="block text-on-surface-variant" style={{ fontSize: 12 }}>{s.description}</span>}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="chat-input-box">
                    <input ref={fileRef} type="file" hidden multiple accept="image/png,image/jpeg,image/webp,image/gif,application/pdf"
                      onChange={(e) => { setFiles((fs) => [...fs, ...Array.from(e.target.files || [])]); if (fileRef.current) fileRef.current.value = ""; }} />
                    <button
                      className="p-2 text-outline hover:text-primary hover:bg-surface-container rounded-lg transition-colors shrink-0"
                      onClick={() => fileRef.current?.click()}
                      title="Attach file"
                    >
                      <span className="material-symbols-outlined">attach_file</span>
                    </button>
                    <textarea
                      ref={textareaRef}
                      className="chat-input"
                      rows={1}
                      placeholder={skills.length && !activeId ? "Ask the AI Coach… (type / for skills)" : "Ask the AI Coach…"}
                      value={input}
                      onChange={(e) => {
                        setInput(e.target.value);
                        e.target.style.height = "";
                        e.target.style.height = e.target.scrollHeight + "px";
                      }}
                      onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
                    />
                    <div className="flex items-center gap-1 shrink-0 p-1">
                      <button
                        className="chat-send-btn"
                        onClick={submit}
                        disabled={loading || (!input.trim() && files.length === 0)}
                      >
                        <span className="material-symbols-outlined" style={{ fontSize: 20 }}>send</span>
                      </button>
                    </div>
                  </div>
                  <p className="text-center mt-2 text-label-sm text-outline">
                    AI responses may contain inaccuracies — verify critical decisions.
                  </p>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right rail: manage panel or knowledge signals */}
        <aside className="w-[280px] shrink-0 border-l border-surface-container-high bg-surface-container-lowest overflow-y-auto p-4 flex flex-col gap-4">
          {project && showManage ? (
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
                {pf?.imported.length === 0 && <div className="muted">None imported.</div>}
                {pf?.imported.map((f) => (
                  <div key={f.id} className="flex items-center gap-2 py-2 border-b border-surface-container text-body-sm">
                    <span className="material-symbols-outlined text-on-surface-variant" style={{ fontSize: 16 }}>library_books</span>
                    <span className="flex-1 font-semibold truncate">{f.name}</span>
                    <span className="text-label-caps text-on-surface-variant">{f.n_docs}</span>
                    <button onClick={async () => { await unimportFolder(project.id, f.id); loadFolders(); }} className="text-error text-label-sm hover:underline ml-1">remove</button>
                  </div>
                ))}
                {pf && pf.available.length > 0 && (
                  <>
                    <div className="card-label mt-3">Available to import</div>
                    {pf.available.map((f) => (
                      <div key={f.id} className="flex items-center gap-2 py-1 text-body-sm">
                        <span className="flex-1 truncate">{f.name}</span>
                        <button className="btn" style={{ height: 28, padding: "0 10px", fontSize: 12 }} onClick={async () => { await importFolder(project.id, f.id); loadFolders(); }}>Import</button>
                      </div>
                    ))}
                  </>
                )}
              </div>
              <div className="card">
                <div className="card-label">Danger zone</div>
                <button
                  className="btn-outline text-error border-error/30 hover:bg-error-container/20 text-label-sm w-full"
                  style={{ height: 36 }}
                  onClick={async () => {
                    if (confirm(`Delete project "${project.name}"?`)) {
                      await deleteProject(project.id);
                      const ps = await listProjects();
                      setProjects(ps);
                      setActiveProject(ps[0]?.id ?? null);
                    }
                  }}
                >
                  Delete project
                </button>
              </div>
            </>
          ) : (
            <>
              {lastReply?.tag && (
                <div className="card">
                  <div className="card-label">Turn measurement</div>
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className="chip phase">{lastReply.tag.phase}</span>
                    <span className="chip">{lastReply.tag.usage_type}</span>
                  </div>
                  {(lastReply.tag.fired_signals?.length ?? 0) > 0 && (
                    <div>
                      <div className="card-label mt-2">Signals observed</div>
                      {(lastReply.tag.fired_signals ?? []).map((s: { id: string; polarity: number; pillar: string; evidence?: string; text: string }) => (
                        <div key={s.id} className="mb-2">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-label-sm font-semibold ${s.polarity > 0 ? "bg-secondary-container/30 text-on-secondary-container" : "bg-error-container/30 text-error"}`}>
                            {s.polarity > 0 ? "▲" : "▼"} {s.pillar}
                          </span>
                          {s.evidence && <div className="muted mt-1 italic">"{s.evidence}"</div>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <div className="card">
                <div className="card-label">Knowledge retrieved</div>
                {!lastReply?.retrieved?.length && <div className="muted">Sources used will appear here.</div>}
                {(() => {
                  const byDoc = new Map<string, { source: string; scope?: string; similarity: number; n: number }>();
                  for (const c of lastReply?.retrieved || []) {
                    const key = `${c.source}|${c.scope}`;
                    const prev = byDoc.get(key);
                    if (!prev) byDoc.set(key, { source: c.source || "knowledge", scope: c.scope, similarity: c.similarity, n: 1 });
                    else { prev.n++; prev.similarity = Math.max(prev.similarity, c.similarity); }
                  }
                  return Array.from(byDoc.values()).map((c, i) => (
                    <div className="knowledge-item" key={i}>
                      <div className="kf truncate">{c.source}</div>
                      <div className="ks">
                        <span className={`uppercase font-bold text-[9px] tracking-wider ${c.scope === "user" ? "text-purple-600" : c.scope === "team" ? "text-secondary" : "text-primary"}`}>
                          {c.scope === "user" ? "project" : c.scope || "org"}
                        </span>
                        {" · "}{(c.similarity * 100).toFixed(0)}% match
                        {c.n > 1 && <span className="muted"> · {c.n} passages</span>}
                      </div>
                    </div>
                  ));
                })()}
              </div>
            </>
          )}
        </aside>
      </div>

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
