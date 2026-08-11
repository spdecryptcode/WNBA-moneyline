"""Senior-DS cleaning / QA: raw SportsDataverse -> curated tables."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from wnba_edge.config import model_config
from wnba_edge.ingest.sportsdataverse import load_raw_concat
from wnba_edge.paths import CURATED, REPORTS_DQ, ensure_dirs


@dataclass
class CheckResult:
    name: str
    passed: bool
    n_fail: int = 0
    detail: str = ""


@dataclass
class DQReport:
    generated_at: str
    checks: list[CheckResult] = field(default_factory=list)
    quarantine_counts: dict[str, int] = field(default_factory=dict)
    row_counts: dict[str, int] = field(default_factory=dict)

    def add(self, check: CheckResult) -> None:
        self.checks.append(check)

    @property
    def all_hard_passed(self) -> bool:
        return all(c.passed for c in self.checks if c.name.startswith("hard:"))

    def to_dict(self) -> dict[str, Any]:
        checks = []
        for c in self.checks:
            checks.append(
                {
                    "name": c.name,
                    "passed": bool(c.passed),
                    "n_fail": int(c.n_fail),
                    "detail": c.detail,
                }
            )
        return {
            "generated_at": self.generated_at,
            "all_hard_passed": bool(self.all_hard_passed),
            "checks": checks,
            "quarantine_counts": {k: int(v) for k, v in self.quarantine_counts.items()},
            "row_counts": {k: int(v) for k, v in self.row_counts.items()},
        }


def _normalize_schedule(raw: pd.DataFrame) -> pd.DataFrame:
    src = raw.copy()
    out = pd.DataFrame(index=src.index)

    def pick(*candidates: str) -> pd.Series | None:
        for c in candidates:
            if c in src.columns:
                return src[c]
        return None

    out["game_id"] = pick("game_id", "id")
    out["season"] = pick("season")
    out["season_type"] = pick("season_type", "type_id")
    tip = pick("game_date_time", "start_date", "game_date", "date")
    out["game_date"] = pd.to_datetime(tip, errors="coerce", utc=True)
    out["home_team_id"] = pick("home_team_id", "home_id")
    out["away_team_id"] = pick("away_team_id", "away_id")
    out["home_abbr"] = pick("home_abbreviation", "home_team_abb")
    out["away_abbr"] = pick("away_abbreviation", "away_team_abb")
    out["home_score"] = pick("home_score", "home_team_score")
    out["away_score"] = pick("away_score", "away_team_score")
    out["home_name"] = pick("home_display_name", "home_name", "home_team_name")
    out["away_name"] = pick("away_display_name", "away_name", "away_team_name")
    out["completed"] = pick("status_type_completed", "completed")
    return out


def _build_games_from_team_box(team_box: pd.DataFrame, report: DQReport) -> pd.DataFrame:
    tb = team_box.copy()
    rename = {
        "game_id": "game_id",
        "season": "season",
        "season_type": "season_type",
        "game_date": "game_date",
        "team_id": "team_id",
        "team_abbreviation": "team_abbr",
        "team_name": "team_name",
        "team_location": "team_location",
        "opponent_team_id": "opp_team_id",
        "team_score": "team_score",
        "opponent_team_score": "opp_score",
        "home_away": "home_away",
        "team_home_away": "home_away",
        "team_winner": "winner",
    }
    present = {k: v for k, v in rename.items() if k in tb.columns}
    tb = tb.rename(columns=present)
    # Prefer game_date_time when present
    if "game_date_time" in team_box.columns and "game_date" not in tb.columns:
        tb["game_date"] = team_box["game_date_time"]
    if "game_date" in tb.columns:
        tb["game_date"] = pd.to_datetime(tb["game_date"], errors="coerce", utc=True)

    if "home_away" not in tb.columns and "team_home_away" in team_box.columns:
        tb["home_away"] = team_box["team_home_away"]

    # home_away values vary: 'home'/'away' or 'H'/'A'
    ha = tb["home_away"].astype(str).str.lower()
    tb["is_home"] = ha.isin(["home", "h", "1", "true"])

    home = tb[tb["is_home"]].copy()
    away = tb[~tb["is_home"]].copy()

    games = home.merge(
        away,
        on=["game_id"],
        suffixes=("_home", "_away"),
        how="inner",
    )

    out = pd.DataFrame(
        {
            "game_id": games["game_id"],
            "season": games.get("season_home", games.get("season_away")),
            "season_type": games.get("season_type_home", games.get("season_type_away")),
            "game_date": games.get("game_date_home", games.get("game_date_away")),
            "home_team_id": games["team_id_home"],
            "away_team_id": games["team_id_away"],
            "home_abbr": games.get("team_abbr_home"),
            "away_abbr": games.get("team_abbr_away"),
            "home_name": games.get("team_name_home"),
            "away_name": games.get("team_name_away"),
            "home_score": pd.to_numeric(games.get("team_score_home"), errors="coerce"),
            "away_score": pd.to_numeric(games.get("team_score_away"), errors="coerce"),
        }
    )
    out = out.drop_duplicates(subset=["game_id"])
    out["margin"] = out["home_score"] - out["away_score"]
    out["home_win"] = (out["margin"] > 0).astype(int)
    out["completed"] = out["home_score"].notna() & out["away_score"].notna()

    n_orphan = len(tb["game_id"].unique()) - len(out)
    report.add(
        CheckResult(
            "soft:team_box_pair_coverage",
            n_orphan == 0,
            n_fail=max(n_orphan, 0),
            detail=f"games without home+away pair: {max(n_orphan, 0)}",
        )
    )
    return out


def _clean_team_box(team_box: pd.DataFrame, valid_game_ids: set) -> tuple[pd.DataFrame, pd.DataFrame]:
    tb = team_box.copy()
    rename = {
        "game_id": "game_id",
        "season": "season",
        "season_type": "season_type",
        "game_date": "game_date",
        "team_id": "team_id",
        "team_abbreviation": "team_abbr",
        "opponent_team_id": "opp_team_id",
        "team_score": "team_score",
        "opponent_team_score": "opp_score",
        "home_away": "home_away",
        "team_home_away": "home_away",
        "field_goals_made": "fgm",
        "field_goals_attempted": "fga",
        "three_point_field_goals_made": "fg3m",
        "three_point_field_goals_attempted": "fg3a",
        "free_throws_made": "ftm",
        "free_throws_attempted": "fta",
        "offensive_rebounds": "oreb",
        "defensive_rebounds": "dreb",
        "rebounds": "reb",
        "assists": "ast",
        "turnovers": "tov",
        "steals": "stl",
        "blocks": "blk",
        "team_turnovers": "team_tov",
    }
    present = {k: v for k, v in rename.items() if k in tb.columns}
    tb = tb.rename(columns=present)
    if "game_date_time" in team_box.columns:
        tb["game_date"] = pd.to_datetime(
            team_box["game_date_time"], errors="coerce", utc=True
        )
    elif "game_date" in tb.columns:
        tb["game_date"] = pd.to_datetime(tb["game_date"], errors="coerce", utc=True)

    if "home_away" not in tb.columns:
        raise KeyError("team box missing home/away column")
    ha = tb["home_away"].astype(str).str.lower()
    tb["is_home"] = ha.isin(["home", "h", "1", "true"]).astype(int)

    # Possessions proxy (standard basketball estimate)
    for col in ("fga", "fta", "oreb", "tov"):
        if col not in tb.columns:
            tb[col] = np.nan
    tb["poss_est"] = (
        tb["fga"].fillna(0)
        + 0.44 * tb["fta"].fillna(0)
        - tb["oreb"].fillna(0)
        + tb["tov"].fillna(0)
    )
    tb["off_eff"] = np.where(
        tb["poss_est"] > 0, 100 * tb["team_score"] / tb["poss_est"], np.nan
    )
    tb["def_eff"] = np.where(
        tb["poss_est"] > 0, 100 * tb["opp_score"] / tb["poss_est"], np.nan
    )

    quarantine_mask = ~tb["game_id"].isin(valid_game_ids)
    if "team_score" in tb.columns:
        quarantine_mask |= tb["team_score"].isna() | (tb["team_score"] < 0)
    if "fga" in tb.columns:
        quarantine_mask |= tb["fga"].fillna(0) < 0

    clean = tb.loc[~quarantine_mask].copy()
    quarantine = tb.loc[quarantine_mask].copy()
    return clean, quarantine


def _clean_player_box(player_box: pd.DataFrame, valid_game_ids: set) -> tuple[pd.DataFrame, pd.DataFrame]:
    pb = player_box.copy()
    rename = {
        "game_id": "game_id",
        "season": "season",
        "season_type": "season_type",
        "game_date": "game_date",
        "athlete_id": "player_id",
        "athlete_display_name": "player_name",
        "team_id": "team_id",
        "minutes": "minutes",
        "points": "pts",
        "rebounds": "reb",
        "assists": "ast",
        "starter": "starter",
        "active": "active",
        "did_not_play": "dnp",
    }
    present = {k: v for k, v in rename.items() if k in pb.columns}
    pb = pb.rename(columns=present)
    if "game_date" in pb.columns:
        pb["game_date"] = pd.to_datetime(pb["game_date"], errors="coerce", utc=True)

    if "minutes" in pb.columns:
        # ESPN sometimes stores minutes as "MM:SS" strings
        if pb["minutes"].dtype == object:
            def parse_min(x):
                if pd.isna(x):
                    return np.nan
                if isinstance(x, (int, float)):
                    return float(x)
                s = str(x)
                if ":" in s:
                    try:
                        m, sec = s.split(":")
                        return float(m) + float(sec) / 60.0
                    except ValueError:
                        return np.nan
                try:
                    return float(s)
                except ValueError:
                    return np.nan

            pb["minutes"] = pb["minutes"].map(parse_min)
        pb["minutes"] = pd.to_numeric(pb["minutes"], errors="coerce")

    quarantine_mask = ~pb["game_id"].isin(valid_game_ids)
    if "minutes" in pb.columns:
        quarantine_mask |= pb["minutes"].fillna(0) > 60
        quarantine_mask |= pb["minutes"].fillna(0) < 0

    clean = pb.loc[~quarantine_mask].copy()
    quarantine = pb.loc[quarantine_mask].copy()
    return clean, quarantine


def _upcoming_games_from_schedule(
    sched: pd.DataFrame, existing_ids: set
) -> pd.DataFrame:
    """Build unplayed game rows from schedule (completed=False)."""
    if sched.empty:
        return pd.DataFrame()

    s = sched.copy()
    s = s[s["game_id"].notna()].copy()
    s["game_id"] = pd.to_numeric(s["game_id"], errors="coerce")
    s = s[s["game_id"].notna()]
    s["game_id"] = s["game_id"].astype("int64")
    # Keep games not already present from box scores
    s = s[~s["game_id"].isin(existing_ids)]

    if "completed" in s.columns:
        # include explicit incomplete + null completed
        done = s["completed"].fillna(False)
        if done.dtype == object:
            done = done.astype(str).str.lower().isin(["true", "1", "yes"])
        s = s[~done.astype(bool)]

    # Drop stale schedule leftovers; keep only near-term / future tipoffs
    if "game_date" in s.columns:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=1)
        s = s[pd.to_datetime(s["game_date"], utc=True) >= cutoff]

    if s.empty:
        return pd.DataFrame()

    out = pd.DataFrame(
        {
            "game_id": s["game_id"],
            "season": s.get("season"),
            "season_type": s.get("season_type"),
            "game_date": s.get("game_date"),
            "tipoff_ts": s.get("game_date"),
            "home_team_id": s.get("home_team_id"),
            "away_team_id": s.get("away_team_id"),
            "home_abbr": s.get("home_abbr"),
            "away_abbr": s.get("away_abbr"),
            "home_name": s.get("home_name"),
            "away_name": s.get("away_name"),
            "home_score": pd.NA,
            "away_score": pd.NA,
            "margin": pd.NA,
            "home_win": pd.NA,
            "completed": False,
        }
    )
    out = out.dropna(subset=["home_team_id", "away_team_id", "game_date"])
    return out.drop_duplicates(subset=["game_id"])


def run_cleaning(
    seasons: list[int] | None = None,
    *,
    regular_season_only: bool = True,
) -> DQReport:
    ensure_dirs()
    cfg = model_config()
    seasons = seasons or list(cfg["seasons_model"])
    report = DQReport(generated_at=datetime.now(timezone.utc).isoformat())

    team_box_raw = load_raw_concat("team_box", seasons)
    player_box_raw = load_raw_concat("player_box", seasons)
    schedule_raw = load_raw_concat("schedules", seasons)

    report.row_counts["raw_team_box"] = len(team_box_raw)
    report.row_counts["raw_player_box"] = len(player_box_raw)
    report.row_counts["raw_schedules"] = len(schedule_raw)

    report.add(
        CheckResult(
            "hard:raw_team_box_present",
            len(team_box_raw) > 0,
            detail=f"rows={len(team_box_raw)}",
        )
    )
    if team_box_raw.empty:
        _write_report(report)
        return report

    games = _build_games_from_team_box(team_box_raw, report)

    if regular_season_only and "season_type" in games.columns:
        # ESPN season_type: 2 = regular season (common in sportsdataverse)
        allowed = set(cfg.get("season_types", [2]))
        games = games[games["season_type"].isin(allowed) | games["season_type"].isna()]

    # Hard integrity
    bad_scores = games["completed"] & (
        (games["home_score"] < 0)
        | (games["away_score"] < 0)
        | games["home_score"].isna()
        | games["away_score"].isna()
    )
    report.add(
        CheckResult(
            "hard:non_negative_scores",
            int(bad_scores.sum()) == 0,
            n_fail=int(bad_scores.sum()),
        )
    )
    games = games.loc[~bad_scores].copy()

    dupes = games["game_id"].duplicated().sum()
    report.add(CheckResult("hard:unique_game_id", dupes == 0, n_fail=int(dupes)))
    games = games.drop_duplicates(subset=["game_id"])

    missing_teams = games["home_team_id"].isna().sum() + games["away_team_id"].isna().sum()
    report.add(
        CheckResult("hard:team_ids_present", missing_teams == 0, n_fail=int(missing_teams))
    )
    games = games.dropna(subset=["home_team_id", "away_team_id"])

    # Margin sanity
    extreme = games["completed"] & (games["margin"].abs() > 80)
    report.add(
        CheckResult(
            "soft:extreme_margins",
            int(extreme.sum()) == 0,
            n_fail=int(extreme.sum()),
            detail="margins > 80 pts quarantined",
        )
    )
    games = games.loc[~extreme].copy()

    valid_ids = set(games["game_id"].tolist())
    team_clean, team_q = _clean_team_box(team_box_raw, valid_ids)
    player_clean, player_q = _clean_player_box(player_box_raw, valid_ids)

    if not schedule_raw.empty:
        sched = _normalize_schedule(schedule_raw)
        # Prefer tipoff from schedule when available
        if "game_id" in sched.columns and "game_date" in sched.columns:
            tip = sched[["game_id", "game_date"]].drop_duplicates("game_id")
            tip = tip.rename(columns={"game_date": "tipoff_ts"})
            games = games.merge(tip, on="game_id", how="left")
            games["game_date"] = games["tipoff_ts"].fillna(games["game_date"])

        # Add future / not-yet-played games from schedule (needed for live predictions)
        upcoming = _upcoming_games_from_schedule(sched, set(games["game_id"].tolist()))
        if regular_season_only and not upcoming.empty:
            # SportsDataverse schedule type_id=1 is STD; map to model season_type=2
            upcoming["season_type"] = upcoming["season_type"].fillna(2)
            upcoming.loc[upcoming["season_type"] == 1, "season_type"] = 2
            allowed = set(cfg.get("season_types", [2]))
            upcoming = upcoming[
                upcoming["season_type"].isin(allowed) | upcoming["season_type"].isna()
            ]
        if not upcoming.empty:
            games = pd.concat([games, upcoming], ignore_index=True, sort=False)
            report.add(
                CheckResult(
                    "soft:upcoming_schedule_games",
                    True,
                    detail=f"added {len(upcoming)} scheduled future/unplayed games",
                )
            )
            report.row_counts["upcoming_games"] = int(len(upcoming))

    if "tipoff_ts" not in games.columns:
        games["tipoff_ts"] = games["game_date"]
    games["tipoff_ts"] = games["tipoff_ts"].fillna(games["game_date"])

    games = games.sort_values(["game_date", "game_id"]).reset_index(drop=True)

    # Dimensions
    teams = pd.concat(
        [
            games[["home_team_id", "home_abbr", "home_name"]].rename(
                columns={
                    "home_team_id": "team_id",
                    "home_abbr": "abbr",
                    "home_name": "name",
                }
            ),
            games[["away_team_id", "away_abbr", "away_name"]].rename(
                columns={
                    "away_team_id": "team_id",
                    "away_abbr": "abbr",
                    "away_name": "name",
                }
            ),
        ],
        ignore_index=True,
    ).drop_duplicates("team_id")

    report.quarantine_counts = {
        "team_box": len(team_q),
        "player_box": len(player_q),
    }
    report.row_counts.update(
        {
            "games_clean": len(games),
            "team_games_clean": len(team_clean),
            "player_games_clean": len(player_clean),
            "team_dim": len(teams),
        }
    )
    report.add(
        CheckResult(
            "hard:min_games_for_modeling",
            len(games) >= 200,
            n_fail=0 if len(games) >= 200 else 1,
            detail=f"games_clean={len(games)}",
        )
    )

    games.to_parquet(CURATED / "games_clean.parquet", index=False)
    team_clean.to_parquet(CURATED / "team_games_clean.parquet", index=False)
    player_clean.to_parquet(CURATED / "player_games_clean.parquet", index=False)
    teams.to_parquet(CURATED / "team_dim.parquet", index=False)
    if len(team_q):
        team_q.to_parquet(CURATED / "team_box_quarantine.parquet", index=False)
    if len(player_q):
        player_q.to_parquet(CURATED / "player_box_quarantine.parquet", index=False)

    dict_path = CURATED / "data_dictionary.md"
    dict_path.write_text(
        """# WNBA Edge Data Dictionary

## games_clean
- `game_id`: ESPN game id
- `season`, `season_type`: season identifiers (type 2 = regular season)
- `game_date` / `tipoff_ts`: tipoff timestamp (UTC when available)
- `home_team_id`, `away_team_id`: team ids
- `home_score`, `away_score`, `margin`, `home_win`: final result fields
- `completed`: both scores present

## team_games_clean
One row per team per game with box stats and efficiency proxies (`poss_est`, `off_eff`, `def_eff`).

## player_games_clean
One row per player per game; `minutes` normalized to float minutes.

## Exclusion / quarantine rules
- Non-paired home/away team-box rows
- Negative scores, extreme margins (>80)
- Player minutes outside [0, 60]
- Rows whose `game_id` is not in curated games
"""
    )

    _write_report(report)
    return report


def _write_report(report: DQReport) -> None:
    REPORTS_DQ.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DQ / "latest.json"
    path.write_text(json.dumps(report.to_dict(), indent=2))
    # human summary
    lines = [
        f"# DQ Report ({report.generated_at})",
        "",
        f"**Hard checks passed:** {report.all_hard_passed}",
        "",
        "## Checks",
    ]
    for c in report.checks:
        status = "PASS" if c.passed else "FAIL"
        lines.append(f"- [{status}] `{c.name}` fail={c.n_fail} {c.detail}")
    lines += ["", "## Row counts"]
    for k, v in report.row_counts.items():
        lines.append(f"- {k}: {v}")
    (REPORTS_DQ / "latest.md").write_text("\n".join(lines) + "\n")
