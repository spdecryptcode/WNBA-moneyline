import { useNavigate } from "react-router-dom";
import type { GameCard } from "../api/client";
import { GateBadge } from "./GateBadge";

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

export function SlateBoard({ games }: { games: GameCard[] }) {
  const navigate = useNavigate();

  if (!games.length) {
    return <p className="muted">No scored games on this slate.</p>;
  }

  return (
    <div className="slate-board">
      {games.map((g, i) => {
        const pHome = Number(g.p_home_win_cal ?? 0);
        const pAway = 1 - pHome;
        return (
          <div
            className="match-row"
            key={g.game_id}
            style={{ animationDelay: `${0.05 * i}s` }}
            onClick={() => navigate(`/game/${g.game_id}`)}
            role="link"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter") navigate(`/game/${g.game_id}`);
            }}
          >
            <div className="match-main">
              <div className="match-top">
                <div className="match-meta">{g.completed ? "Final" : "Upcoming tip"}</div>
                <div className="match-meta">#{g.game_id}</div>
              </div>

              <div className="team-duel">
                <div className="team away">
                  <span className="role">Away</span>
                  <span className="abbr">{g.away_abbr || "—"}</span>
                  <span className="chance">{pct(pAway)}</span>
                </div>
                <div className="vs-mark">VS</div>
                <div className="team home">
                  <span className="role">Home</span>
                  <span className="abbr">{g.home_abbr || "—"}</span>
                  <span className="chance">{pct(pHome)}</span>
                </div>
              </div>

              <div className="tug" aria-hidden>
                <div className="away-fill" style={{ width: `${pAway * 100}%` }} />
                <div className="home-fill" style={{ width: `${pHome * 100}%` }} />
              </div>

              <div className="match-stats">
                <div>
                  <div className="stat-label">Margin μ</div>
                  <div className="stat-value">
                    {g.mu >= 0 ? "+" : ""}
                    {g.mu.toFixed(1)}
                  </div>
                </div>
                <div>
                  <div className="stat-label">Sigma</div>
                  <div className="stat-value">{g.sigma.toFixed(1)}</div>
                </div>
              </div>
            </div>

            <div className="match-side">
              <GateBadge bet={Boolean(g.gate?.bet)} />
              <span className="chev">Open →</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
