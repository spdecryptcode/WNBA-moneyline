# Usage Guide

## One-time setup

```bash
cd ~/wnba-edge
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Optional: paste ODDS_API_KEY from https://the-odds-api.com/
```

## Refresh data and score games

```bash
source .venv/bin/activate
wnba-ingest          # download/update SportsDataverse files
wnba-clean           # curated tables + reports/dq/
wnba-features        # as-of pregame features (includes upcoming schedule)
wnba-train --trials 60   # only when you want to retrain
wnba-predict --date 2026-08-11
```

Upcoming games come from the schedule (completed=false). Historical box scores train the model; schedule rows are for live slates.

## Streamlit UI

```bash
streamlit run app/Home.py
```

Open **http://127.0.0.1:8501** (prefer `127.0.0.1` over `localhost` in Safari).

| Page | What it does |
|---|---|
| **Home** | Pick slate date → table of P(Home Win), projected margin, Bet/Pass |
| **Game Detail** | One game: probs, optional market inputs, SHAP drivers |
| **Backtest** | Walk-forward fold metrics + calibration chart |
| **Data Quality** | Latest DQ pass/fail report |

### Same as CLI `wnba-predict --date YYYY-MM-DD`

1. Home → **Slate date** = that day  
2. Leave **Include completed games** unchecked for future games  
3. Read **P(Home Win)** / **Projected Margin**

### Optional market inputs (Game Detail)

Enter sportsbook American odds / spread to compute no-vig probability, edge, EV, and Bet/Pass. Without them, the model still shows probabilities.

## Odds snapshots (free tier)

```bash
wnba-odds-snapshot
```

Writes under `data/raw/odds_snapshots/`. Quota-safe; use sparingly on the free plan.

## Tests

```bash
pytest -q
```
