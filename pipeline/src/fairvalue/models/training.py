"""Walk-forward ("vintage") training and evaluation.

For every test season s:
  1. inner selection: fit each hyperparameter setting on seasons < s-1 and score
     it on season s-1 (never on s)
  2. refit the chosen setting on all seasons < s
  3. predict season s -> these out-of-sample predictions are what the app shows

Nothing trained on season s ever scores season s; ``walk_forward`` asserts it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from fairvalue.asof import LeakageError

MIN_TRAIN_SEASONS = 3


def make_ridge(numeric: list[str], categorical: list[str], alpha: float) -> Pipeline:
    pre = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20, sparse_output=False), categorical),
    ])  # fmt: skip
    return Pipeline([("pre", pre), ("model", Ridge(alpha=alpha))])


def make_gbm(numeric: list[str], categorical: list[str], **params) -> Pipeline:
    pre = ColumnTransformer([
        ("num", "passthrough", numeric),  # trees handle missing values natively
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20, sparse_output=False), categorical),
    ])  # fmt: skip
    model = HistGradientBoostingRegressor(random_state=0, **params)
    return Pipeline([("pre", pre), ("model", model)])


CANDIDATES: dict[str, list[dict]] = {
    "ridge": [{"alpha": a} for a in (1.0, 10.0, 100.0)],
    "gbm": [
        dict(learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0),
        dict(learning_rate=0.05, max_iter=500, max_leaf_nodes=31, min_samples_leaf=40, l2_regularization=1.0),
        dict(learning_rate=0.03, max_iter=800, max_leaf_nodes=31, min_samples_leaf=80, l2_regularization=3.0),
    ],
}  # fmt: skip
FACTORIES: dict[str, Callable[..., Pipeline]] = {"ridge": make_ridge, "gbm": make_gbm}


@dataclass
class FoldResult:
    season: int
    params: dict
    predictions: pd.DataFrame  # index-aligned rows of the test season with y_hat
    inner_residuals: pd.Series  # residuals on season s-1 from the inner model (calibration fallback)
    model: Pipeline = field(repr=False)
    offset: float = 0.0  # same-market re-centring shift subtracted from raw predictions


def _fit(kind: str, numeric, categorical, params, frame: pd.DataFrame) -> Pipeline:
    m = FACTORIES[kind](numeric, categorical, **params)
    m.fit(frame[numeric + categorical], frame.y)
    return m


def recentre(pred: np.ndarray, anchor: np.ndarray | None) -> tuple[np.ndarray, float]:
    """Same-market re-centring: shift so the median prediction over anchor rows is 0.

    The target is defined relative to that summer's median big-five value, so the
    median target over those rows is 0 by construction. Pinning the median
    PREDICTION there removes drift in the market's shape (it became more unequal
    over time) without looking at any target of the season being predicted.
    """
    if anchor is None or not anchor.any():
        return pred, 0.0
    offset = float(np.median(pred[anchor]))
    return pred - offset, offset


def walk_forward(
    df: pd.DataFrame,
    kind: str,
    numeric: list[str],
    categorical: list[str],
    anchor: pd.Series | None = None,
) -> list[FoldResult]:
    """Out-of-sample predictions for every season with >= MIN_TRAIN_SEASONS earlier seasons.

    ``anchor``: optional boolean Series (aligned to df) marking rows used for
    same-market re-centring (see ``recentre``); applied identically during
    inner hyperparameter selection.
    """
    labelled = df[df.y.notna()]
    seasons = sorted(labelled.season.unique())
    anc = (lambda rows: anchor.loc[rows.index].to_numpy()) if anchor is not None else (lambda rows: None)  # noqa: E731
    results = []
    for s in seasons[MIN_TRAIN_SEASONS:] + ([max(df.season)] if max(df.season) > seasons[-1] else []):
        train = labelled[labelled.season < s]
        inner_train, inner_val = train[train.season < s - 1], train[train.season == s - 1]
        best, best_mae, best_inner = None, np.inf, None
        for params in CANDIDATES[kind]:
            m = _fit(kind, numeric, categorical, params, inner_train)
            pred, _ = recentre(m.predict(inner_val[numeric + categorical]), anc(inner_val))
            mae = float(np.mean(np.abs(inner_val.y - pred)))
            if mae < best_mae:
                best, best_mae, best_inner = (
                    params,
                    mae,
                    pd.Series(inner_val.y.values - pred, index=inner_val.index),
                )
        model = _fit(kind, numeric, categorical, best, train)
        if (train.season >= s).any():
            raise LeakageError(f"fold {s}: training data includes season >= {s}")
        test = df[df.season == s]
        pred, offset = recentre(model.predict(test[numeric + categorical]), anc(test))
        preds = test[["season"]].assign(y_hat=pred)
        results.append(FoldResult(int(s), best, preds, best_inner, model, offset))
    return results


def predictions_frame(results: list[FoldResult]) -> pd.DataFrame:
    return pd.concat([r.predictions for r in results])


def metrics(y: pd.Series, y_hat: pd.Series) -> dict:
    ok = y.notna()
    y, y_hat = y[ok], y_hat[ok]
    err = y - y_hat
    ape = np.abs(np.exp(y_hat - y) - 1)  # |pred - actual| / actual, in euros (index cancels)
    ss_res, ss_tot = float((err**2).sum()), float(((y - y.mean()) ** 2).sum())
    return {
        "n": int(len(y)),
        "mae_log": round(float(np.abs(err).mean()), 4),
        "r2_log": round(1 - ss_res / ss_tot, 4) if ss_tot > 0 else float("nan"),
        "median_ape": round(float(np.median(ape)), 4),
        "within_25pct": round(float((ape <= 0.25).mean()), 4),
        "within_50pct": round(float((ape <= 0.5).mean()), 4),
        "bias_log": round(float(err.mean()), 4),
    }


def baseline_predictions(df: pd.DataFrame) -> pd.Series:
    """Naive walk-forward baseline: median target by position group x age band, from earlier seasons."""
    band = pd.cut(df.age, [0, 21, 24, 27, 30, 50]).astype(str)
    key = df.position_group + "|" + band
    out = pd.Series(np.nan, index=df.index)
    labelled = df.y.notna()
    for s in sorted(df.season.unique()):
        past = labelled & (df.season < s)
        if df.loc[past, "season"].nunique() < MIN_TRAIN_SEASONS:
            continue
        med = df.loc[past].groupby(key[past]).y.median()
        cur = df.season == s
        out[cur] = key[cur].map(med).fillna(df.loc[past, "y"].median()).values
    return out
