"""Train, evaluate and publish the Performance-Implied Value model: `fairvalue train-piv`.

Two tiers (full = xG-level big five; basic = Transfermarkt data, all leagues),
two candidate model kinds (Ridge, gradient boosting), walk-forward vintages.

Selection rule (spec 7.2): gradient boosting is used only if it beats Ridge on
pooled walk-forward MAE (log) by >= 5% AND its 80% interval coverage is no
further from 80% than Ridge's. Otherwise Ridge ships.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from fairvalue import __version__
from fairvalue.config import BIG5, DATA_DIR
from fairvalue.io import read_table, write_table
from fairvalue.models import dataset, explain, training, uncertainty

GBM_MIN_IMPROVEMENT = 0.05


CAL_COLS = ["season", "competition_id", "minutes_band", "line"]


def _calibrated(frame: pd.DataFrame, results: list[training.FoldResult], peer: bool = False) -> pd.DataFrame:
    """Vintage predictions + conformal intervals calibrated only on earlier seasons.

    peer=False: intervals around the model prediction (whole-market view).
    peer=True:  intervals around the prediction shifted by the league-season's
                median residual (same-league peers, same summer; decision D11).
                Calibration residuals from earlier seasons are peer-centred the
                same way, so the interval width matches what it's applied to.
    The returned 'center' column is the point the interval is built around.
    """
    preds = training.predictions_frame(results)
    rows = frame.loc[preds.index, [*CAL_COLS, "y"]].assign(y_hat=preds.y_hat)
    rows["shift"] = uncertainty.peer_shift(rows.assign(r=rows.y - rows.y_hat)) if peer else 0.0
    rows["center"] = rows.y_hat + rows["shift"]
    store = {}  # season -> out-of-sample residuals around the centre
    out = []
    for fr in results:
        s = fr.season
        pool = [store[k] for k in range(s - uncertainty.CALIBRATION_SEASONS, s) if k in store]
        if s - 1 not in store and len(fr.inner_residuals):
            inner = frame.loc[fr.inner_residuals.index, CAL_COLS].assign(r=fr.inner_residuals)
            if peer:
                inner["r"] = inner.r - uncertainty.peer_shift(inner)
            pool.append(inner)
        table = uncertainty.calibrate(pd.concat(pool)) if pool else {}
        cur = rows[rows.season == s]
        res = uncertainty.apply_intervals(cur.assign(y_hat=cur.center), table)
        res["y_hat"] = cur.y_hat
        out.append(res)
        store[s] = cur.loc[cur.y.notna(), CAL_COLS].assign(r=cur.y - cur.center)
    return pd.concat(out)


def _coverage(cal: pd.DataFrame) -> dict:
    ok = cal.y.notna() & cal["80_lo"].notna()
    c = cal[ok]
    inside80 = (c.y >= c["80_lo"]) & (c.y <= c["80_hi"])
    inside95 = (c.y >= c["95_lo"]) & (c.y <= c["95_hi"])
    by_group = c.assign(inside80=inside80).groupby(["minutes_band", "line"]).inside80.agg(["mean", "size"]).round(3)
    return {
        "n": int(ok.sum()),
        "coverage80": round(float(inside80.mean()), 4),
        "coverage95": round(float(inside95.mean()), 4),
        "median_width80_ratio": round(float(np.median(np.exp(c["80_hi"] - c["80_lo"]))), 3),
        "by_group": {
            f"{b}/{ln}": {"coverage80": float(r["mean"]), "n": int(r["size"])} for (b, ln), r in by_group.iterrows()
        },  # fmt: skip
    }


def evaluate_tier(frame: pd.DataFrame, tier: str, log=print) -> dict:
    spec = dataset.FEATURES[tier]
    num, cat = spec["numeric"], spec["categorical"]
    out = {"kinds": {}}
    for kind in ("ridge", "gbm"):
        t0 = time.time()
        anchor = frame.competition_id.isin(BIG5)  # median big-five target is 0 by construction
        results = training.walk_forward(frame, kind, num, cat, anchor=anchor)
        cal = _calibrated(frame, results)
        preds = cal.y_hat
        evaluated = frame.loc[preds.index]
        out["kinds"][kind] = {
            "results": results,
            "calibrated": cal,
            "metrics": training.metrics(evaluated.y, preds),
            "by_season": {int(s): training.metrics(g.y, preds.loc[g.index]) for s, g in evaluated.groupby("season")},
            "coverage": _coverage(cal),
            "params": {r.season: r.params for r in results},
            "recentre_offsets": {r.season: round(r.offset, 4) for r in results},
        }  # fmt: skip
        log(f"  {tier}/{kind}: {out['kinds'][kind]['metrics']} cov80={out['kinds'][kind]['coverage']['coverage80']}"
            f" ({time.time() - t0:.0f}s)")  # fmt: skip
    base = training.baseline_predictions(frame)
    ev = frame[base.notna() & frame.season.isin(out["kinds"]["ridge"]["calibrated"].season.unique())]
    out["baseline"] = training.metrics(ev.y, base.loc[ev.index])
    r, g = out["kinds"]["ridge"], out["kinds"]["gbm"]
    better = g["metrics"]["mae_log"] <= (1 - GBM_MIN_IMPROVEMENT) * r["metrics"]["mae_log"]
    calib_ok = abs(g["coverage"]["coverage80"] - 0.8) <= abs(r["coverage"]["coverage80"] - 0.8) + 0.01
    out["chosen"] = "gbm" if (better and calib_ok) else "ridge"
    out["peer_calibrated"] = _calibrated(frame, out["kinds"][out["chosen"]]["results"], peer=True)
    out["peer_coverage"] = _coverage(out["peer_calibrated"])
    log(f"  {tier}: peer-relative coverage80={out['peer_coverage']['coverage80']}")
    out["selection_reason"] = (
        f"gbm MAE {g['metrics']['mae_log']} vs ridge {r['metrics']['mae_log']} "
        f"({'>=' if better else '<'} {GBM_MIN_IMPROVEMENT:.0%} better); coverage80 gbm "
        f"{g['coverage']['coverage80']} vs ridge {r['coverage']['coverage80']}"
    )
    return out


def publish(frame: pd.DataFrame, tier: str, ev: dict) -> pd.DataFrame:
    kind = ev["chosen"]
    chosen = ev["kinds"][kind]
    cal = chosen["calibrated"]
    spec = dataset.FEATURES[tier]
    drivers = []
    for fr in chosen["results"]:
        idx = fr.predictions.index
        contrib, _ = explain.contributions(fr.model, frame.loc[idx, spec["numeric"] + spec["categorical"]])
        drivers.append(contrib.apply(explain.drivers_json, axis=1).rename("drivers"))
    drivers = pd.concat(drivers)

    peer = ev["peer_calibrated"]
    rows = frame.loc[cal.index].copy()
    rows = rows.join(cal[["y_hat", "80_lo", "80_hi", "95_lo", "95_hi", "calibration_group"]]).join(drivers)
    rows = rows.join(peer[["shift", "center", "80_lo", "80_hi", "95_lo", "95_hi"]].add_prefix("peer_"))
    rows["model_tier"], rows["model_kind"] = tier, kind
    rows["train_through"] = rows.season - 1
    data_tier = rows.data_tier if tier == "full" else pd.Series("basic", index=rows.index)
    rel = [
        uncertainty.reliability(dt, m, pg, pd.notna(lo))
        for dt, m, pg, lo in zip(data_tier, rows.minutes, rows.position_group, rows["80_lo"], strict=True)
    ]
    rows["reliability"] = [t for t, _ in rel]
    rows["reliability_reason"] = [r for _, r in rel]
    idx = np.log(rows.market_index_eur)
    ok = rows.reliability != "Insufficient"
    for col, src in [("estimate_eur", "y_hat"), ("lo80_eur", "80_lo"), ("hi80_eur", "80_hi"),
                     ("lo95_eur", "95_lo"), ("hi95_eur", "95_hi")]:  # fmt: skip
        rows[col] = np.where(ok, np.exp(rows[src] + idx), np.nan)  # rule R3: no estimate without a range
    # Peer-relative view (D11): same-league peers, same summer. Gap labels use this view.
    peer_ok = ok & rows.peer_80_lo.notna()
    for col, src in [("peer_estimate_eur", "peer_center"), ("peer_lo80_eur", "peer_80_lo"),
                     ("peer_hi80_eur", "peer_80_hi"), ("peer_lo95_eur", "peer_95_lo"),
                     ("peer_hi95_eur", "peer_95_hi")]:  # fmt: skip
        rows[col] = np.where(peer_ok, np.exp(rows[src] + idx), np.nan)
    rows["league_shift_log"] = rows.peer_shift
    rows["market_gap_log"] = np.where(ok, rows.y - rows.y_hat, np.nan)
    rows["gap_log"] = np.where(peer_ok, rows.y - rows.peer_center, np.nan)
    rows["gap_label"] = [
        uncertainty.gap_label(y, a, b, c, d) if k else None
        for y, a, b, c, d, k in zip(
            rows.y, rows.peer_80_lo, rows.peer_80_hi, rows.peer_95_lo, rows.peer_95_hi, peer_ok, strict=True
        )
    ]
    rows["drivers"] = np.where(ok, rows.drivers, None)
    return rows


def run(log=print) -> dict:
    t0 = time.time()
    log("loading features...")
    frame_all = dataset.build(
        read_table("features", "player_season_features"),
        read_table("features", "profiles"),
        read_table("staging", "valuations"),
    )
    published, summary = [], {}
    for tier in ("full", "basic"):
        frame = dataset.tier_frame(frame_all, tier)
        log(f"tier {tier}: {len(frame):,} player-seasons, seasons {frame.season.min()}-{frame.season.max()}")
        ev = evaluate_tier(frame, tier, log)
        published.append(publish(frame, tier, ev))
        summary[tier] = {
            "rows": int(len(frame)),
            "chosen": ev["chosen"],
            "selection_reason": ev["selection_reason"],
            "baseline": ev["baseline"],
            "peer_coverage": ev["peer_coverage"],
            **{k: {"metrics": v["metrics"], "by_season": v["by_season"], "coverage": v["coverage"],
                   "params": {str(s): p for s, p in v["params"].items()},
                   "recentre_offsets": {str(s): o for s, o in v["recentre_offsets"].items()}}
                for k, v in ev["kinds"].items()},
        }  # fmt: skip
    preds = pd.concat(published, ignore_index=True)
    n = write_table(preds, "outputs", "piv_predictions")
    run_meta = {
        "model": "piv",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pipeline_version": __version__,
        "market_index_eur": {int(k): float(v) for k, v in dataset.market_index(frame_all).items()},
        "tiers": summary,
        "rows_published": n,
        "seconds": round(time.time() - t0),
    }
    path = DATA_DIR / "outputs" / "piv_run.json"
    path.write_text(json.dumps(run_meta, indent=2, default=str), encoding="utf-8")
    from fairvalue.models.report import write_report

    log(f"model card: {write_report()}")
    log(f"done in {run_meta['seconds']}s, {n:,} rows -> {path.parent}")
    return run_meta
