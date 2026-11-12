# FairValue Football

Transfer-market intelligence for European football. It shows how market values and transfer fees compare with what measurable performance and context usually command, **with the uncertainty shown**.

> Non-commercial research and portfolio project. Data is a frozen snapshot: Transfermarkt (via the community transfermarkt-datasets project) to 6 Jul 2026, Understat to 2024/25. See [DATA_SOURCES.md](DATA_SOURCES.md). Raw data is never committed.

## Repository

| Path | What |
|---|---|
| `pipeline/` | Python package `fairvalue`: ingest → staging → as-of features → models → exports (offline, batch) |
| `web/` | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui application (read-only) |
| `supabase/` | Database migrations and row-level security policies |
| `docs/` | [Product specification](docs/PRODUCT_SPEC.md), model cards, decision records |
| `reports/` | Feasibility study and model evaluation outputs |
| `scripts/feasibility/` | The original data-feasibility study (kept for provenance) |
| `data/` | Local only, git-ignored (third-party data) |

## Getting started

```bash
# Python pipeline
python -m venv .venv
.venv/Scripts/python -m pip install -e "pipeline[dev]"     # macOS/Linux: .venv/bin/python
cd pipeline && ../.venv/Scripts/python -m pytest

# Data pipeline (needs the local raw snapshot, see DATA_SOURCES.md)
.venv/Scripts/fairvalue stage      # verify checksums, build data/staging/
.venv/Scripts/fairvalue check      # reconcile with published feasibility numbers
.venv/Scripts/fairvalue quality    # write reports/staging/data_quality.md
.venv/Scripts/fairvalue features   # as-of features + performance profiles -> data/features/
.venv/Scripts/fairvalue train-piv  # walk-forward valuation model -> data/outputs/ + model card

# Web app
cd web && npm install && npm run dev                       # http://localhost:3000
```

## Project status

See [PROGRESS.md](PROGRESS.md).
