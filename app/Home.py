"""WNBA Edge — production slate overview."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from theme import apply_theme, brand_hero, match_board, metric_strip, page_config, section_heading

FEATURES = ROOT / "data" / "features" / "pregame_features.parquet"
ARTIFACTS = ROOT / "artifacts"
PREDICTIONS = ROOT / "predictions"

page_config("Slate")
apply_theme()
brand_hero("Tonight’s board — calibrated win probabilities and projected margins.")

if not (ARTIFACTS / "margin_lgbm.joblib").exists():
    st.warning("Model artifacts not found. Run ingest → clean → features → train first.")
    st.stop()

feat = pd.read_parquet(FEATURES) if FEATURES.exists() else pd.DataFrame()
if feat.empty:
    st.warning("No pregame features found.")
    st.stop()

feat["game_date"] = pd.to_datetime(feat["game_date"], utc=True)
feat["slate_date"] = feat["game_date"].dt.date

with st.sidebar:
    st.markdown("### Filters")
    show_completed = st.checkbox("Include completed games", value=False)
    st.caption("Upcoming games use schedule rows scored with as-of team strength.")

visible = feat if show_completed else feat[~feat["completed"].fillna(False)]
if visible.empty:
    st.info(
        "No upcoming games in the feature table yet. "
        "Enable **Include completed games** to browse historical slates."
    )
    st.stop()

dates = sorted(visible["slate_date"].unique(), reverse=True)
with st.sidebar:
    date = st.selectbox(
        "Slate date",
        options=dates,
        index=0,
        format_func=lambda d: d.isoformat(),
    )

day = visible[visible["slate_date"] == date].copy()
if day.empty:
    st.info("No games for this date with the current filters.")
    st.stop()

pred_path = PREDICTIONS / f"{date}.json"
from wnba_edge.models.predict import predict_games

need_score = True
cards: list = []
if pred_path.exists():
    try:
        loaded = json.loads(pred_path.read_text())
        wanted = set(day["game_id"].tolist())
        cards = [c for c in loaded if c.get("game_id") in wanted]
        need_score = len(cards) != len(day)
    except Exception:
        need_score = True

if need_score:
    with st.spinner("Scoring slate..."):
        cards = predict_games(day, as_of_date=str(date))

n_bet = sum(1 for c in cards if c.get("gate", {}).get("bet"))
avg_p = sum(float(c.get("p_home_win_cal", 0)) for c in cards) / max(len(cards), 1)

metric_strip(
    [
        ("Games", str(len(cards)), date.isoformat()),
        ("Avg P(Home)", f"{avg_p:.0%}", "Calibrated model"),
        ("Bet signals", str(n_bet), "Needs market lines"),
        ("Status", "Live board", "As-of tipoff features"),
    ]
)

section_heading("Matchups", "Open Game Detail for SHAP + EV")

board_rows = []
completed_map = dict(zip(day["game_id"], day["completed"].fillna(False)))
for c in cards:
    board_rows.append(
        {
            "away": c.get("away_abbr") or "—",
            "home": c.get("home_abbr") or "—",
            "meta": "Final" if completed_map.get(c.get("game_id")) else "Upcoming",
            "p_home": f"{float(c.get('p_home_win_cal', 0)):.1%}",
            "margin": f"{float(c.get('mu', 0)):+.1f}",
            "sigma": f"{float(c.get('sigma', 0)):.1f}",
            "bet": bool(c.get("gate", {}).get("bet")),
        }
    )

if board_rows:
    match_board(board_rows)
else:
    st.info("No scored games on this slate.")

st.markdown(
    '<p class="footnote">PASS is expected until sportsbook lines are entered on Game Detail '
    "or live odds are joined automatically.</p>",
    unsafe_allow_html=True,
)
