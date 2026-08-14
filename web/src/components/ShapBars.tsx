import type { ShapItem } from "../api/client";

export function ShapBars({ items }: { items: ShapItem[] }) {
  if (!items?.length) {
    return <p className="muted">No SHAP drivers for this game.</p>;
  }
  const maxAbs = Math.max(...items.map((s) => Math.abs(s.shap_value)), 1e-6);

  return (
    <div>
      {items.map((s) => {
        const pos = s.shap_value >= 0;
        const width = `${(Math.abs(s.shap_value) / maxAbs) * 100}%`;
        return (
          <div className="shap-row" key={s.feature}>
            <div className="shap-name">{s.feature}</div>
            <div className="shap-track">
              <div
                className={`shap-fill ${pos ? "pos" : "neg"}`}
                style={{ width }}
              />
            </div>
            <div className="shap-val">
              {pos ? "+" : ""}
              {s.shap_value.toFixed(2)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
