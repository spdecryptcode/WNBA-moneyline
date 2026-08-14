"""Walk-forward metrics — production backtest view."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))

from theme import apply_theme, brand_hero, metric_strip, page_config, panel, section_heading

META = ROOT / "artifacts" / "model_meta.json"
OOF = ROOT / "artifacts" / "oof_predictions.parquet"

page_config("Backtest")
apply_theme()
brand_hero("Walk-forward proof — skill metrics separated from betting PnL.")

if not META.exists():
    st.warning("Train the model first to populate artifacts.")
    st.stop()

meta = json.loads(META.read_text())
oof_metrics = meta.get("oof_metrics", {})

metric_strip(
    [
        ("Log loss", f"{oof_metrics.get('log_loss_cal', float('nan')):.3f}", "Calibrated"),
        ("Brier", f"{oof_metrics.get('brier_cal', float('nan')):.3f}", "Calibrated"),
        ("MAE", f"{oof_metrics.get('mae', float('nan')):.1f}", "Margin points"),
        ("Folds", str(len(meta.get("walk_forward_folds", []))), "Held-out seasons"),
    ]
)

section_heading("Season folds", "Train only on earlier seasons")
folds = pd.DataFrame(meta.get("walk_forward_folds", []))
if folds.empty:
    st.info("No fold metrics stored.")
else:
    st.dataframe(folds, use_container_width=True, hide_index=True)

section_heading("Calibration", "Reliability by probability bucket")
if OOF.exists():
    oof = pd.read_parquet(OOF).copy()
    oof["bucket"] = pd.cut(oof["p_home_win_cal"], bins=10, labels=False)
    cal = (
        oof.groupby("bucket")
        .agg(pred=("p_home_win_cal", "mean"), actual=("home_win", "mean"), n=("home_win", "size"))
        .dropna()
    )
    st.line_chart(cal.set_index("pred")["actual"])
    st.dataframe(cal, use_container_width=True)
else:
    st.info("No OOF prediction file found.")

panel(
    "Betting metrics",
    "<p>ROI and CLV appear after free-tier odds snapshots accumulate. "
    "The skill metrics above do not require odds.</p>",
)
