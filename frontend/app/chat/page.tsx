"use client";

import { useEffect, useRef, useState } from "react";
import {
  ChatResponse,
  RetrievedChunk,
  Tag,
  User,
  getUsers,
  sendChat,
} from "@/lib/api";

interface Msg {
  role: "user" | "coach";
  content: string;
  handoff?: boolean;
}

export default function ChatPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [userId, setUserId] = useState<string>("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [retrieved, setRetrieved] = useState<RetrievedChunk[]>([]);
  const [lastTag, setLastTag] = useState<Tag | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getUsers()
      .then((u) => {
        setUsers(u);
        if (u.length) setUserId(u[0].id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [messages, loading]);

  const currentUser = users.find((u) => u.id === userId);

  async function submit() {
    const text = input.trim();
    if (!text || !userId || loading) return;
    setInput("");
    const history = messages.map((m) => ({
      role: m.role === "coach" ? "assistant" : "user",
      content: m.content,
    }));
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const res: ChatResponse = await sendChat({
        message: text,
        user_id: userId,
        sector: currentUser?.sector ?? null,
        conversation_id: conversationId,
        history,
      });
      setConversationId(res.conversation_id);
      setRetrieved(res.retrieved);
      setLastTag(res.tag);
      setMessages((m) => [
        ...m,
        { role: "coach", content: res.reply, handoff: res.tag?.handoff },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: "coach",
          content:
            "⚠️ Could not reach the coach. Is the backend running on :8000 and GEMINI_API_KEY set?",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-shell">
      <div className="chat-main">
        <div className="chat-log" ref={logRef}>
          {messages.length === 0 && (
            <div className="muted" style={{ margin: "auto", textAlign: "center" }}>
              Ask the coach about a design challenge you&apos;re working on.
              <br />
              Try: &ldquo;We already know the solution, let&apos;s just build it.&rdquo;
            </div>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`bubble ${m.role} ${m.handoff ? "handoff" : ""}`}
            >
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
            placeholder="Describe what you're working on…"
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

      <aside className="chat-side">
        <div className="card">
          <div className="card-label">Coaching as</div>
          <select
            className="select"
            style={{ width: "100%" }}
            value={userId}
            onChange={(e) => {
              setUserId(e.target.value);
              setMessages([]);
              setConversationId(null);
              setRetrieved([]);
              setLastTag(null);
            }}
          >
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} · {u.dept}
              </option>
            ))}
          </select>
          {currentUser && (
            <div className="muted" style={{ marginTop: 8 }}>
              Sector calibration: <strong>{currentUser.sector.toUpperCase()}</strong>
            </div>
          )}
        </div>

        {lastTag && (
          <div className="card">
            <div className="card-label">How this turn was measured</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              <span className="chip phase">{lastTag.phase}</span>
              <span className="chip">{lastTag.pillar}</span>
              <span className="chip">{lastTag.usage_type}</span>
            </div>
            <div className="muted" style={{ marginTop: 10 }}>
              Quality {lastTag.quality_score}/5 ·{" "}
              {lastTag.evidence_backed ? "evidence-backed" : "assumption-based"}
            </div>
          </div>
        )}

        <div className="card">
          <div className="card-label">KPMG knowledge retrieved</div>
          {retrieved.length === 0 && (
            <div className="muted">Knowledge used to ground the reply shows here.</div>
          )}
          {retrieved.map((c, i) => (
            <div className="knowledge-item" key={i}>
              <span className="kf">{c.framework || "Knowledge"}</span>
              <div className="ks">
                {c.phase ? `${c.phase} · ` : ""}
                match {(c.similarity * 100).toFixed(0)}%
              </div>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
