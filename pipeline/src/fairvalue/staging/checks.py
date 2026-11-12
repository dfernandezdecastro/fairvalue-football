"""Reconcile staging against the numbers published in the feasibility report.

If a refactor changes any of these, either the refactor has a bug or the change
is deliberate, and then the report must be updated too. Usable-transfer counts
(1,792 / 4,892) depend on as-of features and are reconciled in Step 3.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fairvalue.config import BIG5
from fairvalue.staging.build import read_staging


@dataclass(frozen=True)
class Check:
    name: str
    expected: float
    actual: float
    tolerance: float = 0.0

    @property
    def ok(self) -> bool:
        return abs(self.actual - self.expected) <= self.tolerance


# Published in reports/feasibility/FEASIBILITY_REPORT.md (12 Nov 2026), with one
# correction (see the report's erratum): the feasibility loan rule depended on the
# arbitrary order of same-day rows and excluded 11 "buy and loan back" transfers.
# Staging requires the return to happen on a later date: 15,405 -> 15,416 and
# 5,630 -> 5,637.
EXPECTED = {
    "paid_fee_transfers_2015_cutoff": 15_794,
    "paid_excluding_probable_loans": 15_416,
    "paid_big5_involved": 5_637,
    "understat_player_seasons": 24_160,
    "understat_league_seasons_recovered": 45,
    "understat_match_rate": 0.981,
    "understat_players_mapped": 7_819,
}


def run_checks() -> list[Check]:
    t = read_staging("transfers")
    window = t[t.date >= pd.Timestamp("2015-07-01")]
    paid = window[window.fee_status == "paid"]
    not_loan = paid[paid.move_type == "paid_transfer"]
    big5 = not_loan[not_loan.to_competition_id.isin(BIG5) | not_loan.from_competition_id.isin(BIG5)]

    us = read_staging("understat_player_seasons")
    cov = read_staging("understat_coverage")
    m = read_staging("understat_tm_matches")
    pm = read_staging("player_id_map")

    actual = {
        "paid_fee_transfers_2015_cutoff": len(paid),
        "paid_excluding_probable_loans": len(not_loan),
        "paid_big5_involved": len(big5),
        "understat_player_seasons": len(us),
        "understat_league_seasons_recovered": int((cov.status != "missing").sum()),
        "understat_match_rate": round(float((m.confidence != "unmatched").mean()), 3),
        "understat_players_mapped": len(pm),
    }
    return [
        Check(k, v, actual[k], tolerance=0.001 if isinstance(v, float) else 0) for k, v in EXPECTED.items()
    ]
