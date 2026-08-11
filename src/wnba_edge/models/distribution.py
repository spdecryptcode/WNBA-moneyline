"""Convert margin mean/sigma into win and cover probabilities."""

from __future__ import annotations

import numpy as np
from scipy import stats


def margin_cdf(
    x: np.ndarray | float,
    mu: np.ndarray | float,
    sigma: np.ndarray | float,
    *,
    family: str = "student_t",
    df: float = 6.0,
) -> np.ndarray:
    mu = np.asarray(mu, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    x = np.asarray(x, dtype=float)
    sigma = np.clip(sigma, 1e-3, None)
    if family == "normal":
        return stats.norm.cdf(x, loc=mu, scale=sigma)
    return stats.t.cdf(x, df, loc=mu, scale=sigma)


def p_home_win(
    mu: np.ndarray | float,
    sigma: np.ndarray | float,
    *,
    family: str = "student_t",
    df: float = 6.0,
    continuity: float = 0.5,
) -> np.ndarray:
    # P(margin > 0) with continuity correction ~= 1 - F(0.5)
    return 1.0 - margin_cdf(continuity, mu, sigma, family=family, df=df)


def p_home_covers(
    mu: np.ndarray | float,
    sigma: np.ndarray | float,
    home_spread: np.ndarray | float,
    *,
    family: str = "student_t",
    df: float = 6.0,
) -> np.ndarray:
    """home_spread is sportsbook number for home (e.g. -4.5 means home favored by 4.5).

    Home covers if margin + home_spread > 0 => margin > -home_spread.
    """
    threshold = -np.asarray(home_spread, dtype=float)
    return 1.0 - margin_cdf(threshold, mu, sigma, family=family, df=df)
