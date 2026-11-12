"""Integration check on the real staging output. Skipped where data is absent (e.g. CI)."""

import pytest

from fairvalue.config import STAGING_DIR

pytestmark = pytest.mark.skipif(
    not (STAGING_DIR / "manifest.json").exists(), reason="local data only: run `fairvalue stage` first"
)


def test_staging_reproduces_published_numbers():
    from fairvalue.staging.checks import run_checks

    failed = [c for c in run_checks() if not c.ok]
    assert not failed, failed
