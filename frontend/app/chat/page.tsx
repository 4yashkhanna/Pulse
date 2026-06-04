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
  const logRef = useRef<HTMLDivElement>(null);

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
  }

  async function submit() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const r = await sendMessage(text, activeId);
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
        <div className="chat-input-row">
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
          <button className="btn" onClick={submit} disabled={loading || !input.trim()}>
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
              <span className="chip">{lastReply.tag.pillar}</span>
              <span className="chip">{lastReply.tag.usage_type}</span>
            </div>
            <div className="muted" style={{ marginTop: 10 }}>
              Quality {lastReply.tag.quality_score}/5 ·{" "}
              {lastReply.tag.evidence_backed ? "evidence-backed" : "assumption-based"}
            </div>
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
              <div className="ks">match {(c.similarity * 100).toFixed(0)}%</div>
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
