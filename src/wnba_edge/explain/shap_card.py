"""SHAP helpers for prediction cards."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def shap_top_drivers(model, X_row: pd.DataFrame, top_n: int = 8) -> list[dict[str, Any]]:
    import shap

    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(X_row)
    if isinstance(values, list):
        values = values[0]
    vals = np.asarray(values).reshape(-1)
    feats = list(X_row.columns)
    order = np.argsort(np.abs(vals))[::-1][:top_n]
    return [
        {"feature": feats[i], "shap_value": float(vals[i]), "value": float(X_row.iloc[0, i])}
        for i in order
    ]
