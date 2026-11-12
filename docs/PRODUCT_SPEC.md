# FairValue Football: Product Specification v1.0

*Status: for approval · 12 November 2026 · supersedes the MVP sections of the original proposal.*
*Inputs: `reports/feasibility/FEASIBILITY_REPORT.md`, `DATA_SOURCES.md`.*

---

## 1. Product definition

**FairValue Football is a market-intelligence platform for the European transfer market.** It shows how a player's market valuation and transfer fees compare with what their measurable performance and context would typically command, and how sure we can be about that.

**One-line pitch:** *"Where does the market's price disagree with the evidence, and how confident can we be?"*

| Fact | Value |
|---|---|
| Coverage | 14 European top flights (big five fully, with xG; nine more with basic stats), seasons 2015/16–2025/26 |
| Data vintage | Frozen snapshot: Transfermarkt to 6 Jul 2026; Understat to 2024/25 |
| Positioning | Non-commercial research and portfolio project. Attributed sources. Raw data never published |
| Users | Recruitment analysts (discovery), football-business analysts (transfer economics), data-literate fans (exploration) |

### Non-negotiable product rules

| # | Rule | How the product enforces it |
|---|---|---|
| R1 | **No definitive verdicts.** Never "overpaid", "underpaid", "bargain", "flop", "true value", "worth". | Controlled vocabulary (section 2). Labels come from interval positions, never from the sign of a gap. Lint test fails the build if banned words appear in UI strings. |
| R2 | **No leakage.** Every number shown for a date uses only information available at that date. | `as_of` contract in the feature builder, walk-forward "vintage" models, automated leakage tests (section 7.5). |
| R3 | **Uncertainty is always visible.** No estimate without a range; insufficient data is stated, not hidden. | Every estimate component requires `lo`/`hi`/`reliability`. An "Insufficient data" state replaces the estimate when rules fail (section 2.3). |
| R4 | **Scope discipline.** | MVP = Player Intelligence, Fair Value Engine, Hidden Gems, Club Audit, plus the supporting Transfers and Methodology pages. AI Analyst deferred. |
| R5 | **Licensing.** | `data/` git-ignored; only derived outputs are loaded to the database; attribution footer on every page; no Transfermarkt images. |

---

## 2. Language and uncertainty system

### 2.1 Controlled vocabulary

| Concept | Use | Never |
|---|---|---|
| Model estimate of market value | **Performance-implied value (PIV)** | "true value", "real worth", "fair price" |
| Market value − PIV | **Valuation gap** | "mispricing" |
| PIV clearly above market value | **Potential undervaluation** | "underrated", "steal" |
| PIV clearly below market value | **Market premium** (the market values him above his measurable profile) | "overrated", "overvalued" |
| Model estimate of a fee | **Expected fee** | "correct fee" |
| Fee − expected fee | **Transfer premium** (positive) / **fee discount** (negative) | "overpaid", "underpaid", "bargain" |
| Classification outside the 80% range | **Notable** premium / discount | "bad deal", "good deal" |
| Classification outside the 95% range | **Unusual** premium / discount | "scandalous", "robbery" |

Every gap is paired with an "Unobserved factors" note. For fees that means contract length, release clauses, add-ons, competition between clubs, and agent and personal terms. For market values it means injuries, reputation, contract and off-pitch factors.

### 2.2 Classification from intervals (never from the gap's sign)

```
            95% lo   80% lo        estimate        80% hi   95% hi
   ──────────┼────────┼──────────────●──────────────┼────────┼──────────
   Unusual   │Notable │     Within expected range   │Notable │ Unusual
   discount  │discount│                             │premium │ premium
```

The same scheme is used for valuation gaps: outside the 80% range on the low side is "Potential undervaluation", outside the 95% range is "Strong signal of potential undervaluation".

### 2.3 Reliability tiers

Every prediction gets a tier from **deterministic rules** that are shown to the user:

| Tier | Rule (PIV model; Expected Fee is analogous) | UI |
|---|---|---|
| **High** | Full feature set (xG data), ≥1,800 minutes, outfield, match confidence high | Solid badge |
| **Moderate** | Full features with 900–1,799 min, **or** basic features with ≥1,800 min | Outlined badge |
| **Low** | Basic features with 900–1,799 min, or position group with weak metrics (centre-backs, full-backs) | Faded badge plus a note |
| **Insufficient** | <900 min, goalkeepers (performance models), missing league-season data, unmatched player | **No estimate shown.** An "Insufficient data" panel explains which rule failed and what would fix it |

The interval widths themselves come from **group-wise conformal calibration** (section 7.4), so a Low-tier estimate visibly carries a wider band. The tier and the band reinforce each other.

---

## 3. Information architecture

```
FairValue Football
├── /                      Market Overview
├── /players               Player Explorer (table + filters)
│   └── /players/[slug]    Player Intelligence
├── /transfers             Transfer Intelligence (table, filters, rankings)
│   └── /transfers/[id]    Transfer detail
├── /hidden-gems           Hidden Gems Finder
├── /clubs                 Club rankings
│   └── /clubs/[slug]      Club Transfer Audit
└── /methodology           Model card · data coverage · glossary · licensing
```

**Global chrome:**
- Top navigation and ⌘K global search (players, clubs).
- A **data-vintage pill** on every page ("Data to 6 Jul 2026 · Understat to 2024/25") linking to Methodology.
- A footer with attribution (Transfermarkt via transfermarkt-datasets; Understat), a non-commercial notice and "not affiliated with any club or data provider".

All filters live in the **URL query string**, so every view can be shared, bookmarked and reproduced. That's a recruitment-workflow requirement, not a nicety.

---

## 4. Pages and features

### 4.1 Market Overview `/`
The purpose is orientation in under 30 seconds and showing what's interesting. Not a wall of KPIs.
- **Header strip (4 KPIs max):** transfers covered · total fees covered · players with PIV this season · median transfer premium (last window), with interval.
- **"Signals this season"** has three compact lists: top potential undervaluations (High/Moderate reliability only), most unusual transfer premiums of the last window, and the most price-efficient clubs (minimum sample). Each row links to its page.
- **Market level chart:** median fee ÷ market value by window, 2015–2026 (the market-index layer, section 7.3). Explains drift visibly.
- **Coverage map teaser:** a league × season heatmap of data tier (full / basic / missing).

### 4.2 Player Explorer `/players`
- Server-paginated table: name, age, position, club, league, minutes, market value, PIV (range), valuation gap, reliability.
- Filters: season, league, position group, age range, minutes ≥, market value range, reliability ≥, data tier.
- Column sets: "Valuation" / "Attacking" / "Creation & build-up".

### 4.3 Player Intelligence `/players/[slug]`
This is the flagship page. Layout (desktop; it stacks on mobile):

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Player name · 24 · Left Winger · Club · League        [Season ▾ 2024/25]  │
│ Data tier: Full · Reliability: High · 2,734 min                            │
├───────────────────────────────┬────────────────────────────────────────────┤
│ VALUATION                     │ WHY THIS ESTIMATE (top drivers)            │
│ Market value      €18.0M      │ + xA/90 (93rd pct)              +€3.1M     │
│ Performance-implied €26.5M    │ + Age 24                        +€2.4M     │
│  80% range  €17M ─●── €39M    │ − League strength (Ligue 1)     −€2.0M     │
│ Gap: Potential undervaluation │ + Minutes share 88%             +€1.6M     │
│ (notable, outside 80% range)  │ … unobserved: contract, injuries, …        │
├───────────────────────────────┴────────────────────────────────────────────┤
│ PERFORMANCE PROFILE vs left/right wingers, big five, 2024/25 (n = 212)     │
│ npxG/90  ███████████░░░  78th   xA/90  █████████████░  93rd  …             │
│ Metrics not measured: dribbles, progressive carries, defensive actions ⓘ   │
├────────────────────────────────────────────────────────────────────────────┤
│ VALUATION HISTORY  market value (line) vs PIV band per season (vintage)    │
├────────────────────────────────────────────────────────────────────────────┤
│ TRANSFER HISTORY  date · from → to · fee · expected fee (range) · label    │
├────────────────────────────────────────────────────────────────────────────┤
│ SIMILAR PROFILES (same position, same season)  6 cards with MV & PIV      │
├────────────────────────────────────────────────────────────────────────────┤
│ DATA & COVERAGE  sources · match confidence · seasons available · caveats │
└────────────────────────────────────────────────────────────────────────────┘
```

Design decisions:
- **Percentile bars instead of radar charts** as the primary view. Radars distort area and hide uncertainty. A radar is available as a secondary toggle, because users expect one.
- **Drivers are shown in euros**, converted from log-scale contributions (approximate, labelled as such), because "+€3.1M from xA" is understandable and "+0.17 log units" isn't.
- **Valuation history uses vintage predictions:** each season's PIV comes from a model trained only on earlier seasons, so the chart is an honest record of what the model would have said at the time.

### 4.4 Transfer Intelligence `/transfers` and `/transfers/[id]`
- **Table:** player, date, from → to, fee, market value at the time, expected fee (range), premium (€ and %), classification, reliability.
- **Filters:** season/window, buying or selling league, club, position, age, fee range, expected-fee range, classification, data tier.
- **Rankings tabs:** Most unusual premiums · Largest fee discounts vs expectation · Largest absolute gaps. Each excludes Insufficient rows and states its minimum reliability.
- **Detail page:** a fee-vs-expected interval chart, drivers, pre-transfer snapshot (last season's profile, market value trajectory over 12 months), an "Unobserved factors" checklist, and the **post-transfer outcome**: market value change 12 and 24 months after the move. That last one is explicitly labelled *"outcome, observed after the transfer, not used by the model"*. This is the one place future data appears, clearly separated, and it's how we distinguish price efficiency from what happened next.

### 4.5 Hidden Gems Finder `/hidden-gems`
- **Query builder (left rail):** season (default: latest full-tier season 2024/25, with a switch to the 2025/26 basic tier), position group, age range, league(s), max market value, min minutes, min reliability, and metric thresholds on percentiles (e.g. xA/90 ≥ 80th).
- **Example query (pre-filled):** *"Wingers ≤ 23, market value ≤ €20M, xA/90 and npxG/90 ≥ 70th percentile, reliability ≥ Moderate."*
- **Result cards:** profile line, market value vs PIV with range, top 3 percentile strengths, data tier and reliability, plus a **scouting rationale** generated from a deterministic template (not an LLM): *"Market value €9M sits below the 80% performance-implied range (€11–24M). Creation profile is 91st percentile among wingers (xA/90). Caveat: 1,240 minutes, so Moderate reliability."*
- **Similarity mode:** pick a player and get the nearest profiles within the position group, sorted by distance, with a market-value filter (*"cheaper alternatives to X"*).
- **Backtest banner (honesty feature):** *"Historically, players flagged as potential undervaluation saw a median market value change of X% over the next 12 months vs Y% for comparable unflagged players (seasons 20xx–20xx)."* Computed by the pipeline. **Shown whatever the result**, even if the signal turns out weak.

### 4.6 Club Transfer Audit `/clubs` and `/clubs/[slug]`
- **Rankings:** clubs with ≥ 8 assessed purchases in the selected period. Metrics: total fees, total expected fees, **price-efficiency ratio** = Σ fee ÷ Σ expected fee with a bootstrap 80% interval, and the share of notable premiums and discounts. Default sort is by the interval's upper bound, so small samples don't top the table by luck.
- **Club page:**
  - KPI strip.
  - Purchases table with classifications.
  - Recruitment patterns: age at signing, position mix, source leagues (charts).
  - Fee vs expected fee scatter, log-log, with the 80% band.
  - Post-transfer market value outcome (labelled as outcome).
  - A permanent note: *"Price efficiency is not sporting success. A club can pay premiums for players who succeed."*

### 4.7 Methodology `/methodology`
A first-class feature for credibility and interviews:
- **Model cards** for PIV and Expected Fee: target, data, splits, metrics vs baselines, interval coverage by reliability tier, known failure modes.
- **Data funnel** (15,794 → 4,892 / 1,792), **coverage heatmap** (league × season × tier) and the matching method and error rate.
- **Leakage policy**, explained in plain language, plus the vintage-model concept.
- Glossary (the vocabulary from section 2), the licensing summary and the data vintage.

### 4.8 Cross-cutting UX states
- **Insufficient data panel:** reason, rule, and what would change it. Reused everywhere an estimate would appear.
- **Skeleton loading** shaped like the final layout; **empty states** with a suggestion to relax filters; **error boundaries** per section, so one failed chart doesn't blank the page.
- **Responsive:** tables collapse to cards under 768px; charts keep the axis and the interval.

---

## 5. Design system

| Element | Decision | Why |
|---|---|---|
| Theme | Dark-first, with full light theme via tokens | Analyst tool norms; tokens keep both consistent |
| Type | Inter for UI with **tabular numerals**; JetBrains Mono for IDs only | Columns of numbers must align |
| Colour | Neutral greys + one brand accent. **Diverging pair blue ↔ amber** for discount ↔ premium | Red/green would imply moral judgement (rule R1) and fails for colour-blind users |
| Uncertainty | Always dot-and-range or band; never a bare number for a model output | Rule R3 made visual |
| Numbers | €12.4M / €850k; percentiles as "93rd"; ranges as "€11–24M" | Consistent, scannable |
| Components | shadcn/ui primitives + our own `EstimateRange`, `ReliabilityBadge`, `GapLabel`, `PercentileBar`, `InsufficientData`, `DataTierPill`, `SourceFootnote` | Domain components enforce the rules once, everywhere |
| Charts | Recharts, wrapped in our own chart components with shared axes, tooltips and tokens | Visual consistency across pages |
| Motion | 150–200ms fades and number tweens only | Subtle, never decorative |

---

## 6. System architecture and data flow

```
 OFFLINE (Python, run locally)                         ONLINE
 ───────────────────────────────────────────────       ─────────────────────────────────────

 data/raw (frozen, git-ignored, checksummed)
   ├─ transfermarkt-datasets zip (to 6 Jul 2026)
   └─ understat_wayback html cache (2014/15–2024/25)
            │ ingest + validate (schemas, row counts, checksums)
            ▼
 staging  (clean parquet: players, clubs, transfers, valuations,
           appearances, understat player-seasons, id_map)
            │ as-of feature builder  (feature(entity, as_of))
            ▼
 features (player_season_features, transfer_features)
            │
            ├─► L1 Performance Profiles  (percentiles, shrinkage, similarity)
            ├─► L2 PIV model   (walk-forward vintages, conformal, drivers)
            └─► L3 Expected Fee (uses L2 vintages, conformal, drivers)
            │
            ▼ export + evaluation reports + model cards
 outputs (parquet + model_run manifest)
            │ load (service-role key, from the pipeline only)
            ▼
 ┌───────────────────────── Supabase Postgres ─────────────────────────┐
 │ dimension tables · player_seasons · transfers · predictions · views │
 │ RLS: public SELECT only; no public writes                          │
 └──────────────────────────────────┬──────────────────────────────────┘
                                    │ server-side queries
                                    ▼
                         Next.js App Router (Vercel)
                         Server Components fetch → props → client charts
```

Key decisions:
- **Batch, offline ML; read-only web app.** The data is frozen, so predictions are computed once per model run and stored. The web app does no ML at runtime, so it's fast, cheap and has nothing to break at request time.
- **The database holds derived data only.** Raw tables never leave the laptop, and Postgres holds the facts each page needs plus our outputs (rule R5).
- **Server Components for data fetching.** Queries run on the server, no API keys reach the browser, and HTML arrives already populated. Only charts and filters are client components.
- **Every prediction row stores `model_run_id`.** Re-running the pipeline creates a new run; the app reads the run marked `is_current`. Results stay auditable and reversible.
- **No authentication in the MVP.** Everything is public read-only. Auth only returns with the AI Analyst (for rate limiting) or saved shortlists.

### 6.1 Repository layout

```
fairvalue-football/
├── pipeline/                 Python package (pip install -e pipeline)
│   ├── fairvalue/ingest/     load + validate frozen sources
│   ├── fairvalue/staging/    cleaning, ID matching (from feasibility scripts)
│   ├── fairvalue/features/   as-of feature builder
│   ├── fairvalue/profiles/   percentiles, shrinkage, similarity
│   ├── fairvalue/models/     piv.py, expected_fee.py, conformal.py, explain.py
│   ├── fairvalue/export/     parquet → Postgres loader
│   └── tests/                leakage, calibration, gap math, matching
├── web/                      Next.js app
│   ├── app/                  routes from section 3
│   ├── components/domain/    EstimateRange, ReliabilityBadge, …
│   ├── components/charts/
│   └── lib/db/               typed queries (generated Supabase types)
├── supabase/migrations/      SQL schema, RLS policies, views
├── docs/                     PRODUCT_SPEC, MODEL_CARD_*, ADRs (decision log)
├── reports/                  evaluation outputs
├── scripts/feasibility/      the feasibility study (kept for provenance)
└── data/                     git-ignored
```

---

## 7. Modelling architecture

### 7.1 Layer 1: Performance Profiles (facts, not models)
- **Unit:** player × season × league, ≥ 900 league minutes.
- **Metrics:**
  - Full tier (big five, Understat): npxG, xA, shots, key passes, xGChain, xGBuildup, goals, assists, all per 90.
  - Basic tier (all 14 leagues, Transfermarkt): goals, assists, minutes share, starts share, cards per 90.
- **Position group as of the season:** from Understat's per-season position where available, otherwise Transfermarkt's current label, flagged as "current label". This avoids leaking today's position into the past.
- **Shrinkage:** per-90 rates are pulled toward the position mean in proportion to minutes (empirical Bayes), so 950 brilliant minutes don't rank like 3,000.
- **Percentiles:** within position group × season × tier peer set; the peer-set size n is always displayed.
- **Similarity:** cosine distance on standardised shrunk per-90s within a position group and season; top 20 neighbours precomputed.

### 7.2 Layer 2: Performance-Implied Value (main model)
- **Question:** *"Given this season's measurable performance and context, what market value do players with this profile typically carry?"*
- **Unit and target:** player-season. Target = log of the Transfermarkt market value at the first valuation dated after the season ends, within 120 days.
- **Market-level normalisation:** the target is modelled relative to that summer's median valuation of comparable players. That median is known at that date, so it's not leakage. This removes market-wide inflation from what the model must learn and fixes the drift problem the feasibility probe exposed.
- **Two feature tiers, two models:**
  - **PIV-Full:** big five, 2014/15–2024/25, about 11k player-seasons; Understat + Transfermarkt features.
  - **PIV-Basic:** 14 leagues, 2012/13–2025/26, about 3.6k player-seasons per year; Transfermarkt features only. This provides 2025/26 estimates (where Understat is missing) and covers the nine non-big-five leagues, at lower reliability tiers.
- **Features (all as of season end):** age, age², position group, league, team strength (points per game), minutes and starts share, shrunk per-90s for this and the previous season, change versus the previous season. **Excluded:** the player's own market value (that would be circular), caps, contract and current club (snapshot fields).
- **Candidates:** Ridge (baseline and explanation reference) vs histogram gradient boosting. **Selection rule:** gradient boosting must beat Ridge on walk-forward MAE (log) by ≥ 5% *and* not worsen calibration. Otherwise ship Ridge. The probe suggests gradient boosting will win here (R² 0.71 vs 0.65).
- **Explanations:** SHAP values for gradient boosting (exact coefficient × value for Ridge), aggregated into readable driver groups and converted to approximate euros.

### 7.3 Layer 3: Expected Fee (secondary)
- **Question:** *"Given everything public at the transfer date, what fee did comparable deals command?"*
- **Unit:** a paid transfer, 2015/16–2025/26. About 4.9k with basic features; about 1.8k flagged full-tier.
- **Target:** log(fee ÷ point-in-time market value), i.e. the premium over the market value. Expected fee = market value × predicted ratio. This anchors on the strongest signal and learns the deviations.
- **Features:**
  - Point-in-time market value and its 12-month trajectory.
  - The player's latest **vintage PIV** and gap (from Layer 2, trained only on earlier seasons).
  - Age, position, seller and buyer league, buyer's spending power (fees paid in the previous 2 windows).
  - Window (summer/winter), deadline-week flag, minutes in the prior 365 days.
  - **Market index:** median fee/value ratio of the previous two windows, from past windows only.
- **Model:** Ridge first. The probe showed gradient boosting doesn't help at this sample size; it gets re-tested, not assumed.
- **Outputs:** expected fee, 80% and 95% ranges, transfer premium, classification (section 2.2), drivers and reliability.

### 7.4 Uncertainty: group-wise split-conformal intervals
- **What it is:** use held-out residuals to find the error size that covers 80% (or 95%) of cases, and put that band around each new prediction. It's model-agnostic and comes with a coverage guarantee.
- **Group-wise ("Mondrian"):** calibrate separately per reliability group (tier × minutes band × position group), so uncertain kinds of players get honestly wider bands.
- **Validation:** coverage is measured per group on later seasons and published in the model card. A group with coverage far off target is downgraded a tier.

### 7.5 Leakage prevention (rule R2): enforced, not promised
1. **`as_of` contract:** every feature function takes `as_of: date` and may only read rows dated strictly before it. A guard checks each feature row's maximum source date against `as_of`.
2. **Vintage models:** predictions for season s (PIV) or window w (Expected Fee) come from a model trained only on data before s or w. These walk-forward models are what the app shows historically. The "current" model is trained on everything and used only for the latest season.
3. **Snapshot-field blocklist:** `international_caps`, `contract_expiration_date`, `current_club_*`, `market_value_in_eur` (players table) and `highest_market_value_in_eur` can't be imported by feature code; a test asserts this.
4. **Calendar traps:** official fixture seasons are used (COVID 2019/20 fix), and transfers dated after the data cutoff are excluded.
5. **Market index and normalisation** are computed only from data before (or exactly at) the reference date.
6. **Test suite:** synthetic "future spike" tests (inject an absurd value after `as_of` and assert features don't change), schema tests, calibration tests and gap-math tests.

### 7.6 Evaluation protocol
- **Walk-forward folds:** train ≤ s−1 → test s, for s = 2019/20 … 2025/26. Hyperparameters are tuned only inside training folds. Final numbers come from folds the model never saw.
- **Metrics:** MAE (log), median absolute % error, R² (log), share within ±25% and ±50%, interval coverage and width per group, and bias per season (the drift check).
- **Baselines that must be beaten:** median by position × age; context-only Ridge.
- **Hidden Gems backtest:** the 12-month market value change of flagged vs matched unflagged players, published as is.

---

## 8. Database schema (Supabase Postgres)

```sql
-- dimensions
competitions(id pk, code, name, country, tier_label, has_full_history bool)
clubs(id pk, tm_id, name, slug, country)
players(id pk, tm_id, understat_id null, name, slug, dob, foot, height_cm,
        position_label_current, nationality)       -- nationality: display only, not a model feature
seasons(id pk "2024/25", start_year)

-- facts
player_seasons(player_id, season_id, competition_id, club_id,
               data_tier 'full'|'basic', minutes, starts, games,
               goals, assists, npxg, xa, shots, key_passes, xg_chain, xg_buildup,
               per90 jsonb, per90_shrunk jsonb, percentiles jsonb, peer_n int,
               position_group, position_source 'season'|'current_label',
               pk(player_id, season_id, competition_id))
market_values(player_id, value_date, value_eur, pk(player_id, value_date))
transfers(id pk, player_id, date, season_id, window, from_club_id, to_club_id,
          from_competition_id, to_competition_id, fee_eur, age_at_transfer,
          mv_before_eur, mv_before_date, data_tier)

-- model outputs
model_runs(id pk, model 'piv_full'|'piv_basic'|'expected_fee', version, trained_through,
           is_current bool, metrics jsonb, coverage jsonb, created_at)
piv_predictions(model_run_id, player_id, season_id, vintage bool,
                estimate_eur, lo80, hi80, lo95, hi95, reliability, reliability_reason,
                drivers jsonb, market_value_eur, gap_eur, gap_label)
fee_predictions(model_run_id, transfer_id, expected_fee_eur, lo80, hi80, lo95, hi95,
                premium_eur, premium_pct, label, reliability, reliability_reason, drivers jsonb)
similar_players(player_id, season_id, neighbour_id, distance, rank)
post_transfer_outcomes(transfer_id, mv_12m_after, mv_24m_after)   -- outcome only

-- reference
data_coverage(competition_id, season_id, tier, source, status)   -- heatmap
app_meta(key pk, value)                                           -- data vintage, attribution
```

Views (SQL, so pages stay simple): `v_player_latest`, `v_transfer_intel`, `v_club_audit` (aggregates; bootstrap intervals precomputed in Python and stored on a `club_audit` table), `v_hidden_gem_candidates`.

**RLS:** all tables `SELECT` for `anon`; no `INSERT/UPDATE/DELETE` policies. Loads use the service-role key from the pipeline machine only and never touch the web app.

---

## 9. Explicitly out of scope for the MVP

| Deferred | Why | When |
|---|---|---|
| AI Football Analyst | Needs stable models and data first (your rule) | After MVP sign-off |
| Player comparison page | Similarity search covers the core need | v1.1 |
| Auth, saved shortlists | No user data needed for read-only analytics | With the AI Analyst |
| Live data refresh | Sources frozen or offline | Requires licensed data |
| Defender and GK performance models | No legal free metrics | Requires licensed data |
| StatsBomb showcase pages | Nice-to-have; adds licence obligations | Optional, post-MVP |

---

## 10. Delivery plan (step by step)

Each step ends with something working, tested and explained, and I'll walk you through the key concept of each step as we do it.

| Step | Deliverable | Concepts you'll learn | Done when |
|---|---|---|---|
| **1. Foundation** | Git repo + GitHub (private), monorepo layout, Python package skeleton, Next.js + Tailwind + shadcn skeleton, CI running tests | Monorepos, Python packaging, CI basics | `pytest` and `next build` pass in CI |
| **2. Staging pipeline** | Ingest + validation, refactored ID matching, staging parquet | Data contracts, idempotent pipelines | Row counts and checksums reproduce the feasibility numbers |
| **3. As-of features + Layer 1** | Feature builder with leakage guards; profiles, percentiles, similarity | Point-in-time correctness, empirical Bayes shrinkage | Leakage tests green |
| **4. PIV model** | Walk-forward training, model selection, conformal, SHAP drivers, model card | Temporal CV, conformal prediction, SHAP | Model card with coverage per group |
| **5. Expected Fee + club audit** | Fee model, labels, bootstrap club intervals, gems backtest | Anchored targets, bootstrap | Model card #2; backtest published |
| **6. Database** | Supabase migrations, RLS, loader, generated TS types | Postgres views, RLS | App can query every page's data |
| **7. Design system + shell** | Tokens, domain components, layout, search, states | Design tokens, component APIs | Storybook-like component page reviewed by you |
| **8. Core pages** | Player Intelligence → Transfers → Hidden Gems → Clubs → Overview → Methodology | Server Components, URL state, data viz | Each page passes its user-journey test |
| **9. Polish + deploy** | Responsive pass, performance, accessibility, Vercel deploy, README, case studies | Deployment, Web Vitals | Public URL + docs |

Steps 1–5 are roughly weeks 1–2.5, steps 6–8 weeks 2.5–4.5, and step 9 week 5.

---

## 11. Decisions taken in this spec (for the decision log)

1. **PIV is the main model; Expected Fee anchors on market value.** This follows from the feasibility probe (market value explains about 72% of fee variance).
2. **Two PIV feature tiers.** This recovers 2025/26 and nine more leagues at honest, lower reliability, using data we already hold, so it's no new scope risk.
3. **Market-level normalisation** of targets, because the probe showed 26–35% drift bias.
4. **Group-wise conformal intervals plus rule-based reliability tiers**, instead of a single global interval.
5. **Percentile bars over radar charts** as the primary profile view.
6. **Deterministic template rationales** instead of LLM text in the MVP (consistent with deferring the AI Analyst).
7. **Blue/amber diverging palette**, with no red/green value judgements.
8. **Read-only public database, no auth**; batch ML only.
