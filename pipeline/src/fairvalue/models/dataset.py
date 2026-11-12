"""Modelling dataset for the performance-implied value (PIV) model.

Unit: player x league x season (outfield, >= 900 league minutes).

Target: log of the player's Transfermarkt market value at the FIRST valuation
published after his league's season ended (within 120 days), relative to that
summer's market level:

    y = log(MV_after_season) - log(market_index[season])

market_index = median post-season value of eligible big-five outfield players
that summer. This turns a 2016 and a 2024 valuation into comparable numbers, so
the model learns how profiles are priced RELATIVE to the market, not the
market's inflation.

Why using that summer's index is not leakage: PIV is a cross-sectional
("same market") valuation that is compared with market values from the very
same summer. It is not a forecast of future prices. Features themselves only
use data up to the season end (see fairvalue.features).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fairvalue.config import BIG5, MIN_MINUTES_FOR_ESTIMATE

TARGET_WINDOW_DAYS = 120

BASE_NUM = [
    "age", "age2", "minutes_share", "starts_share", "team_ppg", "team_gd_pg", "log_prev_minutes", "n_clubs",
    "league_mv_level",
]  # fmt: skip
BASIC_RATES = ["goals_p90_shrunk", "assists_p90_shrunk", "prev_goals_p90", "prev_assists_p90"]
FULL_RATES = [
    "npxg_p90_shrunk", "xa_p90_shrunk", "shots_p90_shrunk", "key_passes_p90_shrunk",
    "xg_chain_p90_shrunk", "xg_buildup_p90_shrunk", "prev_npxg_p90", "prev_xa_p90",
]  # fmt: skip
CATEGORICAL = ["position_group", "competition_id"]

FEATURES = {
    "basic": {"numeric": BASE_NUM + BASIC_RATES, "categorical": CATEGORICAL},
    "full": {"numeric": BASE_NUM + BASIC_RATES + FULL_RATES, "categorical": CATEGORICAL},
}


def attach_target(ps: pd.DataFrame, valuations: pd.DataFrame, window_days: int = TARGET_WINDOW_DAYS) -> pd.DataFrame:
    """First valuation on/after as_of_date (season end + 1 day), within the window."""
    v = valuations.rename(columns={"date": "target_date", "value_eur": "target_mv_eur"}).sort_values("target_date")
    left = ps.sort_values("as_of_date")
    out = pd.merge_asof(left, v, left_on="as_of_date", right_on="target_date", by="player_id",
                        direction="forward", tolerance=pd.Timedelta(days=window_days))  # fmt: skip
    return out.sort_index()


def market_index(df: pd.DataFrame) -> pd.Series:
    """season -> median post-season market value of eligible big-five outfield players."""
    ref = df[df.competition_id.isin(BIG5) & df.target_mv_eur.notna()]
    return ref.groupby("season").target_mv_eur.median().rename("market_index_eur")


def league_market_level(df: pd.DataFrame, valuations: pd.DataFrame) -> pd.DataFrame:
    """competition_id, season -> league_mv_level (log scale, known at season end).

    Median of players' latest market values dated strictly BEFORE the season
    ended, relative to the same statistic for the big five. Leagues drift a lot
    relative to the big five (Portugal's typical player fell ~1.6 log points
    2013-2019; Russia fell after 2022), so a league coefficient learned from
    earlier seasons goes stale. This aggregate over hundreds of players tracks
    it point-in-time; any single player's own value barely moves it.
    """
    v = valuations.rename(columns={"date": "pre_date", "value_eur": "pre_mv"}).sort_values("pre_date")
    left = df[["player_id", "competition_id", "season", "as_of_date"]].sort_values("as_of_date")
    pre = pd.merge_asof(left, v, left_on="as_of_date", right_on="pre_date", by="player_id", direction="backward",
                        allow_exact_matches=False, tolerance=pd.Timedelta(days=365))  # fmt: skip
    pre = pre.dropna(subset=["pre_mv"]).assign(log_mv=lambda d: np.log(d.pre_mv))
    league = pre.groupby(["competition_id", "season"]).log_mv.median()
    big5 = pre[pre.competition_id.isin(BIG5)].groupby("season").log_mv.median()
    out = (league - big5.reindex(league.index.get_level_values("season")).to_numpy()).rename("league_mv_level")
    return out.reset_index()


def build(ps: pd.DataFrame, profiles: pd.DataFrame, valuations: pd.DataFrame) -> pd.DataFrame:
    """All outfield player-seasons with >= 900 minutes, with features, target and index."""
    keys = ["player_id", "season", "competition_id"]
    shrunk = [c for c in profiles.columns if c.endswith("_shrunk")]
    df = ps.merge(profiles[keys + shrunk], on=keys, how="left")
    df = df[(df.minutes >= MIN_MINUTES_FOR_ESTIMATE) & ~df.position_group.isin(["GK", "UNK"])].copy()
    df["age2"] = df.age**2
    df["log_prev_minutes"] = np.log1p(df.prev_minutes.fillna(0))
    df = df.merge(league_market_level(df, valuations), on=["competition_id", "season"], how="left")
    df = attach_target(df.reset_index(drop=True), valuations)
    df = df.join(market_index(df), on="season")
    df["y"] = np.log(df.target_mv_eur) - np.log(df.market_index_eur)
    df["minutes_band"] = np.where(df.minutes >= 1800, "1800+", "900-1799")
    df["line"] = df.position_group.map({"CB": "DEF", "FB": "DEF", "CM": "MID", "AM_W": "ATT", "ST": "ATT"})
    return df.reset_index(drop=True)


def tier_frame(df: pd.DataFrame, tier: str) -> pd.DataFrame:
    """Rows a tier's model can score. Full tier = Understat-matched big-five rows."""
    if tier == "full":
        return df[df.data_tier == "full"].reset_index(drop=True)
    return df.reset_index(drop=True)  # basic features exist for every row
