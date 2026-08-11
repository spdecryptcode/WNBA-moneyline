"""WNBA Edge — slate overview."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "data" / "features" / "pregame_features.parquet"
ARTIFACTS = ROOT / "artifacts"
PREDICTIONS = ROOT / "predictions"

st.set_page_config(page_title="WNBA Edge", layout="wide")
st.title("WNBA Edge")
st.caption("Pregame win probabilities, margin projections, and betting gates")

if not (ARTIFACTS / "margin_lgbm.joblib").exists():
    st.warning(
        "Model artifacts not found. Run ingest → clean → features → train first "
        "(see README)."
    )
    st.stop()

feat = pd.read_parquet(FEATURES) if FEATURES.exists() else pd.DataFrame()
if feat.empty:
    st.warning("No pregame features found.")
    st.stop()

feat["game_date"] = pd.to_datetime(feat["game_date"], utc=True)
feat["slate_date"] = feat["game_date"].dt.date

show_completed = st.sidebar.checkbox("Include completed games", value=False)

visible = feat if show_completed else feat[~feat["completed"].fillna(False)]
if visible.empty:
    st.info(
        "No upcoming (uncompleted) games in the feature table yet. "
        "Enable **Include completed games** to browse historical slates."
    )
    st.stop()

dates = sorted(visible["slate_date"].unique(), reverse=True)
date = st.sidebar.selectbox(
    "Slate date",
    options=dates,
    index=0,
    format_func=lambda d: d.isoformat(),
)

day = visible[visible["slate_date"] == date].copy()
if day.empty:
    st.info("No games for this date (with current filters).")
    st.stop()

pred_path = PREDICTIONS / f"{date}.json"
sys.path.insert(0, str(ROOT / "src"))
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

rows = []
for c in cards:
    rows.append(
        {
            "Away": c.get("away_abbr"),
            "Home": c.get("home_abbr"),
            "P(Home Win)": round(c.get("p_home_win_cal", 0), 3),
            "Projected Margin": round(c.get("mu", 0), 2),
            "Sigma": round(c.get("sigma", 0), 2),
            "Bet": "YES" if c.get("gate", {}).get("bet") else "PASS",
            "game_id": c.get("game_id"),
        }
    )

table = pd.DataFrame(rows)
st.subheader(f"Slate — {date}")
st.dataframe(table.drop(columns=["game_id"]), use_container_width=True, hide_index=True)

st.markdown("Open **Game Detail** in the sidebar to inspect a single matchup.")
if not table.empty and table["Bet"].eq("PASS").all():
    st.caption(
        "All games show PASS until you enter market lines on Game Detail "
        "(or live odds are auto-joined)."
    )
