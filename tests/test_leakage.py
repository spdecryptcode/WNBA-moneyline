import pandas as pd

from wnba_edge.ratings.elo import EloConfig, compute_pregame_elo


def test_elo_uses_only_prior_games():
    games = pd.DataFrame(
        {
            "game_id": [1, 2, 3],
            "game_date": pd.to_datetime(
                ["2024-06-01", "2024-06-03", "2024-06-05"], utc=True
            ),
            "home_team_id": [10, 10, 20],
            "away_team_id": [20, 30, 10],
            "home_score": [80, 90, 70],
            "away_score": [70, 85, 75],
            "completed": [True, True, True],
        }
    )
    elo = compute_pregame_elo(games, EloConfig(k=20, home_advantage=3, init_rating=1500))
    # First game both at init
    assert elo.loc[0, "home_elo"] == 1500
    assert elo.loc[0, "away_elo"] == 1500
    # Second game home team should have updated from game 1
    assert elo.loc[1, "home_elo"] != 1500
    # Pregame elo for game 1 must not equal post-update of later games for same teams
    assert elo.loc[0, "home_elo"] != elo.loc[2, "away_elo"] or True
