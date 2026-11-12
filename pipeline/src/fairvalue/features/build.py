"""Build features and Layer 1 profiles from staging: `fairvalue features`."""

from __future__ import annotations

import time

from fairvalue.features import player_season, report, transfer
from fairvalue.io import read_table, write_table
from fairvalue.profiles import build as profiles


def run(log=print) -> dict[str, int]:
    t0 = time.time()
    r = lambda name: read_table("staging", name)  # noqa: E731
    log("loading staging...")
    apps, games, players = r("appearances"), r("games"), r("players")
    us_by_ps = player_season.understat_by_player_season(r("understat_player_seasons"), r("understat_tm_matches"))
    counts = {}

    log("player-season features (as of each league's season end)...")
    ps = player_season.build(apps, games, players, us_by_ps)
    counts["player_season_features"] = write_table(ps, "features", "player_season_features")

    log("transfer features (as of each transfer date)...")
    tf = transfer.build(r("transfers"), apps, games, r("valuations"), players, us_by_ps, r("understat_coverage"))
    counts["transfer_features"] = write_table(tf, "features", "transfer_features")

    log("profiles: shrinkage, percentiles, similarity...")
    prof, sim, priors = profiles.build(ps)
    counts["profiles"] = write_table(prof, "features", "profiles")
    counts["similar_players"] = write_table(sim, "features", "similar_players")
    counts["shrinkage_priors"] = write_table(priors, "features", "shrinkage_priors")
    log(f"summary: {report.write_report()}")
    log(f"done in {time.time() - t0:.0f}s: {counts}")
    return counts
