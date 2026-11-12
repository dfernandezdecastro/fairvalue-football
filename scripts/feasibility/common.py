"""Shared loaders for the feasibility study (Transfermarkt-derived tables)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TM = ROOT / "data" / "raw" / "transfermarkt" / "extracted"
INTERIM = ROOT / "data" / "interim"
REPORTS = ROOT / "reports" / "feasibility"

BIG5 = {"GB1": "Premier League", "ES1": "LaLiga", "L1": "Bundesliga", "IT1": "Serie A", "FR1": "Ligue 1"}
# Leagues with full domestic-league match coverage 2012-2025 in the dataset.
FULL_HISTORY = set(BIG5) | {"NL1", "PO1", "BE1", "TR1", "RU1", "SC1", "GR1", "DK1", "UKR1"}
DATA_CUTOFF = pd.Timestamp("2026-07-06")  # dataset is "current to 6 July 2026"


def read(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(TM / f"{name}.csv.gz", **kw)


def season_of(date: pd.Series) -> pd.Series:
    """Season start year: Jul-Dec -> same year; Jan-Jun -> previous year."""
    return np.where(date.dt.month >= 7, date.dt.year, date.dt.year - 1)


def window_of(date: pd.Series) -> pd.Series:
    m = date.dt.month
    return np.select([m.isin([6, 7, 8, 9]), m.isin([12, 1, 2])], ["summer", "winter"], "other")


def club_league_by_season() -> pd.DataFrame:
    """club_id, season -> domestic league competition_id (from league fixtures)."""
    g = read("games", usecols=["competition_id", "season", "home_club_id", "away_club_id", "competition_type"])
    g = g[g.competition_type == "domestic_league"]
    long = pd.concat(
        [g[["competition_id", "season", "home_club_id"]].rename(columns={"home_club_id": "club_id"}),
         g[["competition_id", "season", "away_club_id"]].rename(columns={"away_club_id": "club_id"})]
    )
    out = long.groupby(["club_id", "season"]).competition_id.agg(lambda s: s.mode().iat[0]).reset_index()
    return out.rename(columns={"competition_id": "league"})


def load_transfers() -> pd.DataFrame:
    t = read("transfers")
    t["date"] = pd.to_datetime(t.transfer_date, errors="coerce")
    t["season"] = season_of(t.date)
    t["window"] = window_of(t.date)
    p = read("players", usecols=["player_id", "date_of_birth", "position", "sub_position", "foot",
                                 "height_in_cm", "country_of_citizenship", "international_caps"])
    p["dob"] = pd.to_datetime(p.date_of_birth, errors="coerce")
    t = t.merge(p.drop(columns="date_of_birth"), on="player_id", how="left")
    t["age"] = (t.date - t.dob).dt.days / 365.25

    cl = club_league_by_season()
    # buying league: buyer's league in the season of the transfer
    t = t.merge(cl.rename(columns={"club_id": "to_club_id", "league": "to_league"}),
                on=["to_club_id", "season"], how="left")
    # selling league: seller's league in the season the player is leaving
    # (summer move -> season just finished; winter move -> current season)
    t["sell_season"] = np.where(t.window == "summer", t.season - 1, t.season)
    t = t.merge(cl.rename(columns={"club_id": "from_club_id", "league": "from_league", "season": "sell_season"}),
                on=["from_club_id", "sell_season"], how="left")
    # loan detection: a move A->B followed by B->A within 400 days
    t = t.sort_values(["player_id", "date"]).reset_index(drop=True)
    nxt = t.groupby("player_id")[["from_club_id", "to_club_id", "date"]].shift(-1)
    t["returns_within_400d"] = (
        (nxt.from_club_id == t.to_club_id) & (nxt.to_club_id == t.from_club_id)
        & ((nxt.date - t.date).dt.days <= 400)
    )
    t["fee_status"] = np.select(
        [t.transfer_fee > 0, t.transfer_fee == 0, t.transfer_fee.isna()],
        ["paid", "zero (free or loan)", "unknown"], "other")
    return t
