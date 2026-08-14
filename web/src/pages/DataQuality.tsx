import { useEffect, useState } from "react";
import { fetchDq, type DqResponse } from "../api/client";
import { MetricRail } from "../components/MetricRail";
import { PageFrame } from "../components/PageFrame";

export function DataQuality() {
  const [data, setData] = useState<DqResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDq()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <PageFrame
      title="Data quality"
      subtitle="Hard integrity checks before any model claim."
    >
      {error && <div className="error-box">{error}</div>}
      {loading && <div className="loading">Loading data quality</div>}

      {data && (
        <>
          <div className={`status-banner ${data.all_hard_passed ? "" : "fail"}`}>
            <strong>{data.all_hard_passed ? "ALL HARD CHECKS PASSED" : "HARD CHECKS FAILED"}</strong>
            <span className="muted">Generated {data.generated_at}</span>
          </div>

          <MetricRail
            items={[
              {
                label: "Checks",
                value: String(data.checks?.length ?? 0),
                hint: "Hard + soft",
              },
              {
                label: "Games clean",
                value: String(data.row_counts?.games_clean ?? "—"),
                hint: "Modeling table",
              },
              {
                label: "Quarantine team",
                value: String(data.quarantine_counts?.team_box ?? 0),
                hint: "Rows held out",
              },
              {
                label: "Quarantine player",
                value: String(data.quarantine_counts?.player_box ?? 0),
                hint: "Rows held out",
              },
            ]}
          />

          <div className="panel">
            <h3>Checks</h3>
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Fails</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {data.checks.map((c) => (
                  <tr key={c.name}>
                    <td>{c.name}</td>
                    <td
                      style={{
                        color: c.passed ? "var(--mint-deep)" : "var(--coral)",
                        fontWeight: 700,
                      }}
                    >
                      {c.passed ? "PASS" : "FAIL"}
                    </td>
                    <td>{c.n_fail}</td>
                    <td className="muted">{c.detail || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.markdown ? (
            <div className="panel">
              <h3>Report</h3>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  fontFamily: "var(--font-body)",
                  fontSize: "0.88rem",
                  lineHeight: 1.5,
                  margin: 0,
                  color: "var(--ink-2)",
                }}
              >
                {data.markdown}
              </pre>
            </div>
          ) : null}
        </>
      )}
    </PageFrame>
  );
}
