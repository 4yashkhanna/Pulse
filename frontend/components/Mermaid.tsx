"use client";

import { useEffect, useRef, useState } from "react";

let initialized = false;
async function getMermaid() {
  const mod = await import("mermaid");
  const mermaid = mod.default;
  if (!initialized) {
    // securityLevel "strict" sanitizes labels and disables embedded scripts/click handlers.
    mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral" });
    initialized = true;
  }
  return mermaid;
}

export default function Mermaid({ chart }: { chart: string }) {
  const [svg, setSvg] = useState("");
  const [failed, setFailed] = useState(false);
  const idRef = useRef("m" + Math.random().toString(36).slice(2));

  useEffect(() => {
    let cancelled = false;
    getMermaid()
      .then((mermaid) => mermaid.render(idRef.current, chart))
      .then(({ svg }) => !cancelled && setSvg(svg))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [chart]);

  // If the model produced invalid mermaid, fall back to showing the source.
  if (failed) return <div className="code-block">{chart}</div>;
  if (!svg) return <div className="muted" style={{ fontSize: 12 }}>rendering diagram…</div>;
  // svg is mermaid-generated under strict security — safe to inject.
  return <div className="mermaid-diagram" dangerouslySetInnerHTML={{ __html: svg }} />;
}
