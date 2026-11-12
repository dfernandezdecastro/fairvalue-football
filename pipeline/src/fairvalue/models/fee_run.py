"""Train, evaluate and publish Expected Fee, then the club audit and Hidden Gems backtest.

`fairvalue train-fee` (needs `fairvalue train-piv` first).
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from fairvalue import __version__
from fairvalue.config import DATA_DIR
from fairvalue.io import read_table, write_table
from fairvalue.models import club_audit, explain, gems_backtest, training, uncertainty
from fairvalue.models import expected_fee as ef

GBM_MIN_IMPROVEMENT = 0.05
CAL = ["season", "mv_band", "buyer_big5"]


def calibrated(df: pd.DataFrame, results: list[training.FoldResult]) -> pd.DataFrame:
    preds = training.predictions_frame(results)
    rows = df.loc[preds.index, [*CAL, "y"]].assign(y_hat=preds.y_hat)
    store, out = {}, []
    for fr in results:
        s = fr.season
        pool = [store[k] for k in range(s - uncertainty.CALIBRATION_SEASONS, s) if k in store]
        if s - 1 not in store and len(fr.inner_residuals):
            pool.append(df.loc[fr.inner_residuals.index, CAL].assign(r=fr.inner_residuals))
        table = uncertainty.calibrate(pd.concat(pool), ef.FEE_HIERARCHY) if pool else {}
        cur = rows[rows.season == s]
        out.append(uncertainty.apply_intervals(cur, table, ef.FEE_HIERARCHY))
        store[s] = cur.loc[cur.y.notna(), CAL].assign(r=cur.y - cur.y_hat)
    return pd.concat(out)


def coverage(cal: pd.DataFrame) -> dict:
    c = cal[cal["80_lo"].notna()]
    in80 = (c.y >= c["80_lo"]) & (c.y <= c["80_hi"])
    in95 = (c.y >= c["95_lo"]) & (c.y <= c["95_hi"])
    by = c.assign(in80=in80).groupby("mv_band").in80.agg(["mean", "size"])
    return {
        "n": int(len(c)),
        "coverage80": round(float(in80.mean()), 4),
        "coverage95": round(float(in95.mean()), 4),
        "median_width80_ratio": round(float(np.median(np.exp(c["80_hi"] - c["80_lo"]))), 3),
        "by_mv_band": {k: {"coverage80": round(float(v["mean"]), 4), "n": int(v["size"])} for k, v in by.iterrows()},
    }


def fee_metrics(df: pd.DataFrame, y_hat: pd.Series) -> dict:
    """Metrics on the premium scale; MAE and % errors equal those on log fee (market value cancels)."""
    m = training.metrics(df.y, y_hat)
    log_fee, pred_fee = np.log(df.fee_eur), df.log_mv + y_hat
    m["r2_log_fee"] = round(1 - float(((log_fee - pred_fee) ** 2).sum() / ((log_fee - log_fee.mean()) ** 2).sum()), 4)
    return m


def evaluate(df: pd.DataFrame, log=print) -> dict:
    out = {"kinds": {}}
    for kind in ("ridge", "gbm"):
        t0 = time.time()
        res = training.walk_forward(df, kind, ef.NUMERIC, ef.CATEGORICAL)
        cal = calibrated(df, res)
        ev = df.loc[cal.index]
        out["kinds"][kind] = {
            "results": res,
            "calibrated": cal,
            "metrics": fee_metrics(ev, cal.y_hat),
            "by_season": {int(s): fee_metrics(g, cal.y_hat.loc[g.index]) for s, g in ev.groupby("season")},
            "coverage": coverage(cal),
            "params": {str(r.season): r.params for r in res},
        }
        log(f"  fee/{kind}: {out['kinds'][kind]['metrics']} cov80={out['kinds'][kind]['coverage']['coverage80']} "
            f"({time.time() - t0:.0f}s)")  # fmt: skip
    ev = df.loc[out["kinds"]["ridge"]["calibrated"].index]
    out["baselines"] = {
        "fee = market value": fee_metrics(ev, pd.Series(0.0, index=ev.index)),
        "fee = market value x recent market premium": fee_metrics(ev, ev.market_premium_level.fillna(0.0)),
    }
    r, g = out["kinds"]["ridge"], out["kinds"]["gbm"]
    better = g["metrics"]["mae_log"] <= (1 - GBM_MIN_IMPROVEMENT) * r["metrics"]["mae_log"]
    calib_ok = abs(g["coverage"]["coverage80"] - 0.8) <= abs(r["coverage"]["coverage80"] - 0.8) + 0.01
    out["chosen"] = "gbm" if (better and calib_ok) else "ridge"
    out["selection_reason"] = (
        f"gbm MAE {g['metrics']['mae_log']} vs ridge {r['metrics']['mae_log']} "
        f"({'>=' if better else '<'} {GBM_MIN_IMPROVEMENT:.0%} better); coverage80 gbm "
        f"{g['coverage']['coverage80']} vs ridge {r['coverage']['coverage80']}"
    )
    return out


def publish(df: pd.DataFrame, ev: dict) -> pd.DataFrame:
    kind = ev["chosen"]
    ch = ev["kinds"][kind]
    cal = ch["calibrated"]
    drivers = []
    for fr in ch["results"]:
        idx = fr.predictions.index
        contrib, _ = explain.contributions(fr.model, df.loc[idx, ef.NUMERIC + ef.CATEGORICAL], ef.DRIVER_GROUPS)
        drivers.append(contrib.apply(explain.drivers_json, axis=1).rename("drivers"))
    rows = df.loc[cal.index].join(cal[["y_hat", "80_lo", "80_hi", "95_lo", "95_hi", "calibration_group"]])
    rows = rows.join(pd.concat(drivers))
    rel = [
        ef.reliability(pd.notna(lo), pf, m, a)
        for lo, pf, m, a in zip(rows["80_lo"], rows.piv_full, rows.tm365_minutes, rows.mv_pit_age_days, strict=True)
    ]
    rows["reliability"] = [t for t, _ in rel]
    rows["reliability_reason"] = [r for _, r in rel]
    ok = rows.reliability != "Insufficient"
    lm = rows.log_mv
    for col, src in [("expected_fee_eur", "y_hat"), ("lo80_eur", "80_lo"), ("hi80_eur", "80_hi"),
                     ("lo95_eur", "95_lo"), ("hi95_eur", "95_hi")]:  # fmt: skip
        rows[col] = np.where(ok, np.exp(lm + rows[src]), np.nan)
    rows["premium_eur"] = np.where(ok, rows.fee_eur - rows.expected_fee_eur, np.nan)
    rows["premium_pct"] = np.where(ok, rows.fee_eur / rows.expected_fee_eur - 1, np.nan)
    rows["label"] = [
        ef.fee_label(y, a, b, c, d) if k else None
        for y, a, b, c, d, k in zip(rows.y, rows["80_lo"], rows["80_hi"], rows["95_lo"], rows["95_hi"], ok, strict=True)
    ]
    rows["drivers"] = np.where(ok, rows.drivers, None)
    rows["model_kind"] = kind
    return rows


def run(log=print) -> dict:
    t0 = time.time()
    log("building expected-fee dataset (point-in-time)...")
    df = ef.build(read_table("features", "transfer_features"), read_table("outputs", "piv_predictions"),
                  read_table("staging", "transfers"))  # fmt: skip
    log(f"  {len(df):,} paid transfers with a market value <= 365 days old")
    ev = evaluate(df, log)
    fees = publish(df, ev)
    n = write_table(fees, "outputs", "fee_predictions")

    log("club audit (bootstrap intervals)...")
    valuations = read_table("staging", "valuations")
    audit = club_audit.build(fees, valuations)
    write_table(audit, "outputs", "club_audit")

    log("hidden gems backtest...")
    backtest = gems_backtest.run(
        read_table("outputs", "piv_predictions"), valuations, read_table("features", "player_season_features")
    )

    meta = {
        "model": "expected_fee",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pipeline_version": __version__,
        "rows": int(len(df)),
        "chosen": ev["chosen"],
        "selection_reason": ev["selection_reason"],
        "baselines": ev["baselines"],
        **{k: {kk: vv for kk, vv in v.items() if kk not in ("results", "calibrated")} for k, v in ev["kinds"].items()},
        "published": n,
        "club_audit_rows": int(len(audit)),
        "gems_backtest": backtest,
        "seconds": round(time.time() - t0),
    }
    (DATA_DIR / "outputs" / "fee_run.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    from fairvalue.models.report_fee import write_reports

    for path in write_reports():
        log(f"report: {path}")
    log(f"done in {meta['seconds']}s")
    return meta
