import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchGame, type GameCard } from "../api/client";
import { GateBadge } from "../components/GateBadge";
import { MetricRail } from "../components/MetricRail";
import { PageFrame } from "../components/PageFrame";
import { ShapBars } from "../components/ShapBars";

function fmtPct(n?: number) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function fmtNum(n?: number, digits = 3) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

export function GameDetail() {
  const { gameId } = useParams();
  const id = Number(gameId);
  const [homeMl, setHomeMl] = useState("");
  const [awayMl, setAwayMl] = useState("");
  const [homeSpread, setHomeSpread] = useState("");
  const [card, setCard] = useState<GameCard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = (opts?: { home_ml?: number; away_ml?: number; home_spread?: number }) => {
    if (!Number.isFinite(id)) {
      setError("Invalid game id");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    fetchGame(id, opts)
      .then(setCard)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    load({
      home_ml: homeMl === "" ? undefined : Number(homeMl),
      away_ml: awayMl === "" ? undefined : Number(awayMl),
      home_spread: homeSpread === "" ? undefined : Number(homeSpread),
    });
  };

  return (
    <PageFrame
      title="Game detail"
      subtitle="Probabilities, market edge, and model drivers."
    >
      <Link className="back-link" to="/">
        ← Back to slate
      </Link>

      <form className="controls" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="home-ml">Home ML</label>
          <input
            id="home-ml"
            value={homeMl}
            onChange={(e) => setHomeMl(e.target.value)}
            placeholder="-150"
            inputMode="decimal"
          />
        </div>
        <div className="field">
          <label htmlFor="away-ml">Away ML</label>
          <input
            id="away-ml"
            value={awayMl}
            onChange={(e) => setAwayMl(e.target.value)}
            placeholder="+130"
            inputMode="decimal"
          />
        </div>
        <div className="field">
          <label htmlFor="home-spread">Home spread</label>
          <input
            id="home-spread"
            value={homeSpread}
            onChange={(e) => setHomeSpread(e.target.value)}
            placeholder="-3.5"
            inputMode="decimal"
          />
        </div>
        <div className="field">
          <label>&nbsp;</label>
          <button type="submit" className="btn-primary">
            Score with lines
          </button>
        </div>
      </form>

      {error && <div className="error-box">{error}</div>}
      {loading && !card && <div className="loading">Scoring game</div>}

      {card && (
        <>
          <div className="section-head">
            <h2>
              {card.away_abbr} @ {card.home_abbr}
            </h2>
            <GateBadge bet={Boolean(card.gate?.bet)} />
          </div>

          <MetricRail
            items={[
              {
                label: "P(Home)",
                value: fmtPct(card.p_home_win_cal),
                hint: "Calibrated",
              },
              {
                label: "Margin μ",
                value: `${card.mu >= 0 ? "+" : ""}${card.mu.toFixed(1)}`,
                hint: "Projected home margin",
              },
              {
                label: "Sigma",
                value: card.sigma.toFixed(1),
                hint: "Uncertainty",
              },
              {
                label: "Status",
                value: card.completed ? "Final" : "Upcoming",
                hint: card.game_date.slice(0, 10),
              },
            ]}
          />

          <div className="grid-2">
            <div className="panel">
              <h3>Market</h3>
              {card.market && Object.keys(card.market).length ? (
                <dl className="kv">
                  <dt>No-vig home</dt>
                  <dd>{fmtPct(card.market.no_vig_home)}</dd>
                  <dt>Edge home</dt>
                  <dd>{fmtNum(card.market.edge_home)}</dd>
                  <dt>EV home</dt>
                  <dd>{fmtNum(card.market.ev_home)}</dd>
                  <dt>Kelly</dt>
                  <dd>{fmtNum(card.market.kelly)}</dd>
                </dl>
              ) : (
                <p className="muted">Enter moneylines to compute edge / EV / Kelly.</p>
              )}
              {card.home_spread != null && (
                <dl className="kv" style={{ marginTop: "1rem" }}>
                  <dt>P(Home cover)</dt>
                  <dd>{fmtPct(card.p_home_cover)}</dd>
                  <dt>Spread EV</dt>
                  <dd>{fmtNum(card.spread_ev)}</dd>
                </dl>
              )}
              {card.gate?.reasons?.length ? (
                <p className="footnote">{card.gate.reasons.join(" · ")}</p>
              ) : null}
            </div>
            <div className="panel">
              <h3>Top drivers</h3>
              <ShapBars items={card.shap ?? []} />
            </div>
          </div>
        </>
      )}
    </PageFrame>
  );
}
