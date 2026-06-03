import Link from "next/link";

export default function Home() {
  return (
    <div className="page">
      <div className="page-title">The Design Intelligence Coach</div>
      <div className="page-sub">
        Coaches in the moment · measures design quality passively
      </div>

      <div className="grid grid-2" style={{ marginTop: 8 }}>
        <Link href="/chat" className="card" style={{ display: "block" }}>
          <div className="card-label">Start here</div>
          <h3 style={{ color: "var(--blue)", marginBottom: 6 }}>Open the Coach →</h3>
          <p className="muted">
            A Socratic, phase-aware coach grounded in KPMG&apos;s design methodology.
            It nudges you toward stronger decisions and hands off to real human work
            when AI shouldn&apos;t fake it.
          </p>
        </Link>
        <Link href="/dashboard/leadership" className="card" style={{ display: "block" }}>
          <div className="card-label">The proof</div>
          <h3 style={{ color: "var(--blue)", marginBottom: 6 }}>Transformation Dashboard →</h3>
          <p className="muted">
            Every conversation is tagged against the 6 pillars and fed into a live
            Design Quality score — no surveys. Employee, team, and leadership views.
          </p>
        </Link>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-label">Try these in the coach</div>
        <p className="muted" style={{ marginBottom: 8 }}>
          <strong style={{ color: "var(--ink-2)" }}>Nudge:</strong> &ldquo;We already
          know the solution, let&apos;s just build it.&rdquo;
        </p>
        <p className="muted">
          <strong style={{ color: "var(--ink-2)" }}>Handoff:</strong> &ldquo;Can you tell
          me how our users will react to this screen?&rdquo;
        </p>
      </div>
    </div>
  );
}
