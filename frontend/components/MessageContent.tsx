"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Mermaid from "./Mermaid";

/**
 * Renders a coach reply as Markdown (GFM: tables, lists, etc.). A ```mermaid code
 * fence is rendered as a real diagram. Raw HTML in the model output is NOT executed —
 * react-markdown escapes it by default, so there's no injection surface here.
 */
export default function MessageContent({ content }: { content: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Let block code render our own element (no extra <pre> wrapper).
          pre: ({ children }: any) => <>{children}</>,
          code: ({ className, children }: any) => {
            const text = String(children).replace(/\n$/, "");
            const lang = /language-(\w+)/.exec(className || "")?.[1];
            if (lang === "mermaid") return <Mermaid chart={text} />;
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
