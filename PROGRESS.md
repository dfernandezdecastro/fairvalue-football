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

### Decisions pending (user)
- Approve `docs/PRODUCT_SPEC.md` before any application code.

### Next (if approved)
- Step 1 Foundation: Git + private GitHub repo, monorepo layout, Python package skeleton, Next.js skeleton, CI.

### Known limitations to carry forward
- No contract length at transfer; caps, position and contract fields are current snapshots (leakage risk).
- No defensive or GK metrics; Understat season-level only; 2025/26 Understat missing.
- Fee drift across market cycles needs an explicit market index.
