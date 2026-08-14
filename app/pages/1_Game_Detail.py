"""Single-game prediction — production detail view."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "src"))

from theme import apply_theme, brand_hero, metric_strip, page_config, panel, section_heading
from wnba_edge.models.predict import predict_games

FEATURES = ROOT / "data" / "features" / "pregame_features.parquet"

page_config("Game Detail")
apply_theme()
brand_hero("One matchup. Probabilities, market edge, and model drivers.")

feat = pd.read_parquet(FEATURES)
feat["game_date"] = pd.to_datetime(feat["game_date"], utc=True)
feat = feat.sort_values("game_date", ascending=False)
feat["label"] = (
    feat["game_date"].dt.date.astype(str)
    + " · "
    + feat["away_abbr"].astype(str)
    + " @ "
    + feat["home_abbr"].astype(str)
)

with st.sidebar:
    st.markdown("### Matchup")
    # Prefer upcoming first in the list
    upcoming = feat[~feat["completed"].fillna(False)]
    options = (
        upcoming["label"].tolist() + feat[feat["completed"].fillna(False)]["label"].tolist()
        if not upcoming.empty
        else feat["label"].tolist()
    )
    choice = st.selectbox("Game", options=options)

    st.markdown("### Market inputs")
    home_ml = st.number_input("Home ML (American)", value=-150)
    away_ml = st.number_input("Away ML (American)", value=130)
    use_ml = st.checkbox("Use moneyline for EV / gate", value=True)
    home_spread = st.number_input("Home spread", value=-3.5)
    use_spread = st.checkbox("Compute cover probability", value=True)
    st.caption("Paste live book numbers to compare model vs market.")

row = feat.loc[feat["label"] == choice].iloc[[0]]
cards = predict_games(
    row,
    home_ml=home_ml if use_ml else None,
    away_ml=away_ml if use_ml else None,
    home_spread=home_spread if use_spread else None,
)
card = cards[0]

away = card.get("away_abbr", "AWAY")
home = card.get("home_abbr", "HOME")
gate_bet = bool(card.get("gate", {}).get("bet"))

st.markdown(
    f"""
<div class="section-head">
  <h2 style="font-size:2rem;">{away} <span style="opacity:.45;font-weight:500;">@</span> {home}</h2>
  <span>{str(card.get("game_date", ""))[:10]}</span>
</div>
    """,
    unsafe_allow_html=True,
)

metric_strip(
    [
        ("P(Home Win)", f"{card['p_home_win_cal']:.1%}", "Calibrated"),
        ("Projected Margin", f"{card['mu']:+.1f}", "Home − away"),
        ("Sigma", f"{card['sigma']:.1f}", "Uncertainty (pts)"),
        ("Gate", "BET" if gate_bet else "PASS", ", ".join(card.get("gate", {}).get("reasons", []))[:48]),
    ]
)

col_a, col_b = st.columns(2)

with col_a:
    if card.get("market"):
        m = card["market"]
        panel(
            "Market comparison",
            f"""
            <ul>
              <li><strong>No-vig home:</strong> {m['no_vig_home']:.1%}</li>
              <li><strong>Model home:</strong> {card['p_home_win_cal']:.1%}</li>
              <li><strong>Edge:</strong> {m['edge_home']:+.1%}</li>
              <li><strong>EV:</strong> {m['ev_home']:+.3f}</li>
              <li><strong>Kelly fraction:</strong> {m['kelly']:.3f}</li>
            </ul>
            """,
        )
    else:
        panel(
            "Market comparison",
            "<p>Enable moneyline inputs in the sidebar to compute no-vig probability, edge, and EV.</p>",
        )

with col_b:
    if "p_home_cover" in card:
        panel(
            "Spread cover",
            f"""
            <ul>
              <li><strong>Home spread:</strong> {card['home_spread']}</li>
              <li><strong>P(home covers):</strong> {card['p_home_cover']:.1%}</li>
              <li><strong>EV @ -110:</strong> {card.get('spread_ev', 0):+.3f}</li>
            </ul>
            """,
        )
    else:
        panel(
            "Spread cover",
            "<p>Enable spread input to derive cover probability from the shared margin distribution.</p>",
        )

section_heading("Why this projection", "SHAP drivers")
shap = card.get("shap") or []
if shap:
    shap_df = pd.DataFrame(shap).rename(
        columns={"feature": "Feature", "shap_value": "Impact", "value": "Value"}
    )
    st.dataframe(shap_df, use_container_width=True, hide_index=True)
else:
    st.caption("SHAP unavailable for this row.")
