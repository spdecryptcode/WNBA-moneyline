"""FastAPI app serving slate, game detail, backtest, and DQ JSON."""

from __future__ import annotations

import json
from datetime import date as date_cls
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from wnba_edge.paths import ARTIFACTS, FEATURES, PREDICTIONS, REPORTS_DQ

app = FastAPI(title="WNBA Edge API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_features() -> pd.DataFrame:
    path = FEATURES / "pregame_features.parquet"
    if not path.exists():
        raise HTTPException(status_code=404, detail="pregame features not found")
    feat = pd.read_parquet(path)
    feat["game_date"] = pd.to_datetime(feat["game_date"], utc=True)
    feat["slate_date"] = feat["game_date"].dt.date
    return feat


def _load_cards_for_day(day: pd.DataFrame, slate: date) -> list[dict[str, Any]]:
    from wnba_edge.models.predict import predict_games

    pred_path = PREDICTIONS / f"{slate.isoformat()}.json"
    wanted = set(day["game_id"].tolist())
    if pred_path.exists():
        try:
            loaded = json.loads(pred_path.read_text())
            cards = [c for c in loaded if c.get("game_id") in wanted]
            if len(cards) == len(day):
                return cards
        except Exception:
            pass
    return predict_games(day, as_of_date=slate.isoformat())


def _calibration_buckets(oof: pd.DataFrame, n_bins: int = 10) -> list[dict[str, float]]:
    df = oof.dropna(subset=["p_home_win_cal", "home_win"]).copy()
    if df.empty:
        return []
    df["bucket"] = pd.cut(df["p_home_win_cal"], bins=n_bins, labels=False, include_lowest=True)
    rows: list[dict[str, float]] = []
    for b, g in df.groupby("bucket", observed=True):
        if pd.isna(b):
            continue
        rows.append(
            {
                "bucket": int(b),
                "p_mean": float(g["p_home_win_cal"].mean()),
                "win_rate": float(g["home_win"].mean()),
                "n": int(len(g)),
            }
        )
    return rows


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/slate/dates")
def slate_dates(
    include_completed: bool = Query(False, description="Include completed game dates"),
) -> dict[str, Any]:
    feat = _load_features()
    visible = feat if include_completed else feat[~feat["completed"].fillna(False)]
    dates = sorted({d.isoformat() for d in visible["slate_date"].unique()}, reverse=True)
    return {"dates": dates, "include_completed": include_completed}


@app.get("/api/slate")
def slate(
    slate_date: str = Query(..., alias="date", description="Slate date YYYY-MM-DD"),
    include_completed: bool = Query(False),
) -> dict[str, Any]:
    try:
        slate_d = date_cls.fromisoformat(slate_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date") from exc

    feat = _load_features()
    visible = feat if include_completed else feat[~feat["completed"].fillna(False)]
    day = visible[visible["slate_date"] == slate_d].copy()
    if day.empty:
        day = feat[feat["slate_date"] == slate_d].copy()
    if day.empty:
        raise HTTPException(status_code=404, detail=f"No games for {slate_date}")

    if not (ARTIFACTS / "margin_lgbm.joblib").exists():
        raise HTTPException(status_code=503, detail="Model artifacts missing")

    cards = _load_cards_for_day(day, slate_d)
    completed_map = dict(zip(day["game_id"], day["completed"].fillna(False)))
    for c in cards:
        c["completed"] = bool(completed_map.get(c.get("game_id"), False))

    n_bet = sum(1 for c in cards if c.get("gate", {}).get("bet"))
    avg_p = float(np.mean([float(c.get("p_home_win_cal", 0)) for c in cards])) if cards else 0.0
    return {
        "date": slate_date,
        "games": cards,
        "summary": {
            "n_games": len(cards),
            "n_bet": n_bet,
            "avg_p_home": avg_p,
        },
    }


@app.get("/api/games/{game_id}")
def game_detail(
    game_id: int,
    home_ml: float | None = None,
    away_ml: float | None = None,
    home_spread: float | None = None,
) -> dict[str, Any]:
    if not (ARTIFACTS / "margin_lgbm.joblib").exists():
        raise HTTPException(status_code=503, detail="Model artifacts missing")

    from wnba_edge.models.predict import predict_games

    feat = _load_features()
    row = feat[feat["game_id"] == game_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

    slate_d = row.iloc[0]["slate_date"]
    cards = predict_games(
        row,
        as_of_date=str(slate_d),
        home_ml=home_ml,
        away_ml=away_ml,
        home_spread=home_spread,
    )
    if not cards:
        raise HTTPException(status_code=500, detail="Scoring returned empty")
    card = cards[0]
    card["completed"] = bool(row.iloc[0].get("completed", False))
    return card


@app.get("/api/backtest")
def backtest() -> dict[str, Any]:
    meta_path = ARTIFACTS / "model_meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="model_meta.json not found")
    meta = json.loads(meta_path.read_text())
    calibration: list[dict[str, float]] = []
    oof_path = ARTIFACTS / "oof_predictions.parquet"
    if oof_path.exists():
        oof = pd.read_parquet(oof_path)
        calibration = _calibration_buckets(oof)
    return {
        "oof_metrics": meta.get("oof_metrics", {}),
        "walk_forward_folds": meta.get("walk_forward_folds", []),
        "selection_note": meta.get("selection_note"),
        "param_source": meta.get("param_source"),
        "sigma": meta.get("sigma"),
        "calibration": calibration,
    }


@app.get("/api/dq")
def data_quality() -> dict[str, Any]:
    path = REPORTS_DQ / "latest.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="DQ report not found")
    report = json.loads(path.read_text())
    md_path = REPORTS_DQ / "latest.md"
    report["markdown"] = md_path.read_text() if md_path.exists() else ""
    return report
