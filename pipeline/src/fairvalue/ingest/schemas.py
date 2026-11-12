"""Data contracts: the columns and types every table must have.

A contract is a mapping ``column -> dtype``. ``enforce`` checks that every
column exists, casts it to the declared type (failing loudly on bad values) and
drops undeclared columns. Applying contracts both when reading raw data and when
reading staging files means a silent upstream format change becomes an error
here, not a subtly wrong model later.

Dtypes: "int" (non-null int64), "Int" (nullable Int64), "float", "str",
"date" (datetime64), "bool".
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

Schema = Mapping[str, str]


class SchemaError(ValueError):
    """A table does not satisfy its contract."""


def _cast(s: pd.Series, dtype: str, table: str, col: str) -> pd.Series:
    try:
        if dtype == "int":
            if s.isna().any():
                raise SchemaError(f"{table}.{col}: {int(s.isna().sum())} nulls in non-null int column")
            return pd.to_numeric(s, errors="raise").astype("int64")
        if dtype == "Int":
            return pd.to_numeric(s, errors="raise").astype("Int64")
        if dtype == "float":
            return pd.to_numeric(s, errors="raise").astype("float64")
        if dtype == "str":
            return s.astype("str")  # pandas 3 keeps missing values missing
        if dtype == "date":
            return pd.to_datetime(s, errors="raise")
        if dtype == "bool":
            if s.dtype == bool:
                return s
            mapped = s.map({True: True, False: False, "True": True, "False": False})
            if mapped.isna().any():
                raise SchemaError(f"{table}.{col}: non-boolean values")
            return mapped.astype(bool)
    except SchemaError:
        raise
    except (ValueError, TypeError) as e:
        raise SchemaError(f"{table}.{col}: cannot cast to {dtype}: {e}") from e
    raise SchemaError(f"{table}.{col}: unknown dtype '{dtype}'")


def enforce(df: pd.DataFrame, schema: Schema, table: str) -> pd.DataFrame:
    missing = [c for c in schema if c not in df.columns]
    if missing:
        raise SchemaError(f"{table}: missing column(s) {missing}")
    return pd.DataFrame({c: _cast(df[c], t, table, c) for c, t in schema.items()})


# ---------------------------------------------------------------------------
# Raw Transfermarkt tables (only the columns we use).
# Snapshot-only fields (current caps, contract expiry, current club, latest
# market value, agent) are deliberately NOT part of any contract, so they never
# enter staging at all. That is the strongest leakage guard there is.
# ---------------------------------------------------------------------------
TM_RAW: dict[str, Schema] = {
    "competitions": {
        "competition_id": "str",
        "name": "str",
        "type": "str",
        "sub_type": "str",
        "country_name": "str",
    },
    "clubs": {"club_id": "int", "club_code": "str", "name": "str"},
    "players": {
        "player_id": "int",
        "name": "str",
        "first_name": "str",
        "last_name": "str",
        "player_code": "str",
        "date_of_birth": "date",
        "position": "str",
        "sub_position": "str",
        "foot": "str",
        "height_in_cm": "float",
        "country_of_citizenship": "str",
    },
    "games": {
        "game_id": "int",
        "competition_id": "str",
        "competition_type": "str",
        "season": "int",
        "date": "date",
        "home_club_id": "int",
        "away_club_id": "int",
        "home_club_goals": "Int",
        "away_club_goals": "Int",
    },
    "appearances": {
        "game_id": "int",
        "player_id": "int",
        "player_club_id": "int",
        "date": "date",
        "player_name": "str",
        "competition_id": "str",
        "yellow_cards": "int",
        "red_cards": "int",
        "goals": "int",
        "assists": "int",
        "minutes_played": "int",
    },
    "game_lineups": {"game_id": "int", "player_id": "int", "club_id": "int", "type": "str"},
    "player_valuations": {"player_id": "int", "date": "date", "market_value_in_eur": "float"},
    "transfers": {
        "player_id": "int",
        "transfer_date": "date",
        "from_club_id": "int",
        "to_club_id": "int",
        "from_club_name": "str",
        "to_club_name": "str",
        "transfer_fee": "float",
        "market_value_in_eur": "float",
        "player_name": "str",
    },
}

# Understat season-level player rows as embedded in archived league pages.
UNDERSTAT_RAW: Schema = {
    "id": "int",
    "player_name": "str",
    "games": "int",
    "time": "int",
    "goals": "int",
    "xG": "float",
    "assists": "int",
    "xA": "float",
    "shots": "int",
    "key_passes": "int",
    "yellow_cards": "int",
    "red_cards": "int",
    "position": "str",
    "team_title": "str",
    "npg": "int",
    "npxG": "float",
    "xGChain": "float",
    "xGBuildup": "float",
}

# ---------------------------------------------------------------------------
# Staging tables (written by fairvalue.staging, read by everything downstream)
# ---------------------------------------------------------------------------
STAGING: dict[str, Schema] = {
    "competitions": {
        "competition_id": "str",
        "name": "str",
        "type": "str",
        "country_name": "str",
        "is_big5": "bool",
        "has_full_history": "bool",
    },
    "clubs": {"club_id": "int", "slug": "str", "name": "str"},
    "players": {
        "player_id": "int",
        "name": "str",
        "slug": "str",
        "date_of_birth": "date",
        "position": "str",
        "sub_position": "str",
        "foot": "str",
        "height_cm": "float",
        "citizenship": "str",
    },
    "games": {
        "game_id": "int",
        "competition_id": "str",
        "competition_type": "str",
        "season": "int",
        "date": "date",
        "home_club_id": "int",
        "away_club_id": "int",
        "home_goals": "Int",
        "away_goals": "Int",
    },
    "appearances": {
        "game_id": "int",
        "player_id": "int",
        "club_id": "int",
        "date": "date",
        "season": "int",
        "competition_id": "str",
        "competition_type": "str",
        "started": "bool",
        "minutes": "int",
        "goals": "int",
        "assists": "int",
        "yellow_cards": "int",
        "red_cards": "int",
    },
    "valuations": {"player_id": "int", "date": "date", "value_eur": "float"},
    "club_league_seasons": {"club_id": "int", "season": "int", "competition_id": "str"},
    "transfers": {
        "transfer_id": "int",
        "player_id": "int",
        "date": "date",
        "season": "int",
        "window": "str",
        "from_club_id": "int",
        "to_club_id": "int",
        "from_club_name": "str",
        "to_club_name": "str",
        "from_competition_id": "str",
        "to_competition_id": "str",
        "fee_eur": "float",
        "fee_status": "str",
        "returns_within_400d": "bool",
        "move_type": "str",
        "tm_reported_mv_eur": "float",
    },
    "understat_player_seasons": {
        "understat_id": "int",
        "player_name": "str",
        "league": "str",
        "competition_id": "str",
        "season": "int",
        "team_title": "str",
        "position": "str",
        "games": "int",
        "minutes": "int",
        "goals": "int",
        "npg": "int",
        "xg": "float",
        "npxg": "float",
        "assists": "int",
        "xa": "float",
        "shots": "int",
        "key_passes": "int",
        "xg_chain": "float",
        "xg_buildup": "float",
        "yellow_cards": "int",
        "red_cards": "int",
        "snapshot": "str",
    },
    "understat_coverage": {
        "league": "str",
        "competition_id": "str",
        "season": "int",
        "status": "str",
        "snapshot": "str",
        "players": "int",
    },
    "understat_tm_matches": {
        "understat_id": "int",
        "league": "str",
        "season": "int",
        "us_name": "str",
        "tm_player_id": "Int",
        "tm_name": "str",
        "name_score": "float",
        "runner_up_score": "float",
        "stat_exact": "bool",
        "n_stat_candidates": "int",
        "confidence": "str",
        "agrees_with_player_map": "bool",
    },
    "player_id_map": {
        "understat_id": "int",
        "tm_player_id": "int",
        "seasons_matched": "int",
        "n_tm_ids": "int",
        "confidence": "str",
    },
}
