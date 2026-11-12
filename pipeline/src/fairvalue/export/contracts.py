"""Contracts for the published (database) tables. Column order = COPY order = SQL definition.

Keep in sync with supabase/migrations/*.sql; `tests/test_export.py` checks that
every contract column appears in the migration.
"""

from __future__ import annotations

from fairvalue.ingest.schemas import Schema

RATE = ["goals", "assists", "npxg", "xa", "shots", "key_passes", "xg_chain", "xg_buildup"]

PUBLISH: dict[str, Schema] = {
    "competitions": {"id": "str", "name": "str", "country": "str", "is_big5": "bool", "has_full_history": "bool"},
    "clubs": {"id": "int", "name": "str", "slug": "str"},
    "players": {
        "id": "int", "name": "str", "slug": "str", "birth_year": "Int", "position": "str", "sub_position": "str",
        "foot": "str", "height_cm": "float", "citizenship": "str",
    },
    "model_runs": {
        "id": "str", "model": "str", "created_at": "str", "pipeline_version": "str", "is_current": "bool",
        "summary": "str",
    },
    "player_seasons": {
        "player_id": "int", "season": "int", "competition_id": "str", "club_id": "Int", "data_tier": "str",
        "position_group": "str", "position_source": "str", "age": "float", "games": "int", "minutes": "int",
        "starts": "int", "goals": "int", "assists": "int", "npxg": "float", "xa": "float", "shots": "float",
        "key_passes": "float", "xg_chain": "float", "xg_buildup": "float", "minutes_share": "float",
        "starts_share": "float", "team_ppg": "float", "eligible": "bool", "peer_scope": "str", "peer_n": "int",
        **{f"{m}_p90": "float" for m in RATE},
        **{f"{m}_p90_shrunk": "float" for m in RATE},
        **{f"{m}_p90_pct": "float" for m in RATE},
        "minutes_share_pct": "float", "starts_share_pct": "float",
    },
    "similar_players": {
        "player_id": "int", "season": "int", "competition_id": "str", "rank": "int", "neighbour_id": "int",
        "neighbour_competition_id": "str", "similarity": "float",
    },
    "piv_estimates": {
        "player_id": "int", "season": "int", "competition_id": "str", "model_tier": "str", "model_run_id": "str",
        "model_kind": "str", "train_through": "int", "reliability": "str", "reliability_reason": "str",
        "market_value_eur": "float", "market_value_date": "date", "market_index_eur": "float",
        "estimate_eur": "float", "lo80_eur": "float", "hi80_eur": "float", "lo95_eur": "float", "hi95_eur": "float",
        "peer_estimate_eur": "float", "peer_lo80_eur": "float", "peer_hi80_eur": "float", "peer_lo95_eur": "float",
        "peer_hi95_eur": "float", "league_shift_log": "float", "market_gap_log": "float", "gap_log": "float",
        "gap_label": "str", "calibration_group": "str", "drivers": "str",
    },
    "transfers": {
        "id": "int", "player_id": "int", "date": "date", "season": "int", "transfer_window": "str",
        "from_club_id": "int", "to_club_id": "int", "from_competition_id": "str", "to_competition_id": "str",
        "position_group": "str", "age": "float", "fee_eur": "float", "mv_before_eur": "float",
        "mv_before_date": "date", "model_run_id": "str", "expected_fee_eur": "float", "lo80_eur": "float",
        "hi80_eur": "float", "lo95_eur": "float", "hi95_eur": "float", "premium_eur": "float",
        "premium_pct": "float", "label": "str", "reliability": "str", "reliability_reason": "str",
        "calibration_group": "str", "drivers": "str",
    },
    "club_audit": {
        "club_id": "int", "period": "str", "season_from": "int", "season_to": "int", "n_assessed": "int",
        "ranked": "bool", "total_fee_eur": "float", "total_expected_eur": "float", "price_ratio": "float",
        "price_ratio_lo80": "float", "price_ratio_hi80": "float", "share_notable_premium": "float",
        "share_notable_discount": "float", "outcome_n": "int", "outcome_median_mv_change_12m": "float",
    },
    "data_coverage": {"source": "str", "competition_id": "str", "season": "int", "status": "str"},
    "app_meta": {"key": "str", "value": "str"},
}  # fmt: skip

# Load order respects foreign keys; truncation runs in reverse.
LOAD_ORDER = [
    "competitions", "clubs", "players", "model_runs", "player_seasons", "similar_players", "piv_estimates",
    "transfers", "club_audit", "data_coverage", "app_meta",
]  # fmt: skip
JSON_COLUMNS = {
    ("model_runs", "summary"),
    ("piv_estimates", "drivers"),
    ("transfers", "drivers"),
    ("app_meta", "value"),
}

# Licensing / privacy guard: these must never be published (DATA_SOURCES.md, decision D15).
FORBIDDEN_COLUMNS = {
    "date_of_birth", "contract_expiration_date", "international_caps", "agent_name", "current_club_id",
    "highest_market_value_in_eur", "city_of_birth", "image_url", "minutes_played", "game_id",
}  # fmt: skip
