"""Uncertainty (rule R3): conformal intervals, reliability tiers and gap labels.

Group-wise split-conformal intervals
------------------------------------
For test season s, collect the model's OUT-OF-SAMPLE residuals (actual - predicted,
log scale) from the previous CALIBRATION_SEASONS seasons. Within the row's
calibration group (league x line, falling back to
league, minutes band x line, minutes band, all), take empirical quantiles of the signed
residuals and add them to the prediction:

    80% interval = [y_hat + q(0.10), y_hat + q(0.90)]
    95% interval = [y_hat + q(0.025), y_hat + q(0.975)]

Signed (not absolute) residuals keep intervals asymmetric when errors are skewed
and absorb any systematic bias. If a group has fewer than MIN_CALIBRATION
residuals we fall back to the minutes band, then to all rows. Groups are
calibrated separately ("Mondrian" conformal) so that harder cases, e.g. fewer
minutes, honestly get wider bands.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CALIBRATION_SEASONS = 3
MIN_CALIBRATION = 100
LEVELS = {"80": (0.10, 0.90), "95": (0.025, 0.975)}
# Most specific first. League-level groups give each league its own width (value dispersion differs
# a lot: Scotland's Celtic/Rangers gap vs a compact Premier League); fall back when history is thin.
GROUP_HIERARCHY = [["competition_id", "line"], ["competition_id"], ["minutes_band", "line"], ["minutes_band"], []]


def _conformal_quantile(r: np.ndarray, q: float) -> float:
    """Finite-sample-corrected empirical quantile (split conformal)."""
    n = len(r)
    level = np.clip(np.ceil((n + 1) * q) / n if q > 0.5 else np.floor((n + 1) * q) / n, 0, 1)
    return float(np.quantile(r, level, method="higher" if q > 0.5 else "lower"))


def calibrate(residuals: pd.DataFrame, hierarchy: list[list[str]] | None = None) -> dict[tuple, dict[str, float]]:
    """residuals: columns minutes_band, line, r -> {(level_keys...): {q: value}}."""
    table: dict[tuple, dict[str, float]] = {}
    for keys in hierarchy or GROUP_HIERARCHY:
        if not set(keys) <= set(residuals.columns):
            continue
        groups = residuals.groupby(keys) if keys else [((), residuals)]
        for k, g in groups:
            if len(g) < MIN_CALIBRATION:
                continue
            k = k if isinstance(k, tuple) else (k,)
            qs = {f"{lvl}_{side}": _conformal_quantile(g.r.to_numpy(), q)
                  for lvl, (lo, hi) in LEVELS.items() for side, q in (("lo", lo), ("hi", hi))}  # fmt: skip
            table[(tuple(keys), k)] = qs | {"n": len(g)}
    return table


def apply_intervals(rows: pd.DataFrame, table: dict, hierarchy: list[list[str]] | None = None) -> pd.DataFrame:
    """Adds q columns + calibration_group to rows (needs minutes_band, line, y_hat)."""
    out = rows.copy()
    for col in ["80_lo", "80_hi", "95_lo", "95_hi"]:
        out[col] = np.nan
    out["calibration_group"] = None
    for idx, row in out.iterrows():
        for keys in hierarchy or GROUP_HIERARCHY:
            if not set(keys) <= set(row.index):
                continue
            k = tuple(row[c] for c in keys)
            hit = table.get((tuple(keys), k))
            if hit:
                for col in ["80_lo", "80_hi", "95_lo", "95_hi"]:
                    out.at[idx, col] = row.y_hat + hit[col]
                out.at[idx, "calibration_group"] = "/".join(map(str, k)) or "all"
                break
    return out


# ------------------------------------------------------------------ peer-relative gaps (decision D11)
MIN_PEER_ROWS = 30


def peer_shift(rows: pd.DataFrame) -> pd.Series:
    """Median residual r of each league-season (rows need season, competition_id, r).

    Used to centre valuation gaps on same-league peers in the same summer, so a
    league-wide market move (e.g. LaLiga 2024/25) isn't mistaken for individual
    undervaluation. League-seasons with fewer than MIN_PEER_ROWS valued players
    get no shift (0) rather than a noisy one.
    """
    g = rows.groupby(["season", "competition_id"]).r
    med, n = g.transform("median"), g.transform("count")
    return med.where(n >= MIN_PEER_ROWS, 0.0).fillna(0.0)


# ------------------------------------------------------------------ reliability tiers (spec 2.3)
TIERS = ["Insufficient", "Low", "Moderate", "High"]
WEAK_METRIC_GROUPS = {"CB", "FB"}


def reliability(data_tier: str, minutes: int, position_group: str, calibrated: bool) -> tuple[str, str]:
    """Deterministic, explainable tier + reason (shown to users)."""
    if position_group in {"GK", "UNK"}:
        return "Insufficient", "No performance model for this position"
    if minutes < 900:
        return "Insufficient", "Fewer than 900 league minutes"
    if not calibrated:
        return "Insufficient", "Not enough past predictions to calibrate an uncertainty range"
    if data_tier == "full":
        tier, reason = ("High", "xG-level data, 1,800+ minutes") if minutes >= 1800 else (
            "Moderate", "xG-level data, 900-1,799 minutes")  # fmt: skip
    else:
        tier, reason = ("Moderate", "Basic data only, 1,800+ minutes") if minutes >= 1800 else (
            "Low", "Basic data only, 900-1,799 minutes")  # fmt: skip
    if position_group in WEAK_METRIC_GROUPS:
        tier = TIERS[TIERS.index(tier) - 1]
        reason += "; defensive contribution not measured"
    return tier, reason


# ------------------------------------------------------------------ gap labels (spec 2.2, rule R1)
def gap_label(mv_log: float, lo80: float, hi80: float, lo95: float, hi95: float) -> str | None:
    """Label a market value against the PIV range. Never from the gap's sign alone."""
    if any(np.isnan(x) for x in (mv_log, lo80, hi80, lo95, hi95)):
        return None
    if mv_log < lo95:
        return "Strong signal of potential undervaluation"
    if mv_log < lo80:
        return "Potential undervaluation"
    if mv_log > hi95:
        return "Unusual market premium"
    if mv_log > hi80:
        return "Market premium"
    return "Within expected range"
