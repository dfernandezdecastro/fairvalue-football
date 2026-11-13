import numpy as np
import pandas as pd
import pytest

from fairvalue.models import club_audit, gems_backtest
from fairvalue.models import expected_fee as ef

D = pd.Timestamp


# ----------------------------------------------------------------------------- expected fee features
def test_club_flow_counts_only_the_previous_365_days():
    paid = pd.DataFrame({"to_club_id": [7, 7, 7, 7], "fee_eur": [1.0, 2.0, 4.0, 8.0],
                         "date": [D("2022-06-01"), D("2023-03-01"), D("2023-07-01"), D("2023-08-01")]})  # fmt: skip
    t = pd.DataFrame({"transfer_id": [1], "to_club_id": [7], "date": [D("2023-07-01")]})
    # 2022-06-01 is more than a year before; 2023-07-01 is the same day (excluded); 2023-08-01 is later
    assert ef.club_flow_365(t, paid, "to_club_id")[0] == 2.0


def test_market_premium_level_uses_earlier_months_only():
    past = pd.DataFrame({"date": pd.date_range("2023-01-01", periods=60, freq="D"), "y": 0.3})
    now = pd.DataFrame({"date": [D("2023-07-15"), D("2023-07-20")], "y": [5.0, 5.0]})
    df = pd.concat([past, now], ignore_index=True)
    lvl = ef.market_premium_level(df)
    assert lvl.iloc[-1] == pytest.approx(0.3)  # July's own transfers (y=5) don't count
    assert np.isnan(lvl.iloc[0])  # nothing in the 12 months before January 2023


def test_deadline_week():
    d = pd.Series([D("2023-08-31"), D("2023-09-01"), D("2024-01-30"), D("2023-07-15")])
    assert ef.is_deadline_week(d).tolist() == [1, 1, 1, 0]


def test_piv_for_transfers_prefers_full_tier_of_the_feature_season():
    piv = pd.DataFrame({
        "player_id": [1, 1, 1], "season": [2022, 2022, 2023], "model_tier": ["basic", "full", "full"],
        "minutes": [2500, 2500, 2500], "estimate_eur": [10e6, 20e6, 99e6], "market_index_eur": [10e6] * 3,
    })  # fmt: skip
    out = ef.piv_for_transfers(pd.DataFrame({"player_id": [1], "feat_season": [2022]}), piv).iloc[0]
    assert out.piv_full == 1 and out.piv_rel_log == pytest.approx(np.log(2.0))


@pytest.mark.parametrize(
    "y, expected",
    [(0.3, "Within expected range"), (0.6, "Notable transfer premium"), (1.0, "Unusual transfer premium"),
     (-0.6, "Notable fee discount"), (-1.0, "Unusually low fee")],
)  # fmt: skip
def test_fee_label_from_interval(y, expected):
    assert ef.fee_label(y, -0.5, 0.5, -0.9, 0.9) == expected


def test_fee_reliability():
    assert ef.reliability(False, 1, 2000, 30)[0] == "Insufficient"
    assert ef.reliability(True, 1, 2000, 30)[0] == "High"
    assert ef.reliability(True, 0, 2000, 30)[0] == "Moderate"
    assert ef.reliability(True, 1, 2000, 300)[0] == "Moderate"  # market value too old for High
    assert ef.reliability(True, 1, 100, 30)[0] == "Low"


# ----------------------------------------------------------------------------- club audit
def test_bootstrap_ratio_brackets_the_point_estimate():
    rng = np.random.default_rng(0)
    fee = rng.uniform(1, 10, 30)
    exp = fee * rng.uniform(0.7, 1.1, 30)
    lo, hi = club_audit.bootstrap_ratio(fee, exp, rng)
    assert lo < fee.sum() / exp.sum() < hi


def test_club_audit_rows_and_ranking_threshold():
    n = 10
    fees = pd.DataFrame({
        "transfer_id": range(n), "player_id": range(n), "date": [D("2023-07-01")] * n, "season": 2023,
        "to_club_id": [1] * 9 + [2], "to_club_name": ["A"] * 9 + ["B"], "fee_eur": 10e6,
        "expected_fee_eur": 8e6, "mv_pit_eur": 9e6, "reliability": "High", "label": "Within expected range",
    })  # fmt: skip
    vals = pd.DataFrame({"player_id": range(n), "date": [D("2024-07-20")] * n, "value_eur": 18e6})
    a = club_audit.build(fees, vals).set_index(["club_name", "period"])
    assert a.loc[("A", "all"), "ranked"] and not a.loc[("B", "all"), "ranked"]
    assert a.loc[("A", "all"), "price_ratio"] == pytest.approx(1.25)
    assert a.loc[("A", "all"), "outcome_median_mv_change_12m"] == pytest.approx(1.0)  # 9M -> 18M


# ----------------------------------------------------------------------------- hidden gems backtest
def test_backtest_recovers_a_known_effect():
    rng = np.random.default_rng(1)
    n = 600
    label = rng.choice(["Potential undervaluation", "Within expected range"], n, p=[0.3, 0.7])
    target_date = D("2022-06-10")
    piv = pd.DataFrame({
        "player_id": range(n), "season": 2021, "competition_id": "GB1", "model_tier": "full",
        "gap_label": label, "reliability": "High", "target_date": target_date,
        "target_mv_eur": rng.uniform(1e6, 50e6, n), "position_group": rng.choice(["ST", "CB"], n),
    })  # fmt: skip
    rise = np.where(label == "Potential undervaluation", 0.20, 0.0) + rng.normal(0, 0.05, n)
    vals = pd.DataFrame({"player_id": range(n), "date": target_date + pd.Timedelta(days=370),
                         "value_eur": piv.target_mv_eur * np.exp(rise)})  # fmt: skip
    ps = pd.DataFrame({"player_id": range(n), "season": 2021, "competition_id": "GB1", "age": 25.0})
    res = gems_backtest.run(piv, vals, ps)
    assert res["pooled"]["under"]["median_excess_pct"] == pytest.approx(22.1, abs=2.0)  # exp(0.2)-1
    lo, hi = res["pooled"]["under"]["ci80_pct"]
    assert lo > 15 and res["pooled"]["under"]["share_beating_peers"] > 0.95


def test_club_audit_one_row_per_club_even_with_two_spellings():
    fees = pd.DataFrame({
        "transfer_id": range(10), "player_id": range(10), "date": [D("2023-07-01")] * 10, "season": 2023,
        "to_club_id": 12, "to_club_name": ["Roma"] * 6 + ["AS Roma"] * 4, "fee_eur": 10e6,
        "expected_fee_eur": 8e6, "mv_pit_eur": 9e6, "reliability": "High", "label": "Within expected range",
    })  # fmt: skip
    vals = pd.DataFrame({"player_id": range(10), "date": [D("2024-07-01")] * 10, "value_eur": 9e6})
    a = club_audit.build(fees, vals)
    assert len(a[a.period == "all"]) == 1 and a.club_name.iat[0] == "Roma"


def test_club_audit_ranks_only_clubs_from_covered_leagues():
    n = 10
    fees = pd.DataFrame({
        "transfer_id": range(n), "player_id": range(n), "date": [D("2023-07-01")] * n, "season": 2023,
        "to_club_id": [1] * 9 + [2], "to_club_name": ["A"] * 9 + ["B"], "fee_eur": 10e6,
        "expected_fee_eur": 8e6, "mv_pit_eur": 9e6, "reliability": "High", "label": "Within expected range",
    })  # fmt: skip
    vals = pd.DataFrame({"player_id": range(n), "date": [D("2024-07-20")] * n, "value_eur": 9e6})
    a = club_audit.build(fees, vals, covered_club_ids={2}).set_index(["club_name", "period"])
    assert not a.loc[("A", "all"), "ranked"]  # 9 purchases but never in a covered league (e.g. a reserve team)
