"""Chronological margin-aware Elo ratings (pregame only)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from wnba_edge.config import features_config


@dataclass
class EloConfig:
    k: float = 20.0
    home_advantage: float = 3.0
    init_rating: float = 1500.0
    scale: float = 400.0


def expected_score(rating_a: float, rating_b: float, scale: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / scale))


def compute_pregame_elo(games: pd.DataFrame, cfg: EloConfig | None = None) -> pd.DataFrame:
    """Return one row per game with pregame Elo for home/away (no leakage)."""
    if cfg is None:
        raw = features_config()["elo"]
        cfg = EloConfig(**raw)

    g = games.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    ratings: dict[int, float] = {}

    rows = []
    for row in g.itertuples(index=False):
        home_id = int(row.home_team_id)
        away_id = int(row.away_team_id)
        home_elo = ratings.get(home_id, cfg.init_rating)
        away_elo = ratings.get(away_id, cfg.init_rating)

        rows.append(
            {
                "game_id": row.game_id,
                "home_elo": home_elo,
                "away_elo": away_elo,
                "elo_diff": home_elo - away_elo,
            }
        )

        if not bool(getattr(row, "completed", True)):
            continue
        if pd.isna(row.home_score) or pd.isna(row.away_score):
            continue

        # Update after game using win/loss + margin factor
        exp_home = expected_score(
            home_elo + cfg.home_advantage, away_elo, cfg.scale
        )
        actual = 1.0 if row.home_score > row.away_score else 0.0
        if row.home_score == row.away_score:
            actual = 0.5
        margin = abs(float(row.home_score) - float(row.away_score))
        mov_mult = np.log1p(margin) * (2.2 / ((abs(home_elo - away_elo) * 0.001) + 2.2))
        delta = cfg.k * mov_mult * (actual - exp_home)
        ratings[home_id] = home_elo + delta
        ratings[away_id] = away_elo - delta

    return pd.DataFrame(rows)
