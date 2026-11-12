"""Read Transfermarkt tables straight from the verified snapshot zip."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from fairvalue.ingest.schemas import TM_RAW, enforce
from fairvalue.ingest.sources import TM_ZIP


def read_table(name: str, zip_path: Path = TM_ZIP) -> pd.DataFrame:
    """Load one table (e.g. 'transfers') with its contract applied.

    Only contract columns are parsed (usecols), which keeps memory low for
    the ~1.9M-row appearances table.
    """
    schema = TM_RAW[name]
    with zipfile.ZipFile(zip_path) as z:
        raw = z.read(f"{name}.csv.gz")
    df = pd.read_csv(io.BytesIO(raw), compression="gzip", usecols=list(schema), low_memory=False)
    return enforce(df, schema, f"tm.{name}")
