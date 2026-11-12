"""Understat season tables recovered from the Internet Archive.

understat.com has served a maintenance page since ~2 Nov 2026. Archived league
pages (until ~Feb 2026) embed ``playersData`` JSON: one row per player per
league-season. ``fetch_cache`` downloads them politely (one request at a time,
pauses, cached on disk); ``read_cache`` parses the cache offline. The rest of
the pipeline only ever uses ``read_cache``.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd

from fairvalue.ingest.schemas import UNDERSTAT_RAW, enforce
from fairvalue.ingest.sources import UNDERSTAT_CACHE

LEAGUES = {
    "EPL": "GB1",
    "La_liga": "ES1",
    "Bundesliga": "L1",
    "Serie_A": "IT1",
    "Ligue_1": "FR1",
}
SEASONS = range(2014, 2026)  # 2014/15 ... 2025/26 (2025/26 is not recoverable)

_PLAYERS = re.compile(r"var\s+playersData\s*=\s*JSON\.parse\('(.*?)'\)", re.S)
_FILENAME = re.compile(r"^(?P<league>.+)_(?P<season>\d{4})_(?P<ts>\d{14})$")


def decode_js_string(s: str) -> str:
    """Understat escapes characters as \\xNN UTF-8 bytes: rebuild bytes, decode UTF-8."""
    raw = re.sub(rb"\\x([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), s.encode("utf-8"))
    return raw.decode("utf-8").replace("\\'", "'").replace("\\\\", "\\")


def parse_players(html: str) -> list[dict] | None:
    """Rows from a league page, or None if absent/truncated (some captures stop at 1 MB)."""
    m = _PLAYERS.search(html)
    if not m:
        return None
    try:
        return json.loads(decode_js_string(m.group(1)))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def snapshot_status(season: int, ts: str) -> str:
    """'final' if captured after 1 June following the season, else 'near_final'."""
    return "final" if ts >= f"{season + 1}0601" else "near_final"


def read_cache(pages: list[Path] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse cached pages -> (player-season rows, coverage table)."""
    pages = pages if pages is not None else sorted(UNDERSTAT_CACHE.glob("*.html"))
    frames, cov = [], []
    found = set()
    for p in pages:
        m = _FILENAME.match(p.stem)
        if not m:
            raise ValueError(f"unexpected cache filename: {p.name}")
        league, season, ts = m["league"], int(m["season"]), m["ts"]
        rows = parse_players(p.read_text(encoding="utf-8"))
        if not rows:
            raise ValueError(f"cached page has no parseable playersData: {p.name}")
        df = enforce(pd.DataFrame(rows), UNDERSTAT_RAW, f"understat.{p.stem}")
        df["league"], df["season"], df["snapshot"] = league, season, ts
        frames.append(df)
        found.add((league, season))
        cov.append(dict(league=league, season=season, status=snapshot_status(season, ts), snapshot=ts, players=len(df)))
    for league in LEAGUES:
        for season in SEASONS:
            if (league, season) not in found:
                cov.append(dict(league=league, season=season, status="missing", snapshot=None, players=0))
    coverage = pd.DataFrame(cov)
    coverage["competition_id"] = coverage.league.map(LEAGUES)
    return pd.concat(frames, ignore_index=True), coverage.sort_values(["league", "season"])


# --------------------------------------------------------------------------- network
def fetch_cache(cache: Path = UNDERSTAT_CACHE, pause: float = 1.5) -> None:  # pragma: no cover
    """Rebuild the cache from the Wayback Machine. Slow and polite; skips cached seasons."""
    import requests

    session = requests.Session()
    session.headers["User-Agent"] = "FairValueFootball/0.1 (non-commercial research)"
    cache.mkdir(parents=True, exist_ok=True)

    def get(url: str) -> requests.Response | None:
        for attempt in range(4):
            try:
                r = session.get(url, timeout=60)
                if r.status_code in (429, 503):
                    time.sleep(10 * (attempt + 1))
                    continue
                return r
            except requests.RequestException:
                time.sleep(5 * (attempt + 1))
        return None

    for league in LEAGUES:
        for season in SEASONS:
            if list(cache.glob(f"{league}_{season}_*.html")):
                continue
            r = get(
                "https://web.archive.org/cdx/search/cdx"
                f"?url=understat.com/league/{league}/{season}&output=json"
                "&filter=statuscode:200&collapse=digest"
            )
            time.sleep(pause)
            rows = r.json()[1:] if r is not None and r.text.strip() else []

            def size_ok(row: list[str]) -> bool:  # post-Feb-2026 captures are ~6 KB data-less shells
                return row[6].isdigit() and int(row[6]) > 20000

            final = sorted(row[1] for row in rows if row[1] >= f"{season + 1}0601" and size_ok(row))
            near = sorted(
                (row[1] for row in rows if f"{season + 1}0510" <= row[1] < f"{season + 1}0601" and size_ok(row)),
                reverse=True,
            )
            for ts in (final + near)[:15]:
                page = get(f"https://web.archive.org/web/{ts}id_/https://understat.com/league/{league}/{season}")
                time.sleep(pause)
                if page is not None and page.status_code == 200:
                    players = parse_players(page.text)
                    if players and len(players) > 300:
                        (cache / f"{league}_{season}_{ts}.html").write_text(page.text, encoding="utf-8")
                        break
