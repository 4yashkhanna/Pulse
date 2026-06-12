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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-primary">
      <div style={{ width: 400 }}>
        {/* Brand */}
        <div className="mb-8 px-2">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 rounded bg-surface-container-lowest flex items-center justify-center">
              <span className="material-symbols-outlined text-primary icon-fill" style={{ fontSize: 22 }}>analytics</span>
            </div>
            <div>
              <div className="text-headline-md font-semibold text-on-primary">Pulse</div>
              <div className="text-label-caps text-tertiary-fixed-dim">Design Intelligence Platform</div>
            </div>
          </div>
        </div>

        {/* Card */}
        <div className="bg-surface-container-lowest rounded-xl p-8" style={{ boxShadow: "0 4px 24px rgba(0,0,0,0.15)" }}>
          <div className="card-label mb-6">Sign in to your account</div>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-label-sm text-on-surface-variant mb-1 block">Email</label>
              <input
                className="input-field w-full"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="text-label-sm text-on-surface-variant mb-1 block">Password</label>
              <input
                className="input-field w-full"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && (
              <div className="text-error text-body-sm bg-error-container/30 border border-error/20 px-3 py-2 rounded-lg">{error}</div>
            )}
            <button className="btn w-full" style={{ height: 44, marginTop: 8 }} disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        <div className="text-center mt-5 text-label-sm px-2" style={{ color: "rgba(255,255,255,0.35)" }}>
          Demo accounts (pw: pulse1234) · admin@kpmg.com · maya@northwind.com · raj@northwind.com
        </div>
      </div>
    </div>
  );
}
