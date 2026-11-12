"""Build all staging tables from the verified raw snapshot.

Output: data/staging/<table>.csv.gz (+ manifest.json with row counts and the
source checksums). Files are written and read through the STAGING contracts,
so types survive the CSV round trip. CSV rather than Parquet because pyarrow's
native DLL is blocked by Windows Smart App Control on the development machine.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from fairvalue import __version__
from fairvalue.config import BIG5, STAGING_DIR, TRANSFERMARKT_CUTOFF
from fairvalue.ingest import sources
from fairvalue.ingest.transfermarkt import read_table
from fairvalue.ingest.understat_archive import read_cache
from fairvalue.io import read_table as read_table_
from fairvalue.io import write_table
from fairvalue.staging import core, matching


def write_staging(df: pd.DataFrame, name: str, out_dir: Path = STAGING_DIR) -> int:
    return write_table(df, "staging", name, base=out_dir.parent)


def read_staging(name: str, out_dir: Path = STAGING_DIR) -> pd.DataFrame:
    return read_table_("staging", name, base=out_dir.parent)


def run(out_dir: Path = STAGING_DIR, log=print) -> dict:
    t0 = time.time()
    log("verifying raw sources (checksums)...")
    sources.verify_transfermarkt()
    pages = sources.verify_understat_cache()
    cutoff = pd.Timestamp(TRANSFERMARKT_CUTOFF)
    counts: dict[str, int] = {}

    log("transfermarkt: dimensions")
    comp = read_table("competitions")
    raw_transfers = read_table("transfers")
    players = core.stage_players(read_table("players"))
    counts["competitions"] = write_staging(core.stage_competitions(comp), "competitions", out_dir)
    counts["clubs"] = write_staging(core.stage_clubs(read_table("clubs"), raw_transfers), "clubs", out_dir)
    counts["players"] = write_staging(players, "players", out_dir)

    log("transfermarkt: games, appearances, valuations")
    games = core.stage_games(read_table("games"))
    games = games[games.date <= cutoff]
    counts["games"] = write_staging(games, "games", out_dir)
    cls = core.club_league_seasons(games)
    counts["club_league_seasons"] = write_staging(cls, "club_league_seasons", out_dir)
    apps = core.stage_appearances(read_table("appearances"), games, read_table("game_lineups"))
    counts["appearances"] = write_staging(apps, "appearances", out_dir)
    counts["valuations"] = write_staging(
        core.stage_valuations(read_table("player_valuations"), cutoff), "valuations", out_dir
    )

    log("transfermarkt: transfers")
    counts["transfers"] = write_staging(
        core.stage_transfers(raw_transfers, cls, cutoff), "transfers", out_dir
    )

    log("understat: parse archive cache")
    us_raw, coverage = read_cache(pages)
    us = us_raw.rename(
        columns={
            "id": "understat_id", "time": "minutes", "xG": "xg", "npxG": "npxg", "xA": "xa",
            "xGChain": "xg_chain", "xGBuildup": "xg_buildup",
        }
    )  # fmt: skip
    us["competition_id"] = us.league.map(
        {"EPL": "GB1", "La_liga": "ES1", "Bundesliga": "L1", "Serie_A": "IT1", "Ligue_1": "FR1"}
    )
    counts["understat_player_seasons"] = write_staging(us, "understat_player_seasons", out_dir)
    counts["understat_coverage"] = write_staging(coverage, "understat_coverage", out_dir)

    log("matching understat -> transfermarkt (takes a minute)...")
    tm_tot = matching.tm_league_season_totals(apps, list(BIG5))
    m = matching.match_player_seasons(us, tm_tot, players.set_index("player_id").name)
    pm, m = matching.player_id_map(m)
    counts["understat_tm_matches"] = write_staging(m, "understat_tm_matches", out_dir)
    counts["player_id_map"] = write_staging(pm, "player_id_map", out_dir)

    manifest = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pipeline_version": __version__,
        "sources": {
            "transfermarkt_zip_sha256": sources.TM_ZIP_SHA256,
            "understat_cache_sha256": sources.UNDERSTAT_CACHE_SHA256,
            "transfermarkt_cutoff": str(TRANSFERMARKT_CUTOFF),
        },
        "row_counts": counts,
        "seconds": round(time.time() - t0, 1),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log(f"done in {manifest['seconds']}s")
    return manifest
