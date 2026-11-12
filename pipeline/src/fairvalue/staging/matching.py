"""Match Understat player-seasons to Transfermarkt player IDs.

Understat has no date of birth and no external IDs, so matching happens inside
each league-season using two independent signals:

1. **Stat agreement:** Transfermarkt candidates whose league totals agree with
   the Understat row (games +/-2, goals +/-1, minutes within max(90, 12%)).
   The sources count minutes slightly differently, hence the tolerance.
2. **Name similarity** (accent-stripped, token-aware) among those candidates.

Acceptance:
* high:   name score >= 0.85
* medium: name score >= 0.60, exact games and goals, and a margin >= 0.15 over
  the runner-up candidate

Then a player-level majority vote: each Understat ID gets the Transfermarkt ID
it matched most often; season matches that disagree are flagged and dropped.
Measured in the feasibility study: 98.1% match rate, ~0.2% estimated error.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

HIGH = 0.85
MEDIUM = 0.60
MEDIUM_MARGIN = 0.15


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def name_score(a: str, b: str) -> float:
    """Similarity in [0, 1] that tolerates nicknames, extra names and accents."""
    a, b = norm_name(a), norm_name(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = set(a.split()), set(b.split())
    contain = 0.92 if (ta <= tb or tb <= ta) else 0.0  # "Vitinha" vs "Vitor Ferreira Vitinha"
    jacc = len(ta & tb) / len(ta | tb)
    seq = SequenceMatcher(None, a, b).ratio()
    last = 0.85 if a.split()[-1] == b.split()[-1] and len(a.split()[-1]) > 3 else 0.0
    return max(contain, seq, last, 0.5 + 0.5 * jacc if jacc > 0 else 0.0)


def tm_league_season_totals(appearances: pd.DataFrame, competitions: list[str]) -> pd.DataFrame:
    """Per player, league and OFFICIAL season: name, games, goals, assists, minutes."""
    a = appearances[appearances.competition_id.isin(competitions)]
    return (
        a.groupby(["competition_id", "season", "player_id"])
        .agg(
            tm_games=("game_id", "nunique"),
            tm_goals=("goals", "sum"),
            tm_assists=("assists", "sum"),
            tm_minutes=("minutes", "sum"),
        )
        .reset_index()
    )


def match_player_seasons(us: pd.DataFrame, tm: pd.DataFrame, tm_names: pd.Series) -> pd.DataFrame:
    """One output row per Understat row, with the best candidate and a confidence label.

    ``us`` needs understat_id, player_name, league, competition_id, season, games, minutes, goals.
    ``tm`` comes from ``tm_league_season_totals``; ``tm_names`` maps player_id -> name.
    """
    out = []
    for (comp, season), u in us.groupby(["competition_id", "season"], sort=True):
        cand = tm[(tm.competition_id == comp) & (tm.season == season)]
        cg, cgl, cm = cand.tm_games.values, cand.tm_goals.values, cand.tm_minutes.values
        cid = cand.player_id.values
        cn = tm_names.reindex(cid).values
        for r in u.itertuples():
            ok = (
                (np.abs(cg - r.games) <= 2)
                & (np.abs(cgl - r.goals) <= 1)
                & (np.abs(cm - r.minutes) <= np.maximum(90, 0.12 * r.minutes))
            )
            best, best_s, second_s = None, 0.0, 0.0
            for i in np.where(ok)[0]:
                s = name_score(r.player_name, cn[i])
                if s > best_s:
                    best, best_s, second_s = i, s, best_s
                elif s > second_s:
                    second_s = s
            rec = dict(
                understat_id=r.understat_id, league=r.league, season=season, us_name=r.player_name,
                n_stat_candidates=int(ok.sum()), tm_player_id=None, tm_name=None,
                name_score=0.0, runner_up_score=0.0, stat_exact=False,
            )  # fmt: skip
            if best is not None:
                rec.update(
                    tm_player_id=int(cid[best]),
                    tm_name=cn[best],
                    name_score=round(best_s, 3),
                    runner_up_score=round(second_s, 3),
                    stat_exact=bool(cg[best] == r.games and cgl[best] == r.goals),
                )
            out.append(rec)
    m = pd.DataFrame(out)
    m["confidence"] = np.select(
        [
            m.name_score >= HIGH,
            (m.name_score >= MEDIUM) & m.stat_exact & ((m.name_score - m.runner_up_score) >= MEDIUM_MARGIN),
        ],
        ["high", "medium"],
        "unmatched",
    )
    return m


def player_id_map(matches: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Majority vote per Understat ID -> (player map, matches with agreement flag)."""
    acc = matches[matches.confidence != "unmatched"]
    pm = (
        acc.groupby("understat_id")
        .agg(
            tm_player_id=("tm_player_id", lambda s: int(s.mode().iat[0])),
            seasons_matched=("season", "nunique"),
            n_tm_ids=("tm_player_id", "nunique"),
            confidence=("confidence", lambda s: "medium" if (s == "medium").any() else "high"),
        )
        .reset_index()
    )
    m = matches.merge(pm[["understat_id", "tm_player_id"]].rename(columns={"tm_player_id": "_mode"}),
                      on="understat_id", how="left")  # fmt: skip
    m["agrees_with_player_map"] = (m.confidence != "unmatched") & (m.tm_player_id == m._mode)
    return pm, m.drop(columns="_mode")
