# WNBA Edge

Independent WNBA moneyline / spread probability system:

- SportsDataverse historical stats (free)
- Senior-DS cleaning + DQ reports
- Shared margin-distribution model (LightGBM)
- Calibration, odds/EV math, React production UI (+ Streamlit legacy)

## Docs

| Doc | Description |
|---|---|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/USAGE.md](docs/USAGE.md) | CLI + UI how-to |
| [docs/DATA.md](docs/DATA.md) | Data sources and layout |
| [docs/FEATURES.md](docs/FEATURES.md) | Feature reference |
| [docs/METRICS.md](docs/METRICS.md) | Evaluation metrics |
| [docs/BETTING.md](docs/BETTING.md) | Odds, EV, bet gates |
| [docs/NBA_ROADMAP.md](docs/NBA_ROADMAP.md) | NBA expansion plan |
| [data/curated/data_dictionary.md](data/curated/data_dictionary.md) | Curated table schema |
| [reports/dq/latest.md](reports/dq/latest.md) | Latest data-quality report |

## Setup

```bash
cd ~/wnba-edge
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # optional: add ODDS_API_KEY for live odds
```

## Pipeline

```bash
wnba-ingest
wnba-clean
wnba-features
wnba-train --trials 60
wnba-predict --date 2026-08-11
```

Odds snapshots (free tier; optional):

```bash
wnba-odds-snapshot
```

## UI (primary)

React product site + FastAPI:

```bash
# terminal 1 — API
wnba-api

# terminal 2 — web
cd web && npm install && npm run dev
```

Open **http://127.0.0.1:5173**

- **Slate** — match board with calibrated P(Home), margin, sigma, BET/PASS  
- **Game Detail** — market inputs, EV/edge/Kelly, SHAP drivers  
- **Backtest** / **Data Quality** — walk-forward metrics and DQ  

Legacy Streamlit (optional): `streamlit run app/Home.py` → http://127.0.0.1:8501

## Notes

- No paid data. Model evaluation (log loss / Brier / MAE) works on all seasons.
- ROI / CLV only after free-tier odds history accumulates.
