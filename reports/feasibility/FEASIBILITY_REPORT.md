# FairValue Football: Data Feasibility Report

*12 November 2026. All numbers come from the scripts in `scripts/feasibility/` run on real data; nothing here is synthetic.*

## TL;DR

**Recommendation: CONDITIONAL GO.** Go for a re-scoped, non-commercial product built on a frozen snapshot. **No-go for the original framing.**

- There's enough real data for an honest ML experiment: **1,792** paid transfers with point-in-time xG-level features, **4,892** with basic-stats features, and about **11,000** player-seasons for a market-value model.
- There isn't enough to support the original headline claim, "performance-based fair value vs fee → overpaid/underpaid". A performance-only fee model is typically **±47%** off, and an honest 80% interval spans roughly **0.2× to 1.7×** the estimate. Almost every transfer would sit "within range".
- Both sources the plan depended on have failed in 2026. FBref lost Opta data in January, transfermarkt-datasets froze in July, and Understat has been offline since November. This must be a **snapshot product (data to July 2026)**, not a live one.
- The "young hidden gems" idea is the worst-supported part: only **8%** of paid big-five transfers of players aged 21 or under have xG-level pre-transfer data.

---

## 1. What we downloaded and inspected

| Table (transfermarkt-datasets, snapshot 6 Jul 2026) | Rows | Notes |
|---|---:|---|
| transfers | 175,165 | 17,554 with fee > 0; 96,085 fee = 0 (free **or** loan, indistinguishable); 61,526 fee unknown; 488 rows dated in the future (contract-end placeholders) |
| player_valuations | 656,301 | Dated, 2000 – 12 Jun 2026; dense from 2013 |
| players | 50,149 | DOB, position, foot, height. Caps, contract expiry and current club are **current snapshots only** |
| appearances | ~1.9M | Per match: minutes, goals, assists, cards; 2012 – Jun 2026 |
| games | 88k | **Full domestic-league history 2012–2025 for 14 leagues** (big five plus NL, PT, BE, TR, RU, SC, GR, DK, UKR); 17 more leagues only from 2024 |

**Sanity check against public figures:** the dataset's Premier League 2022/23 gross spend is **€3.13bn**, in line with widely reported totals of about €3bn. Early seasons look under-covered (2015/16 Premier League ≈ €1.0bn in the dataset, below commonly reported totals), probably because the scrape covers players present in the dataset rather than every transfer.

**Loans:** paid loan fees are recorded as 0 (for example Mbappé's 2017 loan and João Félix's 2023 loan both show €0), so they don't contaminate the fee > 0 set. 389 fee > 0 moves followed by a return to the selling club within 400 days were excluded as probable loans with fees.

## 2. Disclosed-fee transfers (2015/16 – 2025/26)

- **15,794** transfers with fee > 0 (all leagues). **5,630** involve a big-five club as buyer or seller. There's no "disclosed vs estimated" flag: Transfermarkt fees are often media-reported estimates, and add-ons aren't separated.
- When a big-five club buys from a covered top flight, fees are almost never "unknown" (32 of 8,713). Transfermarkt fills undisclosed fees with reported figures, which is good for coverage and bad for precision.

**Paid transfers involving a big-five club, by season and buyer** (full tables in `coverage_tables.md`):

| Season | 15/16 | 16/17 | 17/18 | 18/19 | 19/20 | 20/21 | 21/22 | 22/23 | 23/24 | 24/25 | 25/26 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Transfers | 298 | 345 | 398 | 437 | 506 | 348 | 449 | 622 | 731 | 692 | 757 |

The jump after 2021/22 is partly real market growth and partly better coverage of recent years. That's a temporal-drift problem in itself (section 6).

## 3. Understat: availability and matching

- **Availability:** recovered from the Internet Archive because understat.com is offline. **45/55** league-seasons 2014/15–2024/25; 2025/26 missing for every league (gaps listed in `DATA_SOURCES.md`). 24,160 player-season rows, 7,966 players.
- **Granularity:** **season-level only.** We couldn't recover per-match data, so winter transfers can only use the previous full season.
- **Matching method:** Understat has no DOB and no external IDs. Within each league-season we filter Transfermarkt candidates by games (±2), goals (±1) and minutes (±12%, min 90), then pick the best name match (accent-stripped, token-aware). A player-level majority vote removes per-season contradictions.
- **Match rate:** **98.1%** of Understat player-seasons; **99.2%** for players with ≥450 minutes. Most misses are Transfermarkt appearance gaps (e.g. some 2021/22 rows), not name problems.
- **Precision:** a manual review of 45 random non-exact name matches found 1 error ("Lluis López" matched to "Pedro López"). Non-exact matches are 7.5% of the total, so the **estimated overall error rate is about 0.2%**. 18 of 7,819 Understat IDs had conflicting per-season matches, resolved by majority vote.
- **One bug found and fixed along the way:** assigning seasons by calendar month mis-assigned COVID-delayed 2019/20 matches played in July 2020 and dropped those seasons' match rate to ~33%. The fixed version uses the official fixture season.

## 4. Funnel: how many transfers remain usable

| Step | Transfers | % |
|---|---:|---:|
| F0 Paid fee, 1 Jul 2015 – 6 Jul 2026 | 15,794 | 100% |
| F1 Not a probable paid loan | 15,405 | 97.5% |
| F2 Buying or selling club in big five | 5,630 | 35.6% |
| F3 Player appeared in a big-five league the prior season | 3,070 | 19.4% |
| F4 That league-season exists in the Understat archive | 2,423 | 15.3% |
| F5 Matched to an Understat player | 2,417 | 15.3% |
| F6 ≥ 900 Understat minutes in the prior season | 1,792 | 11.3% |
| **F7 Plus point-in-time market value ≤ 365 days old → USABLE (xG-level)** | **1,792** | **11.3%** |
| *ALT: ≥ 900 Transfermarkt minutes in the prior 365 days (any of the 14 leagues) + point-in-time market value* | ***4,892*** | *31.0%* |

The biggest drop is F2 → F3: **45% of big-five transfers involve players who weren't in a big-five league the season before.** Of these, 1,229 come from second tiers, South America or youth teams, and about 450 from the Netherlands, Portugal or Belgium. Understat can't describe them.

**What the usable set looks like:**
- **Age:** median 25.5; ≤20: **27**; 21–23: 327; 24–26: 629; 27–29: 490; 30+: 318.
- **Fee:** median €9.5M; <€2M 238 · €2–5M 340 · €5–10M 367 · €10–20M 393 · €20–40M 285 · €40–80M 144 · €80M+ **25**.
- **Position:** CB 346, CF 320, CM 211, DM 185, RB 125, LW 114, RW 114, AM 111, GK **109**, LB 107.
- **Window:** summer 1,538, winter 236.
- **By season:** 56 (15/16) up to 261 (22/23). Ligue 1 2015–2017 and Serie A 2015/16 and 2017/18 are nearly empty because of archive gaps.

## 5. Metrics actually available

| Available (point-in-time safe) | Source |
|---|---|
| Minutes, games, goals, assists, cards (per match, exact dates) | Transfermarkt appearances |
| Starting vs bench role, substitutions | Transfermarkt lineups/events |
| xG, npxG, xA, shots, key passes, xGChain, xGBuildup (season level) | Understat (archive) |
| Age, position (current label), foot, height | Transfermarkt players |
| Selling/buying league and club, club league position, transfer window | Transfermarkt games/transfers |
| Market value history (dated) | Transfermarkt valuations |

| **Missing** (no free, legal source found) | Consequence |
|---|---|
| Progressive passes/carries, dribbles, pass completion, tackles, interceptions, aerial duels, pressures | Defenders and midfielders are described almost only by minutes and context |
| Goalkeeper metrics (saves, PSxG) | GKs (109 usable) can't be assessed on performance |
| **Contract length at transfer date** | The biggest known fee driver is unobserved; contract expiry exists only as a current snapshot |
| International caps at transfer date | Only current totals: **leakage if used** (excluded) |
| Historical position | Position is today's label |
| Add-ons, sell-on clauses, fee disclosure status | Fee itself is noisy |
| Per-match xG | Winter transfers use stale stats |
| Anything for 2025/26 from Understat | Current-season player pages limited to Transfermarkt basics |

## 6. Predictive-signal probe

These are quick, untuned models, not the product model. They train on 2015/16–2021/22 and test on 2022/23–2025/26, never shuffled. Errors are measured on held-out seasons. APE is |predicted − actual| / actual in euros.

| Target / features | Test n | R² (log) | Median APE | Within ±50% |
|---|---:|---:|---:|---:|
| **Fee**: naive median by position × age | 925 | −0.02 | 72% | 32% |
| Fee: context only (age, position, leagues, minutes), Ridge | 925 | 0.47 | 52% | 49% |
| Fee: + Transfermarkt goals/assists, Ridge | 925 | 0.53 | 49% | 50% |
| Fee: + Understat xG family (performance only), Ridge | 925 | 0.56 | 47% | 53% |
| Fee: same, gradient boosting | 925 | 0.54 | 48% | 52% |
| Fee: **market value only**, Ridge | 925 | 0.72 | 34% | 66% |
| Fee: performance + market value, Ridge | 925 | **0.77** | **32%** | **74%** |
| Fee (broad TM-only population): performance only | 2,669 | 0.56 | 57% | 44% |
| Fee (broad TM-only population): performance + market value | 2,669 | 0.80 | 36% | 67% |
| **Market value** from Understat performance, Ridge | 2,856 | 0.65 | 47% | 52% |
| **Market value** from Understat performance, gradient boosting | 2,856 | 0.71 | 40% | 61% |

What this tells us:

1. **There is real signal.** Every model beats the naive baseline by a wide margin.
2. **Most of it is context, not performance.** Age, position, leagues and minutes reach R² 0.47. Understat xG adds about 0.035 over Transfermarkt basics. Without licensed event data, "performance" is a modest part of any valuation.
3. **The crowd beats our features.** The point-in-time Transfermarkt market value alone predicts fees better than all performance data combined.
4. **Gradient boosting doesn't beat Ridge on the fee targets** (too little data). It does win on the larger market-value panel. This supports the "start explainable" principle.
5. **Uncertainty is large.** A split-conformal 80% interval for the performance-only fee model is about **×0.23 to ×1.69** the point estimate (79% empirical coverage on the test seasons).
6. **Temporal drift is material.** The performance-only model over-predicts every test season (mean log residual −0.30: predictions about 35% above actual fees). A linear season trend learned across the 2015–2019 boom and the COVID dip doesn't extrapolate. We'll need an explicit market-level index.

## 7. Is the dataset representative enough for ML?

**Yes, for a carefully scoped experiment. No, for some of the promised segments.**

- **Adequate:** established big-five players aged 21–31 with €2–80M fees, in the major outfield positions. Hundreds of rows per segment and about 925 held-out test transfers.
- **Under-represented or unusable:**
  - Under-21s: 27 usable rows aged ≤20.
  - Imports from outside the big five, which is the core scouting use case.
  - €80M+ deals: 25 rows.
  - Goalkeepers: no performance metrics.
  - Ligue 1 and Serie A in specific seasons (archive gaps).
  - Winter transfers: stale features.
- **Selection bias:** transfers with fees aren't a random sample of players. A fee model applied to non-transferred players is extrapolation. The market-value panel doesn't have this problem, because valuations exist for almost everyone.

## 8. Problems that could make the valuation model unreliable

1. **Circularity:** if Transfermarkt value is used as a feature or target, the model partly learns crowd opinion, including its biases (reputation, league prestige, nationality effects).
2. **Unobserved contract length:** it's systematically confounded with "overpayment". Short contracts produce low fees, and release clauses produce high ones.
3. **Fee noise:** reported estimates, missing add-ons and currency conversions. A ±20% fee error is common.
4. **Temporal drift:** market inflation, COVID collapse, Premier League broadcast cycles and Saudi demand (2023+). The probe already shows a 26–35% bias.
5. **Leakage traps found in the data:** current-snapshot fields (caps, contract expiry, current club, position); "future" transfer rows; valuation dates recorded after the transfer. All have to be guarded explicitly; the probe excludes caps and uses strictly-before valuation dates.
6. **Selection bias:** see section 7.
7. **Archive gaps:** missingness isn't random; it's tied to specific leagues and seasons, which biases league coefficients.
8. **Small-sample positions:** separate per-position models aren't viable. We need pooled models with position terms.
9. **Source fragility:** no refresh path exists, and both sources may never return.

## 9. Choosing the modelling target

| Option | Strengths | Weaknesses (with our data) |
|---|---|---|
| **A. Predict historical fees from performance** (original plan) | Directly answers "overpaid?"; independent of crowd values | n ≈ 1.8k; ±47% typical error; huge intervals mean almost nothing gets flagged; selection bias; contract confound; can't value non-transferred players |
| **B. Predict market valuations** | ~11k player-seasons (more if extended); covers every player, so no transfer-selection bias; annual cadence; best ML signal (R² 0.71) | Target is crowd opinion, so the model learns "what the market typically thinks", not a truth; circular if presented as independent |
| **C. Performance index (no money)** | Purely factual; percentiles vs position peers; no model risk | Limited metrics (attacking-heavy), weak for defenders and GKs; doesn't answer value questions alone |
| **D. Combination (recommended)** | Each layer is used where its data is strong, and every claim is framed honestly | More concepts to explain (but that's a strength in interviews) |

### Recommended: three layers

1. **Performance Profile** (option C). Per-90 metrics and percentiles against position peers, with sample-size reliability. Shown on player pages. No modelling claims.
2. **Performance-Implied Market Value** (option B, the main ML model). It predicts a player's Transfermarkt valuation from performance, age, position, league and minutes. Trained on all matched player-seasons with a temporal split and conformal intervals. The **gap between actual market value and performance-implied value** drives Hidden Gems ("the market values him below what players with this profile are usually valued at") and is explicitly described as relative to market norms, not as a "true" value.
3. **Expected Fee** (an honest version of option A). It predicts the fee from everything public *at the transfer date*, including the point-in-time market value, performance and context, with a learned market-level index. Test R² ≈ 0.77–0.80 and median error ≈ 32–36%. **Transfer premium** = actual fee − expected fee, flagged only outside the 80% interval. This answers "did the club pay more than comparable public information predicted?", which is defensible. A performance-only fee model is kept as a **secondary diagnostic** to show what performance alone explains (a key portfolio insight), not as the headline.

## 10. GO / NO-GO

**CONDITIONAL GO**, on these conditions:

1. **Freeze the data** at the 6 Jul 2026 Transfermarkt snapshot and the archived Understat seasons. Label it "historical analysis 2015/16–2025/26", not live.
2. **Non-commercial positioning** and the attribution and redistribution rules in `DATA_SOURCES.md`. Raw data never goes to GitHub.
3. **Adopt the three-layer target design** above. Drop "performance-based fair fee" as the headline.
4. **Restrict claims** to the populations the data supports. Hidden Gems is big-five-only and can't find "the next star from the Eredivisie".

**NO-GO** for: a live or updating product; a commercial product on these sources; rich position-specific scouting (defenders, GKs); hidden gems outside the big five or among under-21s; and labelling transfers "overpaid" from performance alone.

## 11. Revised MVP (replaces section 4 of the proposal)

| Module | Original | Revised |
|---|---|---|
| Fair Value Engine | Performance → fee | **Performance-implied market value** (main model) + **Expected Fee** (with market value) + performance-only diagnostic |
| Player Intelligence | Rich position metrics, radar | Attacking/creative per-90s + minutes, percentiles vs position peers, market value history, model estimate + interval. Defenders and GKs shown with an explicit "limited metrics" notice |
| Transfer Intelligence | Overpaid/underpaid vs fair value | **Transfer premium vs Expected Fee**, flagged only outside the 80% interval; filters and rankings as planned. Covers ~4.9k transfers (basic features), with an xG-enriched badge on ~1.8k |
| Hidden Gems | Young players, any league | Big-five players 2024/25 season where market value is well below performance-implied value; similarity search on the Understat profile |
| Club Audit | As planned | As planned, over the 4.9k-transfer set; price efficiency only (no "sporting success" claim) |
| AI Analyst | As planned | As planned (tool-grounded); must cite data vintage and coverage limits |
| Methodology page | Planned | **Promoted to a headline feature:** model card, the probe results, the data funnel and the licensing posture |

Timeline impact: the data pipeline gets simpler (the sources are frozen and already working in these scripts), and modelling gets one extra model. **Net: the 5-week plan still holds.** Week 1 (data) is largely done by this study.

---

### Erratum (Step 2 staging, 12 Nov 2026)

The probable-loan rule ("the player's next move reverses this one within 400 days") depended on the arbitrary order of same-day rows. In **"buy and loan back"** deals (for example Atalanta → Inter €40.7M in 2017 with an immediate loan back to Atalanta), it sometimes excluded the permanent paid transfer as a loan. The staging pipeline now requires the return to happen on a *later* date. Corrected counts: F1 **15,416** (was 15,405) and F2 **5,637** (was 5,630); 11 transfers restored in total. Usable-set counts (F7 and ALT) are recomputed by the as-of feature builder in Step 3.

### Reproducibility

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -e "pipeline[dev]"
# 1. Download transfermarkt-datasets.zip to data/raw/transfermarkt/ and unzip into extracted/
.venv/Scripts/python -P scripts/feasibility/fetch_understat_wayback.py   # slow, cached, polite
.venv/Scripts/python -P scripts/feasibility/match_tm_understat.py
.venv/Scripts/python -P scripts/feasibility/build_usable.py
.venv/Scripts/python -P -W ignore scripts/feasibility/probe_models.py
```

Outputs: `reports/feasibility/coverage_tables.md`, `reports/feasibility/probe_results.md`, `data/sample/sample_100_transfers.csv`, `data/interim/*`.
