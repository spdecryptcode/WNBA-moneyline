"""Load artifacts and produce prediction cards."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import joblib
import numpy as np
import pandas as pd

from wnba_edge.config import betting_config, model_config
from wnba_edge.explain.shap_card import shap_top_drivers
from wnba_edge.features.build import feature_matrix
from wnba_edge.models.distribution import p_home_covers, p_home_win
from wnba_edge.odds.math import (
    american_to_implied,
    edge,
    expected_value,
    kelly_fraction,
    remove_vig_multiplicative,
)
from wnba_edge.paths import ARTIFACTS, FEATURES, PREDICTIONS, ensure_dirs


def load_artifacts() -> dict[str, Any]:
    model = joblib.load(ARTIFACTS / "margin_lgbm.joblib")
    calibrator = joblib.load(ARTIFACTS / "calibrator_isotonic.joblib")
    meta = json.loads((ARTIFACTS / "model_meta.json").read_text())
    return {"model": model, "calibrator": calibrator, "meta": meta}


def _gate(
    p_cal: float,
    sigma: float,
    edge_val: float | None,
    market: str,
) -> dict[str, Any]:
    cfg = betting_config()
    reasons = []
    ok = True
    if sigma > cfg["max_sigma"]:
        ok = False
        reasons.append(f"sigma {sigma:.1f} > max {cfg['max_sigma']}")
    if edge_val is None:
        reasons.append("no market odds; predictive view only")
        ok = False
    else:
        min_edge = cfg["min_edge_ml"] if market == "h2h" else cfg["min_edge_spread"]
        if edge_val < min_edge:
            ok = False
            reasons.append(f"edge {edge_val:.3f} < min {min_edge}")
        else:
            reasons.append("edge and uncertainty gates passed")
    return {"bet": ok, "reasons": reasons}


def predict_games(
    games: pd.DataFrame | None = None,
    *,
    as_of_date: str | None = None,
    home_ml: float | None = None,
    away_ml: float | None = None,
    home_spread: float | None = None,
    spread_price: float = -110,
) -> list[dict[str, Any]]:
    ensure_dirs()
    arts = load_artifacts()
    model = arts["model"]
    cal = arts["calibrator"]
    meta = arts["meta"]
    dist = meta["margin_distribution"]
    sigma_default = float(meta["sigma"])

    feat = games if games is not None else pd.read_parquet(FEATURES / "pregame_features.parquet")
    if as_of_date:
        d = pd.Timestamp(as_of_date, tz="UTC")
        feat = feat[pd.to_datetime(feat["game_date"], utc=True).dt.normalize() == d.normalize()]

    if feat.empty:
        return []

    X, cols = feature_matrix(feat)
    # align columns to training
    train_cols = meta.get("feature_columns", cols)
    for c in train_cols:
        if c not in X.columns:
            X[c] = 0.0
    X = X[train_cols]
    mu = model.predict(X)
    sigma = np.full(len(feat), sigma_default, dtype=float)
    p_raw = p_home_win(
        mu,
        sigma,
        family=dist["family"],
        df=dist["df"],
        continuity=dist.get("continuity_correction", 0.5),
    )
    p_cal = cal.predict(np.clip(p_raw, 1e-6, 1 - 1e-6))

    cards = []
    for i, row in enumerate(feat.itertuples(index=False)):
        card: dict[str, Any] = {
            "game_id": row.game_id,
            "season": int(row.season) if not pd.isna(row.season) else None,
            "game_date": str(row.game_date),
            "home_team_id": int(row.home_team_id),
            "away_team_id": int(row.away_team_id),
            "home_abbr": getattr(row, "home_abbr", None),
            "away_abbr": getattr(row, "away_abbr", None),
            "mu": float(mu[i]),
            "sigma": float(sigma[i]),
            "p_home_win_raw": float(p_raw[i]),
            "p_home_win_cal": float(p_cal[i]),
            "market": {},
            "gate": {},
            "shap": [],
        }

        # optional single-game market override (UI)
        if home_ml is not None and away_ml is not None:
            ih = american_to_implied(home_ml)
            ia = american_to_implied(away_ml)
            nh, na = remove_vig_multiplicative(ih, ia)
            ev = expected_value(p_cal[i], home_ml)
            ed = edge(p_cal[i], nh)
            card["market"] = {
                "home_ml": home_ml,
                "away_ml": away_ml,
                "implied_home": ih,
                "implied_away": ia,
                "no_vig_home": nh,
                "no_vig_away": na,
                "ev_home": ev,
                "edge_home": ed,
                "kelly": kelly_fraction(p_cal[i], home_ml, betting_config()["kelly_fraction"]),
            }
            card["gate"] = _gate(p_cal[i], sigma[i], ed, "h2h")
        else:
            card["gate"] = _gate(p_cal[i], sigma[i], None, "h2h")

        if home_spread is not None:
            p_cover = float(
                p_home_covers(
                    mu[i],
                    sigma[i],
                    home_spread,
                    family=dist["family"],
                    df=dist["df"],
                )
            )
            card["p_home_cover"] = p_cover
            card["home_spread"] = home_spread
            card["spread_ev"] = expected_value(p_cover, spread_price)

        # SHAP for this row
        try:
            card["shap"] = shap_top_drivers(model, X.iloc[[i]], top_n=8)
        except Exception:
            card["shap"] = []

        cards.append(card)

    # persist
    day = as_of_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = PREDICTIONS / f"{day}.json"
    out.write_text(json.dumps(cards, indent=2, default=str))
    return cards
