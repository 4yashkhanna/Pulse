"use client";

import { useState } from "react";
import { forgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await forgotPassword(email);
    } finally {
      // Always show the same message, whether or not the email exists.
      setSent(true);
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
          <div className="card-label mb-6">Reset your password</div>
          {sent ? (
            <div className="text-body-sm text-on-surface">
              If an account exists for <strong>{email}</strong>, we've sent a link to reset the password. Check your inbox.
            </div>
          ) : (
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
              <button className="btn w-full" style={{ height: 44, marginTop: 8 }} disabled={busy}>
                {busy ? "Sending…" : "Send reset link"}
              </button>
            </form>
          )}
          <div className="text-center mt-5">
            <a href="/login" className="text-label-sm text-primary hover:underline">Back to sign in</a>
          </div>
        </div>
      </div>
    </div>
  );
}
