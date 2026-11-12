"""Transfer features: one row per paid transfer, computed AS OF the transfer date.

Point-in-time rules (rule R2):
* Market value: last valuation dated strictly BEFORE the transfer.
* Transfermarkt form: all appearances in the 365 days strictly before.
* Season-level stats (Understat, big-five minutes): the most recent season whose
  league had FINISHED before the transfer date. Normally season s-1; for some
  summer-2020 moves (COVID-delayed seasons ended as late as 2 Aug 2020) it is s-2.

After building, every source date is checked against the transfer date and a
LeakageError is raised if anything is on or after it.

Usable-set funnel (see reports/feasibility):
  F1 paid transfer, not a probable paid loan
  F2 + big-five club buying or selling
  F3 + played in a big-five league in the feature season
  F4 + that league-season exists in the Understat archive
  F5 + matched to an Understat player
  F6 + >= 900 Understat minutes in the feature season
  F7 + point-in-time market value <= 365 days old        -> usable_full
  usable_basic: F1 + >= 900 TM minutes in prior 365 days + PIT value <= 365 days old
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fairvalue.asof import LeakageError
from fairvalue.config import BIG5, MIN_MINUTES_FOR_ESTIMATE
from fairvalue.features.player_season import league_season_ends
from fairvalue.features.positions import resolve_group, tm_group
from fairvalue.ingest.schemas import US_METRICS

FIRST_DATE = pd.Timestamp("2015-07-01")
MAX_MV_AGE_DAYS = 365


def point_in_time_values(t: pd.DataFrame, valuations: pd.DataFrame) -> pd.DataFrame:
    v = valuations.rename(columns={"date": "mv_date"}).sort_values("mv_date")
    left = t[["transfer_id", "player_id", "date"]].sort_values("date")
    pit = pd.merge_asof(left, v, left_on="date", right_on="mv_date", by="player_id",
                        direction="backward", allow_exact_matches=False)  # strictly before  # fmt: skip
    year_ago = left.assign(lookup=left.date - pd.Timedelta(days=365)).sort_values("lookup")
    m12 = pd.merge_asof(year_ago, v, left_on="lookup", right_on="mv_date", by="player_id", direction="backward")
    out = pit.rename(columns={"value_eur": "mv_pit_eur", "mv_date": "mv_pit_date"})[
        ["transfer_id", "mv_pit_eur", "mv_pit_date"]
    ]
    out["mv_pit_age_days"] = (pit.date - pit.mv_date).dt.days
    return out.merge(m12[["transfer_id", "value_eur"]].rename(columns={"value_eur": "mv_12m_before_eur"}),
                     on="transfer_id")  # fmt: skip


def recent_form(t: pd.DataFrame, apps: pd.DataFrame, days: int = 365) -> pd.DataFrame:
    a = apps[apps.player_id.isin(t.player_id)][["player_id", "date", "minutes", "started", "goals", "assists"]]
    x = t[["transfer_id", "player_id", "date"]].merge(a.rename(columns={"date": "adate"}), on="player_id")
    x = x[(x.adate < x.date) & (x.adate >= x.date - pd.Timedelta(days=days))]
    g = x.groupby("transfer_id").agg(
        tm365_apps=("adate", "size"), tm365_minutes=("minutes", "sum"), tm365_starts=("started", "sum"),
        tm365_goals=("goals", "sum"), tm365_assists=("assists", "sum"), tm365_last_app_date=("adate", "max"),
    )  # fmt: skip
    return g.reset_index()


def feature_season(t: pd.DataFrame, apps: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Most recent season, s-1 or s-2, whose league(s) finished before the transfer."""
    ends = league_season_ends(games)
    dom = apps[apps.competition_type == "domestic_league"]
    pls = dom.groupby(["player_id", "season", "competition_id"]).minutes.sum().reset_index()
    pls = pls.merge(ends, on=["competition_id", "season"], how="left")
    player_end = pls.groupby(["player_id", "season"]).season_end.max()
    big5_end = ends[ends.competition_id.isin(BIG5)].groupby("season").season_end.max()

    s1 = t.season - 1
    end1 = pd.Series(player_end.reindex(list(zip(t.player_id, s1, strict=True))).values, index=t.index)
    end1 = end1.fillna(s1.map(big5_end))
    feat = np.where(end1 < t.date, s1, s1 - 1)
    out = t[["transfer_id", "player_id"]].assign(feat_season=feat)

    b5 = pls[pls.competition_id.isin(BIG5)].sort_values("minutes", ascending=False)
    b5_main = b5.drop_duplicates(["player_id", "season"]).set_index(["player_id", "season"])
    b5_min = b5.groupby(["player_id", "season"]).minutes.sum()
    key = list(zip(out.player_id, out.feat_season, strict=True))
    out["feat_big5_league"] = b5_main.competition_id.reindex(key).values
    out["feat_tm_big5_minutes"] = b5_min.reindex(key).fillna(0).values
    out = out.merge(ends.rename(columns={"competition_id": "feat_big5_league", "season": "feat_season"}),
                    on=["feat_big5_league", "feat_season"], how="left")  # fmt: skip
    return out.rename(columns={"season_end": "feat_season_end"}).drop(columns="player_id")


def assert_point_in_time(f: pd.DataFrame) -> None:
    checks = {
        "mv_pit_date": f.mv_pit_date >= f.date,
        "tm365_last_app_date": f.tm365_last_app_date >= f.date,
        "feat_season_end": f.feat_season_end.notna() & (f.feat_season_end >= f.date),
    }
    for col, bad in checks.items():
        if bad.fillna(False).any():
            raise LeakageError(f"{int(bad.sum())} transfer(s) use {col} on/after the transfer date")


def build(
    transfers: pd.DataFrame,
    apps: pd.DataFrame,
    games: pd.DataFrame,
    valuations: pd.DataFrame,
    players: pd.DataFrame,
    us_by_ps: pd.DataFrame,
    coverage: pd.DataFrame,
) -> pd.DataFrame:
    t = transfers[(transfers.fee_status == "paid") & (transfers.date >= FIRST_DATE)].copy()
    t = t.rename(columns={"fee_eur": "fee_eur"})
    t = t.merge(point_in_time_values(t, valuations), on="transfer_id", how="left")
    t = t.merge(recent_form(t, apps), on="transfer_id", how="left")
    for c in ["tm365_apps", "tm365_minutes", "tm365_starts", "tm365_goals", "tm365_assists"]:
        t[c] = t[c].fillna(0).astype(int)
    t = t.merge(feature_season(t, apps, games), on="transfer_id", how="left")

    archived = coverage[coverage.status != "missing"][["competition_id", "season"]].assign(_arch=True)
    t = t.merge(archived.rename(columns={"competition_id": "feat_big5_league", "season": "feat_season"}),
                on=["feat_big5_league", "feat_season"], how="left")  # fmt: skip
    t["us_league_season_archived"] = t._arch.fillna(False).astype(bool)

    us = us_by_ps.groupby(["player_id", "season"]).agg(
        understat_id=("understat_id", "first"), us_minutes=("us_minutes", "sum"),
        us_position=("us_position", "first"), us_goals=("us_goals", "sum"), us_assists=("us_assists", "sum"),
        **{m: (m, "sum") for m in US_METRICS},
    ).reset_index().rename(columns={"season": "feat_season"})  # fmt: skip
    t = t.merge(us, on=["player_id", "feat_season"], how="left")

    t = t.merge(players[["player_id", "date_of_birth", "sub_position"]], on="player_id", how="left")
    t["age"] = (t.date - t.date_of_birth).dt.days / 365.25
    t["position_group"] = [resolve_group(g, u)[0] for g, u in zip(tm_group(t.sub_position), t.us_position, strict=True)]

    t["F1"] = t.move_type == "paid_transfer"
    t["F2"] = t.F1 & (t.to_competition_id.isin(BIG5) | t.from_competition_id.isin(BIG5))
    t["F3"] = t.F2 & (t.feat_tm_big5_minutes > 0)
    t["F4"] = t.F3 & t.us_league_season_archived
    t["F5"] = t.F4 & t.understat_id.notna()
    t["F6"] = t.F5 & (t.us_minutes >= MIN_MINUTES_FOR_ESTIMATE)
    fresh_mv = t.mv_pit_age_days <= MAX_MV_AGE_DAYS
    t["F7"] = t.F6 & fresh_mv
    t["usable_full"] = t.F7
    t["usable_basic"] = t.F1 & (t.tm365_minutes >= MIN_MINUTES_FOR_ESTIMATE) & fresh_mv

    assert_point_in_time(t)
    return t
