"""Command line: `fairvalue <command>`.

fetch-understat   rebuild the Understat archive cache (network, slow, polite)
stage             verify raw sources and build data/staging/
check             reconcile staging with the published feasibility numbers
quality           write reports/staging/data_quality.md
features          build as-of features and performance profiles from staging
train-piv         walk-forward train, evaluate and publish the performance-implied value model
train-fee         expected fee model, club audit and hidden gems backtest (after train-piv)
publish           build the published tables and print their sizes (no database needed)
db-load           apply migrations and load published tables into Supabase (needs .env)
db-check          verify anonymous visitors can read but not write (needs .env)
gen-types         write web/lib/db/types.ts from the live schema (needs .env)
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fairvalue", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    parser.add_argument(
        "command",
        choices=[
            "fetch-understat",
            "stage",
            "check",
            "quality",
            "features",
            "train-piv",
            "train-fee",
            "publish",
            "db-load",
            "db-check",
            "gen-types",
        ],
    )
    args = parser.parse_args(argv)

    if args.command == "fetch-understat":
        from fairvalue.ingest.understat_archive import fetch_cache

        fetch_cache()
        return 0
    if args.command == "stage":
        from fairvalue.staging.build import run

        run()
        return 0

    if args.command == "publish":
        from fairvalue.export.publish import build_tables, summary

        s = summary(build_tables())
        print(s.to_string())
        print(f"total {s.csv_mb.sum():.1f} MB as CSV")
        return 0
    if args.command == "db-load":
        from fairvalue.export.load import run_load

        run_load()
        return 0
    if args.command == "db-check":
        from fairvalue.export.load import check_public_access

        return 0 if check_public_access() else 1
    if args.command == "gen-types":
        from fairvalue.export.load import gen_types

        gen_types()
        return 0

    if args.command == "train-fee":
        from fairvalue.models.fee_run import run as run_fee

        run_fee()
        return 0

    if args.command == "train-piv":
        from fairvalue.models.piv import run as run_piv

        run_piv()
        return 0

    if args.command == "features":
        from fairvalue.features.build import run as run_features

        run_features()
        return 0

    if args.command == "quality":
        from fairvalue.staging.quality import write_report

        print(write_report())
        return 0

    from fairvalue.staging.checks import run_checks

    results = run_checks()
    width = max(len(c.name) for c in results)
    for c in results:
        status = "OK  " if c.ok else "FAIL"
        print(f"{status}  {c.name:<{width}}  expected {c.expected:>10}  actual {c.actual:>10}")
    return 0 if all(c.ok for c in results) else 1


if __name__ == "__main__":
    sys.exit(main())
