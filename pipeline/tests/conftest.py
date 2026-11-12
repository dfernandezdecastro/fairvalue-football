"""Tiny synthetic staging tables shared by feature tests (no third-party data)."""

import pandas as pd
import pytest

D = pd.Timestamp
ARS, MCI, ROMA = 11, 12, 21


def _games():
    rows = []
    gid = 1
    # 2018/19 and 2019/20 Premier League; 2019/20 ends late (COVID) on 2020-07-26
    for season, last in [(2018, D("2019-05-12")), (2019, D("2020-07-26"))]:
        for i, (h, a, hg, ag) in enumerate([(ARS, MCI, 2, 1), (MCI, ARS, 0, 0), (ARS, 99, 1, 3)]):
            date = last - pd.Timedelta(days=30 * (2 - i))
            rows.append((gid, "GB1", "domestic_league", season, date, h, a, hg, ag))
            gid += 1
    rows.append((gid, "IT1", "domestic_league", 2019, D("2020-08-02"), ROMA, 22, 1, 0))
    cols = ["game_id", "competition_id", "competition_type", "season", "date", "home_club_id", "away_club_id",
            "home_goals", "away_goals"]  # fmt: skip
    g = pd.DataFrame(rows, columns=cols)
    g["home_goals"] = g.home_goals.astype("Int64")
    g["away_goals"] = g.away_goals.astype("Int64")
    return g


@pytest.fixture
def games():
    return _games()


@pytest.fixture
def apps(games):
    """Player 1 plays every Arsenal league game (90 min, 1 goal each)."""
    g = games[(games.home_club_id == ARS) | (games.away_club_id == ARS)]
    return pd.DataFrame({
        "game_id": g.game_id, "player_id": 1, "club_id": ARS, "date": g.date, "season": g.season,
        "competition_id": g.competition_id, "competition_type": g.competition_type, "started": True,
        "minutes": 90, "goals": 1, "assists": 0, "yellow_cards": 0, "red_cards": 0,
    }).reset_index(drop=True)  # fmt: skip


@pytest.fixture
def players():
    return pd.DataFrame(
        {"player_id": [1], "date_of_birth": [D("1995-07-01")], "sub_position": ["Centre-Forward"]}
    )


@pytest.fixture
def valuations():
    return pd.DataFrame({"player_id": [1, 1, 1], "date": [D("2019-06-01"), D("2020-01-15"), D("2020-07-01")],
                         "value_eur": [10e6, 20e6, 99e6]})  # fmt: skip


@pytest.fixture
def no_understat():
    return pd.DataFrame(columns=["player_id", "competition_id", "season", "understat_id", "us_minutes",
                                 "us_position", "us_goals", "us_assists", "npxg", "xa", "shots",
                                 "key_passes", "xg_chain", "xg_buildup"])  # fmt: skip
