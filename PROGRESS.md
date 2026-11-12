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

### Pending (user)
- Fix the Git remote: it contains the literal placeholder `<your-username>`. Then push.

### Next
- Step 3: as-of feature builder (player-season and transfer features), Layer 1 performance profiles (shrinkage, percentiles, similarity), leakage tests; reproduce the usable-set counts (feasibility 1,792 / 4,892, expected to rise slightly after the loan correction).

### Known limitations to carry forward
- No contract length at transfer; caps, position and contract fields are current snapshots (leakage risk).
- No defensive or GK metrics; Understat season-level only; 2025/26 Understat missing.
- Fee drift across market cycles needs an explicit market index.
