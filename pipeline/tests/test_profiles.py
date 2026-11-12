import numpy as np
import pandas as pd
import pytest

from fairvalue.profiles import build as prof


def test_estimate_prior_no_true_differences_means_max_shrinkage():
    e = np.full(50, 30.0)
    count = np.full(50, 15.0)  # every player has exactly the same rate
    mu, k = prof.estimate_prior(count, e)
    assert mu == pytest.approx(0.5) and k == prof.K_MAX


def test_estimate_prior_real_differences_mean_less_shrinkage():
    rng = np.random.default_rng(0)
    e = np.full(400, 30.0)
    true = rng.gamma(shape=2.0, scale=0.25, size=400)  # mean 0.5, sd ~0.35
    count = rng.poisson(true * e)
    mu, k = prof.estimate_prior(count.astype(float), e)
    assert mu == pytest.approx(0.5, abs=0.05)
    assert k == pytest.approx(0.5 / 0.125, rel=0.35)  # theory: k = mean / between-variance = 4


def _season(n=30, seed=1):
    rng = np.random.default_rng(seed)
    minutes = rng.integers(900, 3400, n)
    return pd.DataFrame({
        "player_id": np.arange(n), "season": 2023, "competition_id": "GB1", "position_group": "ST",
        "data_tier": "full", "minutes": minutes, "us_minutes": minutes.astype(float),
        "goals": rng.poisson(minutes / 90 * 0.4), "assists": rng.poisson(minutes / 90 * 0.1),
        "npxg": minutes / 90 * rng.uniform(0.2, 0.6, n), "xa": minutes / 90 * rng.uniform(0.05, 0.2, n),
        "shots": rng.poisson(minutes / 90 * 3.0), "key_passes": rng.poisson(minutes / 90 * 1.2),
        "xg_chain": minutes / 90 * 0.5, "xg_buildup": minutes / 90 * 0.1,
        "minutes_share": minutes / 3420, "starts_share": minutes / 3420,
    })  # fmt: skip


def test_shrinkage_pulls_low_minute_players_more():
    ps = _season()
    hot = dict(player_id=100, minutes=950, us_minutes=950.0, goals=15, shots=40, key_passes=10)
    ps = pd.concat([ps, pd.DataFrame([{**ps.iloc[0].to_dict(), **hot}]),
                    pd.DataFrame([{**ps.iloc[0].to_dict(), **hot, "player_id": 101, "minutes": 3200,
                                   "us_minutes": 3200.0, "goals": 50}])], ignore_index=True)  # fmt: skip
    p, _, _ = prof.build(ps)
    p = p.set_index("player_id")
    for pid in (100, 101):  # both score ~1.4 per 90
        assert p.loc[pid, "goals_p90_shrunk"] < p.loc[pid, "goals_p90"]
    pull = lambda pid: p.loc[pid, "goals_p90"] - p.loc[pid, "goals_p90_shrunk"]  # noqa: E731
    assert pull(100) > pull(101)  # fewer minutes -> stronger pull to the mean


def test_percentiles_only_for_eligible_and_within_peers():
    ps = pd.concat([_season(), _season(seed=2).assign(position_group="CB", player_id=lambda d: d.player_id + 50)])
    ps.loc[0, "minutes"] = 300  # below the 900-minute threshold
    p, _, _ = prof.build(ps)
    assert np.isnan(p.loc[0, "goals_p90_pct"])
    st = p[(p.position_group == "ST") & p.eligible]
    assert st.peer_n.iloc[0] == len(st) == 29
    assert st.goals_p90_pct.max() == 100


def test_similarity_self_excluded_and_identical_profiles_match():
    ps = _season(n=10)
    twin = ps.iloc[[3]].assign(player_id=99)
    p, sim, _ = prof.build(pd.concat([ps, twin], ignore_index=True))
    top = sim[(sim.player_id == 3) & (sim["rank"] == 1)].iloc[0]
    assert top.neighbour_id == 99 and top.similarity == pytest.approx(1.0)
    assert not ((sim.player_id == sim.neighbour_id).any())
    assert sim.groupby("player_id").size().max() == 10  # n-1 neighbours when fewer than 20 peers
