"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = await login(email, password);
      setUser(user);
      router.push(user.role === "kpmg_admin" ? "/admin" : "/chat");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "var(--blue)" }}>
      <div style={{ width: 380 }}>
        <div style={{ color: "#fff", fontSize: 34, fontWeight: 800, marginBottom: 4 }}>
          Pulse<span style={{ color: "var(--teal)" }}>.</span>
        </div>
        <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 13, marginBottom: 24 }}>
          KPMG · Design Excellence &amp; Quality
        </div>
        <form onSubmit={submit} className="card" style={{ padding: 28 }}>
          <div className="card-label">Sign in</div>
          <input
            className="chat-input"
            style={{ width: "100%", marginBottom: 10 }}
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="chat-input"
            style={{ width: "100%", marginBottom: 14 }}
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && (
            <div style={{ color: "var(--coral)", fontSize: 13, marginBottom: 12 }}>{error}</div>
          )}
          <button className="btn" style={{ width: "100%", height: 44 }} disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 11, marginTop: 14, lineHeight: 1.7 }}>
          Demo accounts (pw: pulse1234) · admin@kpmg.com · maya@northwind.com · raj@northwind.com
        </div>
      </div>
    </div>
  );
}
