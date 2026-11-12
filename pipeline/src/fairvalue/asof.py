"""Point-in-time ("as-of") guards: the core of rule R2 (no leakage).

Every feature for a historical prediction must be computable from rows dated
strictly before the prediction's reference date. These helpers make that a
checked contract instead of a promise:

* ``rows_before`` - the only sanctioned way to filter a dated table for features.
* ``assert_no_future_rows`` - fails loudly if any row is dated at/after ``as_of``.
* ``assert_no_snapshot_fields`` - blocks columns that only describe *today*
  (e.g. current international caps), which silently leak the future.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

import pandas as pd

# Columns in the Transfermarkt snapshot that reflect the state at scrape time,
# not at a historical date. Never use them as model features.
SNAPSHOT_FIELDS = frozenset(
    {
        "international_caps",
        "international_goals",
        "current_national_team_id",
        "contract_expiration_date",
        "current_club_id",
        "current_club_name",
        "current_club_domestic_competition_id",
        "player_current_club_id",
        "market_value_in_eur",  # players table: latest value, not historical
        "highest_market_value_in_eur",
        "last_season",
        "agent_name",
    }
)


class LeakageError(AssertionError):
    """Raised when data from the future could reach a feature."""


def _ts(d: date | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(d)


def rows_before(df: pd.DataFrame, date_col: str, as_of: date | pd.Timestamp) -> pd.DataFrame:
    """Rows strictly before ``as_of`` (same-day rows are excluded on purpose:
    a valuation published on transfer day may already reflect the transfer)."""
    dates = pd.to_datetime(df[date_col])
    return df.loc[dates < _ts(as_of)]


def assert_no_future_rows(df: pd.DataFrame, date_col: str, as_of: date | pd.Timestamp) -> None:
    dates = pd.to_datetime(df[date_col])
    bad = dates >= _ts(as_of)
    if bad.any():
        raise LeakageError(
            f"{int(bad.sum())} row(s) in '{date_col}' are dated on/after as_of={_ts(as_of).date()} "
            f"(latest: {dates[bad].max().date()})"
        )


def assert_no_snapshot_fields(columns: Iterable[str]) -> None:
    found = sorted(set(columns) & SNAPSHOT_FIELDS)
    if found:
        raise LeakageError(f"snapshot-only fields cannot be used as features: {found}")
