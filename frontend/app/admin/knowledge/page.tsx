"use client";

import { useEffect, useMemo, useState } from "react";
import Guard from "@/components/Guard";
import { Org, listOrgs } from "@/lib/api";

const STAGES = [
  { n: 1, label: "Initial Assessment", icon: "assessment", desc: "Ad-hoc processes and siloed design initiatives." },
  { n: 2, label: "Foundation", icon: "foundation", desc: "Establishing shared libraries and initial AI-assisted workflows." },
  { n: 3, label: "Optimization", icon: "tune", desc: "Scaled design systems and integrated performance metrics." },
  { n: 4, label: "Optimized", icon: "speed", desc: "AI deeply integrated into generative design and fully automated compliance." },
  { n: 5, label: "Target Goal", icon: "flag", desc: "Continuous autonomous improvement and strategic design leadership." },
];

const SECTORS = [
  { name: "Retail", icon: "shopping_cart", desc: "Consumer-focused design, e-commerce, and store-level experience." },
  { name: "Fintech", icon: "account_balance", desc: "Security-first design, financial literacy, and transactional efficiency." },
  { name: "Healthcare", icon: "monitor_heart", desc: "Accessibility, patient data privacy, and medical compliance." },
  { name: "Manufacturing", icon: "precision_manufacturing", desc: "Process optimization, industrial IoT, and workforce training." },
];

function StageKnowledge() {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    listOrgs().then(setOrgs).catch(() => {});
  }, []);

  const countByStage = useMemo(() => {
    const m: Record<number, number> = {};
    orgs.forEach((o) => { m[o.maturity_stage] = (m[o.maturity_stage] || 0) + 1; });
    return m;
  }, [orgs]);

  // the stage with the most active orgs is the current focus
  const focusStage = useMemo(() => {
    let best = 0, n = -1;
    Object.entries(countByStage).forEach(([s, c]) => { if (c > n) { n = c; best = Number(s); } });
    return best;
  }, [countByStage]);

  const visibleStages = STAGES.filter(
    (s) => !query || s.label.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="app-main">
      {/* TopNavBar */}
      <header className="topbar">
        <div className="text-headline-md font-bold text-primary">Stage Management</div>
        <div className="flex items-center gap-4">
          <div className="relative">
            <span className="material-symbols-outlined text-outline absolute left-3 top-1/2 -translate-y-1/2">search</span>
            <input
              className="pl-10 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded focus:border-pulse-teal-vibrant focus:ring-2 focus:ring-pulse-teal-vibrant/10 outline-none transition-all text-body-sm w-64"
              placeholder="Search templates..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <button className="p-2 text-on-surface-variant hover:text-primary transition-colors">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="p-2 text-on-surface-variant hover:text-primary transition-colors">
            <span className="material-symbols-outlined">help</span>
          </button>
        </div>
      </header>

      <div className="page-canvas">
        <div className="mb-10 max-w-4xl">
          <p className="text-body-lg text-on-surface-variant">
            Define and manage global maturity roadmaps and industry-specific coaching contexts.
          </p>
        </div>

        {/* Maturity Stage Templates */}
        <section className="mb-16">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-headline-md text-on-surface border-l-4 border-primary pl-3">Maturity Stage Templates</h2>
          </div>
          <div className="flex gap-6 overflow-x-auto pb-6">
            {visibleStages.map((s) => {
              const active = s.n === focusStage;
              const orgsAtStage = countByStage[s.n] || 0;
              return (
                <div
                  key={s.n}
                  className="bg-surface-container-lowest rounded-xl p-stack-md border border-outline-variant shadow-ambient flex flex-col flex-shrink-0 relative transition-all hover:-translate-y-0.5 hover:shadow-md hover:border-pulse-teal-vibrant"
                  style={{ minWidth: 300, width: 300 }}
                >
                  <div className="absolute top-0 right-0 p-4">
                    <button className="text-outline-variant hover:text-primary transition-colors">
                      <span className="material-symbols-outlined text-sm">edit</span>
                    </button>
                  </div>
                  <div
                    className={`w-12 h-12 rounded flex items-center justify-center mb-4 relative overflow-hidden ${
                      active ? "bg-primary-container text-white" : "bg-surface-container-highest text-primary"
                    }`}
                  >
                    {active && <div className="absolute inset-0 bg-pulse-teal-vibrant/20" />}
                    <span className="material-symbols-outlined text-2xl icon-fill relative z-10">{s.icon}</span>
                  </div>
                  <div className={`text-label-caps mb-1 ${active ? "text-primary font-bold" : s.n === 5 ? "text-pulse-teal-vibrant font-bold" : "text-on-surface-variant"}`}>
                    STAGE {s.n}{active ? " · CURRENT FOCUS" : ""}
                  </div>
                  <h3 className="text-headline-sm text-primary font-semibold mb-3">{s.label}</h3>
                  <p className="text-body-sm text-on-surface-variant flex-1">{s.desc}</p>
                  <div className="mt-4 pt-4 border-t border-outline-variant/30 flex justify-between items-center">
                    <span className={`text-xs font-medium ${active ? "text-primary font-bold" : "text-outline"}`}>
                      {orgsAtStage} Active Organization{orgsAtStage === 1 ? "" : "s"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Industry Sector Templates */}
        <section className="bg-surface-container-lowest rounded-xl p-stack-md border border-outline-variant shadow-ambient flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-headline-md text-on-surface border-l-4 border-secondary pl-3">Industry Sector Templates</h2>
            <button className="bg-primary text-white text-label-sm px-4 py-2 rounded hover:bg-primary/90 transition-colors">
              Add New Sector
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {SECTORS.map((sec) => (
              <div
                key={sec.name}
                className="bg-white/95 border border-outline-variant shadow-ambient p-6 rounded-lg flex flex-col h-full transition-all hover:-translate-y-0.5 hover:shadow-md hover:border-pulse-teal-vibrant"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded bg-tertiary/10 text-tertiary flex items-center justify-center">
                      <span className="material-symbols-outlined">{sec.icon}</span>
                    </div>
                    <h3 className="text-headline-sm text-primary font-semibold">{sec.name}</h3>
                  </div>
                </div>
                <p className="text-body-sm text-on-surface-variant flex-1 mb-6">{sec.desc}</p>
                <div className="flex gap-2 mt-auto">
                  <button className="flex-1 border border-outline text-on-surface-variant text-label-sm py-2 rounded hover:bg-surface-container-low transition-colors">
                    Edit Sector
                  </button>
                  <button className="flex-1 bg-surface-container text-primary text-label-sm py-2 rounded hover:bg-primary/10 transition-colors font-medium">
                    Manage Prompt
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Guard role="kpmg_admin">
      <StageKnowledge />
    </Guard>
  );
}
