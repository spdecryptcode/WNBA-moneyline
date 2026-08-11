"""Walk-forward metrics view."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "artifacts" / "model_meta.json"
OOF = ROOT / "artifacts" / "oof_predictions.parquet"

st.set_page_config(page_title="Backtest", layout="wide")
st.title("Walk-forward backtest")

if not META.exists():
    st.warning("Train the model first to populate artifacts.")
    st.stop()

meta = json.loads(META.read_text())
folds = pd.DataFrame(meta.get("walk_forward_folds", []))
st.subheader("Fold metrics")
if folds.empty:
    st.info("No fold metrics stored.")
else:
    st.dataframe(folds, use_container_width=True, hide_index=True)

st.subheader("Overall OOF metrics")
st.json(meta.get("oof_metrics", {}))

if OOF.exists():
    oof = pd.read_parquet(OOF)
    st.subheader("Calibration (reliability)")
    oof = oof.copy()
    oof["bucket"] = pd.cut(oof["p_home_win_cal"], bins=10, labels=False)
    cal = (
        oof.groupby("bucket")
        .agg(pred=("p_home_win_cal", "mean"), actual=("home_win", "mean"), n=("home_win", "size"))
        .dropna()
    )
    st.line_chart(cal.set_index("pred")["actual"])
    st.caption("Predicted vs empirical win rate by probability bucket.")
    st.dataframe(cal, use_container_width=True)

st.info(
    "ROI / CLV appear here only after free-tier odds snapshots accumulate. "
    "Model skill metrics above do not require odds."
)
