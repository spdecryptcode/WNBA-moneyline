from wnba_edge.odds.math import (
    american_to_decimal,
    american_to_implied,
    edge,
    expected_value,
    remove_vig_multiplicative,
)


def test_american_favorites_and_dogs():
    assert abs(american_to_implied(-110) - (110 / 210)) < 1e-9
    assert abs(american_to_implied(150) - (100 / 250)) < 1e-9
    assert abs(american_to_decimal(-110) - (100 / 110 + 1)) < 1e-9


def test_vig_removal_sums_to_one():
    p1, p2 = remove_vig_multiplicative(american_to_implied(-110), american_to_implied(-110))
    assert abs(p1 + p2 - 1.0) < 1e-9
    assert abs(p1 - 0.5) < 1e-9


def test_ev_positive_when_model_beats_price():
    # Fair coin at +100 has EV 0 at p=0.5; p=0.6 => +0.2
    assert abs(expected_value(0.6, 100) - 0.2) < 1e-9
    assert abs(edge(0.6, 0.5) - 0.1) < 1e-9
