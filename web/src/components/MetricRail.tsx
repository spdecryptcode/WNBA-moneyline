type Item = { label: string; value: string; hint: string };

export function MetricRail({ items }: { items: Item[] }) {
  return (
    <div className="metric-rail">
      {items.map((m) => (
        <div className="metric-tile" key={m.label}>
          <div className="label">{m.label}</div>
          <div className="value">{m.value}</div>
          <div className="hint">{m.hint}</div>
        </div>
      ))}
    </div>
  );
}
