"""Hidden Gems backtest: did players flagged as potential undervaluation gain value afterwards?

For every walk-forward PIV season, take players with a peer-relative gap label
and reliability High or Moderate. Outcome: change in market value from the
post-season valuation (the one the label was based on) to the valuation
closest to 12 months later (+/- 90 days).

Comparison: each player's change is measured against the median change of
"Within expected range" players in the same stratum (season x position group x
age band x market-value tercile), the "excess change". This controls for the
obvious confounders: young players and cheap players rise more on average.

Published as is, whatever it shows (spec 4.5). Caveats: survivors only (no
later valuation, e.g. retired, means no outcome); market values are crowd
opinion, so "rose" means the crowd revised up, not that the player was
objectively worth more.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

UNDER = {"Potential undervaluation", "Strong signal of potential undervaluation"}
PREMIUM = {"Market premium", "Unusual market premium"}
BOOTSTRAP = 2000


def outcomes(piv: pd.DataFrame, valuations: pd.DataFrame, days: int = 365, tol: int = 90) -> pd.DataFrame:
    p = piv[piv.gap_label.notna() & piv.reliability.isin(["High", "Moderate"]) & piv.target_date.notna()].copy()
    # one row per player-season: the full (xG-level) tier when available ("full" sorts after "basic")
    p = p.sort_values("model_tier", ascending=False).drop_duplicates(["player_id", "season", "competition_id"])
    p["when"] = p.target_date + pd.Timedelta(days=days)
    v = valuations.rename(columns={"date": "v_date", "value_eur": "mv_after"}).sort_values("v_date")
    m = pd.merge_asof(p.sort_values("when"), v, left_on="when", right_on="v_date", by="player_id",
                      direction="nearest", tolerance=pd.Timedelta(days=tol))  # fmt: skip
    m["change_log"] = np.log(m.mv_after / m.target_mv_eur)
    m["group"] = np.select([m.gap_label.isin(UNDER), m.gap_label.isin(PREMIUM)], ["under", "premium"], "within")
    return m


def excess_change(m: pd.DataFrame) -> pd.DataFrame:
    m = m[m.change_log.notna()].copy()
    m["age_band"] = pd.cut(m.age, [0, 21, 24, 27, 30, 50]).astype(str)
    m["mv_tercile"] = m.groupby("season").target_mv_eur.transform(
        lambda s: pd.qcut(s, 3, labels=False, duplicates="drop")
    )
    keys = ["season", "position_group", "age_band", "mv_tercile"]
    base = m[m.group == "within"].groupby(keys).change_log.median().rename("stratum_median")
    m = m.join(base, on=keys)
    m["excess"] = m.change_log - m.stratum_median
    return m[m.excess.notna()]


def _summary(x: pd.Series, rng: np.random.Generator) -> dict:
    if len(x) < 20:
        return {"n": int(len(x))}
    boots = np.median(rng.choice(x.to_numpy(), size=(BOOTSTRAP, len(x))), axis=1)
    return {
        "n": int(len(x)),
        "median_excess_pct": round(float(np.expm1(np.median(x))) * 100, 1),
        "ci80_pct": [
            round(float(np.expm1(np.quantile(boots, 0.1))) * 100, 1),
            round(float(np.expm1(np.quantile(boots, 0.9))) * 100, 1),
        ],  # fmt: skip
        "share_beating_peers": round(float((x > 0).mean()), 3),
    }


def run(piv: pd.DataFrame, valuations: pd.DataFrame, player_seasons: pd.DataFrame, seed: int = 0) -> dict:
    keys = ["player_id", "season", "competition_id"]
    piv = piv.merge(player_seasons[[*keys, "age"]], on=keys, how="left")
    m = outcomes(piv, valuations)
    e = excess_change(m)
    rng = np.random.default_rng(seed)
    result = {
        "players_with_label": int(len(m)),
        "players_with_outcome": int(m.change_log.notna().sum()),
        "pooled": {g: _summary(e.loc[e.group == g, "excess"], rng) for g in ("under", "premium", "within")},
        "by_season": {
            int(s): {g: _summary(gg.loc[gg.group == g, "excess"], rng) for g in ("under", "premium")}
            for s, gg in e.groupby("season")
        },
        "strong_signal_only": _summary(
            e.loc[e.gap_label == "Strong signal of potential undervaluation", "excess"], rng
        ),
    }
    return result
