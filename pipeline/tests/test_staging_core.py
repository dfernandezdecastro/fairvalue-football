import pandas as pd

from fairvalue.staging import core

D = pd.Timestamp
CUTOFF = D("2026-07-06")
A, B, C = 1, 2, 3  # club ids


def transfers(rows):
    df = pd.DataFrame(
        rows, columns=["player_id", "transfer_date", "from_club_id", "to_club_id", "transfer_fee"]
    )
    df["transfer_date"] = pd.to_datetime(df.transfer_date)
    df["from_club_name"] = df.from_club_id.map(str)
    df["to_club_name"] = df.to_club_id.map(str)
    df["market_value_in_eur"] = 1e6
    df["player_name"] = "x"
    return df


CLS = pd.DataFrame(
    {"club_id": [A, A, B, B, C], "season": [2019, 2020, 2019, 2020, 2020],
     "competition_id": ["GB1", "GB1", "ES1", "ES1", "NL1"]}
)  # fmt: skip


def staged(rows):
    return core.stage_transfers(transfers(rows), CLS, CUTOFF).set_index(["player_id", "date"])


def test_paid_move_that_returns_is_probable_paid_loan():
    s = staged([(1, "2020-01-20", A, B, 5e6), (1, "2020-06-30", B, A, 0)])
    assert s.loc[(1, D("2020-01-20")), "move_type"] == "probable_paid_loan"


def test_buy_and_loan_back_same_day_is_a_permanent_transfer():
    # B buys from A, then loans him back to A the same day; he returns to B later.
    s = staged([(1, "2020-01-20", A, B, 15e6), (1, "2020-01-20", B, A, 0), (1, "2020-08-31", A, B, 0)])
    day = s.loc[(1, D("2020-01-20"))].set_index("from_club_id")
    assert day.loc[A, "move_type"] == "paid_transfer"
    assert day.loc[B, "move_type"] == "probable_loan"


def test_future_rows_inform_loans_but_are_dropped():
    s = staged([(1, "2026-01-15", A, B, 0), (1, "2026-06-30", B, A, 0), (1, "2027-06-30", A, C, 0)])
    assert D("2027-06-30") not in s.index.get_level_values("date")
    assert s.loc[(1, D("2026-01-15")), "move_type"] == "probable_loan"


def test_leagues_window_and_ids():
    s = core.stage_transfers(
        transfers(
            [(1, "2020-08-01", A, B, 1e6), (2, "2021-01-10", B, C, 2e6), (3, "2020-07-15", C, A, None)]
        ),
        CLS,
        CUTOFF,
    )
    summer = s[s.player_id == 1].iloc[0]
    assert (summer.window, summer.season) == ("summer", 2020)
    assert summer.from_competition_id == "GB1"  # seller's league in 2019/20, the season just finished
    assert summer.to_competition_id == "ES1"
    winter = s[s.player_id == 2].iloc[0]
    assert winter.window == "winter" and winter.from_competition_id == "ES1"  # 2020/21, current season
    assert s[s.player_id == 3].iloc[0].fee_status == "unknown"
    assert s.transfer_id.tolist() == [1, 2, 3]


def test_club_league_seasons_uses_fixture_season():
    games = pd.DataFrame(
        {"competition_id": ["IT1", "IT1", "CIT"], "season": [2019, 2019, 2019], "home_club_id": [A, A, A],
         "away_club_id": [B, C, B], "competition_type": ["domestic_league"] * 2 + ["domestic_cup"]}
    )  # fmt: skip
    out = core.club_league_seasons(games)
    assert set(out.competition_id) == {"IT1"} and len(out) == 3


def test_appearances_official_season_and_starts():
    # A COVID-delayed 2019/20 match played in July 2020 keeps season 2019.
    apps = pd.DataFrame(
        {"game_id": [10, 10], "player_id": [7, 8], "player_club_id": [A, A], "date": [D("2020-07-20")] * 2,
         "player_name": ["p", "q"], "competition_id": ["IT1"] * 2, "yellow_cards": [0, 0],
         "red_cards": [0, 0], "goals": [1, 0], "assists": [0, 0], "minutes_played": [90, 20]}
    )  # fmt: skip
    games = pd.DataFrame({"game_id": [10], "season": [2019], "competition_type": ["domestic_league"]})
    lineups = pd.DataFrame({"game_id": [10, 10], "player_id": [7, 8], "club_id": [A, A],
                            "type": ["starting_lineup", "substitutes"]})  # fmt: skip
    out = core.stage_appearances(apps, games, lineups).set_index("player_id")
    assert out.season.tolist() == [2019, 2019]
    assert out.loc[7, "started"] and not out.loc[8, "started"]


def test_valuations_dedupe_and_cutoff():
    v = pd.DataFrame(
        {
            "player_id": [1, 1, 1, 1],
            "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2025-01-01", "2026-08-01"]),
            "market_value_in_eur": [1, 2, 0, 3],
        }
    )
    out = core.stage_valuations(v, CUTOFF)
    assert out.value_eur.tolist() == [2]  # same-day duplicate keeps last; zero and post-cutoff dropped


def test_clubs_include_transfer_only_clubs():
    clubs = pd.DataFrame({"club_id": [A], "club_code": ["club-a"], "name": ["Club A"]})
    out = core.stage_clubs(clubs, transfers([(1, "2020-01-01", A, 99, 1)]).assign(to_club_name="Ümit FC"))
    assert out.set_index("club_id").loc[99, "slug"] == "umit-fc-99"
