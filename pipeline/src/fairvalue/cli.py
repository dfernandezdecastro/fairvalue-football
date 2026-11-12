"""Command line: `fairvalue <command>`.

fetch-understat   rebuild the Understat archive cache (network, slow, polite)
stage             verify raw sources and build data/staging/
check             reconcile staging with the published feasibility numbers
quality           write reports/staging/data_quality.md
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fairvalue", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    parser.add_argument("command", choices=["fetch-understat", "stage", "check", "quality"])
    args = parser.parse_args(argv)

    if args.command == "fetch-understat":
        from fairvalue.ingest.understat_archive import fetch_cache

        fetch_cache()
        return 0
    if args.command == "stage":
        from fairvalue.staging.build import run

        run()
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
