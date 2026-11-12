"""Project-wide constants and paths. Nothing here reads data."""

from __future__ import annotations

from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"  # git-ignored: raw third-party data never leaves the machine
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
OUTPUT_DIR = DATA_DIR / "outputs"

# Frozen data vintage (see DATA_SOURCES.md)
TRANSFERMARKT_CUTOFF = date(2026, 7, 6)
UNDERSTAT_LAST_SEASON = 2024  # season start year: 2024 = 2024/25

BIG5 = {
    "GB1": "Premier League",
    "ES1": "LaLiga",
    "L1": "Bundesliga",
    "IT1": "Serie A",
    "FR1": "Ligue 1",
}
# Domestic leagues with full match history 2012/13-2025/26 in the Transfermarkt snapshot
FULL_HISTORY_LEAGUES = frozenset(BIG5) | frozenset(
    {"NL1", "PO1", "BE1", "TR1", "RU1", "SC1", "GR1", "DK1", "UKR1"}
)

MIN_MINUTES_FOR_ESTIMATE = 900
