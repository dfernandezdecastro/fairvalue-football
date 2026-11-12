"""Frozen raw sources: where they live and how we recognise them.

The data is a fixed snapshot (see DATA_SOURCES.md). Recording checksums makes
every pipeline run provably use the same inputs; if a file is replaced, the
pipeline stops instead of silently producing different numbers.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from fairvalue.config import RAW_DIR

TM_ZIP = RAW_DIR / "transfermarkt" / "transfermarkt-datasets.zip"
TM_ZIP_URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.zip"
TM_ZIP_SHA256 = "ae2270f7820e09329c423a12562f4494e237d0dc1a4624cff21df050e79d5a18"

UNDERSTAT_CACHE = RAW_DIR / "understat_wayback" / "html"
# sha256 over the bytes of all cached pages, concatenated in sorted filename order
UNDERSTAT_CACHE_SHA256 = "14ac86022982201c95a9ebca093fac39ab52026b2cc3f48ee5cb91b620f72f72"
UNDERSTAT_EXPECTED_PAGES = 45


class SourceError(RuntimeError):
    """A raw source is missing or is not the expected snapshot."""


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def sha256_files(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda p: p.name):
        h.update(p.read_bytes())
    return h.hexdigest()


def verify_transfermarkt(path: Path = TM_ZIP) -> None:
    if not path.exists():
        raise SourceError(f"Transfermarkt snapshot not found at {path}. Download it from {TM_ZIP_URL}")
    got = sha256_file(path)
    if got != TM_ZIP_SHA256:
        raise SourceError(f"{path.name} checksum {got[:12]}... != expected {TM_ZIP_SHA256[:12]}...")


def verify_understat_cache(cache: Path = UNDERSTAT_CACHE) -> list[Path]:
    pages = sorted(cache.glob("*.html"))
    if len(pages) != UNDERSTAT_EXPECTED_PAGES:
        raise SourceError(
            f"Understat cache has {len(pages)} pages, expected {UNDERSTAT_EXPECTED_PAGES}. "
            "Rebuild it with: fairvalue fetch-understat"
        )
    got = sha256_files(pages)
    if got != UNDERSTAT_CACHE_SHA256:
        raise SourceError(f"Understat cache checksum {got[:12]}... does not match the recorded snapshot")
    return pages
