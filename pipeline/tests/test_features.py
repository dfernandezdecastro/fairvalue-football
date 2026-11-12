import pandas as pd
import pytest

from fairvalue.asof import LeakageError
from fairvalue.features import player_season, transfer
from fairvalue.features.positions import resolve_group

D = pd.Timestamp


# ----------------------------------------------------------------------------- positions
@pytest.mark.parametrize(
    "tm, us, expected",
    [
        ("ST", None, ("ST", "tm_current")),  # no Understat: keep label
        ("ST", "F M S", ("ST", "tm_current_confirmed")),
        ("ST", "D S", ("CB", "understat_season")),  # only ever used in defence that season
        ("AM_W", "D M", ("AM_W", "tm_current_confirmed")),  # M compatible with AM_W
        ("UNK", "M", ("CM", "understat_season")),
    ],
)
def test_resolve_group(tm, us, expected):
    assert resolve_group(tm, us) == expected


# ----------------------------------------------------------------------------- player-season
def test_team_strength(games):
    s = player_season.team_strength(games).set_index(["club_id", "season"])
    ars = s.loc[(11, 2018)]
    assert ars.team_games == 3 and ars.pts == 4  # W, D, L
    assert ars.team_gd_pg == pytest.approx((1 + 0 - 2) / 3)


def test_player_season_rows_are_as_of_season_end(apps, games, players, no_understat):
    ps = player_season.build(apps, games, players, no_understat).set_index("season")
    row = ps.loc[2019]
    assert row.as_of_date == D("2020-07-27")  # day after the delayed 2019/20 final round
    assert row.minutes == 270 and row.minutes_share == pytest.approx(1.0)
    assert row.data_tier == "basic" and row.position_group == "ST"
    assert row.prev_minutes == 270 and row.prev_goals_p90 == pytest.approx(1.0)  # from 2018/19
    assert pd.isna(ps.loc[2018].prev_minutes)
    assert row.age == pytest.approx((D("2020-07-27") - D("1995-07-01")).days / 365.25)


# ----------------------------------------------------------------------------- transfers
def _transfer(date, season):
    return pd.DataFrame({
        "transfer_id": [1], "player_id": [1], "date": [D(date)], "season": [season],
        "window": ["summer"], "fee_eur": [30e6], "fee_status": ["paid"], "move_type": ["paid_transfer"],
        "from_competition_id": ["GB1"], "to_competition_id": ["IT1"],
    })  # fmt: skip


def test_market_value_strictly_before_transfer(valuations):
    t = _transfer("2020-07-01", 2020)
    pit = transfer.point_in_time_values(t, valuations).iloc[0]
    assert pit.mv_pit_eur == 20e6  # the 2020-07-01 valuation is same-day: excluded
    assert pit.mv_pit_age_days == (D("2020-07-01") - D("2020-01-15")).days
    assert pit.mv_12m_before_eur == 10e6


def test_recent_form_window(apps):
    t = _transfer("2020-07-01", 2020)
    f = transfer.recent_form(t, apps).iloc[0]
    # 2019/20 games on 2020-05-27 and 2020-06-26 are inside; 2020-07-26 is after the transfer
    assert f.tm365_apps == 2 and f.tm365_last_app_date < D("2020-07-01")


def test_feature_season_falls_back_when_season_unfinished(apps, games):
    # 1 July 2020: the 2019/20 Premier League only ended on 26 July -> use 2018/19
    early = transfer.feature_season(_transfer("2020-07-01", 2020), apps, games).iloc[0]
    assert early.feat_season == 2018
    late = transfer.feature_season(_transfer("2020-08-10", 2020), apps, games).iloc[0]
    assert late.feat_season == 2019


def _build(apps, games, valuations, players, no_understat, date="2020-07-01"):
    cov = pd.DataFrame({"competition_id": ["GB1"], "season": [2018], "status": ["final"]})
    return transfer.build(_transfer(date, 2020), apps, games, valuations, players, no_understat, cov)


def test_future_spike_does_not_change_transfer_features(apps, games, valuations, players, no_understat):
    base = _build(apps, games, valuations, players, no_understat)
    spike_apps = pd.concat([apps, apps.tail(1).assign(date=D("2020-07-05"), goals=50, game_id=999)])
    spike_val = pd.concat([valuations, pd.DataFrame({"player_id": [1], "date": [D("2020-07-02")],
                                                     "value_eur": [1e9]})])  # fmt: skip
    spiked = _build(spike_apps, games, spike_val, players, no_understat)
    pd.testing.assert_frame_equal(base, spiked)


def test_funnel_flags(apps, games, valuations, players, no_understat):
    f = _build(apps, games, valuations, players, no_understat).iloc[0]
    assert f.F1 and f.F2 and f.F3 and f.F4  # big-five, played 2018/19, archived
    assert not f.F5 and not f.usable_full  # no Understat match
    assert not f.usable_basic  # only 180 TM minutes in the prior 365 days


def test_point_in_time_assertion_catches_leaks():
    bad = pd.DataFrame(
        {
            "date": [D("2020-07-01")],
            "mv_pit_date": [D("2020-07-01")],  # same-day valuation: a leak
            "tm365_last_app_date": [D("2020-06-01")],
            "feat_season_end": [D("2020-05-01")],
        }
    )
    with pytest.raises(LeakageError, match="mv_pit_date"):
        transfer.assert_point_in_time(bad)
