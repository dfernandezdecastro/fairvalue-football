"""Read/write pipeline tables through their contracts (schema-on-write and on-read)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fairvalue.config import DATA_DIR
from fairvalue.ingest.schemas import FEATURES, STAGING, enforce

LAYERS = {"staging": STAGING, "features": FEATURES}


def _path(layer: str, name: str, base: Path) -> Path:
    return base / layer / f"{name}.csv.gz"


def write_table(df: pd.DataFrame, layer: str, name: str, base: Path = DATA_DIR) -> int:
    path = _path(layer, name, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    checked = enforce(df, LAYERS[layer][name], f"{layer}.{name}")
    checked.to_csv(path, index=False, date_format="%Y-%m-%d")
    return len(checked)


def read_table(layer: str, name: str, base: Path = DATA_DIR) -> pd.DataFrame:
    path = _path(layer, name, base)
    if not path.exists():
        cmd = "stage" if layer == "staging" else "features"
        raise FileNotFoundError(f"{path} missing. Run: fairvalue {cmd}")
    return enforce(pd.read_csv(path, low_memory=False), LAYERS[layer][name], f"{layer}.{name}")
