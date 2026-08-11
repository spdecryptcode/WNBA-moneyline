import numpy as np

from wnba_edge.models.distribution import p_home_covers, p_home_win


def test_higher_mu_higher_win_prob():
    p_low = p_home_win(0.0, 12.0)
    p_high = p_home_win(6.0, 12.0)
    assert p_high > p_low


def test_cover_vs_spread_consistency():
    mu, sigma = 3.0, 12.0
    # Home -3.5 should have lower cover prob than win prob roughly around even
    p_win = float(p_home_win(mu, sigma))
    p_cover = float(p_home_covers(mu, sigma, -3.5))
    assert 0 < p_cover < 1
    assert p_cover < p_win
