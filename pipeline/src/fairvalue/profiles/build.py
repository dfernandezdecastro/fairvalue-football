"""Layer 1: performance profiles - facts, not model outputs.

Per player-season:
1. per-90 rates (Transfermarkt goals/assists; Understat xG family for full tier)
2. empirical-Bayes SHRINKAGE of each rate toward the peer-group average
3. PERCENTILES within peers: same season, position group and peer scope
   (all big-five leagues together, or the player's own league elsewhere)
4. SIMILAR PLAYERS by cosine similarity of standardised shrunk profiles

Shrinkage, in one paragraph: a rate measured over few minutes is noisy. We treat
each player's true rate as drawn from the peer distribution and the observed
count as Poisson noise around it. The posterior mean is
    shrunk = (count + k * prior_rate) / (games90 + k)
i.e. the player's own data plus k "virtual 90s" at the peer average. k is
estimated per metric and peer group by the method of moments: the more players
genuinely differ (between-player variance), the smaller k.

The Poisson noise assumption only holds for true COUNTS (goals, assists, shots,
key passes). xG-type metrics are sums of probabilities and far less noisy than
a Poisson count with the same mean; applying the formula to them treats almost
all variation as noise and over-shrinks (Haaland 2023/24: 0.89 -> 0.61 npxG/90).
Their noise is driven by how many chances occur, so each borrows k from its
underlying count: npxG <- shots; xA, xGChain, xGBuildup <- key passes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fairvalue.config import BIG5, MIN_MINUTES_FOR_ESTIMATE
from fairvalue.ingest.schemas import BASIC_RATE_METRICS, US_METRICS

K_MIN, K_MAX = 1.0, 40.0  # prior strength bounds, in 90-minute units (90 to 3,600 minutes)
TOP_K_SIMILAR = 20
COUNT_METRICS = ["goals", "assists", "shots", "key_passes"]  # Poisson-like: k estimated directly
K_SOURCE = {"npxg": "shots", "xa": "key_passes", "xg_chain": "key_passes", "xg_buildup": "key_passes"}


def per90(ps: pd.DataFrame) -> pd.DataFrame:
    p = ps.reset_index(drop=True)  # later steps align on the index; it must be unique
    tm90 = p.minutes / 90
    for m in BASIC_RATE_METRICS:
        p[f"{m}_p90"] = p[m] / tm90.where(tm90 > 0)
    us90 = p.us_minutes / 90
    for m in US_METRICS:
        p[f"{m}_p90"] = p[m] / us90.where(us90 > 0)
    p["peer_scope"] = np.where(p.competition_id.isin(BIG5), "big5", p.competition_id)
    p["eligible"] = (p.minutes >= MIN_MINUTES_FOR_ESTIMATE) & (p.position_group != "UNK")
    return p


def estimate_prior(count: np.ndarray, exposure: np.ndarray) -> tuple[float, float]:
    """(prior_rate per 90, k in 90s) by method of moments under a Gamma-Poisson model."""
    tot_e = exposure.sum()
    if tot_e <= 0 or len(count) < 5:
        return float("nan"), K_MAX
    mu = count.sum() / tot_e
    rates = count / exposure
    between = ((exposure * (rates - mu) ** 2).sum() - len(count) * mu) / tot_e
    k = mu / between if between > 0 else K_MAX
    return float(mu), float(np.clip(k, K_MIN, K_MAX))


def shrink(p: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = p.copy()
    priors = []
    exposures = {m: p.minutes / 90 for m in BASIC_RATE_METRICS} | {m: p.us_minutes / 90 for m in US_METRICS}
    order = COUNT_METRICS + [m for m in exposures if m not in COUNT_METRICS]  # counts first
    for (season, group, scope), idx in p.groupby(["season", "position_group", "peer_scope"]).groups.items():
        g = p.loc[idx]
        ks: dict[str, float] = {}
        for m in order:
            e = exposures[m].loc[idx]
            elig = g.eligible & g[m].notna() & (e > 0)
            mu, k = estimate_prior(g.loc[elig, m].to_numpy(float), e[elig].to_numpy(float))
            if m in K_SOURCE:
                k = ks[K_SOURCE[m]]
            ks[m] = k
            priors.append(dict(season=season, position_group=group, peer_scope=scope, metric=f"{m}_p90",
                               prior_rate=mu, prior_minutes=k * 90, k_source=K_SOURCE.get(m, m)))  # fmt: skip
            p.loc[idx, f"{m}_p90_shrunk"] = (g[m] + k * mu) / (e + k)
    return p, pd.DataFrame(priors)


def percentiles(p: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    p = p.copy()
    keys = ["season", "position_group", "peer_scope"]
    elig = p[p.eligible]
    p["peer_n"] = p.groupby(keys).eligible.transform("sum").astype(int)
    for m in metrics:
        src = f"{m}_shrunk" if f"{m}_shrunk" in p else m
        pct = elig.groupby(keys)[src].rank(pct=True, method="average") * 100
        p[f"{m}_pct"] = pct.reindex(p.index)
    return p


def similar_players(p: pd.DataFrame, top_k: int = TOP_K_SIMILAR) -> pd.DataFrame:
    full_cols = [f"{m}_p90_shrunk" for m in BASIC_RATE_METRICS + US_METRICS] + [
        "minutes_share",
        "starts_share",
    ]
    basic_cols = [f"{m}_p90_shrunk" for m in BASIC_RATE_METRICS] + ["minutes_share", "starts_share"]
    out = []
    e = p[p.eligible & (p.position_group != "GK")]
    for (_, _, _, tier), g in e.groupby(["season", "position_group", "peer_scope", "data_tier"]):
        cols = full_cols if tier == "full" else basic_cols
        g = g.dropna(subset=cols)
        if len(g) < 3:
            continue
        x = g[cols].to_numpy(float)
        sd = x.std(axis=0)
        z = (x - x.mean(axis=0)) / np.where(sd > 0, sd, 1)
        norm = np.linalg.norm(z, axis=1, keepdims=True)
        u = z / np.where(norm > 0, norm, 1)
        sim = u @ u.T
        np.fill_diagonal(sim, -np.inf)
        k = min(top_k, len(g) - 1)
        order = np.argsort(-sim, axis=1)[:, :k]
        ids, comps, season = g.player_id.to_numpy(), g.competition_id.to_numpy(), g.season.iat[0]
        for i in range(len(g)):
            for r, j in enumerate(order[i], start=1):
                out.append((ids[i], season, comps[i], ids[j], comps[j], float(sim[i, j]), r))
    return pd.DataFrame(out, columns=["player_id", "season", "competition_id", "neighbour_id",
                                      "neighbour_competition_id", "similarity", "rank"])  # fmt: skip


def build(ps: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """-> (profiles, similar_players, shrinkage_priors)"""
    p = per90(ps)
    p, priors = shrink(p)
    metrics = [f"{m}_p90" for m in BASIC_RATE_METRICS + US_METRICS] + ["minutes_share", "starts_share"]
    p = percentiles(p, metrics)
    return p, similar_players(p), priors
