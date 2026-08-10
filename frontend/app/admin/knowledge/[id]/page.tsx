"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Guard from "@/components/Guard";
import KnowledgePanel from "@/components/KnowledgePanel";
import {
  KTemplate,
  deleteTemplateDoc,
  listTemplateDocs,
  listTemplates,
  uploadTemplateDocs,
} from "@/lib/api";

function TemplateDocuments() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [tpl, setTpl] = useState<KTemplate | null>(null);
  const [notFound, setNotFound] = useState(false);

  const reload = () =>
    listTemplates()
      .then((ts) => {
        const found = ts.find((t) => t.id === id) || null;
        setTpl(found);
        if (!found) setNotFound(true);
      })
      .catch(() => setNotFound(true));

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (notFound)
    return <div className="app-main flex items-center justify-center muted">Template not found.</div>;
  if (!tpl) return <div className="app-main flex items-center justify-center muted">Loading…</div>;

  return (
    <div className="app-main">
      <header className="topbar">
        <div className="flex items-center gap-4">
          <button
            className="flex items-center gap-2 text-primary hover:bg-surface-container-low px-2 py-1 rounded transition-colors"
            onClick={() => router.push("/admin/knowledge")}
          >
            <span className="material-symbols-outlined">arrow_back</span>
          </button>
          <div className="flex items-center gap-3">
            <h2 className="text-headline-md text-primary font-bold">{tpl.name}</h2>
            <span
              className="px-2 py-0.5 bg-surface-tint text-on-primary text-label-caps rounded"
              style={{ fontSize: 10 }}
            >
              {tpl.kind === "stage" ? "STAGE TEMPLATE" : "SECTOR TEMPLATE"}
            </span>
          </div>
        </div>
        <div />
      </header>

      <div className="page-canvas">
        <div className="max-w-3xl">
          <p className="text-body-md text-on-surface-variant mb-6">
            Documents added here are embedded once. When this template is applied to an
            organization, these documents are copied into that org&apos;s knowledge instantly —
            no re-embedding — and can then be tweaked per organization.
          </p>

          <KnowledgePanel
            title={`${tpl.name} — documents`}
            hint="Upload PDF, Word, PowerPoint, or text/markdown. Remove anything that no longer belongs."
            load={() => listTemplateDocs(tpl.id)}
            upload={(fs) => uploadTemplateDocs(tpl.id, fs).then((r) => { reload(); return r; })}
            remove={(docId) => deleteTemplateDoc(tpl.id, docId).then((r) => { reload(); return r; })}
          />
        </div>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Guard role="kpmg_admin">
      <TemplateDocuments />
    </Guard>
  );
}
