# FairValue Football: Progress Log

## Status: Phase 1 (discovery). Data feasibility study done; awaiting approval of the revised plan.

### 2026-11-12: Project proposal
- Proposal delivered in chat (13 sections). Not yet approved.

### 2026-11-12: Data feasibility study
- Downloaded transfermarkt-datasets (snapshot to 6 Jul 2026; upstream updates paused).
- Found understat.com offline (since ~2 Nov 2026); recovered 45/55 big-five league-seasons 2014/15–2024/25 from the Wayback Machine.
- TM↔Understat matching: 98.1% match rate, ~0.2% estimated error.
- Usable transfers: 1,792 (xG-level) / 4,892 (basic stats). Market-value panel: ~11k player-seasons.
- Probe models: performance-only fee R² 0.56 (log), median error 47%; with market value R² 0.77, median error 32%.
- Recommendation: **CONDITIONAL GO** with a three-layer target design (performance profile, performance-implied market value, expected fee). See `reports/feasibility/FEASIBILITY_REPORT.md`.
- Deliverables: `reports/feasibility/*`, `DATA_SOURCES.md`, `data/sample/sample_100_transfers.csv`, `scripts/feasibility/*`.

### 2026-11-12: Revised plan approved; product spec written
- User approved the three-layer design and the revised MVP, and set rules R1–R5 (language, leakage, uncertainty, scope, licensing). AI Analyst deferred.
- Final spec: `docs/PRODUCT_SPEC.md` (pages, UX, design system, data flow, models, schema, 9-step delivery plan).

### 2026-11-12: Step 1 Foundation done (spec approved)
- Git repo (`main`), monorepo: `pipeline/` (Python package `fairvalue`), `web/` (Next.js 16.4, React 19, Tailwind v4, shadcn/ui), `supabase/`, `docs/`.
- `fairvalue.asof` (leakage guards: `rows_before`, `assert_no_future_rows`, snapshot-field blocklist) and `fairvalue.calendar`; 14 passing tests.
- Dark-first web shell with data-vintage pill and attribution footer; lint, typecheck and build pass.
- CI workflow (`.github/workflows/ci.yml`): ruff + pytest; lint + typecheck + build.
- Verified: no raw data tracked by Git.
- **Pending (user):** create a private GitHub repo and push. The GitHub CLI isn't installed, so this is a manual step. CI hasn't run on GitHub yet.

### 2026-11-12: Step 2 Staging pipeline done
- `fairvalue.ingest`: data contracts (`schemas.py`, enforced on every read and write); sha256-verified sources; Transfermarkt read straight from the snapshot zip; Understat parsed offline from the archive cache (`fetch-understat` rebuilds it).
- Snapshot-only fields (caps, contract expiry, current club, latest MV, agent) are excluded at ingest, so they can never reach a model.
- `fairvalue.staging`: 12 staging tables in `data/staging/*.csv.gz` + `manifest.json` (≈40 s build). CSV with schema-on-read because Windows Smart App Control blocks pyarrow's DLL.
- ID matching ported unchanged: 98.1% match rate, 7,819 players mapped.
- **Correction found:** the feasibility loan rule depended on the arbitrary order of same-day rows and excluded 11 "buy and loan back" transfers. Fixed (the return must be on a later date) and tested. F1 15,405 → 15,416, F2 5,630 → 5,637; erratum added to the feasibility report.
- CLI: `fairvalue stage | check | quality | fetch-understat`. `check` reconciles 7 published numbers (all OK). `reports/staging/data_quality.md` generated.
- Tests: 46 unit tests (synthetic fixtures, run in CI) + 1 local-data reconciliation test (skipped in CI).
- `.gitignore` now ignores everything under `data/` except `data/sample/README.md`.

- Remote fixed (github.com/dfernandezdecastro/fairvalue-football, private) and pushed. CI first failed (Next.js route types not generated before `tsc`); fixed with `next typegen`; CI green.

### 2026-11-12: Step 3 As-of features + Layer 1 profiles done
- `fairvalue features` (≈30 s) writes `data/features/`: player_season_features (92,958 rows, as of each league's season end), transfer_features (15,794 paid transfers, as of the transfer date, with funnel flags), profiles (per-90, shrunk per-90, percentiles, peer_n), similar_players (top 20), shrinkage_priors; plus `reports/features/feature_summary.md`.
- Leakage guards: strictly-before market values and form windows; season-level stats only from seasons finished before the transfer (COVID guard, 140 transfers); build-time `assert_point_in_time`; "future spike" tests.
- Usable sets: **1,794 full tier / 4,893 basic tier**. Every difference from the feasibility numbers is explained (loan fix +1/+1; COVID guard +6/−5). Added to `fairvalue check` (10/10 OK).
- Shrinkage fix during development: xG metrics were over-shrunk by the Poisson assumption; they now borrow k from their underlying counts (decision D6).
- Sanity checks: Haaland/Kane 99–100th percentile npxG; Saka's nearest profiles are Son, Foden, Palmer, Salah.
- Tests: 64 (synthetic fixtures). Decision log started: `docs/DECISIONS.md` (D1–D6).

### 2026-11-12: Step 4 Performance-implied value model trained
- `fairvalue train-piv` (≈4.5 min): two tiers (full: xG-level big five 2014–2024; basic: 14 leagues 2012–2025) × Ridge vs gradient boosting, walk-forward by season with inner hyperparameter selection on season s−1, group-wise split-conformal intervals (previous 3 seasons), reliability tiers, gap labels, SHAP driver groups. Outputs: `data/outputs/piv_predictions.csv.gz`, `piv_run.json`; model card `reports/models/piv_model_card.md`.
- Two drift problems found and fixed (D8 same-market re-centring; D9 league market level). Final walk-forward results:
  - Full tier (gradient boosting): MAE(log) 0.404, R² 0.82, median error 32%, 71% within ±50%; 80% coverage 80.9%.
  - Basic tier (gradient boosting): MAE(log) 0.419, R² 0.87, median error 34%, 67% within ±50%; 80% coverage 78.9%.
  - Naive baseline: median error 67% (full) / 85% (basic).
- Sanity: Yamal MV €200M vs PIV €205M; Mbappé €180M vs €171M; Kane €75M vs €79M; all within range.
- League-season shocks inflated gap labels (27% of LaLiga 2024/25 flagged). **User chose peer-relative gaps** (D11): gaps vs same-league peers in the same summer, with league-specific interval widths. Peer-relative 80% coverage 81.8% (full) / 80.3% (basic); per league 78.6–83.4% inside across all seasons, except Scotland 72.8% (flagged). Published output keeps both the whole-market and the peer-relative views.
- Known caveat surfaced: top 2024/25 flags include Athletic Club players (Basque-only policy, rarely sold); added to the model card as an example of unobserved club conventions.
- Tests: 84 (incl. leakage canary, conformal coverage, SHAP additivity, re-centring). Ruff line length raised to 120.

### 2026-11-12: Step 5 Expected Fee, club audit, Hidden Gems backtest done
- `fairvalue train-fee` (≈1 min, after train-piv): `data/outputs/fee_predictions.csv.gz` (12,520 assessed of 14,516 paid transfers with a fresh market value), `club_audit.csv.gz`, `fee_run.json`; reports `reports/models/expected_fee_model_card.md` and `hidden_gems_backtest.md`.
- Expected Fee: Ridge (boosting 4.4% better, below the 5% bar). Typical error 44% vs 50% for "fee = market value"; 80% coverage 81.5%, ranges ×9 wide.
- Club audit with bootstrap ranges; highest big-five ratios Athletic Club, Ipswich, Newcastle; largest unusual premiums are the 2023 Saudi moves.
- Backtest: potential undervaluation +7.9% vs peers over 12 months (80% CI 6.5–11.1), strong signal +13.9%, market premium −3.8%; consistent in all 10 seasons.
- Decisions D12–D14. Tests: 100 passing (13 new for Step 5).

### 2026-11-12: Step 6 database code ready (load pending)
- `supabase/migrations/20261112000001_init.sql`: 11 tables, 3 views (security_invoker), trigram search index, RLS read-only policies, R3 check constraints (no estimate without its range).
- `fairvalue publish | db-load | db-check | gen-types`: published tables built with contracts, licensing guard and referential checks (D15); single-transaction load; anonymous read/write verification; TS types from the live schema.
- Setup guide `docs/SUPABASE_SETUP.md`; `.env.example` and `web/.env.example` (secrets git-ignored).
- Loaded into Supabase (EU, Paris): 11 tables, 122 MB of the 500 MB free tier, row counts verified in the load transaction.
- `db-check` passes as an anonymous visitor: reads 200; insert refused (401); delete removed nothing.
- Fixes during setup: club audit grouped by club id (74 clubs with 2+ spellings); primary-key checks before loading; db-check no longer mistakes a rejected key's 401s for "writes refused"; project URL normalised when it includes /rest/v1.
- `web/lib/db/types.ts` generated from the live schema. Tests: 123.

### 2026-11-13: Step 7 Design system and app shell done
- Tokens for dark (default) and light themes: neutral palette, violet brand, blue discount / amber premium (never red/green), five-step chart palette; theme toggle persists without a flash.
- Domain components (`web/components/domain/`): EstimateRange (log-scale dot-and-range with 80/95% bands), GapLabel and ReliabilityBadge (tooltips, wording from `lib/vocabulary.ts`), PercentileBar, DriversList, InsufficientData, DataTierPill, Stat, SourceFootnote. Formatters in `lib/format.ts`.
- Shell: sticky header with nav, data-vintage pill, ⌘K search (players and clubs, accent-insensitive via migration 2), footer with attribution; global loading skeleton, error boundary, not-found. Nav routes are clearly marked "being built" until Step 8.
- Server-only REST client with request-time rendering and a 24 h cache; data streamed behind Suspense (D16). `npm run lint:vocab` added to CI.
- Component review page: `/design` (real database rows; noindex). Verified in browser: dark and light, mobile 375 px, search ("mbappe" → both Mbappés). Production build passes without credentials.

### 2026-11-13: Step 8 Core pages done
- Player Intelligence (`/players/[slug]`): season switcher, valuation vs peer range or an "insufficient" panel, SHAP drivers, percentile profile vs position peers, valuation-history chart (vintage bands), paid transfers, similar profiles, data & coverage.
- Players explorer (`/players`), Transfer Intelligence (`/transfers` with rankings tabs, `/transfers/[id]` with before/after and the outcome kept separate), Hidden Gems (`/hidden-gems`: filters including percentile conditions, template rationales, cheaper-alternatives mode, backtest banner), Clubs (`/clubs` rankings with bootstrap ranges, `/clubs/[slug]` with fee-vs-expected scatter and recruitment patterns), Overview (`/`), Methodology (`/methodology` with live model numbers, coverage grid, leakage policy, backtest by season, glossary, limitations).
- All filters live in the URL; all pages stream behind Suspense; production build passes without credentials.
- Fixes: club rankings limited to covered-league clubs (reserve teams were topping the list); premium rankings by euros; market-cycle series added to app_meta (D17).
- Verified via HTTP (the browser pane was hidden after the restart): every route returns 200 with the expected content. A visual pass in the browser is still to do.

### 2026-11-13: Step 9 Polish and deployment prep
- Visual pass on every page (dark and light, desktop and 375 px): no horizontal overflow on any route. Fixes: nice log-axis ticks, incomplete 2026/27 window excluded from the overview, rationales list only genuine strengths (>= 60th percentile), header pill.
- Accessibility: WCAG contrast measured for every token pair in both themes; light-theme amber darkened to pass AA (3.5:1 to 5.5:1); skip-to-content link; labelled form fields, aria-labels on charts.
- Performance (production build): pages complete in <= 0.2 s locally; static shells stream data.
- Icon, robots rules (/design and /api excluded), Open Graph metadata.
- Portfolio README with results and architecture; `docs/CASE_STUDIES.md` (Mitrović premium, Athletic Club convention, Hidden Gems hits and misses); `docs/DEPLOY.md`.
- **Deployed (2026-11-13):** https://fairvalue-football.vercel.app (Vercel Hobby, root directory `web`, two public read-only env vars). The first deploy lacked the env vars (pages showed the "not configured" state); fixed by adding them and redeploying. Live check: all 8 main routes return 200 with real data (~0.8–1.9 s cold), search works ("mbappe" finds both), robots and icon served.

## Status: MVP complete (Steps 1–9).

### After the MVP
- AI Football Analyst (deferred by decision), player comparison page, scheduled data refresh if a licensed source becomes available.

### Known limitations to carry forward
- No contract length at transfer; caps, position and contract fields are current snapshots (leakage risk).
- No defensive or GK metrics; Understat season-level only; 2025/26 Understat missing.
- Fee drift across market cycles needs an explicit market index.
