"""Match Understat player-seasons to Transfermarkt player IDs.

Understat has no date of birth and no external IDs, so we match inside each
league-season using two independent signals:
  1. name similarity (accent-stripped, token-aware)
  2. agreement of season stats (games, goals, assists, minutes) computed from
     Transfermarkt per-match appearances in the same league-season.
Then we aggregate to one understat_id -> tm_player_id map and flag conflicts.

Output: data/interim/understat_tm_matches.csv  (player-season level)
        data/interim/player_id_map.csv          (player level, with confidence)
"""
from __future__ import annotations

import re
import sys
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import BIG5, INTERIM, read  # noqa: E402

US_LEAGUE = {"EPL": "GB1", "La_liga": "ES1", "Bundesliga": "L1", "Serie_A": "IT1", "Ligue_1": "FR1"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def name_score(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = set(a.split()), set(b.split())
    # one name fully contained in the other ("Vitinha" vs "Vitor Ferreira Vitinha")
    contain = 0.92 if (ta <= tb or tb <= ta) else 0.0
    jacc = len(ta & tb) / len(ta | tb)
    seq = SequenceMatcher(None, a, b).ratio()
    last = 0.85 if a.split()[-1] == b.split()[-1] and len(a.split()[-1]) > 3 else 0.0
    return max(contain, seq, last, 0.5 + 0.5 * jacc if jacc > 0 else 0)


def tm_season_stats() -> pd.DataFrame:
    a = read("appearances", usecols=["game_id", "player_id", "player_name", "competition_id", "date",
                                     "goals", "assists", "minutes_played"])
    a = a[a.competition_id.isin(BIG5)]
    # Use the fixture's official season, not the calendar date: COVID-delayed
    # 2019/20 matches were played in July-August 2020.
    gs = read("games", usecols=["game_id", "season"])
    a = a.merge(gs, on="game_id", how="left")
    g = a.groupby(["competition_id", "season", "player_id"]).agg(
        tm_name=("player_name", "first"), tm_games=("game_id", "nunique"), tm_goals=("goals", "sum"),
        tm_assists=("assists", "sum"), tm_minutes=("minutes_played", "sum")).reset_index()
    return g


def main() -> None:
    us = pd.read_csv(INTERIM / "understat_players.csv")
    us["competition_id"] = us.league.map(US_LEAGUE)
    for c in ["games", "time", "goals", "assists"]:
        us[c] = pd.to_numeric(us[c], errors="coerce")
    tm = tm_season_stats()

    out = []
    for (comp, season), u in us.groupby(["competition_id", "season"]):
        cand = tm[(tm.competition_id == comp) & (tm.season == season)]
        if cand.empty:
            continue
        cg, cgl, cm, cn, cid = (cand.tm_games.values, cand.tm_goals.values, cand.tm_minutes.values,
                                cand.tm_name.values, cand.player_id.values)
        for r in u.itertuples():
            # stat plausibility filter (sources count minutes slightly differently)
            ok = (np.abs(cg - r.games) <= 2) & (np.abs(cgl - r.goals) <= 1) & \
                 (np.abs(cm - r.time) <= np.maximum(90, 0.12 * r.time))
            idx = np.where(ok)[0]
            best, best_s, second_s = None, 0.0, 0.0
            for i in idx:
                s = name_score(r.player_name, cn[i])
                if s > best_s:
                    best, best_s, second_s = i, s, best_s
                elif s > second_s:
                    second_s = s
            rec = dict(understat_id=r.id, us_name=r.player_name, league=r.league, season=season,
                       us_games=r.games, us_minutes=r.time, us_goals=r.goals, n_stat_candidates=len(idx))
            if best is not None:
                stat_exact = (cg[best] == r.games) and (cgl[best] == r.goals)
                rec.update(tm_player_id=cid[best], tm_name=cn[best], name_score=round(best_s, 3),
                           runner_up_score=round(second_s, 3), stat_exact=bool(stat_exact),
                           tm_minutes=cm[best])
            out.append(rec)
    m = pd.DataFrame(out)
    # acceptance rule (documented in report):
    #  high: name >= 0.85 and stats plausible
    #  medium: name >= 0.6, exact games+goals, clear margin over runner-up
    m["confidence"] = np.select(
        [m.name_score >= 0.85,
         (m.name_score >= 0.6) & m.stat_exact.fillna(False) & ((m.name_score - m.runner_up_score) >= 0.15)],
        ["high", "medium"], "unmatched")
    m.to_csv(INTERIM / "understat_tm_matches.csv", index=False)

    acc = m[m.confidence != "unmatched"]
    pm = acc.groupby("understat_id").agg(
        tm_player_id=("tm_player_id", lambda s: s.mode().iat[0]),
        n_tm_ids=("tm_player_id", "nunique"), seasons=("season", "nunique"),
        min_conf=("confidence", lambda s: "medium" if (s == "medium").any() else "high")).reset_index()
    pm.to_csv(INTERIM / "player_id_map.csv", index=False)

    print("understat player-seasons:", len(m))
    print(m.confidence.value_counts().to_string())
    print("match rate (all):", round((m.confidence != "unmatched").mean(), 3))
    big = m[m.us_minutes >= 450]
    print("match rate (>=450 min):", round((big.confidence != "unmatched").mean(), 3))
    print("understat ids mapped to >1 TM id (conflicts):", (pm.n_tm_ids > 1).sum(), "of", len(pm))
    print("TM ids claimed by >1 understat id:", (pm.tm_player_id.value_counts() > 1).sum())


if __name__ == "__main__":
    main()
