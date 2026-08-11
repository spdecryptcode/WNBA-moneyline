"""Single-game prediction card."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from wnba_edge.models.predict import predict_games

FEATURES = ROOT / "data" / "features" / "pregame_features.parquet"

st.set_page_config(page_title="Game Detail", layout="wide")
st.title("Game Detail")

feat = pd.read_parquet(FEATURES)
feat["game_date"] = pd.to_datetime(feat["game_date"], utc=True)
feat["label"] = (
    feat["game_date"].dt.date.astype(str)
    + " | "
    + feat["away_abbr"].astype(str)
    + " @ "
    + feat["home_abbr"].astype(str)
)

choice = st.selectbox("Game", options=feat["label"].tolist())
row = feat.loc[feat["label"] == choice].iloc[[0]]

st.sidebar.header("Optional market inputs")
home_ml = st.sidebar.number_input("Home ML (American)", value=-150)
away_ml = st.sidebar.number_input("Away ML (American)", value=130)
use_ml = st.sidebar.checkbox("Use moneyline for EV/gate", value=True)
home_spread = st.sidebar.number_input("Home spread", value=-3.5)
use_spread = st.sidebar.checkbox("Compute cover probability", value=True)

cards = predict_games(
    row,
    home_ml=home_ml if use_ml else None,
    away_ml=away_ml if use_ml else None,
    home_spread=home_spread if use_spread else None,
)
card = cards[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("P(Home Win)", f"{card['p_home_win_cal']:.1%}")
c2.metric("Projected Margin", f"{card['mu']:+.1f}")
c3.metric("Sigma", f"{card['sigma']:.1f}")
c4.metric("Gate", "BET" if card["gate"].get("bet") else "PASS")

st.write("**Gate reasons:**", ", ".join(card["gate"].get("reasons", [])))

if card.get("market"):
    st.subheader("Market comparison")
    m = card["market"]
    st.write(
        {
            "No-vig home": round(m["no_vig_home"], 3),
            "Model home": round(card["p_home_win_cal"], 3),
            "Edge": round(m["edge_home"], 3),
            "EV": round(m["ev_home"], 3),
            "Kelly frac": round(m["kelly"], 3),
        }
    )

if "p_home_cover" in card:
    st.subheader("Spread")
    st.write(
        {
            "Home spread": card["home_spread"],
            "P(home covers)": round(card["p_home_cover"], 3),
            "EV @ -110": round(card.get("spread_ev", 0), 3),
        }
    )

st.subheader("Top SHAP drivers (margin model)")
shap = card.get("shap") or []
if shap:
    st.dataframe(pd.DataFrame(shap), use_container_width=True, hide_index=True)
else:
    st.caption("SHAP unavailable for this row.")
