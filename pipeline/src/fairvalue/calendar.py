"""Football calendar helpers: seasons and transfer windows.

Convention: a season is identified by its START year (2024 -> "2024/25").
Use these helpers for transfer dates and valuation dates. For matches, always
prefer the fixture's official season field: COVID-delayed 2019/20 matches were
played in July-August 2020, so calendar rules mislabel them.
"""

from __future__ import annotations

from datetime import date

import pandas as pd


def season_of(d: date | pd.Timestamp) -> int:
    """Season start year for a date: Jul-Dec -> same year, Jan-Jun -> previous year."""
    return d.year if d.month >= 7 else d.year - 1


def season_label(start_year: int) -> str:
    """2024 -> '2024/25'."""
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def window_of(d: date | pd.Timestamp) -> str:
    """Transfer window: 'summer' (Jun-Sep), 'winter' (Dec-Feb) or 'other'."""
    if d.month in (6, 7, 8, 9):
        return "summer"
    if d.month in (12, 1, 2):
        return "winter"
    return "other"


def last_completed_season(d: date | pd.Timestamp) -> int:
    """Most recent season fully finished before date `d`.

    A season ends by 30 June, so for any date in season s the last completed
    season is s - 1. Used to pick season-level stats for a transfer without
    peeking at the season in progress.
    """
    return season_of(d) - 1
