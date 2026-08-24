from __future__ import annotations

from bma.experiments.aeat_monthly_matched_games_v0_6_2 import matched_games


def test_all_2024_games_preserve_n_to_n_measure() -> None:
    games = matched_games(tuple(range(1, 13)), (1, 2, 3, 4, 5, 6))
    assert len(games) == 36
    assert all(len(game["training_months"]) == len(game["target_months"]) == game["n"] for game in games)
    assert sum(game["n"] for game in games) == 91


def test_six_month_game_is_january_to_june_against_july_to_december() -> None:
    games = matched_games(tuple(range(1, 13)), (6,))
    assert games == [
        {
            "game_id": "N06_START01",
            "n": 6,
            "training_months": [1, 2, 3, 4, 5, 6],
            "target_months": [7, 8, 9, 10, 11, 12],
        }
    ]
