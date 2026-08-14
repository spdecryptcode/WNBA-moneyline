# Architecture

WNBA Edge predicts pregame **win probability**, **point margin**, and **spread-cover probability** from a shared margin-distribution model.

## Pipeline

```text
SportsDataverse parquet ──► raw/ ──► cleaning/QA ──► curated/
                                              │
                                              ▼
                                         features/ (as-of, leakage-safe)
                                              │
                                              ▼
                              LightGBM margin (mu) + residual sigma
                                              │
                                              ▼
                         Student-t ──► P(win), P(cover) ──► isotonic calibration
                                              │
                                              ▼
                         odds math (vig/EV/edge) ──► Streamlit + predictions/*.json
```

## Design choices

| Choice | Why |
|---|---|
| Shared margin model | Avoids contradictory ML vs spread outputs |
| Walk-forward by season | Time-aware validation; no random leakage |
| Closing odds never a feature | Prevents inflated backtests |
| Free data only | SportsDataverse + Odds API free tier |
| React + FastAPI UI | Production slate / game detail / backtest / DQ |

## Modules (`src/wnba_edge/`)

| Package | Role |
|---|---|
| `ingest/` | Download SportsDataverse season files; odds snapshots |
| `cleaning/` | Integrity checks, quarantine, curated tables, DQ report |
| `ratings/` | Chronological Elo (pregame only) |
| `features/` | Rest, efficiency, form, availability proxies |
| `models/` | Train, distribute probs, calibrate, predict |
| `odds/` | American odds, vig removal, EV, Kelly, snapshots |
| `explain/` | SHAP drivers for prediction cards |
| `api/` | FastAPI JSON for the React frontend |
| `backtest/` / `monitoring/` | Evaluation / drift hooks (expand over time) |

## Artifacts

| Path | Contents |
|---|---|
| `artifacts/margin_lgbm.joblib` | Trained LightGBM margin model |
| `artifacts/calibrator_isotonic.joblib` | Probability calibrator |
| `artifacts/model_meta.json` | Features, sigma, fold metrics |
| `artifacts/oof_predictions.parquet` | Out-of-fold predictions |
| `artifacts/hyperparam_trials.csv` | Search trial log |
| `predictions/YYYY-MM-DD.json` | Daily prediction cards |

## Config

- `configs/model.yaml` — seasons, LightGBM, search, distribution
- `configs/features.yaml` — Elo / rolling / feature list
- `configs/betting.yaml` — edge gates, Odds API settings
