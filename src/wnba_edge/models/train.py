"""LightGBM margin model training, walk-forward eval, calibration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error

from wnba_edge.config import model_config
from wnba_edge.features.build import feature_matrix
from wnba_edge.models.distribution import p_home_win
from wnba_edge.paths import ARTIFACTS, FEATURES, ensure_dirs


@dataclass
class FoldResult:
    test_season: int
    n: int
    mae: float
    log_loss: float
    brier: float
    sigma: float


def _lgb_params(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = model_config()["lightgbm"].copy()
    n_estimators = cfg.pop("n_estimators")
    early = cfg.pop("early_stopping_rounds", 40)
    if overrides:
        cfg.update(overrides)
    return cfg, n_estimators, early


def train_margin_model(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame | None = None,
    y_val: np.ndarray | None = None,
    param_overrides: dict[str, Any] | None = None,
) -> lgb.LGBMRegressor:
    params, n_estimators, early = _lgb_params(param_overrides)
    model = lgb.LGBMRegressor(**params, n_estimators=n_estimators)
    fit_kwargs: dict[str, Any] = {}
    if X_val is not None and y_val is not None:
        # LightGBM 4.7: pass arrays/frames directly (or tuples), not Python lists
        fit_kwargs["eval_X"] = X_val
        fit_kwargs["eval_y"] = y_val
        fit_kwargs["callbacks"] = [lgb.early_stopping(early, verbose=False)]
    model.fit(X_train, y_train, **fit_kwargs)
    return model


def fit_sigma(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    resid = y_true - y_pred
    return float(max(np.std(resid, ddof=1), 1.0))


def sample_param_overrides(rng: np.random.Generator) -> dict[str, Any]:
    return {
        "learning_rate": float(rng.choice([0.02, 0.03, 0.05, 0.08, 0.1])),
        "num_leaves": int(rng.choice([8, 15, 31, 47, 63])),
        "max_depth": int(rng.choice([3, 4, 5, 6, 7])),
        "min_data_in_leaf": int(rng.choice([10, 15, 25, 40, 60])),
        "feature_fraction": float(rng.choice([0.6, 0.7, 0.8, 0.9, 1.0])),
        "bagging_fraction": float(rng.choice([0.6, 0.7, 0.8, 0.9, 1.0])),
        "lambda_l1": float(rng.choice([0.0, 0.05, 0.1, 0.5, 1.0])),
        "lambda_l2": float(rng.choice([0.1, 0.5, 1.0, 2.0, 5.0])),
    }


def walk_forward(
    df: pd.DataFrame,
    param_overrides: dict[str, Any] | None = None,
    *,
    test_seasons: list[int] | None = None,
) -> dict[str, Any]:
    cfg = model_config()
    dist = cfg["margin_distribution"]
    if test_seasons is None:
        test_seasons = cfg["walk_forward_test_seasons"]
    completed = df[df["completed"]].copy()

    oof_rows = []
    fold_metrics: list[dict[str, Any]] = []
    for season in test_seasons:
        train = completed[completed["season"] < season]
        test = completed[completed["season"] == season]
        if train.empty or test.empty:
            continue
        # internal val = last train season
        val_season = int(train["season"].max())
        tr = train[train["season"] < val_season] if (train["season"] < val_season).any() else train
        va = train[train["season"] == val_season] if (train["season"] == val_season).any() else train.tail(50)

        X_tr, cols = feature_matrix(tr)
        X_va, _ = feature_matrix(va)
        X_te, _ = feature_matrix(test)
        y_tr = tr["margin"].to_numpy(float)
        y_va = va["margin"].to_numpy(float)
        y_te = test["margin"].to_numpy(float)

        model = train_margin_model(X_tr, y_tr, X_va, y_va, param_overrides)
        pred = model.predict(X_te)
        sigma = fit_sigma(y_va, model.predict(X_va))
        p_win = p_home_win(
            pred,
            sigma,
            family=dist["family"],
            df=dist["df"],
            continuity=dist.get("continuity_correction", 0.5),
        )
        y_win = test["home_win"].to_numpy(int)
        # clip probs for metrics
        p_clip = np.clip(p_win, 1e-6, 1 - 1e-6)
        metrics = FoldResult(
            test_season=int(season),
            n=len(test),
            mae=float(mean_absolute_error(y_te, pred)),
            log_loss=float(log_loss(y_win, p_clip)),
            brier=float(brier_score_loss(y_win, p_clip)),
            sigma=float(sigma),
        )
        fold_metrics.append(metrics.__dict__)
        part = test[["game_id", "season", "home_win", "margin"]].copy()
        part["mu"] = pred
        part["sigma"] = sigma
        part["p_home_win_raw"] = p_win
        oof_rows.append(part)

    oof = pd.concat(oof_rows, ignore_index=True) if oof_rows else pd.DataFrame()
    return {"folds": fold_metrics, "oof": oof}


def _weighted_fold_metric(folds: list[dict[str, Any]], key: str) -> float:
    if not folds:
        return float("inf")
    n = np.array([f["n"] for f in folds], dtype=float)
    v = np.array([f[key] for f in folds], dtype=float)
    return float(np.average(v, weights=n))


def hyperparam_search(
    df: pd.DataFrame,
    *,
    n_trials: int | None = None,
) -> dict[str, Any]:
    """Select hyperparameters on inner walk-forward folds (not final test seasons).

    Primary objective: mean walk-forward log loss on ``hyperparam_search_seasons``.
    Tie-break / secondary: mean walk-forward MAE.
    Final report folds in ``walk_forward_test_seasons`` stay untouched during search.
    """
    cfg = model_config()
    search_cfg = cfg["hyperparam_search"]
    n_trials = n_trials or int(search_cfg["n_trials"])
    seed = int(search_cfg["seed"])
    rng = np.random.default_rng(seed)

    search_seasons = list(cfg.get("hyperparam_search_seasons", [2020, 2021, 2022]))
    final_test = set(cfg["walk_forward_test_seasons"])
    # Guardrail: never score candidates on final report seasons
    search_seasons = [s for s in search_seasons if s not in final_test]
    if not search_seasons:
        raise ValueError("No valid hyperparam_search_seasons after excluding final test seasons")

    # Only use data available before the first final test season
    first_final = min(final_test)
    search_df = df[(df["season"] < first_final) & df["completed"]].copy()
    _, cols = feature_matrix(search_df.head(5) if len(search_df) else search_df)

    trials: list[dict[str, Any]] = []
    best_score = float("inf")
    best_secondary = float("inf")
    best: dict[str, Any] = {}

    for trial_id in range(n_trials):
        overrides = sample_param_overrides(rng)
        wf = walk_forward(search_df, overrides, test_seasons=search_seasons)
        folds = wf["folds"]
        if not folds:
            continue
        score_ll = _weighted_fold_metric(folds, "log_loss")
        score_mae = _weighted_fold_metric(folds, "mae")
        score_brier = _weighted_fold_metric(folds, "brier")
        trial_rec = {
            "trial_id": trial_id,
            **overrides,
            "search_log_loss": score_ll,
            "search_mae": score_mae,
            "search_brier": score_brier,
            "n_search_games": int(sum(f["n"] for f in folds)),
        }
        trials.append(trial_rec)

        better = score_ll < best_score - 1e-12 or (
            abs(score_ll - best_score) <= 1e-12 and score_mae < best_secondary
        )
        if better:
            best_score = score_ll
            best_secondary = score_mae
            best = overrides.copy()
            best["_search_log_loss"] = score_ll
            best["_search_mae"] = score_mae
            best["_search_brier"] = score_brier
            best["_search_seasons"] = search_seasons
            best["_feature_columns"] = cols

    ensure_dirs()
    if trials:
        pd.DataFrame(trials).sort_values(
            ["search_log_loss", "search_mae"]
        ).to_csv(ARTIFACTS / "hyperparam_trials.csv", index=False)
    return best


def fit_calibrator(oof: pd.DataFrame) -> IsotonicRegression:
    y = oof["home_win"].to_numpy(int)
    p = np.clip(oof["p_home_win_raw"].to_numpy(float), 1e-6, 1 - 1e-6)
    cal = IsotonicRegression(out_of_bounds="clip")
    cal.fit(p, y)
    return cal


def train_production(df: pd.DataFrame, param_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_dirs()
    cfg = model_config()
    dist = cfg["margin_distribution"]
    completed = df[df["completed"]].copy()

    # hold out last season for early stopping / sigma
    last = int(completed["season"].max())
    train = completed[completed["season"] < last]
    val = completed[completed["season"] == last]
    if train.empty:
        train = completed
        val = completed.tail(max(30, len(completed) // 10))

    X_tr, cols = feature_matrix(train)
    X_va, _ = feature_matrix(val)
    model = train_margin_model(
        X_tr,
        train["margin"].to_numpy(float),
        X_va,
        val["margin"].to_numpy(float),
        param_overrides,
    )
    sigma = fit_sigma(val["margin"].to_numpy(float), model.predict(X_va))

    # OOF-style probs on val for calibrator bootstrap if no walk-forward yet
    wf = walk_forward(df, param_overrides)
    oof = wf["oof"]
    if oof.empty:
        pred = model.predict(X_va)
        p = p_home_win(
            pred,
            sigma,
            family=dist["family"],
            df=dist["df"],
            continuity=dist.get("continuity_correction", 0.5),
        )
        oof = val[["game_id", "season", "home_win", "margin"]].copy()
        oof["mu"] = pred
        oof["sigma"] = sigma
        oof["p_home_win_raw"] = p

    calibrator = fit_calibrator(oof)
    oof["p_home_win_cal"] = calibrator.predict(
        np.clip(oof["p_home_win_raw"].to_numpy(float), 1e-6, 1 - 1e-6)
    )

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACTS / "margin_lgbm.joblib")
    joblib.dump(calibrator, ARTIFACTS / "calibrator_isotonic.joblib")
    meta = {
        "feature_columns": cols,
        "sigma": sigma,
        "margin_distribution": dist,
        "param_overrides": param_overrides or {},
        "walk_forward_folds": wf["folds"],
        "oof_metrics": {
            "log_loss_raw": float(
                log_loss(
                    oof["home_win"],
                    np.clip(oof["p_home_win_raw"], 1e-6, 1 - 1e-6),
                )
            ),
            "log_loss_cal": float(
                log_loss(
                    oof["home_win"],
                    np.clip(oof["p_home_win_cal"], 1e-6, 1 - 1e-6),
                )
            ),
            "brier_cal": float(brier_score_loss(oof["home_win"], oof["p_home_win_cal"])),
            "mae": float(mean_absolute_error(oof["margin"], oof["mu"])),
        },
    }
    (ARTIFACTS / "model_meta.json").write_text(json.dumps(meta, indent=2))
    oof.to_parquet(ARTIFACTS / "oof_predictions.parquet", index=False)
    if param_overrides is not None:
        (ARTIFACTS / "best_params.json").write_text(
            json.dumps(param_overrides, indent=2, default=str)
        )
    return meta


def run_training_pipeline(*, n_trials: int | None = None) -> dict[str, Any]:
    ensure_dirs()
    feat_path = FEATURES / "pregame_features.parquet"
    df = pd.read_parquet(feat_path)
    best = hyperparam_search(df, n_trials=n_trials)
    # Persist full search record (includes underscore metrics)
    (ARTIFACTS / "best_params.json").write_text(json.dumps(best, indent=2, default=str))
    overrides = {k: v for k, v in best.items() if not k.startswith("_")}
    meta = train_production(df, overrides)
    meta["hyperparam_search"] = best
    # Keep search diagnostics in model_meta too
    meta["search_objective"] = "walk_forward_log_loss"
    meta["search_seasons"] = best.get("_search_seasons")
    meta["search_scores"] = {
        "log_loss": best.get("_search_log_loss"),
        "mae": best.get("_search_mae"),
        "brier": best.get("_search_brier"),
    }
    (ARTIFACTS / "model_meta.json").write_text(json.dumps(meta, indent=2, default=str))
    return meta
