"""Recover Understat season-level player tables from Wayback Machine snapshots.

Why Wayback: understat.com has been returning a maintenance page
("We will come back soon") since ~2 Nov 2026, so the live site cannot be used.
Archived league pages embed `playersData` (one row per player-team-season with
minutes, goals, xG, assists, xA, shots, key passes, npxG, xGChain, xGBuildup).

Politeness: one request at a time, a pause between requests, raw HTML cached
on disk so nothing is fetched twice.

Usage: python -P scripts/feasibility/fetch_understat_wayback.py
Output: data/raw/understat_wayback/html/*.html  (cache)
        data/interim/understat_players.csv        (parsed, one row per player-team-season)
        data/interim/understat_snapshot_log.csv   (which snapshot was used per league-season)
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "raw" / "understat_wayback" / "html"
OUT = ROOT / "data" / "interim"
LEAGUES = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]
SEASONS = range(2014, 2026)  # 2014 = 2014/15 ... 2025 = 2025/26
UA = {"User-Agent": "FairValueFootball-feasibility/0.1 (non-commercial research)"}
PAUSE = 1.5

session = requests.Session()
session.headers.update(UA)


def get(url: str, **kw) -> requests.Response:
    for attempt in range(4):
        try:
            r = session.get(url, timeout=60, **kw)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 503):
                time.sleep(10 * (attempt + 1))
                continue
            return r
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def snapshots(league: str, season: int) -> list[str]:
    """Snapshot timestamps after the season finished, newest first."""
    url = (
        "https://web.archive.org/cdx/search/cdx"
        f"?url=understat.com/league/{league}/{season}&output=json"
        "&filter=statuscode:200&collapse=digest"
    )
    r = get(url)
    time.sleep(PAUSE)
    rows = r.json()[1:] if r.text.strip() else []
    season_end = f"{season + 1}0601"  # final totals only after the season ends
    # From ~Feb 2026 Understat pages load data client-side; those archived
    # pages are ~6 KB shells with no playersData, so skip small captures.
    def big(row):
        try:
            return int(row[6]) > 20000
        except ValueError:
            return False
    ts = sorted(row[1] for row in rows if row[1] >= season_end and big(row))
    # Fallback: late-season captures (from 10 May) that miss at most the last
    # round or two; flagged "near_final" in the snapshot log. Newest first.
    near = sorted((row[1] for row in rows
                   if f"{season + 1}0510" <= row[1] < season_end and big(row)), reverse=True)
    return ts + near


PAT = re.compile(r"var\s+playersData\s*=\s*JSON\.parse\('(.*?)'\)", re.S)


def decode_js_string(s: str) -> str:
    # Understat escapes characters as \xNN; these are UTF-8 bytes, so rebuild
    # the byte string and decode it as UTF-8 (keeps accented names correct).
    raw = re.sub(rb"\\x([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), s.encode("utf-8"))
    return raw.decode("utf-8").replace("\\'", "'").replace("\\\\", "\\")


def parse(html: str) -> list[dict] | None:
    m = PAT.search(html)
    if not m:
        return None
    try:
        return json.loads(decode_js_string(m.group(1)))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    frames, log = [], []
    for league in LEAGUES:
        for season in SEASONS:
            got = None
            cached = sorted(CACHE.glob(f"{league}_{season}_*.html"))
            for path in cached:
                rows = parse(path.read_text(encoding="utf-8", errors="replace"))
                if rows:
                    got = (path.stem.split("_")[-1], rows, "cache")
                    break
            if not got:
                for ts in snapshots(league, season)[:15]:
                    r = get(f"https://web.archive.org/web/{ts}id_/https://understat.com/league/{league}/{season}")
                    time.sleep(PAUSE)
                    if r.status_code != 200:
                        continue
                    rows = parse(r.text)
                    if rows and len(rows) > 300:
                        (CACHE / f"{league}_{season}_{ts}.html").write_text(r.text, encoding="utf-8")
                        got = (ts, rows, "wayback")
                        break
            if got:
                ts, rows, how = got
                df = pd.DataFrame(rows)
                df["league"], df["season"], df["snapshot"] = league, season, ts
                frames.append(df)
                status = "ok" if ts >= f"{season + 1}0601" else "near_final"
                log.append(dict(league=league, season=season, snapshot=ts, players=len(df), status=status, via=how))
            else:
                log.append(dict(league=league, season=season, snapshot=None, players=0, status="missing", via=None))
            print(log[-1], flush=True)
    pd.DataFrame(log).to_csv(OUT / "understat_snapshot_log.csv", index=False)
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(OUT / "understat_players.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
