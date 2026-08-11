"""As-of pregame feature builder (leakage-safe)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from wnba_edge.config import features_config, model_config
from wnba_edge.paths import CURATED, FEATURES, ensure_dirs
from wnba_edge.ratings.elo import compute_pregame_elo


def _rest_features(games: pd.DataFrame) -> pd.DataFrame:
    g = games.sort_values(["game_date", "game_id"]).copy()
    last_played: dict[int, pd.Timestamp] = {}
    rows = []
    for row in g.itertuples(index=False):
        tip = pd.Timestamp(row.game_date)
        home_id = int(row.home_team_id)
        away_id = int(row.away_team_id)

        def rest_days(tid: int) -> float:
            prev = last_played.get(tid)
            if prev is None:
                return 7.0  # season opener default
            return float((tip.normalize() - prev.normalize()).days)

        home_rest = rest_days(home_id)
        away_rest = rest_days(away_id)
        rows.append(
            {
                "game_id": row.game_id,
                "home_rest_days": home_rest,
                "away_rest_days": away_rest,
                "rest_diff": home_rest - away_rest,
                "home_b2b": int(home_rest <= 1),
                "away_b2b": int(away_rest <= 1),
            }
        )
        # update after using pregame rest
        if bool(getattr(row, "completed", True)):
            last_played[home_id] = tip
            last_played[away_id] = tip
    return pd.DataFrame(rows)


def _team_rolling_efficiency(team_games: pd.DataFrame, window: int) -> pd.DataFrame:
    """Post-game rolling state (includes that game). Pregame use is via asof join."""
    tg = team_games.sort_values(["team_id", "game_date", "game_id"]).copy()
    tg["off_eff_roll"] = (
        tg.groupby("team_id")["off_eff"]
        .transform(lambda s: s.rolling(window, min_periods=1).mean())
    )
    tg["def_eff_roll"] = (
        tg.groupby("team_id")["def_eff"]
        .transform(lambda s: s.rolling(window, min_periods=1).mean())
    )
    tg["team_margin"] = pd.to_numeric(tg["team_score"], errors="coerce") - pd.to_numeric(
        tg["opp_score"], errors="coerce"
    )
    tg["margin_roll"] = (
        tg.groupby("team_id")["team_margin"]
        .transform(lambda s: s.rolling(window, min_periods=1).mean())
    )
    return tg[["game_id", "team_id", "game_date", "off_eff_roll", "def_eff_roll", "margin_roll", "is_home"]]


def _asof_team_rolls(games: pd.DataFrame, roll: pd.DataFrame, *, side: str) -> pd.DataFrame:
    """Attach latest rolling stats for home/away strictly before tipoff (no leakage)."""
    team_col = "home_team_id" if side == "home" else "away_team_id"
    prefix = "home" if side == "home" else "away"

    hist = roll.dropna(subset=["team_id", "game_date"]).copy()
    hist["team_id"] = pd.to_numeric(hist["team_id"], errors="coerce").astype(int)
    hist["game_date"] = pd.to_datetime(hist["game_date"], utc=True)
    hist = hist.sort_values(["game_date", "game_id"], kind="mergesort")

    left = games[["game_id", team_col, "game_date"]].copy()
    left = left.rename(columns={team_col: "team_id"})
    left["team_id"] = pd.to_numeric(left["team_id"], errors="coerce")
    left = left.dropna(subset=["team_id", "game_date"]).copy()
    left["team_id"] = left["team_id"].astype(int)
    left["game_date"] = pd.to_datetime(left["game_date"], utc=True)

    pieces: list[pd.DataFrame] = []
    hist_cols = ["game_date", "off_eff_roll", "def_eff_roll", "margin_roll"]
    for tid, left_grp in left.groupby("team_id", sort=False):
        right_grp = hist.loc[hist["team_id"] == tid, hist_cols]
        lg = left_grp.sort_values(["game_date", "game_id"], kind="mergesort")
        if right_grp.empty:
            tmp = lg.copy()
            tmp["off_eff_roll"] = np.nan
            tmp["def_eff_roll"] = np.nan
            tmp["margin_roll"] = np.nan
        else:
            rg = right_grp.sort_values(["game_date"], kind="mergesort")
            tmp = pd.merge_asof(
                lg,
                rg,
                on="game_date",
                direction="backward",
                allow_exact_matches=False,  # exclude same-game box stats
            )
        pieces.append(tmp)

    merged = pd.concat(pieces, ignore_index=True) if pieces else left.copy()
    return merged.rename(
        columns={
            "off_eff_roll": f"{prefix}_off_eff_roll",
            "def_eff_roll": f"{prefix}_def_eff_roll",
            "margin_roll": f"{prefix}_form",
        }
    )[["game_id", f"{prefix}_off_eff_roll", f"{prefix}_def_eff_roll", f"{prefix}_form"]]


def _availability_proxy(player_games: pd.DataFrame, top_n: int, lookback: int) -> pd.DataFrame:
    if player_games.empty or "minutes" not in player_games.columns:
        return pd.DataFrame(columns=["game_id", "team_id", "avail_proxy"])

    pb = player_games.sort_values(["team_id", "game_date", "game_id"]).copy()
    pb["minutes"] = pd.to_numeric(pb["minutes"], errors="coerce").fillna(0.0)

    # Season-to-date usage share of top N players, then prior-game minutes presence
    rows = []
    for (team_id, season), grp in pb.groupby(["team_id", "season"], sort=False):
        grp = grp.sort_values(["game_date", "game_id"])
        # cumulative minutes by player before each game
        player_cum = {}
        game_ids = grp["game_id"].drop_duplicates().tolist()
        for gid in game_ids:
            game_rows = grp[grp["game_id"] == gid]
            # top N by cumulative minutes so far (pregame)
            usage = sorted(player_cum.items(), key=lambda x: -x[1])[:top_n]
            top_ids = {p for p, _ in usage} if usage else set()
            if not top_ids:
                avail = 1.0
            else:
                # players who played >0 in this team's last lookback games before today
                prior = grp[grp["game_id"] != gid]
                # simpler: fraction of top players with minutes > 0 in this game is leakage.
                # Use prior lookback only:
                recent_games = prior["game_id"].drop_duplicates().tail(lookback)
                recent = prior[prior["game_id"].isin(recent_games)]
                present = 0
                for pid in top_ids:
                    mins = recent.loc[recent["player_id"] == pid, "minutes"].sum()
                    present += int(mins > 0)
                avail = present / max(len(top_ids), 1)

            rows.append({"game_id": gid, "team_id": team_id, "avail_proxy": avail})

            # update cumulative after game
            for r in game_rows.itertuples(index=False):
                pid = getattr(r, "player_id", None)
                if pid is None or pd.isna(pid):
                    continue
                player_cum[int(pid)] = player_cum.get(int(pid), 0.0) + float(r.minutes)

    return pd.DataFrame(rows)


def build_features(*, seasons: list[int] | None = None) -> pd.DataFrame:
    ensure_dirs()
    cfg_f = features_config()
    cfg_m = model_config()
    seasons = seasons or list(cfg_m["seasons_model"])

    games = pd.read_parquet(CURATED / "games_clean.parquet")
    team_games = pd.read_parquet(CURATED / "team_games_clean.parquet")
    player_path = CURATED / "player_games_clean.parquet"
    player_games = pd.read_parquet(player_path) if player_path.exists() else pd.DataFrame()

    games = games[games["season"].isin(seasons)].copy()
    games = games.sort_values(["game_date", "game_id"]).reset_index(drop=True)

    elo = compute_pregame_elo(games)
    rest = _rest_features(games)

    window = int(cfg_f["rolling"]["recent_games"])
    roll = _team_rolling_efficiency(team_games, window)
    # As-of join so upcoming (no box score yet) still get last known team form/efficiency
    home_roll = _asof_team_rolls(games, roll, side="home")
    away_roll = _asof_team_rolls(games, roll, side="away")

    avail = _availability_proxy(
        player_games,
        top_n=int(cfg_f["availability"]["top_n_players"]),
        lookback=int(cfg_f["availability"]["lookback_games"]),
    )
    if avail.empty:
        home_avail = pd.DataFrame({"game_id": games["game_id"], "home_avail_proxy": 1.0})
        away_avail = pd.DataFrame({"game_id": games["game_id"], "away_avail_proxy": 1.0})
    else:
        home_avail = games[["game_id", "home_team_id"]].merge(
            avail, left_on=["game_id", "home_team_id"], right_on=["game_id", "team_id"], how="left"
        ).rename(columns={"avail_proxy": "home_avail_proxy"})[
            ["game_id", "home_avail_proxy"]
        ]
        away_avail = games[["game_id", "away_team_id"]].merge(
            avail, left_on=["game_id", "away_team_id"], right_on=["game_id", "team_id"], how="left"
        ).rename(columns={"avail_proxy": "away_avail_proxy"})[
            ["game_id", "away_avail_proxy"]
        ]

    # season game number (for home team)
    games["season_game_num"] = games.groupby(["season", "home_team_id"]).cumcount() + 1

    feat = (
        games[
            [
                "game_id",
                "season",
                "season_type",
                "game_date",
                "tipoff_ts",
                "home_team_id",
                "away_team_id",
                "home_abbr",
                "away_abbr",
                "home_score",
                "away_score",
                "margin",
                "home_win",
                "completed",
                "season_game_num",
            ]
        ]
        .merge(elo, on="game_id", how="left")
        .merge(rest, on="game_id", how="left")
        .merge(home_roll, on="game_id", how="left")
        .merge(away_roll, on="game_id", how="left")
        .merge(home_avail, on="game_id", how="left")
        .merge(away_avail, on="game_id", how="left")
    )
    feat["form_diff"] = feat["home_form"].fillna(0) - feat["away_form"].fillna(0)
    for col in [
        "home_off_eff_roll",
        "home_def_eff_roll",
        "away_off_eff_roll",
        "away_def_eff_roll",
        "home_avail_proxy",
        "away_avail_proxy",
    ]:
        if col in feat.columns:
            feat[col] = feat[col].fillna(feat[col].median() if feat[col].notna().any() else 0)

    out_path = FEATURES / "pregame_features.parquet"
    feat.to_parquet(out_path, index=False)
    return feat


def feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    cols = features_config()["feature_columns"]
    present = [c for c in cols if c in df.columns]
    X = df[present].astype(float)
    return X, present
