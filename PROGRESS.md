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

### Next
- Step 2 Staging pipeline: ingest + validation of frozen sources, ID matching moved into `fairvalue.staging`, staging parquet that reproduces the feasibility numbers.

### Known limitations to carry forward
- No contract length at transfer; caps, position and contract fields are current snapshots (leakage risk).
- No defensive or GK metrics; Understat season-level only; 2025/26 Understat missing.
- Fee drift across market cycles needs an explicit market index.
