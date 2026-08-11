"""Sportsbook odds math: implied probability, vig removal, EV."""

from __future__ import annotations


def american_to_decimal(american: float) -> float:
    a = float(american)
    if a == 0:
        raise ValueError("American odds cannot be 0")
    if a > 0:
        return 1.0 + a / 100.0
    return 1.0 + 100.0 / abs(a)


def american_to_implied(american: float) -> float:
    a = float(american)
    if a > 0:
        return 100.0 / (a + 100.0)
    return abs(a) / (abs(a) + 100.0)


def remove_vig_multiplicative(p_home: float, p_away: float) -> tuple[float, float]:
    """Two-way multiplicative (proportional) vig removal."""
    total = p_home + p_away
    if total <= 0:
        raise ValueError("implied probabilities must be positive")
    return p_home / total, p_away / total


def expected_value(model_p: float, american_odds: float) -> float:
    """EV per 1 unit stake at American odds."""
    dec = american_to_decimal(american_odds)
    return model_p * dec - 1.0


def edge(model_p: float, market_no_vig_p: float) -> float:
    return model_p - market_no_vig_p


def kelly_fraction(model_p: float, american_odds: float, fraction: float = 0.25) -> float:
    dec = american_to_decimal(american_odds)
    b = dec - 1.0
    q = 1.0 - model_p
    if b <= 0:
        return 0.0
    full = (b * model_p - q) / b
    return max(0.0, full * fraction)
