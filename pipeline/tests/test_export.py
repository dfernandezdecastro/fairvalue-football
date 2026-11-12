import re

import numpy as np
import pandas as pd
import pytest

from fairvalue.export import contracts, load, publish
from fairvalue.ingest.schemas import enforce

SQL = "\n".join(p.read_text(encoding="utf-8") for p in sorted(load.MIGRATIONS.glob("*.sql")))


def _table_block(name: str) -> str:
    m = re.search(rf"create table {name} \((.*?)\n\);", SQL, re.S)
    assert m, f"table {name} missing from migrations"
    return m.group(1)


@pytest.mark.parametrize("table", list(contracts.PUBLISH))
def test_every_contract_column_exists_in_the_migration(table):
    block = _table_block(table)
    for col in contracts.PUBLISH[table]:
        assert re.search(rf"(^|[\s,(]){re.escape(col)}\s", block), f"{table}.{col} not in SQL"


def test_load_order_covers_every_table_and_rls_is_enabled_for_each():
    assert set(contracts.LOAD_ORDER) == set(contracts.PUBLISH)
    for t in contracts.LOAD_ORDER:
        assert f"'{t}'" in SQL  # listed in the RLS loop


def test_licensing_guard_blocks_forbidden_columns():
    with pytest.raises(publish.LicensingError, match="date_of_birth"):
        publish.check_licensing({"players": pd.DataFrame({"id": [1], "date_of_birth": ["1990-01-01"]})})


def test_no_contract_publishes_forbidden_columns():
    for table, schema in contracts.PUBLISH.items():
        assert not contracts.FORBIDDEN_COLUMNS & set(schema), table


def _minimal_tables():
    t = {name: pd.DataFrame(columns=list(schema)) for name, schema in contracts.PUBLISH.items()}
    t["competitions"] = pd.DataFrame({"id": ["GB1"]})
    t["clubs"] = pd.DataFrame({"id": [10]})
    t["players"] = pd.DataFrame({"id": [1]})
    t["player_seasons"] = pd.DataFrame({"player_id": [1], "season": [2024], "competition_id": ["GB1"], "club_id": [10]})
    return t


def test_referential_integrity_passes_and_fails():
    t = _minimal_tables()
    publish.check_referential_integrity(t)
    t["transfers"] = pd.DataFrame({"player_id": [999], "from_club_id": [10], "to_club_id": [10]})
    with pytest.raises(ValueError, match="transfers.player_id"):
        publish.check_referential_integrity(t)


def test_csv_encodes_missing_values_as_null():
    df = enforce(
        pd.DataFrame({"a": [1, None], "b": [1.5, np.nan], "c": ["x", None], "d": [True, False]}),
        {"a": "Int", "b": "float", "c": "str", "d": "bool"},
        "t",
    )
    assert load._csv(df).splitlines() == ["1,1.5,x,True", ",,,False"]  # empty unquoted field = NULL


def test_load_env_and_placeholder_detection(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comment\nSUPABASE_URL=https://abc.supabase.co\nSUPABASE_DB_URL='postgresql://YOUR-PASSWORD'\n")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    load.load_env(env)
    import os

    assert os.environ["SUPABASE_URL"] == "https://abc.supabase.co"
    monkeypatch.setattr(load, "load_env", lambda path=None: None)
    with pytest.raises(SystemExit, match="SUPABASE_DB_URL is not set"):
        load.require("SUPABASE_DB_URL")  # still the template placeholder


def test_primary_key_check_catches_duplicates():
    t = _minimal_tables()
    publish.check_primary_keys(t)
    t["club_audit"] = pd.DataFrame({"club_id": [7, 7], "period": ["all", "all"]})
    with pytest.raises(ValueError, match="club_audit"):
        publish.check_primary_keys(t)


def test_every_table_has_a_primary_key_matching_the_sql():
    assert set(contracts.PRIMARY_KEYS) == set(contracts.PUBLISH)
    for table, cols in contracts.PRIMARY_KEYS.items():
        block = _table_block(table)
        if len(cols) == 1:
            assert re.search(rf"\b{cols[0]}\s+\w+.*primary key", block), table
        else:
            assert f"primary key ({', '.join(cols)})" in block, table


@pytest.mark.parametrize(
    "value", ["https://abc.supabase.co", "https://abc.supabase.co/", "https://abc.supabase.co/rest/v1/"]
)
def test_project_url_normalised(monkeypatch, value):
    monkeypatch.setattr(load, "require", lambda name: value)
    assert load.project_url() == "https://abc.supabase.co"
