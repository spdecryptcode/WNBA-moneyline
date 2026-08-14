"""Shared production UI theme for WNBA Edge Streamlit app."""

from __future__ import annotations

from typing import Any

import streamlit as st

BRAND = "WNBA Edge"
TAGLINE = "Pregame probabilities built for real betting decisions."


def page_config(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} · {BRAND}",
        page_icon="🏀",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_theme() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
  --ink: #0c1c24;
  --ink-soft: #1a3340;
  --paper: #f6f1e8;
  --paper-2: #efe6d8;
  --signal: #d9480f;
  --signal-soft: #f08c00;
  --pass: #5c6b73;
  --bet: #0b6e4f;
  --line: rgba(12, 28, 36, 0.12);
  --shadow: 0 18px 50px rgba(12, 28, 36, 0.08);
}

html, body, [class*="css"] {
  font-family: "Outfit", sans-serif;
}

.stApp {
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(217, 72, 15, 0.16), transparent 55%),
    radial-gradient(900px 500px at 100% 0%, rgba(11, 110, 79, 0.10), transparent 50%),
    linear-gradient(165deg, #f8f4ed 0%, #f0e8db 48%, #e9dfd0 100%);
  color: var(--ink);
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0c1c24 0%, #143040 100%);
  border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * { color: #f6f1e8 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stCheckbox label,
[data-testid="stSidebar"] .stNumberInput label {
  color: #d7dde0 !important;
  font-weight: 500;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] input {
  background: rgba(255,255,255,0.06) !important;
  color: #fff !important;
  border-radius: 10px !important;
}

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

.brand-hero {
  position: relative;
  padding: 1.6rem 0 1.1rem 0;
  margin-bottom: 0.4rem;
  border-bottom: 1px solid var(--line);
  animation: rise 0.7s ease-out both;
}
.brand-kicker {
  font-family: "Outfit", sans-serif;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--signal);
  margin-bottom: 0.45rem;
}
.brand-title {
  font-family: "Syne", sans-serif;
  font-weight: 800;
  font-size: clamp(2.6rem, 5vw, 4.2rem);
  line-height: 0.92;
  letter-spacing: -0.03em;
  color: var(--ink);
  margin: 0;
}
.brand-sub {
  margin-top: 0.75rem;
  max-width: 36rem;
  font-size: 1.05rem;
  font-weight: 400;
  color: var(--ink-soft);
  opacity: 0.88;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  margin: 1.5rem 0 0.85rem;
  animation: rise 0.8s ease-out 0.08s both;
}
.section-head h2 {
  font-family: "Syne", sans-serif;
  font-size: 1.45rem;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.02em;
}
.section-head span {
  font-size: 0.85rem;
  color: var(--pass);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.match-board {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  animation: rise 0.85s ease-out 0.12s both;
}
.match-row {
  display: grid;
  grid-template-columns: 1.4fr 0.9fr 0.9fr 0.7fr 0.7fr;
  gap: 0.75rem;
  align-items: center;
  padding: 1rem 1.15rem;
  background: rgba(255,255,255,0.55);
  border: 1px solid rgba(12,28,36,0.08);
  border-radius: 16px;
  backdrop-filter: blur(8px);
  box-shadow: var(--shadow);
  transition: transform 0.25s ease, border-color 0.25s ease;
}
.match-row:hover {
  transform: translateY(-2px);
  border-color: rgba(217, 72, 15, 0.35);
}
.match-teams {
  font-family: "Syne", sans-serif;
  font-weight: 700;
  font-size: 1.15rem;
  letter-spacing: -0.02em;
}
.match-teams .at {
  color: var(--pass);
  font-weight: 500;
  margin: 0 0.35rem;
  font-size: 0.9rem;
}
.match-meta {
  font-size: 0.78rem;
  color: var(--pass);
  margin-top: 0.15rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.stat-label {
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--pass);
  margin-bottom: 0.2rem;
}
.stat-value {
  font-family: "Syne", sans-serif;
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--ink);
}
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 4.4rem;
  padding: 0.42rem 0.7rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.badge-bet {
  background: rgba(11, 110, 79, 0.14);
  color: var(--bet);
  border: 1px solid rgba(11, 110, 79, 0.28);
}
.badge-pass {
  background: rgba(92, 107, 115, 0.12);
  color: var(--pass);
  border: 1px solid rgba(92, 107, 115, 0.22);
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.85rem;
  margin: 1rem 0 1.4rem;
  animation: rise 0.75s ease-out 0.1s both;
}
.metric-tile {
  padding: 1.05rem 1.1rem;
  background: rgba(255,255,255,0.58);
  border: 1px solid rgba(12,28,36,0.08);
  border-radius: 16px;
  box-shadow: var(--shadow);
}
.metric-tile .label {
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--pass);
}
.metric-tile .value {
  margin-top: 0.35rem;
  font-family: "Syne", sans-serif;
  font-size: 1.7rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--ink);
}
.metric-tile .hint {
  margin-top: 0.2rem;
  font-size: 0.8rem;
  color: var(--ink-soft);
  opacity: 0.75;
}

.panel {
  padding: 1.2rem 1.25rem;
  background: rgba(255,255,255,0.58);
  border: 1px solid rgba(12,28,36,0.08);
  border-radius: 18px;
  box-shadow: var(--shadow);
  margin-bottom: 1rem;
  animation: rise 0.8s ease-out 0.14s both;
}
.panel h3 {
  font-family: "Syne", sans-serif;
  font-size: 1.05rem;
  margin: 0 0 0.65rem 0;
}
.panel p, .panel li {
  color: var(--ink-soft);
  line-height: 1.5;
}

.footnote {
  margin-top: 1.4rem;
  font-size: 0.85rem;
  color: var(--pass);
}

@keyframes rise {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .match-row {
    grid-template-columns: 1fr 1fr;
  }
  .metric-strip {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def brand_hero(subtitle: str | None = None) -> None:
    st.markdown(
        f"""
<div class="brand-hero">
  <div class="brand-kicker">DecryptCode · Sports Models</div>
  <h1 class="brand-title">{BRAND}</h1>
  <p class="brand-sub">{subtitle or TAGLINE}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(title: str, right: str = "") -> None:
    st.markdown(
        f"""
<div class="section-head">
  <h2>{title}</h2>
  <span>{right}</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def metric_strip(items: list[tuple[str, str, str]]) -> None:
    cells = []
    for label, value, hint in items:
        cells.append(
            f"""
<div class="metric-tile">
  <div class="label">{label}</div>
  <div class="value">{value}</div>
  <div class="hint">{hint}</div>
</div>
            """
        )
    st.markdown(
        f'<div class="metric-strip">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )


def match_board(rows: list[dict[str, Any]]) -> None:
    html_rows = []
    for r in rows:
        badge_cls = "badge-bet" if r.get("bet") else "badge-pass"
        badge_txt = "BET" if r.get("bet") else "PASS"
        html_rows.append(
            f"""
<div class="match-row">
  <div>
    <div class="match-teams">{r.get("away","—")}<span class="at">@</span>{r.get("home","—")}</div>
    <div class="match-meta">{r.get("meta","")}</div>
  </div>
  <div>
    <div class="stat-label">P(Home)</div>
    <div class="stat-value">{r.get("p_home","—")}</div>
  </div>
  <div>
    <div class="stat-label">Margin</div>
    <div class="stat-value">{r.get("margin","—")}</div>
  </div>
  <div>
    <div class="stat-label">Sigma</div>
    <div class="stat-value">{r.get("sigma","—")}</div>
  </div>
  <div>
    <span class="badge {badge_cls}">{badge_txt}</span>
  </div>
</div>
            """
        )
    st.markdown(
        f'<div class="match-board">{"".join(html_rows)}</div>',
        unsafe_allow_html=True,
    )


def panel(title: str, body_html: str) -> None:
    st.markdown(
        f'<div class="panel"><h3>{title}</h3>{body_html}</div>',
        unsafe_allow_html=True,
    )
