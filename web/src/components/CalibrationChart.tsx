type Point = {
  bucket: number;
  p_mean: number;
  win_rate: number;
  n: number;
};

export function CalibrationChart({ points }: { points: Point[] }) {
  if (!points.length) {
    return <p className="muted">No calibration buckets available.</p>;
  }

  return (
    <div>
      <div className="cal-chart">
        {points.map((p, i) => (
          <div className="cal-col" key={p.bucket}>
            <div className="cal-bars">
              <span
                className="pred"
                style={{
                  height: `${Math.max(4, p.p_mean * 100)}%`,
                  animationDelay: `${i * 0.05}s`,
                }}
                title={`Predicted ${(p.p_mean * 100).toFixed(0)}%`}
              />
              <span
                className="actual"
                style={{
                  height: `${Math.max(4, p.win_rate * 100)}%`,
                  animationDelay: `${i * 0.05 + 0.05}s`,
                }}
                title={`Actual ${(p.win_rate * 100).toFixed(0)}%`}
              />
            </div>
            <div className="cal-label">{(p.p_mean * 100).toFixed(0)}%</div>
          </div>
        ))}
      </div>
      <p className="footnote">Teal = mean predicted P(Home) · Ink = observed win rate</p>
    </div>
  );
}
