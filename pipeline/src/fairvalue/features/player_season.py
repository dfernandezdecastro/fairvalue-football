"""Player-season features: one row per player x domestic league x season.

This is the unit of the performance-implied value model (Layer 2) and of the
performance profiles (Layer 1). Every row is computed AS OF the day after its
league's last fixture of that season, from that season and earlier only.

Data tiers:
* full  - big-five league-season with a matched Understat record (xG family)
* basic - Transfermarkt match data only (all domestic leagues)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fairvalue.asof import LeakageError
from fairvalue.features.positions import resolve_group, tm_group
from fairvalue.ingest.schemas import US_METRICS


def league_season_ends(games: pd.DataFrame) -> pd.DataFrame:
    """competition_id, season -> date of the last league fixture."""
    g = games[games.competition_type == "domestic_league"]
    return g.groupby(["competition_id", "season"]).date.max().rename("season_end").reset_index()


def team_strength(games: pd.DataFrame) -> pd.DataFrame:
    """club_id, competition_id, season -> league games, points and goal difference per game."""
    g = games[(games.competition_type == "domestic_league") & games.home_goals.notna() & games.away_goals.notna()]
    hg, ag = g.home_goals.astype(int), g.away_goals.astype(int)
    home = pd.DataFrame({"club_id": g.home_club_id, "competition_id": g.competition_id, "season": g.season,
                         "pts": np.select([hg > ag, hg == ag], [3, 1], 0), "gd": hg - ag})  # fmt: skip
    away = pd.DataFrame({"club_id": g.away_club_id, "competition_id": g.competition_id, "season": g.season,
                         "pts": np.select([ag > hg, ag == hg], [3, 1], 0), "gd": ag - hg})  # fmt: skip
    t = pd.concat([home, away]).groupby(["club_id", "competition_id", "season"])
    out = t.agg(team_games=("pts", "size"), pts=("pts", "sum"), gd=("gd", "sum")).reset_index()
    out["team_ppg"] = out.pts / out.team_games
    out["team_gd_pg"] = out.gd / out.team_games
    return out


def understat_by_player_season(us: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Understat totals keyed by Transfermarkt player id, league and season.

    Only season matches that agree with the player-level majority vote are used.
    """
    ok = matches[(matches.confidence != "unmatched") & matches.agrees_with_player_map]
    keys = ok[["understat_id", "league", "season", "tm_player_id"]]
    u = us.merge(keys, on=["understat_id", "league", "season"])
    agg = {m: (m, "sum") for m in [*US_METRICS, "goals", "assists"]}
    return (
        u.groupby(["tm_player_id", "competition_id", "season"])
        .agg(
            understat_id=("understat_id", "first"),
            us_minutes=("minutes", "sum"),
            us_position=("position", "first"),
            us_goals=("goals", "sum"),
            us_assists=("assists", "sum"),
            **{m: v for m, v in agg.items() if m in US_METRICS},
        )  # fmt: skip
        .reset_index()
        .rename(columns={"tm_player_id": "player_id"})
    )


def build(
    apps: pd.DataFrame,
    games: pd.DataFrame,
    players: pd.DataFrame,
    us_by_ps: pd.DataFrame,
) -> pd.DataFrame:
    a = apps[apps.competition_type == "domestic_league"]
    a = a.assign(club_minutes=a.minutes)
    per_club = (
        a.groupby(["player_id", "competition_id", "season", "club_id"])
        .agg(club_minutes=("minutes", "sum"))
        .reset_index()
    )
    ps = (
        a.groupby(["player_id", "competition_id", "season"])
        .agg(
            games=("game_id", "nunique"),
            minutes=("minutes", "sum"),
            starts=("started", "sum"),
            goals=("goals", "sum"),
            assists=("assists", "sum"),
            yellow_cards=("yellow_cards", "sum"),
            red_cards=("red_cards", "sum"),
            n_clubs=("club_id", "nunique"),
            last_app=("date", "max"),
        )  # fmt: skip
        .reset_index()
    )
    # main club = most league minutes; team strength minutes-weighted across clubs
    strength = team_strength(games)
    pc = per_club.merge(strength, on=["club_id", "competition_id", "season"], how="left")
    pc["w"] = pc.club_minutes.clip(lower=1)
    wavg = pc.assign(ppg_w=pc.team_ppg * pc.w, gd_w=pc.team_gd_pg * pc.w).groupby(
        ["player_id", "competition_id", "season"]
    )
    ts = (wavg.ppg_w.sum() / wavg.w.sum()).rename("team_ppg").to_frame()
    ts["team_gd_pg"] = wavg.gd_w.sum() / wavg.w.sum()
    main = (
        pc.sort_values("club_minutes", ascending=False)
        .drop_duplicates(["player_id", "competition_id", "season"])
        .set_index(["player_id", "competition_id", "season"])[["club_id"]]
    )
    ps = ps.join(ts, on=["player_id", "competition_id", "season"]).join(
        main, on=["player_id", "competition_id", "season"]
    )

    # shares of a full league season (most games any club played that season)
    full = strength.groupby(["competition_id", "season"]).team_games.max().rename("league_games")
    ps = ps.join(full, on=["competition_id", "season"])
    ps["minutes_share"] = (ps.minutes / (ps.league_games * 90)).clip(upper=1)
    ps["starts_share"] = (ps.starts / ps.league_games).clip(upper=1)

    ends = league_season_ends(games)
    ps = ps.merge(ends, on=["competition_id", "season"], how="left")
    ps["as_of_date"] = ps.season_end + pd.Timedelta(days=1)
    if (ps.last_app >= ps.as_of_date).any():  # appearances must all precede as_of
        raise LeakageError("player-season row uses an appearance on/after its as_of date")

    ps = ps.merge(players[["player_id", "date_of_birth", "sub_position"]], on="player_id", how="left")
    ps["age"] = (ps.as_of_date - ps.date_of_birth).dt.days / 365.25

    ps = ps.merge(us_by_ps, on=["player_id", "competition_id", "season"], how="left")
    ps["data_tier"] = np.where(ps.understat_id.notna(), "full", "basic")
    tm = tm_group(ps.sub_position)
    resolved = [resolve_group(t, u) for t, u in zip(tm, ps.us_position, strict=True)]
    ps["position_group"] = [g for g, _ in resolved]
    ps["position_source"] = [s for _, s in resolved]

    # previous season (any domestic league, summed) - strictly earlier data
    prev = ps.groupby(["player_id", "season"]).agg(
        p_min=("minutes", "sum"), p_g=("goals", "sum"), p_a=("assists", "sum"),
        p_npxg=("npxg", lambda s: s.sum(min_count=1)), p_xa=("xa", lambda s: s.sum(min_count=1)),
        p_usmin=("us_minutes", lambda s: s.sum(min_count=1)),
    ).reset_index()  # fmt: skip
    prev["season"] = prev.season + 1
    ps = ps.merge(prev, on=["player_id", "season"], how="left")
    ps["prev_minutes"] = ps.p_min
    p90 = 90 / ps.p_min.where(ps.p_min > 0)
    ps["prev_goals_p90"] = ps.p_g * p90
    ps["prev_assists_p90"] = ps.p_a * p90
    us90 = 90 / ps.p_usmin.where(ps.p_usmin > 0)
    ps["prev_npxg_p90"] = ps.p_npxg * us90
    ps["prev_xa_p90"] = ps.p_xa * us90
    return ps
