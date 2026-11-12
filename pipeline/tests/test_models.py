import json

import numpy as np
import pandas as pd
import pytest

from fairvalue.models import dataset, explain, training, uncertainty

D = pd.Timestamp
NUM, CAT = ["x"], ["position_group"]


def synthetic(seasons=range(2014, 2022), n=300, shift=None, seed=0):
    """y = 0.8 x + noise (+ an optional per-season shift only visible in that season)."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in seasons:
        x = rng.normal(size=n)
        y = 0.8 * x + rng.normal(scale=0.3, size=n) + (shift or {}).get(s, 0.0)
        rows.append(pd.DataFrame({"season": s, "x": x, "y": y, "position_group": rng.choice(["ST", "CB"], n),
                                  "age": rng.uniform(18, 34, n)}))  # fmt: skip
    return pd.concat(rows, ignore_index=True)


# ----------------------------------------------------------------------------- target
def test_target_is_first_valuation_after_season_end_within_window():
    ps = pd.DataFrame({"player_id": [1, 2, 3], "as_of_date": [D("2024-05-26")] * 3})
    v = pd.DataFrame({
        "player_id": [1, 1, 1, 2, 3],
        "date": [D("2024-05-01"), D("2024-06-10"), D("2024-07-01"), D("2024-12-01"), D("2024-05-26")],
        "value_eur": [5e6, 8e6, 9e6, 7e6, 3e6],
    })  # fmt: skip
    out = dataset.attach_target(ps, v).set_index("player_id")
    assert out.loc[1, "target_mv_eur"] == 8e6  # May value is before season end: ignored
    assert np.isnan(out.loc[2, "target_mv_eur"])  # 189 days later: outside the 120-day window
    assert out.loc[3, "target_mv_eur"] == 3e6  # published on as_of_date itself: allowed for a target


def test_market_index_uses_big_five_only():
    df = pd.DataFrame({"season": [2023] * 4, "competition_id": ["GB1", "ES1", "NL1", "NL1"],
                       "target_mv_eur": [10e6, 20e6, 1e6, 1e6]})  # fmt: skip
    assert dataset.market_index(df).loc[2023] == 15e6


# ----------------------------------------------------------------------------- walk-forward
def test_walk_forward_starts_after_three_seasons_and_never_sees_the_test_season():
    shift = {2020: 5.0}  # only season 2020 is shifted; a leak-free model cannot know
    df = synthetic(shift=shift)
    res = training.walk_forward(df, "ridge", NUM, CAT)
    assert [r.season for r in res] == list(range(2017, 2022))
    p = training.predictions_frame(res).join(df.y)
    err_2020 = (p.y - p.y_hat)[p.season == 2020].mean()
    assert err_2020 == pytest.approx(5.0, abs=0.3)  # the canary: a leak would shrink this to ~0
    err_2019 = (p.y - p.y_hat)[p.season == 2019].mean()
    assert abs(err_2019) < 0.1


def test_metrics_known_values():
    y = pd.Series([np.log(100.0), np.log(100.0)])
    m = training.metrics(y, pd.Series([np.log(140.0), np.log(70.0)]))  # errors of 40% and 30%
    assert m["median_ape"] == pytest.approx(0.35) and m["within_50pct"] == 1.0 and m["within_25pct"] == 0.0


# ----------------------------------------------------------------------------- uncertainty
def test_conformal_intervals_reach_nominal_coverage():
    rng = np.random.default_rng(1)
    cal = pd.DataFrame({"minutes_band": "1800+", "line": "ATT", "r": rng.standard_t(5, 3000)})
    test = pd.DataFrame({"minutes_band": "1800+", "line": "ATT", "y_hat": 0.0, "r": rng.standard_t(5, 3000)})
    out = uncertainty.apply_intervals(test, uncertainty.calibrate(cal))
    inside80 = ((out.r >= out["80_lo"]) & (out.r <= out["80_hi"])).mean()
    inside95 = ((out.r >= out["95_lo"]) & (out.r <= out["95_hi"])).mean()
    assert inside80 == pytest.approx(0.80, abs=0.03) and inside95 == pytest.approx(0.95, abs=0.02)


def test_small_groups_fall_back_to_coarser_calibration():
    rng = np.random.default_rng(2)
    cal = pd.concat([
        pd.DataFrame({"minutes_band": "1800+", "line": "ATT", "r": rng.normal(size=200)}),
        pd.DataFrame({"minutes_band": "1800+", "line": "DEF", "r": rng.normal(size=20)}),  # too few
    ])  # fmt: skip
    rows = pd.DataFrame({"minutes_band": ["1800+", "1800+"], "line": ["ATT", "DEF"], "y_hat": [0.0, 0.0]})
    out = uncertainty.apply_intervals(rows, uncertainty.calibrate(cal))
    assert out.calibration_group.tolist() == ["1800+/ATT", "1800+"]


@pytest.mark.parametrize(
    "tier, minutes, group, calibrated, expected",
    [
        ("full", 2500, "ST", True, "High"),
        ("full", 1200, "ST", True, "Moderate"),
        ("basic", 2500, "AM_W", True, "Moderate"),
        ("basic", 1200, "CM", True, "Low"),
        ("full", 2500, "CB", True, "Moderate"),  # defensive work not measured: one level down
        ("basic", 1200, "FB", True, "Insufficient"),
        ("full", 2500, "GK", True, "Insufficient"),
        ("full", 2500, "ST", False, "Insufficient"),
    ],
)
def test_reliability_rules(tier, minutes, group, calibrated, expected):
    assert uncertainty.reliability(tier, minutes, group, calibrated)[0] == expected


def test_gap_label_uses_interval_not_sign():
    # market value above the estimate but inside the 80% range: no premium label
    assert uncertainty.gap_label(0.2, -0.5, 0.5, -0.9, 0.9) == "Within expected range"
    assert uncertainty.gap_label(-0.6, -0.5, 0.5, -0.9, 0.9) == "Potential undervaluation"
    assert uncertainty.gap_label(-1.0, -0.5, 0.5, -0.9, 0.9) == "Strong signal of potential undervaluation"
    assert uncertainty.gap_label(0.6, -0.5, 0.5, -0.9, 0.9) == "Market premium"
    assert uncertainty.gap_label(np.nan, -0.5, 0.5, -0.9, 0.9) is None


# ----------------------------------------------------------------------------- explanations
def test_ridge_contributions_add_up_to_prediction():
    df = synthetic(seasons=[2020], n=200)
    df["age2"] = df.age**2
    model = training.make_ridge(["x", "age", "age2"], CAT, alpha=1.0).fit(df[["x", "age", "age2"] + CAT], df.y)
    X = df[["x", "age", "age2"] + CAT]
    contrib, base = explain.contributions(model, X)
    np.testing.assert_allclose(contrib.sum(axis=1) + base, model.predict(X), atol=1e-8)
    assert {"Age", "Position"} <= set(contrib.columns)
    top = json.loads(explain.drivers_json(contrib.iloc[0]))
    assert top[0]["pct"] == pytest.approx((np.exp(top[0]["log"]) - 1) * 100, abs=0.1)


def test_gbm_shap_contributions_add_up_to_prediction():
    df = synthetic(seasons=[2020], n=300)
    model = training.make_gbm(NUM, CAT, max_iter=50).fit(df[NUM + CAT], df.y)
    contrib, base = explain.contributions(model, df[NUM + CAT])
    np.testing.assert_allclose(contrib.sum(axis=1) + base, model.predict(df[NUM + CAT]), atol=1e-6)


def test_recentre_pins_anchor_median_without_targets():
    pred = np.array([0.5, 0.7, 0.9, 3.0, -2.0])
    anchor = np.array([True, True, True, False, False])
    out, offset = training.recentre(pred, anchor)
    assert offset == pytest.approx(0.7) and np.median(out[anchor]) == pytest.approx(0.0)
    assert training.recentre(pred, None)[1] == 0.0


def test_recentring_removes_market_shape_drift():
    # later seasons: same profiles, but everyone below the median loses value (market gets more unequal)
    df = synthetic(seasons=range(2014, 2022))
    late = df.season >= 2019
    df.loc[late, "y"] = np.where(df.loc[late, "x"] < 0, df.loc[late, "y"] - 1.0, df.loc[late, "y"])
    df.loc[late, "y"] -= df.loc[late].groupby("season").y.transform("median")  # target median stays 0
    anchor = pd.Series(True, index=df.index)
    raw = training.predictions_frame(training.walk_forward(df, "ridge", NUM, CAT)).join(df.y)
    rec = training.predictions_frame(training.walk_forward(df, "ridge", NUM, CAT, anchor=anchor)).join(df.y)
    bias = lambda p: abs((p.y - p.y_hat)[p.season == 2019].median())  # noqa: E731
    assert bias(rec) < bias(raw)


def test_league_market_level_uses_only_values_before_season_end():
    asof = D("2024-05-26")
    df = pd.DataFrame({"player_id": [1, 2, 3, 4], "competition_id": ["GB1", "GB1", "NL1", "NL1"],
                       "season": 2023, "as_of_date": asof})  # fmt: skip
    v = pd.DataFrame({
        "player_id": [1, 2, 3, 4, 3],
        "date": [D("2024-03-01"), D("2024-03-01"), D("2024-03-01"), D("2024-03-01"), D("2024-06-01")],
        "value_eur": [20e6, 20e6, 2e6, 2e6, 500e6],  # player 3's post-season value must be ignored
    })  # fmt: skip
    lvl = dataset.league_market_level(df, v).set_index("competition_id").league_mv_level
    assert lvl["GB1"] == pytest.approx(0.0) and lvl["NL1"] == pytest.approx(np.log(0.1))
