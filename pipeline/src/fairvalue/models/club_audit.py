"""Club Transfer Audit: how a club's fees compare with expected fees (price efficiency).

price_ratio = sum(fees paid) / sum(expected fees), over the club's assessed
purchases (expected fee reliability not Insufficient). < 1: paid less than
comparable deals commanded; > 1: paid premiums.

Uncertainty: 80% bootstrap interval from resampling the club's transfers
(2,000 draws). This captures how much the ratio depends on a few deals; it
does not add each transfer's own model uncertainty, so it is a lower bound on
the true uncertainty (stated in the app). Ranked clubs must have played in a covered
domestic league (where the model's comparisons are meaningful; this excludes e.g.
reserve teams whose "purchases" are moves within their own group) and need >= MIN_PURCHASES assessed
purchases to be ranked.

Outcome column (NOT used by any model): median change in market value 12
months after signing, so price efficiency and what happened next are shown
side by side but never mixed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_PURCHASES = 8
BOOTSTRAP = 2000
OUTCOME_TOLERANCE_DAYS = 90
NOTABLE_PREMIUM = {"Notable transfer premium", "Unusual transfer premium"}
NOTABLE_DISCOUNT = {"Notable fee discount", "Unusually low fee"}


def mv_after(fees: pd.DataFrame, valuations: pd.DataFrame, days: int = 365) -> pd.Series:
    """Market value closest to (transfer date + days), within +/- OUTCOME_TOLERANCE_DAYS."""
    v = valuations.rename(columns={"date": "v_date"}).sort_values("v_date")
    left = fees[["transfer_id", "player_id", "date"]].assign(when=fees.date + pd.Timedelta(days=days))
    m = pd.merge_asof(left.sort_values("when"), v, left_on="when", right_on="v_date", by="player_id",
                      direction="nearest", tolerance=pd.Timedelta(days=OUTCOME_TOLERANCE_DAYS))  # fmt: skip
    return m.set_index("transfer_id").value_eur.reindex(fees.transfer_id).to_numpy()


def bootstrap_ratio(fee: np.ndarray, expected: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    idx = rng.integers(0, len(fee), size=(BOOTSTRAP, len(fee)))
    ratios = fee[idx].sum(axis=1) / expected[idx].sum(axis=1)
    return float(np.quantile(ratios, 0.10)), float(np.quantile(ratios, 0.90))


def build(
    fees: pd.DataFrame, valuations: pd.DataFrame, covered_club_ids: set[int] | None = None, seed: int = 0
) -> pd.DataFrame:
    f = fees[fees.reliability != "Insufficient"].copy()
    f["mv_12m_after"] = mv_after(f, valuations)
    f["mv_change_12m_log"] = np.log(f.mv_12m_after / f.mv_pit_eur)
    last = int(f.season.max())
    periods = {"all": (int(f.season.min()), last), "last3": (last - 2, last)}
    rng = np.random.default_rng(seed)
    rows = []
    in_coverage = (lambda cid: True) if covered_club_ids is None else (lambda cid: int(cid) in covered_club_ids)  # noqa: E731
    for period, (lo, hi) in periods.items():
        p = f[(f.season >= lo) & (f.season <= hi)]
        for club_id, g in p.groupby("to_club_id"):  # by id only: 74 clubs appear under 2+ spellings
            club_name = g.to_club_name.mode().iat[0]
            n = len(g)
            ratio = g.fee_eur.sum() / g.expected_fee_eur.sum()
            r_lo, r_hi = bootstrap_ratio(g.fee_eur.to_numpy(), g.expected_fee_eur.to_numpy(), rng) if n >= 2 else (
                np.nan, np.nan)  # fmt: skip
            rows.append(dict(
                club_id=int(club_id), club_name=club_name, period=period, season_from=lo, season_to=hi,
                n_assessed=n, ranked=n >= MIN_PURCHASES and in_coverage(club_id),
                total_fee_eur=float(g.fee_eur.sum()), total_expected_eur=float(g.expected_fee_eur.sum()),
                price_ratio=float(ratio), price_ratio_lo80=r_lo, price_ratio_hi80=r_hi,
                share_notable_premium=float(g.label.isin(NOTABLE_PREMIUM).mean()),
                share_notable_discount=float(g.label.isin(NOTABLE_DISCOUNT).mean()),
                outcome_n=int(g.mv_change_12m_log.notna().sum()),
                outcome_median_mv_change_12m=float(np.expm1(g.mv_change_12m_log.median()))
                if g.mv_change_12m_log.notna().any() else np.nan,
            ))  # fmt: skip
    return pd.DataFrame(rows)
