"""Per-prediction explanations: which feature groups pushed the estimate up or down.

Contributions are on the log scale relative to the model's average prediction:
    y_hat = base + sum(contributions)
* Ridge: exact, contribution = coefficient x (transformed value).
* Gradient boosting: SHAP values (TreeExplainer), which satisfy the same additivity.

Features are grouped into football-readable drivers, then converted to an
approximate percentage effect: exp(c) - 1 ("this driver raises the estimate by
~23% compared with an average profile").
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

DRIVER_GROUPS = {
    "Age": ["age", "age2"],
    "Playing time": ["minutes_share", "starts_share", "log_prev_minutes", "n_clubs"],
    "Team strength": ["team_ppg", "team_gd_pg"],
    "League": ["competition_id", "league_mv_level"],
    "Position": ["position_group"],
    "Goal threat": ["goals_p90_shrunk", "npxg_p90_shrunk", "shots_p90_shrunk", "prev_goals_p90", "prev_npxg_p90"],
    "Chance creation": ["assists_p90_shrunk", "xa_p90_shrunk", "key_passes_p90_shrunk", "prev_assists_p90",
                        "prev_xa_p90"],
    "Build-up involvement": ["xg_chain_p90_shrunk", "xg_buildup_p90_shrunk"],
}  # fmt: skip
_FEATURE_TO_GROUP = {f: g for g, fs in DRIVER_GROUPS.items() for f in fs}


def _source_feature(transformed_name: str) -> str:
    """'num__age' -> 'age'; 'missingindicator_prev_xa_p90' -> 'prev_xa_p90'; 'cat__competition_id_GB1' -> ..."""
    name = transformed_name.split("__", 1)[-1]
    name = name.removeprefix("missingindicator_")
    for cat in ("competition_id", "position_group", "to_lg", "from_lg", "window"):
        if name.startswith(cat):
            return cat
    return name


def contributions(
    model: Pipeline, X: pd.DataFrame, groups: dict[str, list[str]] | None = None
) -> tuple[pd.DataFrame, float]:
    """-> (rows x driver-group log contributions, base value)."""
    pre, est = model.named_steps["pre"], model.named_steps["model"]
    Xt = pre.transform(X)
    names = list(pre.get_feature_names_out())
    if hasattr(est, "coef_"):
        Xt = np.asarray(Xt, dtype=float)
        mean_t = Xt.mean(axis=0)  # centre so contributions are relative to the average row
        raw = (Xt - mean_t) * est.coef_
        base = float(est.intercept_ + mean_t @ est.coef_)
    else:
        import shap  # imported lazily: only needed for tree models

        explainer = shap.TreeExplainer(est)
        raw = explainer.shap_values(np.asarray(Xt, dtype=float))
        base = float(np.ravel(explainer.expected_value)[0])
    per_feature = pd.DataFrame(raw, columns=names, index=X.index)
    mapping = {f: g for g, fs in groups.items() for f in fs} if groups else _FEATURE_TO_GROUP
    grouped = per_feature.T.groupby(lambda n: mapping.get(_source_feature(n), "Other")).sum().T
    return grouped, base


def drivers_json(row: pd.Series, top: int = 6) -> str:
    """Top drivers by absolute effect, as JSON for the app."""
    s = row.dropna()
    s = s.reindex(s.abs().sort_values(ascending=False).index)[:top]
    return json.dumps([{"driver": k, "log": round(float(v), 4), "pct": round(float(np.expm1(v)) * 100, 1)}
                       for k, v in s.items()])  # fmt: skip
