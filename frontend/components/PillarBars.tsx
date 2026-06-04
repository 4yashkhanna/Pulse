const PILLAR_ORDER = ["values", "behavior", "climate", "process", "resources", "success"];

export default function PillarBars({
  scores,
  baseline,
}: {
  scores: Record<string, number | null>;
  baseline?: Record<string, number>;
}) {
  return (
    <div>
      {PILLAR_ORDER.map((p) => {
        const v = scores[p];
        const b = baseline?.[p];
        return (
          <div className="bar-row" key={p}>
            <div className="bar-label">{p}</div>
            <div className="bar-track">
              {v != null && <div className="bar-fill" style={{ width: `${v}%` }} />}
              {b !== undefined && (
                <div
                  style={{
                    position: "relative",
                    top: -10,
                    left: `${b}%`,
                    width: 2,
                    height: 10,
                    background: "var(--coral)",
                  }}
                  title={`baseline ${b}`}
                />
              )}
            </div>
            <div className="bar-val">
              {v != null ? v.toFixed(0) : <span style={{ color: "var(--ink-3)", fontWeight: 400 }}>—</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
