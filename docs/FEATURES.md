# Feature Reference

Pregame features are built in `wnba_edge.features.build` and listed in `configs/features.yaml`.

## Team strength

| Feature | Description |
|---|---|
| `home_elo` / `away_elo` | Chronological Elo before tipoff |
| `elo_diff` | `home_elo - away_elo` |
| `home_off_eff_roll` / `away_off_eff_roll` | Rolling offensive efficiency (pts/100 poss proxy) |
| `home_def_eff_roll` / `away_def_eff_roll` | Rolling defensive efficiency |
| `form_diff` | Recent margin form home − away |

## Schedule / context

| Feature | Description |
|---|---|
| `home_rest_days` / `away_rest_days` | Days since last played (default 7 if unknown) |
| `rest_diff` | Home rest − away rest |
| `home_b2b` / `away_b2b` | 1 if rest ≤ 1 day |
| `season_game_num` | Home team's game number in season |

## Availability (proxy)

| Feature | Description |
|---|---|
| `home_avail_proxy` / `away_avail_proxy` | Rough share of top usage players active recently |

No timestamped injury feed yet — treat availability as uncertain.

## Targets (not features)

| Column | Description |
|---|---|
| `margin` | `home_score - away_score` (training target) |
| `home_win` | 1 if home won |
| `completed` | Whether final score exists |
