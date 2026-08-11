# Evaluation Metrics

Model skill and betting results are tracked separately.

## Model skill (no odds required)

| Metric | Meaning | Good direction |
|---|---|---|
| **Log loss** | Probability quality for home win | Lower |
| **Brier score** | Mean squared error of probabilities | Lower |
| **MAE** | Mean absolute error of projected margin (points) | Lower |
| **Calibration / reliability** | When model says 60%, does home win ~60%? | Closer to diagonal |

Current production is evaluated with **walk-forward** seasons 2023–2026 (train only on earlier seasons).

Hyperparameter search uses inner folds **2020–2022** so final test seasons stay cleaner. Production may still prefer params that transferred best to 2023–2026 (documented in `artifacts/model_meta.json`).

## Betting metrics (need odds history)

| Metric | Meaning |
|---|---|
| **Edge** | `model_p − no_vig_market_p` |
| **EV** | Expected value per 1u stake at offered American odds |
| **CLV** | Closing line value — did we beat the close? |
| **ROI** | Realized profit / amount risked |

These are only meaningful with timestamps of the price you could have bet. We build that from free Odds API snapshots going forward — not from paid archives.

## How to read UI fields

- **P(Home Win)** — calibrated probability home wins  
- **Projected Margin** — expected `home_score − away_score`  
- **Sigma** — residual uncertainty (points); wider → less confident  
- **Bet / PASS** — gate vs configured min edge + uncertainty (needs market inputs or wired odds)
