# NBA Expansion Roadmap

Reuse the WNBA Edge architecture for NBA after WNBA v1 is trustworthy. Do **not** mix WNBA and NBA rows in one model without a league feature and heavy validation.

## What transfers as-is

- Project layout and CLI pattern
- Cleaning / DQ philosophy (raw → curated → features)
- Margin-distribution framework (mu + sigma → P(win)/P(cover))
- Odds math (implied, no-vig, EV, Kelly, gates)
- Streamlit page structure
- Walk-forward + calibration evaluation pattern

## What must be rebuilt / swapped

| Layer | WNBA today | NBA change |
|---|---|---|
| Ingest | SportsDataverse ESPN WNBA releases | NBA SportsDataverse / `nba_api` / stats.nba.com |
| Team IDs | ESPN WNBA ids | NBA team ids + franchise map |
| Schedule context | WNBA rest/B2B | NBA denser schedule; B2B more important |
| Home advantage | WNBA prior | Re-estimate on NBA data |
| Elo / efficiency | Fit on WNBA | Retrain from scratch on NBA history |
| LightGBM | WNBA hyperparameters | Retune on NBA walk-forward folds |
| Odds | `basketball_wnba` | `basketball_nba` (same Odds API free tier) |

## Suggested phases

### Phase N1 — Data parity
1. Add `ingest/nba_sportsdataverse.py` (or nba_api loader).
2. Reuse cleaning contracts with a `league` column.
3. Produce `games_clean` for NBA 2015+ (or similar modern window).

### Phase N2 — Feature parity
1. Port Elo, rest, efficiency, availability proxies.
2. Add NBA-specific features: altitude (DEN), long road trips, 3-in-4 flags.
3. Leakage tests must pass unchanged in spirit.

### Phase N3 — Model + eval
1. Train separate LightGBM margin model (`artifacts/nba_*.joblib`).
2. Walk-forward by season; report log loss / Brier / MAE separately from WNBA.
3. Calibrate independently (isotonic/beta).

### Phase N4 — Product
1. Streamlit league toggle (WNBA | NBA).
2. Odds snapshot job for `basketball_nba`.
3. Keep prediction cards schema identical so UI stays shared.

## Guardrails

- Never claim cross-league transfer without holdout proof.
- Keep ROI/CLV separate from model-skill metrics.
- Prefer two production artifacts (WNBA + NBA) over one blended model at first.
- Document any shared code behind a `league=` parameter.

## Success criteria for NBA v1

- [ ] Curated NBA tables + DQ report green
- [ ] Walk-forward calibrated P(win) competitive with Elo baseline
- [ ] Streamlit can score an NBA slate
- [ ] Free-tier odds snapshots collecting for NBA
- [ ] README section for NBA commands
