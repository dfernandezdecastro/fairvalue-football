import pandas as pd
import pytest

from fairvalue.staging.matching import match_player_seasons, name_score, norm_name, player_id_map


def test_norm_name_strips_accents_and_punctuation():
    assert norm_name("Benoît Badiashile-Mukinayi") == "benoit badiashile mukinayi"


@pytest.mark.parametrize(
    "a, b, lo, hi",
    [
        ("Kylian Mbappé", "Kylian Mbappe", 1.0, 1.0),
        ("Vitinha", "Vitor Ferreira Vitinha", 0.92, 0.92),  # contained
        ("Dayotchanculle Upamecano", "Dayot Upamecano", 0.85, 1.0),  # same surname
        ("Danny Ings", "Wayne Rooney", 0.0, 0.5),
    ],
)
def test_name_score(a, b, lo, hi):
    assert lo <= name_score(a, b) <= hi


def us_rows(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "understat_id",
            "player_name",
            "league",
            "competition_id",
            "season",
            "games",
            "minutes",
            "goals",
        ],
    )


def tm_rows(rows):
    return pd.DataFrame(
        rows,
        columns=["competition_id", "season", "player_id", "tm_games", "tm_goals", "tm_assists", "tm_minutes"],
    )


NAMES = pd.Series({100: "Jamie Vardy", 101: "Harvey Barnes", 102: "James Maddison"})


def test_stats_filter_then_name_picks_the_right_player():
    us = us_rows([(1, "Jamie Vardy", "EPL", "GB1", 2019, 35, 3034, 23)])
    tm = tm_rows(
        [("GB1", 2019, 100, 35, 23, 5, 3000),  # right player
         ("GB1", 2019, 101, 35, 23, 5, 3010),  # same stats, wrong name
         ("GB1", 2019, 102, 10, 2, 1, 800)]  # wrong stats: filtered out
    )  # fmt: skip
    m = match_player_seasons(us, tm, NAMES).iloc[0]
    assert m.tm_player_id == 100 and m.confidence == "high" and m.n_stat_candidates == 2


def test_no_candidate_is_unmatched():
    us = us_rows([(1, "Jamie Vardy", "EPL", "GB1", 2019, 35, 3034, 23)])
    tm = tm_rows([("GB1", 2019, 100, 20, 5, 1, 1500)])
    assert match_player_seasons(us, tm, NAMES).iloc[0].confidence == "unmatched"


def test_player_map_majority_vote_flags_disagreeing_season():
    m = pd.DataFrame(
        {"understat_id": [1, 1, 1], "season": [2017, 2018, 2019], "tm_player_id": [100, 100, 999],
         "confidence": ["high", "high", "high"]}
    )  # fmt: skip
    pm, flagged = player_id_map(m)
    assert pm.iloc[0].tm_player_id == 100 and pm.iloc[0].n_tm_ids == 2
    assert flagged.agrees_with_player_map.tolist() == [True, True, False]
