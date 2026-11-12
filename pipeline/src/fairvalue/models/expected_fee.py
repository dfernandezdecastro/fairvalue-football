"""Layer 3: Expected Fee. `fairvalue train-fee`.

Question: "given everything public at the transfer date, what fee did
comparable deals command?" The model predicts the PREMIUM over the
point-in-time market value:

    y = log(fee / market value before the transfer)
    expected fee = market value x exp(prediction)

Anchoring on market value (by far the strongest public signal; feasibility
probe R^2 0.72) means the model learns systematic deviations: buyer power,
deadline pressure, age, league routes, market cycles, performance.

Point-in-time features only (rule R2):
* market value strictly before the transfer, and its 12-month trend
* performance-implied relative value (Layer 2) for the last season that had
  FINISHED before the transfer (the relative version needs no later valuations)
* buyer's fees paid / seller's fees received in the 365 days before
* market premium level: median log(fee / value) over the previous 12 months,
  computed per calendar month from transfers dated before that month
* recent playing time and output, age, position, leagues, window, deadline week
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fairvalue.config import BIG5, MIN_MINUTES_FOR_ESTIMATE
from fairvalue.features.transfer import MAX_MV_AGE_DAYS

NUMERIC = [
    "log_mv", "mv_trend", "age", "age2", "piv_rel_log", "piv_full", "log_tm365_minutes", "tm365_ga_p90",
    "log_buyer_spend_365", "log_seller_sales_365", "market_premium_level", "deadline_week",
]  # fmt: skip
CATEGORICAL = ["position_group", "to_lg", "from_lg", "window"]
FEE_HIERARCHY = [["mv_band", "buyer_big5"], ["mv_band"], []]
DRIVER_GROUPS = {
    "Market value size": ["log_mv"],
    "Market value trend": ["mv_trend"],
    "Performance-implied value": ["piv_rel_log", "piv_full"],
    "Age": ["age", "age2"],
    "Position": ["position_group"],
    "Buying club": ["to_lg", "log_buyer_spend_365"],
    "Selling club": ["from_lg", "log_seller_sales_365"],
    "Market cycle": ["market_premium_level"],
    "Timing": ["window", "deadline_week"],
    "Recent playing time": ["log_tm365_minutes", "tm365_ga_p90"],
}


def club_flow_365(t: pd.DataFrame, paid: pd.DataFrame, club_col: str) -> pd.Series:
    """Sum of paid fees involving `club_col` in (date - 365 days, date): strictly before the transfer."""
    flows = paid[[club_col, "date", "fee_eur"]].sort_values("date")
    flows["cum"] = flows.groupby(club_col).fee_eur.cumsum()
    left = t[["transfer_id", club_col, "date"]].sort_values("date")
    before = pd.merge_asof(left, flows[[club_col, "date", "cum"]], on="date", by=club_col,
                           allow_exact_matches=False)  # fmt: skip
    year_ago = pd.merge_asof(left.assign(date=left.date - pd.Timedelta(days=365)),
                             flows[[club_col, "date", "cum"]], on="date", by=club_col)  # fmt: skip
    total = before.cum.fillna(0).to_numpy() - year_ago.cum.fillna(0).to_numpy()
    return pd.Series(np.clip(total, 0, None), index=before.transfer_id.to_numpy()).reindex(t.transfer_id).to_numpy()


def market_premium_level(df: pd.DataFrame) -> pd.Series:
    """Median y over transfers dated in the 12 months before the transfer's calendar month."""
    month = df.date.dt.to_period("M")
    out = pd.Series(np.nan, index=df.index)
    for m in month.unique():
        start = m.to_timestamp()
        past = df[(df.date < start) & (df.date >= start - pd.DateOffset(months=12))]
        if len(past) >= 50:
            out[month == m] = past.y.median()
    return out


def is_deadline_week(d: pd.Series) -> pd.Series:
    summer = (d.dt.month == 8) & (d.dt.day >= 25) | (d.dt.month == 9) & (d.dt.day <= 2)
    winter = (d.dt.month == 1) & (d.dt.day >= 25) | (d.dt.month == 2) & (d.dt.day <= 2)
    return (summer | winter).astype(int)


def piv_for_transfers(t: pd.DataFrame, piv: pd.DataFrame) -> pd.DataFrame:
    """Latest finished season's relative PIV (full tier preferred, then most minutes)."""
    p = piv.assign(piv_rel_log=np.log(piv.estimate_eur / piv.market_index_eur),
                   piv_full=(piv.model_tier == "full").astype(int)).dropna(subset=["piv_rel_log"])  # fmt: skip
    p = p.sort_values(["piv_full", "minutes"], ascending=False).drop_duplicates(["player_id", "season"])
    keys = p[["player_id", "season", "piv_rel_log", "piv_full"]].rename(columns={"season": "feat_season"})
    return t.merge(keys, on=["player_id", "feat_season"], how="left")


def build(tf: pd.DataFrame, piv: pd.DataFrame, transfers: pd.DataFrame) -> pd.DataFrame:
    df = tf[tf.F1 & (tf.mv_pit_age_days <= MAX_MV_AGE_DAYS) & (tf.fee_eur > 0)].copy()
    df = df.merge(transfers[["transfer_id", "from_club_id", "to_club_id", "from_club_name", "to_club_name"]],
                  on="transfer_id", how="left")  # fmt: skip
    df["y"] = np.log(df.fee_eur / df.mv_pit_eur)
    df["log_mv"] = np.log(df.mv_pit_eur)
    df["mv_trend"] = np.log(df.mv_pit_eur / df.mv_12m_before_eur)
    df["age2"] = df.age**2
    df["log_tm365_minutes"] = np.log1p(df.tm365_minutes)
    df["tm365_ga_p90"] = ((df.tm365_goals + df.tm365_assists) / df.tm365_minutes * 90).where(df.tm365_minutes >= 450)
    paid = transfers[transfers.move_type == "paid_transfer"]
    df["log_buyer_spend_365"] = np.log1p(club_flow_365(df, paid, "to_club_id"))
    df["log_seller_sales_365"] = np.log1p(club_flow_365(df, paid, "from_club_id"))
    df = df.sort_values("date").reset_index(drop=True)
    df["market_premium_level"] = market_premium_level(df)
    df["deadline_week"] = is_deadline_week(df.date)
    df["to_lg"] = df.to_competition_id.fillna("other")
    df["from_lg"] = df.from_competition_id.fillna("other")
    df = piv_for_transfers(df, piv)
    df["piv_full"] = df.piv_full.fillna(0)
    df["buyer_big5"] = np.where(df.to_competition_id.isin(BIG5), "big5", "other")
    df["mv_band"] = pd.cut(df.mv_pit_eur, [0, 2e6, 10e6, 30e6, np.inf], labels=["<2M", "2-10M", "10-30M", "30M+"]
                           ).astype(str)  # fmt: skip
    return df


def reliability(calibrated: bool, piv_full: int, tm365_minutes: int, mv_age: float) -> tuple[str, str]:
    if not calibrated:
        return "Insufficient", "Not enough past transfers to calibrate an uncertainty range"
    if tm365_minutes >= MIN_MINUTES_FOR_ESTIMATE and piv_full and mv_age <= 180:
        return "High", "Recent market value, xG-level performance data, regular playing time"
    if tm365_minutes >= MIN_MINUTES_FOR_ESTIMATE:
        return "Moderate", "Recent market value and playing-time data"
    return "Low", "Little recent playing time in covered leagues"


def fee_label(y: float, lo80: float, hi80: float, lo95: float, hi95: float) -> str | None:
    """Classification from the interval position, never from the premium's sign (rule R1)."""
    if any(np.isnan(v) for v in (y, lo80, hi80, lo95, hi95)):
        return None
    if y > hi95:
        return "Unusual transfer premium"
    if y > hi80:
        return "Notable transfer premium"
    if y < lo95:
        return "Unusually low fee"
    if y < lo80:
        return "Notable fee discount"
    return "Within expected range"
