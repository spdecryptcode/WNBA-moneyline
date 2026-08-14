"""Data quality — production DQ view."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))

from theme import apply_theme, brand_hero, metric_strip, page_config, panel, section_heading

DQ_JSON = ROOT / "reports" / "dq" / "latest.json"
DQ_MD = ROOT / "reports" / "dq" / "latest.md"

page_config("Data Quality")
apply_theme()
brand_hero("Trust the inputs — hard integrity checks before any model claim.")

if not DQ_JSON.exists():
    st.warning("No DQ report yet. Run `wnba-clean` first.")
    st.stop()

report = json.loads(DQ_JSON.read_text())
passed = bool(report.get("all_hard_passed"))
rows = report.get("row_counts", {})
quarantine = report.get("quarantine_counts", {})

metric_strip(
    [
        ("Hard checks", "PASS" if passed else "FAIL", report.get("generated_at", "")[:19]),
        ("Games clean", str(rows.get("games_clean", "—")), "Curated"),
        ("Upcoming", str(rows.get("upcoming_games", "—")), "Schedule rows"),
        ("Quarantine", str(sum(int(v) for v in quarantine.values()) if quarantine else 0), "Soft/hard holds"),
    ]
)

section_heading("Checks", "Pass / fail detail")
checks = pd.DataFrame(report.get("checks", []))
if not checks.empty:
    st.dataframe(checks, use_container_width=True, hide_index=True)

col1, col2 = st.columns(2)
with col1:
    panel(
        "Row counts",
        "<ul>"
        + "".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in rows.items())
        + "</ul>",
    )
with col2:
    panel(
        "Quarantine",
        "<ul>"
        + "".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in quarantine.items())
        + ("</ul>" if quarantine else "<p>None recorded.</p>"),
    )

if DQ_MD.exists():
    section_heading("Report", "latest.md")
    st.markdown(DQ_MD.read_text())
