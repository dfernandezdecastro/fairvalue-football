"""Build the usable-transfer funnel, point-in-time features and the 100-row sample.

Point-in-time rules (no leakage):
  * Market value = last Transfermarkt valuation dated strictly BEFORE the transfer date.
  * TM performance = appearances strictly BEFORE the transfer date (365-day window).
  * Understat performance = last COMPLETED season before the transfer
    (season s-1 for both summer and winter moves of season s). Understat data is
    season-level only, so winter moves cannot use first-half-of-season stats.

Outputs:
  data/interim/transfers_funnel.csv     every paid transfer with funnel flags + features
  data/sample/sample_100_transfers.csv  stratified random sample of usable rows
  reports/feasibility/coverage_tables.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import BIG5, DATA_CUTOFF, INTERIM, REPORTS, ROOT, load_transfers, read  # noqa: E402

US_LEAGUE = {"EPL": "GB1", "La_liga": "ES1", "Bundesliga": "L1", "Serie_A": "IT1", "Ligue_1": "FR1"}
MIN_US_MINUTES = 900


def point_in_time_mv(t: pd.DataFrame) -> pd.DataFrame:
    v = read("player_valuations", usecols=["player_id", "date", "market_value_in_eur"])
    v["vdate"] = pd.to_datetime(v.date)
    v = v.drop(columns="date").sort_values("vdate")
    left = t[["tid", "player_id", "date"]].sort_values("date")
    # strictly before: shift transfer date back one day for an asof match
    left = left.assign(lookup=left.date - pd.Timedelta(days=1))
    pit = pd.merge_asof(left.sort_values("lookup"), v, left_on="lookup", right_on="vdate",
                        by="player_id", direction="backward")
    pit = pit.rename(columns={"market_value_in_eur": "mv_pit_eur", "vdate": "mv_pit_date"})
    pit["mv_pit_age_days"] = (pit.date - pit.mv_pit_date).dt.days
    left12 = left.assign(lookup=left.date - pd.Timedelta(days=365))
    m12 = pd.merge_asof(left12.sort_values("lookup"), v, left_on="lookup", right_on="vdate",
                        by="player_id", direction="backward")
    pit["mv_12m_before_eur"] = pit.tid.map(m12.set_index("tid").market_value_in_eur)
    return pit[["tid", "mv_pit_eur", "mv_pit_date", "mv_pit_age_days", "mv_12m_before_eur"]]


def tm_pre_window(t: pd.DataFrame) -> pd.DataFrame:
    a = read("appearances", usecols=["player_id", "date", "competition_id", "goals", "assists",
                                     "minutes_played"])
    a["adate"] = pd.to_datetime(a.pop("date"))
    a = a[a.player_id.isin(t.player_id.unique())]
    x = t[["tid", "player_id", "date"]].merge(a, on="player_id", how="inner")
    x = x[(x.adate < x.date) & (x.adate >= x.date - pd.Timedelta(days=365))]
    g = x.groupby("tid").agg(tm365_minutes=("minutes_played", "sum"), tm365_goals=("goals", "sum"),
                             tm365_assists=("assists", "sum"), tm365_apps=("adate", "size"))
    return g.reset_index()


def big5_prev_season(t: pd.DataFrame) -> pd.DataFrame:
    """Did the player appear in a big-5 league in season s-1 (per TM fixtures)?"""
    a = read("appearances", usecols=["game_id", "player_id", "competition_id", "minutes_played"])
    a = a[a.competition_id.isin(BIG5)]
    a = a.merge(read("games", usecols=["game_id", "season"]), on="game_id")
    g = a.groupby(["player_id", "season"]).agg(
        tm_big5_minutes=("minutes_played", "sum"),
        tm_big5_league=("competition_id", lambda s: s.value_counts().index[0])).reset_index()
    return g


def understat_by_tm_season() -> pd.DataFrame:
    us = pd.read_csv(INTERIM / "understat_players.csv")
    m = pd.read_csv(INTERIM / "understat_tm_matches.csv")
    pm = pd.read_csv(INTERIM / "player_id_map.csv")
    m = m[m.confidence != "unmatched"].merge(pm[["understat_id", "tm_player_id"]].rename(
        columns={"tm_player_id": "tm_mode"}), on="understat_id")
    m = m[m.tm_player_id == m.tm_mode]  # drop per-season matches that contradict the player-level map
    keys = m[["understat_id", "league", "season", "tm_player_id", "confidence"]].drop_duplicates()
    us = us.rename(columns={"id": "understat_id"}).merge(keys, on=["understat_id", "league", "season"])
    num = ["games", "time", "goals", "xG", "assists", "xA", "shots", "key_passes", "npg", "npxG",
           "xGChain", "xGBuildup", "yellow_cards", "red_cards"]
    for c in num:
        us[c] = pd.to_numeric(us[c], errors="coerce")
    agg = us.groupby(["tm_player_id", "season"]).agg(
        **{f"us_{c}": (c, "sum") for c in num},
        understat_id=("understat_id", "first"), us_position=("position", "first"),
        us_team=("team_title", "first"), us_match_conf=("confidence", "first")).reset_index()
    return agg


def main() -> None:
    t = load_transfers()
    t = t[(t.date >= "2015-07-01") & (t.date <= DATA_CUTOFF) & (t.fee_status == "paid")].copy()
    t["tid"] = np.arange(len(t))
    t["involves_big5"] = t.to_league.isin(BIG5) | t.from_league.isin(BIG5)
    t["likely_loan"] = t.returns_within_400d
    t["feat_season"] = t.season - 1

    t = t.merge(point_in_time_mv(t), on="tid", how="left")
    t = t.merge(tm_pre_window(t), on="tid", how="left")
    t[["tm365_minutes", "tm365_goals", "tm365_assists", "tm365_apps"]] = \
        t[["tm365_minutes", "tm365_goals", "tm365_assists", "tm365_apps"]].fillna(0)
    b5 = big5_prev_season(t).rename(columns={"player_id": "player_id", "season": "feat_season"})
    t = t.merge(b5, on=["player_id", "feat_season"], how="left")

    log = pd.read_csv(INTERIM / "understat_snapshot_log.csv")
    log["competition_id"] = log.league.map(US_LEAGUE)
    avail = set(map(tuple, log[log.players > 0][["competition_id", "season"]].values))
    t["us_league_season_archived"] = [
        (lg, s) in avail for lg, s in zip(t.tm_big5_league, t.feat_season)]

    us = understat_by_tm_season().rename(columns={"tm_player_id": "player_id", "season": "feat_season"})
    t = t.merge(us, on=["player_id", "feat_season"], how="left")

    # ---- funnel flags (cumulative) ----
    f = {}
    f["F0 paid fee, 2015/16-2025/26 (to 6 Jul 2026)"] = pd.Series(True, index=t.index)
    f["F1 not a probable paid loan"] = f[list(f)[-1]] & ~t.likely_loan
    f["F2 buying or selling club in big-5"] = f[list(f)[-1]] & t.involves_big5
    f["F3 played big-5 league in prior season (TM)"] = f[list(f)[-1]] & t.tm_big5_minutes.gt(0)
    f["F4 that league-season recovered from Understat archive"] = f[list(f)[-1]] & t.us_league_season_archived
    f["F5 matched to Understat player"] = f[list(f)[-1]] & t.understat_id.notna()
    f[f"F6 >= {MIN_US_MINUTES} Understat minutes prior season"] = f[list(f)[-1]] & t.us_time.ge(MIN_US_MINUTES)
    f["F7 point-in-time market value <= 365 days old"] = f[list(f)[-1]] & t.mv_pit_age_days.le(365)
    for k, v in f.items():
        t[k.split()[0]] = v.values
    t["usable"] = t["F7"]
    # Broader alternative population: TM-only features from any covered league
    t["alt_tm_only_usable"] = t.F1 & t.tm365_minutes.ge(MIN_US_MINUTES) & t.mv_pit_age_days.le(365)

    INTERIM.mkdir(parents=True, exist_ok=True)
    t.to_csv(INTERIM / "transfers_funnel.csv", index=False)

    # ---- tables ----
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = ["# Coverage tables (auto-generated by scripts/feasibility/build_usable.py)\n"]
    out.append("## Funnel\n\n| Step | Transfers | % of F0 |\n|---|---:|---:|")
    n0 = len(t)
    for k, v in f.items():
        out.append(f"| {k} | {int(v.sum()):,} | {v.sum() / n0:.1%} |")
    out.append(f"| ALT: TM-only features (>= {MIN_US_MINUTES} TM minutes in prior 365d, any covered league) + PIT market value, F1 base | {int(t.alt_tm_only_usable.sum()):,} | {t.alt_tm_only_usable.mean():.1%} |")

    u = t[t.usable].copy()
    u["fee_bucket"] = pd.cut(u.transfer_fee / 1e6, [0, 2, 5, 10, 20, 40, 80, 1000],
                             labels=["<2M", "2-5M", "5-10M", "10-20M", "20-40M", "40-80M", "80M+"])
    u["age_bucket"] = pd.cut(u.age, [0, 20, 23, 26, 29, 50], labels=["<=20", "21-23", "24-26", "27-29", "30+"])
    u["buyer_league"] = u.to_league.fillna("non-covered").map(lambda x: BIG5.get(x, x))
    u["season_label"] = u.season.map(lambda s: f"{s}/{str(s + 1)[-2:]}")

    def table(df: pd.DataFrame, title: str) -> None:
        out.append(f"\n## {title}\n")
        out.append(df.to_markdown())

    p2 = t[t.F2]
    table(pd.crosstab(p2.season.map(lambda s: f"{s}/{str(s + 1)[-2:]}"), p2.to_league.map(lambda x: BIG5.get(x, "other/non-covered")),
                      margins=True), "F2 (paid, big-5 involved) by season x buying league")
    table(pd.crosstab(u.season_label, u.buyer_league, margins=True), "USABLE (F7) by season x buying league")
    table(pd.crosstab(u.sub_position.fillna("Missing"), u.position.fillna("Missing"), margins=True), "USABLE by position")
    table(u.fee_bucket.value_counts().sort_index().to_frame("transfers"), "USABLE by fee")
    table(u.age_bucket.value_counts().sort_index().to_frame("transfers"), "USABLE by age at transfer")
    table(u.window.value_counts().to_frame("transfers"), "USABLE by window")
    desc = u[["transfer_fee", "mv_pit_eur", "age", "us_time", "tm365_minutes"]].describe().T
    table(desc.round(1), "USABLE numeric summary")
    (REPORTS / "coverage_tables.md").write_text("\n".join(out), encoding="utf-8")

    # ---- 100-row stratified sample ----
    rng = np.random.default_rng(42)
    u = u.assign(_r=rng.random(len(u))).sort_values("_r")
    quota = (u.season_label.value_counts() / len(u) * 100).round().astype(int)
    per = pd.concat([u[u.season_label == s].head(q) for s, q in quota.items()])
    sample = per.head(100)
    if len(sample) < 100:
        sample = pd.concat([sample, u[~u.tid.isin(sample.tid)].head(100 - len(sample))])
    for c in ["goals", "xG", "npxG", "assists", "xA", "shots", "key_passes", "xGChain", "xGBuildup"]:
        sample[f"us_{c}_p90"] = (sample[f"us_{c}"] / sample.us_time * 90).round(3)
    cols = ["player_id", "understat_id", "player_name", "date", "season_label", "window", "age",
            "position", "sub_position", "from_club_name", "from_league", "to_club_name", "to_league",
            "transfer_fee", "mv_pit_eur", "mv_pit_date", "mv_12m_before_eur", "market_value_in_eur",
            "feat_season", "us_team", "us_position", "us_games", "us_time", "us_goals", "us_xG", "us_npxG",
            "us_assists", "us_xA", "us_shots", "us_key_passes", "us_xGChain", "us_xGBuildup",
            "us_goals_p90", "us_xG_p90", "us_npxG_p90", "us_assists_p90", "us_xA_p90", "us_shots_p90",
            "us_key_passes_p90", "us_xGChain_p90", "us_xGBuildup_p90",
            "tm365_minutes", "tm365_goals", "tm365_assists", "us_match_conf"]
    sample = sample[cols].rename(columns={
        "date": "transfer_date", "transfer_fee": "fee_eur_reported_by_tm",
        "mv_pit_eur": "tm_market_value_before_transfer_eur", "mv_pit_date": "tm_market_value_date",
        "mv_12m_before_eur": "tm_market_value_12m_before_eur",
        "market_value_in_eur": "tm_mv_field_in_transfers_table", "feat_season": "understat_feature_season",
        "age": "age_at_transfer"})
    sample["age_at_transfer"] = sample.age_at_transfer.round(2)
    sample["data_status"] = "REAL (Transfermarkt via transfermarkt-datasets; Understat via Wayback archive)"
    out_dir = ROOT / "data" / "sample"
    out_dir.mkdir(parents=True, exist_ok=True)
    sample.sort_values("transfer_date").to_csv(out_dir / "sample_100_transfers.csv", index=False)

    for k, v in f.items():
        print(f"{int(v.sum()):>6}  {k}")
    print("ALT TM-only usable:", int(t.alt_tm_only_usable.sum()))
    print("sample rows:", len(sample))


if __name__ == "__main__":
    main()
