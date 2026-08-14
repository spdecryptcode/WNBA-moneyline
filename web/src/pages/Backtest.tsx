import { useEffect, useState } from "react";
import { fetchBacktest, type BacktestResponse } from "../api/client";
import { CalibrationChart } from "../components/CalibrationChart";
import { MetricRail } from "../components/MetricRail";
import { PageFrame } from "../components/PageFrame";

export function Backtest() {
  const [data, setData] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBacktest()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const m = data?.oof_metrics ?? {};

  return (
    <PageFrame
      title="Backtest"
      subtitle="Walk-forward skill metrics, separate from betting PnL."
    >
      {error && <div className="error-box">{error}</div>}
      {loading && <div className="loading">Loading backtest</div>}

      {data && (
        <>
          <MetricRail
            items={[
              {
                label: "Log loss (cal)",
                value: Number(m.log_loss_cal ?? 0).toFixed(3),
                hint: "Lower is better",
              },
              {
                label: "Brier (cal)",
                value: Number(m.brier_cal ?? 0).toFixed(3),
                hint: "Lower is better",
              },
              {
                label: "MAE",
                value: Number(m.mae ?? 0).toFixed(2),
                hint: "Margin points",
              },
              {
                label: "Folds",
                value: String(data.walk_forward_folds?.length ?? 0),
                hint: data.param_source ?? "walk-forward",
              },
            ]}
          />

          {data.selection_note && <p className="muted">{data.selection_note}</p>}

          <div className="panel">
            <h3>Walk-forward folds</h3>
            <table className="table">
              <thead>
                <tr>
                  <th>Season</th>
                  <th>N</th>
                  <th>MAE</th>
                  <th>Log loss</th>
                  <th>Brier</th>
                  <th>Sigma</th>
                </tr>
              </thead>
              <tbody>
                {data.walk_forward_folds.map((f) => (
                  <tr key={f.test_season}>
                    <td>{f.test_season}</td>
                    <td>{f.n}</td>
                    <td>{Number(f.mae).toFixed(2)}</td>
                    <td>{Number(f.log_loss).toFixed(3)}</td>
                    <td>{Number(f.brier).toFixed(3)}</td>
                    <td>{Number(f.sigma).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <h3>Calibration</h3>
            <CalibrationChart points={data.calibration} />
          </div>
        </>
      )}
    </PageFrame>
  );
}
