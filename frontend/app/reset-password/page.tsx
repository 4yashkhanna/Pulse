"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { resetPassword } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function ResetPasswordForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { setUser } = useAuth();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    setBusy(true);
    try {
      const user = await resetPassword(token, password);
      setUser(user);
      router.push(user.role === "kpmg_admin" ? "/admin" : "/chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Couldn't reset password");
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="text-error text-body-sm bg-error-container/30 border border-error/20 px-3 py-2 rounded-lg">
        This reset link is missing a token. Request a new one from the login page.
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label className="text-label-sm text-on-surface-variant mb-1 block">New password</label>
        <input
          className="input-field w-full"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="text-label-sm text-on-surface-variant mb-1 block">Confirm password</label>
        <input
          className="input-field w-full"
          type="password"
          placeholder="••••••••"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
        />
      </div>
      {error && (
        <div className="text-error text-body-sm bg-error-container/30 border border-error/20 px-3 py-2 rounded-lg">{error}</div>
      )}
      <button className="btn w-full" style={{ height: 44, marginTop: 8 }} disabled={busy}>
        {busy ? "Resetting…" : "Reset password & sign in"}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
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
          <div className="card-label mb-6">Choose a new password</div>
          <Suspense fallback={<div className="muted text-body-sm">Loading…</div>}>
            <ResetPasswordForm />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
