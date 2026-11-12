"""Feasibility PROBE - not the production model.

Question: is there enough signal in the data we can actually obtain to justify
each candidate modelling target? Quick, untuned models; temporal split only.

  Population A (fees, Understat features): usable transfers from build_usable.py
  Population B (fees, TM-only features):   alt_tm_only_usable transfers
  Population C (market values, Understat): player-seasons -> TM value after season end

Split: train on seasons 2015/16-2021/22, test on 2022/23-2025/26 (never shuffled).
Note: players.international_caps is a CURRENT snapshot (leaks the future), so it
is deliberately excluded.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from common import BIG5, INTERIM, REPORTS, read  # noqa: E402

TEST_FROM = 2022
P90 = ["goals", "xG", "npxG", "assists", "xA", "shots", "key_passes", "xGChain", "xGBuildup"]


def metrics(y, p) -> dict:
    fee, hat = np.exp(y), np.exp(p)
    ape = np.abs(hat - fee) / fee
    return dict(n=len(y), MAE_log=round(mean_absolute_error(y, p), 3), R2_log=round(r2_score(y, p), 3),
                median_APE=f"{np.median(ape):.0%}", within_25pct=f"{np.mean(ape <= 0.25):.0%}",
                within_50pct=f"{np.mean(ape <= 0.5):.0%}")


def fit_eval(df, num, cat, target, label, rows, model="both"):
    df = df.copy()
    df[cat] = df[cat].fillna("missing").astype(str)
    tr, te = df[df.season < TEST_FROM], df[df.season >= TEST_FROM]
    pre = ColumnTransformer([("n", StandardScaler(), num),
                             ("c", OneHotEncoder(handle_unknown="ignore", min_frequency=10), cat)])
    if model in ("both", "ridge"):
        m = make_pipeline(pre, RidgeCV(alphas=np.logspace(-2, 3, 20)))
        m.fit(tr[num + cat].fillna(0), tr[target])
        rows.append(dict(model=f"{label} | Ridge", train_n=len(tr),
                         **metrics(te[target].values, m.predict(te[num + cat].fillna(0)))))
    if model in ("both", "gbm"):
        g = make_pipeline(ColumnTransformer([("n", "passthrough", num),
                                             ("c", OneHotEncoder(handle_unknown="ignore", min_frequency=10,
                                                                 sparse_output=False), cat)]),
                          HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05,
                                                        min_samples_leaf=20, random_state=0))
        g.fit(tr[num + cat], tr[target])
        rows.append(dict(model=f"{label} | GBM", train_n=len(tr),
                         **metrics(te[target].values, g.predict(te[num + cat]))))


def baseline(df, target, label, rows):
    tr, te = df[df.season < TEST_FROM], df[df.season >= TEST_FROM]
    key = lambda d: d.sub_position.fillna("?") + "|" + pd.cut(d.age, [0, 21, 24, 27, 30, 50]).astype(str)
    med = tr.groupby(key(tr))[target].median()
    p = key(te).map(med).fillna(tr[target].median())
    rows.append(dict(model=f"{label} | naive median (position x age)", train_n=len(tr),
                     **metrics(te[target].values, p.values)))


def prep_transfer_features(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["y"] = np.log(t.transfer_fee)
    t["log_mv"] = np.log(t.mv_pit_eur)
    t["log_mv12"] = np.log(t.mv_12m_before_eur)
    t["age2"] = t.age ** 2
    t["from_lg"] = t.from_league.fillna("non-covered")
    t["to_lg"] = t.to_league.fillna("non-covered")
    t["seller_big5"] = t.from_league.isin(BIG5).astype(int)
    t["buyer_big5"] = t.to_league.isin(BIG5).astype(int)
    for c in P90:
        t[f"{c}_p90"] = t[f"us_{c}"] / t.us_time * 90 if f"us_{c}" in t else np.nan
    t["tm_g_p90"] = t.tm365_goals / t.tm365_minutes.clip(lower=1) * 90
    t["tm_a_p90"] = t.tm365_assists / t.tm365_minutes.clip(lower=1) * 90
    return t


def market_value_panel() -> pd.DataFrame:
    """Population C: Understat season s -> TM market value at first valuation >= 1 June s+1."""
    us = pd.read_csv(INTERIM / "understat_players.csv")
    m = pd.read_csv(INTERIM / "understat_tm_matches.csv")
    m = m[m.confidence != "unmatched"][["understat_id", "league", "season", "tm_player_id"]]
    us = us.rename(columns={"id": "understat_id"}).merge(m, on=["understat_id", "league", "season"])
    agg = us.groupby(["tm_player_id", "season"]).agg(
        time=("time", "sum"), **{c: (c, "sum") for c in P90}, league=("league", "first")).reset_index()
    agg = agg[agg.time >= 900]
    for c in P90:
        agg[f"{c}_p90"] = agg[c] / agg.time * 90
    p = read("players", usecols=["player_id", "date_of_birth", "sub_position"])
    agg = agg.merge(p, left_on="tm_player_id", right_on="player_id")
    agg["ref"] = pd.to_datetime((agg.season + 1).astype(str) + "-06-01")
    agg["age"] = (agg.ref - pd.to_datetime(agg.date_of_birth)).dt.days / 365.25
    agg["age2"] = agg.age ** 2
    v = read("player_valuations", usecols=["player_id", "date", "market_value_in_eur"])
    v["vdate"] = pd.to_datetime(v.date)
    v = v.sort_values("vdate")
    agg = pd.merge_asof(agg.sort_values("ref"), v[["player_id", "vdate", "market_value_in_eur"]],
                        left_on="ref", right_on="vdate", by="player_id", direction="forward",
                        tolerance=pd.Timedelta(days=120))
    agg = agg.dropna(subset=["market_value_in_eur"])
    agg["y"] = np.log(agg.market_value_in_eur)
    return agg


def main() -> None:
    t = pd.read_csv(INTERIM / "transfers_funnel.csv", parse_dates=["date"])
    rows: list[dict] = []
    base_num = ["age", "age2", "season"]
    base_cat = ["sub_position", "from_lg", "to_lg", "window"]
    us_num = [f"{c}_p90" for c in P90] + ["us_time", "tm365_minutes"]

    A = prep_transfer_features(t[t.usable])
    baseline(A, "y", "A fees/Understat", rows)
    fit_eval(A, base_num + us_num, base_cat, "y", "A fees/Understat - performance only", rows)
    fit_eval(A, ["log_mv"], [], "y", "A fees/Understat - market value only", rows, model="ridge")
    fit_eval(A, base_num + us_num + ["log_mv"], base_cat, "y", "A fees/Understat - performance + market value", rows)

    B = prep_transfer_features(t[t.alt_tm_only_usable])
    tm_num = ["tm_g_p90", "tm_a_p90", "tm365_minutes"]
    baseline(B, "y", "B fees/TM-only", rows)
    fit_eval(B, base_num + tm_num, base_cat, "y", "B fees/TM-only - performance only", rows)
    fit_eval(B, ["log_mv"], [], "y", "B fees/TM-only - market value only", rows, model="ridge")
    fit_eval(B, base_num + tm_num + ["log_mv"], base_cat, "y", "B fees/TM-only - performance + market value", rows)

    C = market_value_panel()
    C["from_lg"], C["to_lg"], C["window"] = C.league, "n/a", "n/a"
    baseline(C, "y", "C market value/Understat", rows)
    fit_eval(C, base_num + [f"{c}_p90" for c in P90] + ["time"], ["sub_position", "league"], "y",
             "C market value/Understat - performance only", rows)

    res = pd.DataFrame(rows)
    print(res.to_string(index=False))
    # residual spread: how wide would honest intervals be?
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "probe_results.md").write_text(
        "# Predictive-signal probe (auto-generated by scripts/feasibility/probe_models.py)\n\n"
        f"Train seasons 2015/16-{TEST_FROM - 1}/{str(TEST_FROM)[-2:]}; test {TEST_FROM}/{str(TEST_FROM + 1)[-2:]}-2025/26. "
        "Untuned models. Targets on log scale; APE = |pred-actual|/actual in euros.\n\n"
        + res.to_markdown(index=False) + f"\n\nPopulation sizes: A={len(A)}, B={len(B)}, C={len(C)} player-seasons.\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
