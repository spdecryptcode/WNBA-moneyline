# Data Guide

## Sources (free only)

| Source | Use |
|---|---|
| [SportsDataverse releases](https://github.com/sportsdataverse/sportsdataverse-data) | Schedules, team box, player box (ESPN) |
| [The Odds API](https://the-odds-api.com/) free tier | Live moneyline / spread snapshots |
| Optional later | stats.wnba.com enrichment via public APIs |

No paid datasets.

## Layout

```text
data/
  raw/           # immutable downloads + checksums (.meta.json)
    schedules/
    team_box/
    player_box/
    odds_snapshots/
  curated/       # cleaned modeling tables
  features/      # as-of pregame feature matrix
```

## Seasons

- **Model / features:** 2018–present (see `configs/model.yaml`)
- **Elo warm-start seasons:** configurable (e.g. 2015–2017) when ingested
- **Regular season:** `season_type` / mapped schedule STD → type `2`

## Upcoming games

`wnba-clean` merges **unplayed schedule rows** (tipoff ≥ yesterday UTC) into `games_clean` with `completed=false`.  
`wnba-features` builds as-of Elo/rest/efficiency for those rows so the UI can score future slates.

## DQ outputs

After `wnba-clean`:

- `reports/dq/latest.json` — machine-readable checks  
- `reports/dq/latest.md` — human summary  
- `data/curated/data_dictionary.md` — field definitions  
- Quarantine tables when rows fail soft/hard rules  

## Leakage rules

- Features for game G use only information available before tipoff  
- Rolling stats exclude the current game (`merge_asof` / chronological Elo updates after the game)  
- Do not join closing odds into training features  

See also unit tests in `tests/test_leakage.py`.
