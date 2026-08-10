"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Mermaid from "./Mermaid";
import { artifactTitle } from "./ArtifactPanel";

/**
 * Renders a coach reply as Markdown (GFM). A ```mermaid fence renders as a diagram.
 * A ```html (or ```artifact) fence is NOT rendered inline — instead it shows a card that
 * opens the visualization in the sandboxed artifact panel. Raw HTML in normal prose is
 * escaped by react-markdown (no execution), so there's no injection surface.
 */
export default function MessageContent({
  content,
  onOpenArtifact,
}: {
  content: string;
  onOpenArtifact?: (html: string, title: string) => void;
}) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre: ({ children }: any) => <>{children}</>,
          code: ({ className, children }: any) => {
            const text = String(children).replace(/\n$/, "");
            const lang = /language-(\w+)/.exec(className || "")?.[1];
            if (lang === "mermaid") return <Mermaid chart={text} />;
            if (lang === "html" || lang === "artifact") {
              const title = artifactTitle(text);
              return (
                <button className="artifact-card" onClick={() => onOpenArtifact?.(text, title)}>
                  <span className="artifact-card-icon">📊</span>
                  <span>
                    <span className="artifact-card-title">{title}</span>
                    <span className="artifact-card-sub">Click to open the visualization →</span>
                  </span>
                </button>
              );
            }
            if (lang) return <div className="code-block">{text}</div>;
            return <code className="inline-code">{children}</code>;
          },
          a: ({ href, children }: any) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
