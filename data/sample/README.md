# sample_100_transfers.csv

**REAL data, not demo data.** This is a stratified random sample (seed 42, proportional by season) of 100 transfers from the 1,792-row usable set built by `scripts/feasibility/build_usable.py`.

Not for redistribution. Derived from Transfermarkt (via transfermarkt-datasets) and Understat (via Internet Archive snapshots). See `DATA_SOURCES.md`.

| Column | Meaning | Point-in-time rule |
|---|---|---|
| player_id / understat_id | Transfermarkt ID / matched Understat ID | — |
| transfer_date, season_label, window | Move date, season, summer/winter/other | — |
| age_at_transfer | From date of birth | at transfer date |
| position, sub_position | Transfermarkt labels | **current label** (not historical) |
| from_/to_club_name, from_/to_league | Clubs; league = club's domestic league in the relevant season | seller: season just finished (summer) or current (winter) |
| fee_eur_reported_by_tm | Fee as reported by Transfermarkt (may be a media estimate; add-ons not separated) | — |
| tm_market_value_before_transfer_eur, tm_market_value_date | Last valuation dated strictly before the transfer | strictly before |
| tm_market_value_12m_before_eur | Last valuation ≥ 365 days before | before |
| tm_mv_field_in_transfers_table | Market value field in the raw transfers table (matches the point-in-time value in 98.9% of usable rows) | — |
| understat_feature_season | Season start year used for Understat features (last completed season) | completed before transfer |
| us_* | Understat season totals: games, minutes (`us_time`), goals, xG, npxG, assists, xA, shots, key passes, xGChain, xGBuildup | completed season |
| us_*_p90 | Same, per 90 minutes | — |
| tm365_minutes/goals/assists | Transfermarkt appearances in the 365 days strictly before the transfer | strictly before |
| us_match_conf | TM↔Understat match confidence (high/medium) | — |
