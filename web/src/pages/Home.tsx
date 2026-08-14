import { useEffect, useState } from "react";
import { fetchDates, fetchSlate, type SlateResponse } from "../api/client";
import { MetricRail } from "../components/MetricRail";
import { PageFrame } from "../components/PageFrame";
import { SlateBoard } from "../components/SlateBoard";

export function Home() {
  const [includeCompleted, setIncludeCompleted] = useState(false);
  const [dates, setDates] = useState<string[]>([]);
  const [date, setDate] = useState<string>("");
  const [slate, setSlate] = useState<SlateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchDates(includeCompleted)
      .then((res) => {
        if (cancelled) return;
        setDates(res.dates);
        setDate((prev) =>
          res.dates.includes(prev) ? prev : res.dates[0] ?? "",
        );
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [includeCompleted]);

  useEffect(() => {
    if (!date) {
      setSlate(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchSlate(date, includeCompleted)
      .then((res) => {
        if (!cancelled) setSlate(res);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date, includeCompleted]);

  return (
    <PageFrame
      title="Slate"
      subtitle="Calibrated win probabilities and projected margins."
    >
      <div className="controls">
        <div className="field">
          <label htmlFor="slate-date">Slate date</label>
          <select
            id="slate-date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            disabled={!dates.length}
          >
            {dates.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
        <label className="check-row">
          <input
            type="checkbox"
            checked={includeCompleted}
            onChange={(e) => setIncludeCompleted(e.target.checked)}
          />
          Include completed
        </label>
      </div>

      {error && <div className="error-box">{error}</div>}
      {loading && !slate && <div className="loading">Loading slate</div>}

      {slate && (
        <>
          <div className="section-head">
            <h2>Matchups</h2>
            <span>{slate.summary.n_games} games · open for drivers</span>
          </div>
          <SlateBoard games={slate.games} />
          <MetricRail
            items={[
              { label: "Games", value: String(slate.summary.n_games), hint: slate.date },
              {
                label: "Avg P(Home)",
                value: `${(slate.summary.avg_p_home * 100).toFixed(0)}%`,
                hint: "Calibrated",
              },
              {
                label: "Bet signals",
                value: String(slate.summary.n_bet),
                hint: "Needs lines",
              },
              { label: "Board", value: "LIVE", hint: "As-of tipoff" },
            ]}
          />
          <p className="footnote">
            PASS is expected until sportsbook lines are entered on Game Detail.
          </p>
        </>
      )}
    </PageFrame>
  );
}
