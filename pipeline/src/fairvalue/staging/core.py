"""Staging transformations: pure functions from contract-checked raw tables to clean tables.

No I/O here, so every rule can be unit-tested on tiny synthetic frames.
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from fairvalue.config import BIG5, FULL_HISTORY_LEAGUES

LOAN_RETURN_DAYS = 400


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# --------------------------------------------------------------------------- dimensions
def stage_competitions(comp: pd.DataFrame) -> pd.DataFrame:
    out = comp.rename(columns={})[["competition_id", "name", "type", "country_name"]].copy()
    out["is_big5"] = out.competition_id.isin(BIG5)
    out["has_full_history"] = out.competition_id.isin(FULL_HISTORY_LEAGUES)
    return out


def stage_players(players: pd.DataFrame) -> pd.DataFrame:
    p = players.copy()
    base = p.player_code.fillna(p.name.map(slugify))
    p["slug"] = base.map(slugify) + "-" + p.player_id.astype(str)  # ids make slugs unique
    return p.rename(columns={"height_in_cm": "height_cm", "country_of_citizenship": "citizenship"})[
        [
            "player_id",
            "name",
            "slug",
            "date_of_birth",
            "position",
            "sub_position",
            "foot",
            "height_cm",
            "citizenship",
        ]
    ]


def stage_clubs(clubs: pd.DataFrame, transfers: pd.DataFrame) -> pd.DataFrame:
    """Clubs table + clubs that only appear in transfers (named from the transfer rows)."""
    known = clubs.rename(columns={"club_code": "slug"})[["club_id", "slug", "name"]]
    seen = pd.concat(
        [
            transfers[["from_club_id", "from_club_name"]].set_axis(["club_id", "name"], axis=1),
            transfers[["to_club_id", "to_club_name"]].set_axis(["club_id", "name"], axis=1),
        ]
    ).dropna()
    extra = seen[~seen.club_id.isin(known.club_id)].groupby("club_id").name.agg(lambda s: s.mode().iat[0])
    extra = extra.reset_index()
    extra["slug"] = extra.name.map(slugify) + "-" + extra.club_id.astype(str)
    return pd.concat([known, extra[["club_id", "slug", "name"]]], ignore_index=True)


# --------------------------------------------------------------------------- facts
def stage_games(games: pd.DataFrame) -> pd.DataFrame:
    return games.rename(columns={"home_club_goals": "home_goals", "away_club_goals": "away_goals"})


def club_league_seasons(games: pd.DataFrame) -> pd.DataFrame:
    """club_id, season -> domestic league, from league fixtures (official season field)."""
    g = games[games.competition_type == "domestic_league"]
    long = pd.concat(
        [
            g[["competition_id", "season", "home_club_id"]].rename(columns={"home_club_id": "club_id"}),
            g[["competition_id", "season", "away_club_id"]].rename(columns={"away_club_id": "club_id"}),
        ]
    )
    out = long.groupby(["club_id", "season"]).competition_id.agg(lambda s: s.mode().iat[0]).reset_index()
    return out[["club_id", "season", "competition_id"]]


def stage_appearances(app: pd.DataFrame, games: pd.DataFrame, lineups: pd.DataFrame) -> pd.DataFrame:
    """Attach the fixture's OFFICIAL season (COVID-safe) and whether the player started."""
    a = app.merge(games[["game_id", "season", "competition_type"]], on="game_id", how="inner")
    starters = lineups.loc[lineups.type == "starting_lineup", ["game_id", "player_id"]].drop_duplicates()
    starters["started"] = True
    a = a.merge(starters, on=["game_id", "player_id"], how="left")
    a["started"] = a.started.fillna(False).astype(bool)
    return a.rename(columns={"player_club_id": "club_id", "minutes_played": "minutes"})[
        ["game_id", "player_id", "club_id", "date", "season", "competition_id", "competition_type",
         "started", "minutes", "goals", "assists", "yellow_cards", "red_cards"]
    ]  # fmt: skip


def stage_valuations(v: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    v = v[(v.date <= cutoff) & (v.market_value_in_eur > 0)]
    v = v.sort_values(["player_id", "date"]).drop_duplicates(["player_id", "date"], keep="last")
    return v.rename(columns={"market_value_in_eur": "value_eur"}).reset_index(drop=True)


def _returns_on_next_date(t: pd.DataFrame) -> pd.Series:
    """True if the player's next move on a LATER date reverses this one within 400 days.

    Same-day rows are skipped on purpose: "buy and loan back" deals record a paid
    A->B move and a B->A loan on the same date. The loan back is not evidence that
    the paid move was a loan, and same-day row order in the source is arbitrary.
    """
    dates = t[["player_id", "transfer_date"]].drop_duplicates().sort_values(["player_id", "transfer_date"])
    dates["next_date"] = dates.groupby("player_id").transfer_date.shift(-1)
    x = t[["player_id", "transfer_date", "from_club_id", "to_club_id"]].merge(
        dates, on=["player_id", "transfer_date"], how="left"
    )
    nxt = t[["player_id", "transfer_date", "from_club_id", "to_club_id"]].rename(
        columns={"transfer_date": "next_date", "from_club_id": "to_club_id", "to_club_id": "from_club_id"}
    )
    nxt = nxt.drop_duplicates().assign(_reverse=True)
    x = x.merge(nxt, on=["player_id", "next_date", "from_club_id", "to_club_id"], how="left")
    within = (x.next_date - x.transfer_date).dt.days <= LOAN_RETURN_DAYS
    return pd.Series((x._reverse.fillna(False).astype(bool) & within).values, index=t.index)


def stage_transfers(t: pd.DataFrame, cls: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Clean transfers, label move types and attach both clubs' leagues.

    Loan detection runs on the FULL table before the cutoff filter, because
    scheduled 'end of loan' rows are often dated in the future. This labels the
    kind of move (a data-cleaning decision), it is never a model feature.
    """
    t = t.drop_duplicates().sort_values(["player_id", "transfer_date", "from_club_id", "to_club_id"])
    t = t.reset_index(drop=True)
    t["returns_within_400d"] = _returns_on_next_date(t)

    t = t[t.transfer_date <= cutoff].copy()
    d = t.transfer_date
    t["season"] = np.where(d.dt.month >= 7, d.dt.year, d.dt.year - 1)
    m = d.dt.month
    t["window"] = np.select([m.isin([6, 7, 8, 9]), m.isin([12, 1, 2])], ["summer", "winter"], "other")
    # Buyer's league in the season the player joins; seller's league in the season
    # the player leaves (summer -> season just finished, otherwise current season).
    t["sell_season"] = np.where(t.window == "summer", t.season - 1, t.season)
    to_lg = cls.rename(columns={"club_id": "to_club_id", "competition_id": "to_competition_id"})
    from_lg = cls.rename(
        columns={"club_id": "from_club_id", "competition_id": "from_competition_id", "season": "sell_season"}
    )
    t = t.merge(to_lg, on=["to_club_id", "season"], how="left").merge(
        from_lg, on=["from_club_id", "sell_season"], how="left"
    )

    fee = t.transfer_fee
    t["fee_status"] = np.select([fee > 0, fee == 0], ["paid", "zero"], "unknown")
    ret = t.returns_within_400d
    t["move_type"] = np.select(
        [(fee > 0) & ret, fee > 0, (fee == 0) & ret, fee == 0],
        ["probable_paid_loan", "paid_transfer", "probable_loan", "free_or_loan"],
        "fee_unknown",
    )
    t = t.sort_values(["transfer_date", "player_id", "from_club_id", "to_club_id"]).reset_index(drop=True)
    t["transfer_id"] = np.arange(1, len(t) + 1)
    return t.rename(
        columns={
            "transfer_date": "date",
            "transfer_fee": "fee_eur",
            "market_value_in_eur": "tm_reported_mv_eur",
        }
    )
