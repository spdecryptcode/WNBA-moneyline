# WNBA Edge Data Dictionary

Generated/maintained with the cleaning pipeline. See also [docs/DATA.md](../../docs/DATA.md).

## games_clean

| Column | Type | Description |
|---|---|---|
| `game_id` | int | ESPN game id |
| `season` | int | Season year |
| `season_type` | int | `2` = regular season (schedule STD mapped to 2) |
| `game_date` | datetime | Tipoff (UTC when available) |
| `tipoff_ts` | datetime | Preferred tipoff timestamp |
| `home_team_id` / `away_team_id` | int | Team ids |
| `home_abbr` / `away_abbr` | str | Team abbreviations |
| `home_name` / `away_name` | str | Team names |
| `home_score` / `away_score` | float | Final scores (null if upcoming) |
| `margin` | float | `home_score - away_score` |
| `home_win` | int | 1 if home won |
| `completed` | bool | True if final scores present |

## team_games_clean

One row per team per completed game.

| Column | Description |
|---|---|
| `game_id`, `team_id`, `game_date` | Keys |
| `is_home` | 1 if home |
| `team_score` / `opp_score` | Points |
| Box stats | FGM/FGA, 3s, FT, rebounds, AST, TOV, etc. when present |
| `poss_est` | Possessions proxy: `FGA + 0.44*FTA - OREB + TOV` |
| `off_eff` / `def_eff` | Points per 100 possessions proxies |

## player_games_clean

One row per player per game.

| Column | Description |
|---|---|
| `player_id`, `player_name` | Player identity |
| `team_id`, `game_id` | Keys |
| `minutes` | Float minutes (parses `MM:SS` strings) |
| `pts`, `reb`, `ast`, … | Box line |
| `starter` / `active` / `dnp` | Availability flags when present |

## team_dim

| Column | Description |
|---|---|
| `team_id` | Canonical id |
| `abbr` | Abbreviation |
| `name` | Display name |

Note: includes All-Star / exhibition teams from source data, not only regular franchises.

## Quarantine tables

- `team_box_quarantine.parquet` / `player_box_quarantine.parquet` — rows failing soft/hard rules (negative stats, absurd minutes, orphan game ids, etc.)

## Exclusion rules

- Non-paired home/away team-box rows for final games table construction  
- Negative scores; extreme margins (>80)  
- Player minutes outside `[0, 60]`  
- Stale unplayed schedule rows older than ~1 day are not added as upcoming  
