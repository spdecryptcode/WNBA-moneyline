"""DQ report viewer."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DQ_JSON = ROOT / "reports" / "dq" / "latest.json"
DQ_MD = ROOT / "reports" / "dq" / "latest.md"

st.set_page_config(page_title="Data Quality", layout="wide")
st.title("Data quality")

if not DQ_JSON.exists():
    st.warning("No DQ report yet. Run `wnba-clean` first.")
    st.stop()

report = json.loads(DQ_JSON.read_text())
st.metric("Hard checks passed", str(report.get("all_hard_passed")))
st.subheader("Checks")
st.dataframe(report.get("checks", []), use_container_width=True, hide_index=True)
st.subheader("Row counts")
st.json(report.get("row_counts", {}))
st.subheader("Quarantine")
st.json(report.get("quarantine_counts", {}))
if DQ_MD.exists():
    st.markdown(DQ_MD.read_text())
