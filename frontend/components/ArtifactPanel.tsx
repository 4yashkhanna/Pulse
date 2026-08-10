"use client";

export interface Artifact {
  html: string;
  title: string;
}

/** Pull a readable title from a self-contained HTML artifact. */
export function artifactTitle(html: string): string {
  const t = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(html)?.[1];
  const h = /<h1[^>]*>([\s\S]*?)<\/h1>/i.exec(html)?.[1];
  const raw = (t || h || "").replace(/<[^>]+>/g, "").trim();
  return raw || "Visualization";
}

/**
 * Renders a model-generated HTML artifact in a locked-down iframe.
 * sandbox="allow-scripts" WITHOUT allow-same-origin means the artifact runs in a
 * null origin: it cannot read the parent page, cookies, or localStorage (no token theft).
 */
export default function ArtifactPanel({ artifact, onClose }: { artifact: Artifact | null; onClose: () => void }) {
  if (!artifact) return null;
  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <span className="artifact-title">📊 {artifact.title}</span>
        <button className="artifact-close" onClick={onClose} title="Close">
          ✕
        </button>
      </div>
      <iframe
        title={artifact.title}
        className="artifact-frame"
        sandbox="allow-scripts"
        srcDoc={artifact.html}
      />
    </div>
  );
}
