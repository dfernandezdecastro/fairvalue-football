"""Build the published tables from pipeline outputs: `fairvalue publish`.

Only derived outputs and the individual facts each page needs are published
(decision D15): no valuation histories, no match-level data, no loans or free
transfers, birth year instead of full date of birth.
"""

from __future__ import annotations

import json
import unicodedata

import numpy as np
import pandas as pd

from fairvalue.config import DATA_DIR, FULL_HISTORY_LEAGUES, TRANSFERMARKT_CUTOFF, UNDERSTAT_LAST_SEASON
from fairvalue.export.contracts import FORBIDDEN_COLUMNS, PRIMARY_KEYS, PUBLISH, RATE
from fairvalue.ingest.schemas import enforce
from fairvalue.io import read_table

SIMILAR_TOP_K = 10
SIMILAR_FROM_SEASON = 2017


class LicensingError(ValueError):
    """A table would publish a forbidden field."""


def _run_id(meta: dict) -> str:
    return f"{meta['model']}-{meta['created_at']}"


def build_tables(base=DATA_DIR) -> dict[str, pd.DataFrame]:
    r = lambda layer, name: read_table(layer, name, base=base)  # noqa: E731
    piv_meta = json.loads((base / "outputs" / "piv_run.json").read_text(encoding="utf-8"))
    fee_meta = json.loads((base / "outputs" / "fee_run.json").read_text(encoding="utf-8"))
    piv_run, fee_run = _run_id(piv_meta), _run_id(fee_meta)

    # ---- player seasons (profiles + selected season facts)
    ps = r("features", "player_season_features")
    prof = r("features", "profiles")
    keys = ["player_id", "season", "competition_id"]
    extra = [c for c in prof.columns if c.endswith(("_p90", "_shrunk", "_pct"))] + ["eligible", "peer_scope", "peer_n"]
    seasons = ps.merge(prof[keys + extra], on=keys, how="left")

    # ---- similar players: top-k, recent seasons only (size budget)
    sim = r("features", "similar_players")
    sim = sim[(sim["rank"] <= SIMILAR_TOP_K) & (sim.season >= SIMILAR_FROM_SEASON)]

    # ---- PIV estimates
    piv = r("outputs", "piv_predictions").rename(
        columns={"target_mv_eur": "market_value_eur", "target_date": "market_value_date"}
    )
    piv["model_run_id"] = piv_run

    # ---- transfers: all paid permanent transfers 2015/16+, with expected fee where scored
    tf = r("features", "transfer_features")
    st = r("staging", "transfers")[["transfer_id", "from_club_id", "to_club_id"]]
    fees = r("outputs", "fee_predictions")
    t = tf[tf.F1].merge(st, on="transfer_id", how="left")
    fee_cols = [
        "transfer_id", "expected_fee_eur", "lo80_eur", "hi80_eur", "lo95_eur", "hi95_eur", "premium_eur",
        "premium_pct", "label", "reliability", "reliability_reason", "calibration_group", "drivers",
    ]  # fmt: skip
    t = t.merge(fees[fee_cols], on="transfer_id", how="left")
    first_scored = int(fees.season.min())
    unscored = t.reliability.isna()
    t.loc[unscored, "reliability"] = "Insufficient"
    t.loc[unscored, "reliability_reason"] = np.where(
        t.loc[unscored, "mv_pit_age_days"].le(365).fillna(False) & (t.loc[unscored, "season"] < first_scored),
        f"Before {first_scored}/{str(first_scored + 1)[-2:]}: these seasons were used to train the first models",
        "No market value within 365 days before the transfer",
    )
    t["model_run_id"] = np.where(unscored, None, fee_run)
    t = t.rename(columns={"transfer_id": "id", "window": "transfer_window", "mv_pit_eur": "mv_before_eur",
                          "mv_pit_date": "mv_before_date"})  # fmt: skip

    # ---- dimensions: only what's referenced
    player_ids = set(seasons.player_id) | set(t.player_id) | set(sim.neighbour_id)
    players = r("staging", "players")
    players = players[players.player_id.isin(player_ids)].rename(columns={"player_id": "id"})
    players["birth_year"] = players.date_of_birth.dt.year.astype("Int64")
    audit = r("outputs", "club_audit")
    club_ids = set(seasons.club_id.dropna()) | set(t.from_club_id) | set(t.to_club_id) | set(audit.club_id)
    clubs = r("staging", "clubs")
    clubs = clubs[clubs.club_id.isin(club_ids)].rename(columns={"club_id": "id"})
    clubs = clubs.drop_duplicates("id")
    clubs["slug"] = np.where(clubs.slug.duplicated(keep=False), clubs.slug + "-" + clubs.id.astype(str), clubs.slug)
    players["search_name"] = players.name.map(search_name)
    clubs["search_name"] = clubs.name.map(search_name)
    comp = r("staging", "competitions").rename(columns={"competition_id": "id", "country_name": "country"})

    # ---- runs, coverage, meta
    runs = pd.DataFrame([
        {"id": piv_run, "model": "piv", "created_at": piv_meta["created_at"],
         "pipeline_version": piv_meta["pipeline_version"], "is_current": True, "summary": json.dumps(piv_meta)},
        {"id": fee_run, "model": "expected_fee", "created_at": fee_meta["created_at"],
         "pipeline_version": fee_meta["pipeline_version"], "is_current": True, "summary": json.dumps(fee_meta)},
    ])  # fmt: skip
    cov = r("staging", "understat_coverage").assign(source="understat")[
        ["source", "competition_id", "season", "status"]
    ]
    cls = r("staging", "club_league_seasons")[["competition_id", "season"]].drop_duplicates()
    tm = cls.assign(source="transfermarkt", status=np.where(cls.competition_id.isin(FULL_HISTORY_LEAGUES),
                                                             "full_history", "recent_only"))  # fmt: skip
    coverage = pd.concat([cov, tm[["source", "competition_id", "season", "status"]]], ignore_index=True)
    meta = pd.DataFrame([
        {"key": "data_vintage", "value": json.dumps({"transfermarkt_to": str(TRANSFERMARKT_CUTOFF),
                                                     "understat_last_season": UNDERSTAT_LAST_SEASON})},
        {"key": "attribution", "value": json.dumps(
            "Transfer and market-value data: Transfermarkt, via the community transfermarkt-datasets project. "
            "xG data: Understat. Non-commercial research project; not affiliated with any club or data provider.")},
        {"key": "market_premium_by_window", "value": json.dumps(market_premium_series(tf))},
        {"key": "published_at", "value": json.dumps(pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"))},
    ])  # fmt: skip

    raw = {
        "competitions": comp, "clubs": clubs, "players": players, "model_runs": runs, "player_seasons": seasons,
        "similar_players": sim, "piv_estimates": piv, "transfers": t, "club_audit": audit,
        "data_coverage": coverage, "app_meta": meta,
    }  # fmt: skip
    tables = {name: enforce(df, PUBLISH[name], f"publish.{name}") for name, df in raw.items()}
    check_licensing(tables)
    check_primary_keys(tables)
    check_referential_integrity(tables)
    return tables


def check_primary_keys(tables: dict[str, pd.DataFrame]) -> None:
    """Fail before touching the database if a primary key would be duplicated."""
    dupes = {name: int(df.duplicated(PRIMARY_KEYS[name]).sum()) for name, df in tables.items()}
    dupes = {k: v for k, v in dupes.items() if v}
    if dupes:
        raise ValueError(f"duplicate primary keys: {dupes}")


def market_premium_series(tf: pd.DataFrame) -> list[dict]:
    """Median fee / market value by season and window (paid transfers, value <= 365 days old): the market cycle."""
    t = tf[tf.F1 & (tf.mv_pit_age_days <= 365) & (tf.fee_eur > 0) & tf.window.isin(["summer", "winter"])].copy()
    t["ratio"] = t.fee_eur / t.mv_pit_eur
    g = t.groupby(["season", "window"]).ratio.agg(["median", "size"]).reset_index()
    g = g[g["size"] >= 30]
    return [
        {"season": int(r.season), "window": r.window, "median_ratio": round(float(r["median"]), 4), "n": int(r["size"])}
        for _, r in g.iterrows()
    ]


def search_name(name: str) -> str:
    """Lower-case, accent-free form used for search ("Mbappé" -> "mbappe")."""
    return unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower().strip()


def check_licensing(tables: dict[str, pd.DataFrame]) -> None:
    for name, df in tables.items():
        bad = FORBIDDEN_COLUMNS & set(df.columns)
        if bad:
            raise LicensingError(f"{name} would publish forbidden column(s): {sorted(bad)}")


def check_referential_integrity(tables: dict[str, pd.DataFrame]) -> None:
    """Fail before touching the database if a foreign key would break."""
    ids = {k: set(tables[k].id) for k in ("competitions", "clubs", "players")}
    k3 = ["player_id", "season", "competition_id"]
    keyset = lambda name: set(map(tuple, tables[name][k3].values))  # noqa: E731
    ps_keys = keyset("player_seasons")
    checks = {
        "player_seasons.player_id": set(tables["player_seasons"].player_id) - ids["players"],
        "player_seasons.club_id": set(tables["player_seasons"].club_id.dropna()) - ids["clubs"],
        "player_seasons.competition_id": set(tables["player_seasons"].competition_id) - ids["competitions"],
        "transfers.player_id": set(tables["transfers"].player_id) - ids["players"],
        "transfers.clubs": (set(tables["transfers"].from_club_id) | set(tables["transfers"].to_club_id)) - ids["clubs"],
        "piv_estimates.player_season": keyset("piv_estimates") - ps_keys,
        "similar_players.player_season": keyset("similar_players") - ps_keys,
        "club_audit.club_id": set(tables["club_audit"].club_id) - ids["clubs"],
    }  # fmt: skip
    broken = {k: len(v) for k, v in checks.items() if v}
    if broken:
        raise ValueError(f"referential integrity would fail: {broken}")


def summary(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.DataFrame(
        {"rows": {k: len(v) for k, v in tables.items()},
         "csv_mb": {k: round(len(v.to_csv(index=False).encode()) / 1e6, 1) for k, v in tables.items()}}
    )  # fmt: skip


__all__ = ["build_tables", "check_licensing", "summary", "RATE"]
