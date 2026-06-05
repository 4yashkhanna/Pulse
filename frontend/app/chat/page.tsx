"use client";

import { useEffect, useRef, useState } from "react";
import Guard from "@/components/Guard";
import {
  ChatReply,
  Conversation,
  deleteConversation,
  getConversation,
  listConversations,
  sendMessage,
} from "@/lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  handoff?: boolean;
}

function Chat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [lastReply, setLastReply] = useState<ChatReply | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const logRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadConvos = (q?: string) => listConversations(q).then(setConversations);
  useEffect(() => {
    loadConvos();
  }, []);
  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [messages, loading]);

  // debounced search
  useEffect(() => {
    const t = setTimeout(() => loadConvos(search || undefined), 250);
    return () => clearTimeout(t);
  }, [search]);

  async function openConversation(id: string) {
    setActiveId(id);
    setLastReply(null);
    const c = await getConversation(id);
    setMessages(c.messages as Msg[]);
  }

  function newChat() {
    setActiveId(null);
    setMessages([]);
    setLastReply(null);
    setInput("");
    setFiles([]);
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
      const r = await sendMessage(text, activeId, attached);
      setActiveId(r.conversation_id);
      setLastReply(r);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: r.reply, handoff: r.tag?.handoff },
      ]);
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
      {/* Conversation sidebar */}
      <aside className="chat-side" style={{ width: 260 }}>
        <button className="btn" style={{ height: 40 }} onClick={newChat}>
          + New chat
        </button>
        <input
          className="select"
          placeholder="Search chats…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
          {conversations.map((c) => (
            <div
              key={c.id}
              onClick={() => openConversation(c.id)}
              className="knowledge-item"
              style={{
                cursor: "pointer",
                marginBottom: 0,
                background: c.id === activeId ? "var(--blue-pale)" : "var(--surface)",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {c.title}
              </span>
              <span
                onClick={async (e) => {
                  e.stopPropagation();
                  await deleteConversation(c.id);
                  if (c.id === activeId) newChat();
                  loadConvos(search || undefined);
                }}
                style={{ color: "var(--ink-3)", fontSize: 14 }}
                title="Delete"
              >
                ×
              </span>
            </div>
          ))}
          {conversations.length === 0 && <div className="muted" style={{ fontSize: 12 }}>No chats yet.</div>}
        </div>
      </aside>

      {/* Main chat */}
      <div className="chat-main">
        <div className="chat-log" ref={logRef}>
          {messages.length === 0 && (
            <div className="muted" style={{ margin: "auto", textAlign: "center" }}>
              Ask Pulse about a design challenge you&apos;re working on.
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
                <span
                  style={{ cursor: "pointer" }}
                  onClick={() => setFiles((fs) => fs.filter((_, j) => j !== i))}
                >
                  ×
                </span>
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
            title="Attach image or PDF"
          >
            📎
          </button>
          <textarea
            className="chat-input"
            rows={1}
            placeholder="Message Pulse… (attach an image or PDF with 📎)"
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

      {/* Knowledge transparency */}
      <aside className="chat-side" style={{ width: 250 }}>
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
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        padding: "2px 7px",
                        borderRadius: 5,
                        background: s.polarity > 0 ? "var(--teal-pale)" : "var(--coral-pale)",
                        color: s.polarity > 0 ? "#0f6e56" : "var(--coral)",
                      }}
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
            <div className="muted">Org knowledge used to ground the reply appears here.</div>
          )}
          {lastReply?.retrieved?.map((c, i) => (
            <div className="knowledge-item" key={i}>
              <span className="kf">{c.source || "knowledge"}</span>
              <div className="ks">
                <span
                  style={{
                    textTransform: "uppercase",
                    fontWeight: 700,
                    fontSize: 9,
                    letterSpacing: "0.05em",
                    color:
                      c.scope === "user" ? "var(--purple)" : c.scope === "team" ? "var(--teal)" : "var(--blue-mid)",
                  }}
                >
                  {c.scope === "user" ? "personal" : c.scope || "org"}
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
