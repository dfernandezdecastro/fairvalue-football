import numpy as np
import pandas as pd
import pytest

from fairvalue.ingest.schemas import STAGING, TM_RAW, SchemaError, enforce


def test_enforce_casts_and_drops_undeclared_columns():
    df = pd.DataFrame({"a": ["1", "2"], "b": ["2024-01-01", "2024-02-01"], "junk": [0, 0]})
    out = enforce(df, {"a": "int", "b": "date"}, "t")
    assert list(out.columns) == ["a", "b"]
    assert out.a.dtype == "int64" and str(out.b.dtype).startswith("datetime64")


def test_missing_column_raises():
    with pytest.raises(SchemaError, match="missing column"):
        enforce(pd.DataFrame({"a": [1]}), {"a": "int", "b": "str"}, "t")


def test_null_in_non_null_int_raises():
    with pytest.raises(SchemaError, match="nulls"):
        enforce(pd.DataFrame({"a": [1, None]}), {"a": "int"}, "t")


def test_bad_value_raises():
    with pytest.raises(SchemaError, match="cannot cast"):
        enforce(pd.DataFrame({"a": ["x"]}), {"a": "float"}, "t")


def test_nullable_int_and_str_keep_missing():
    out = enforce(pd.DataFrame({"a": [1, None], "s": ["x", np.nan]}), {"a": "Int", "s": "str"}, "t")
    assert out.a.isna().tolist() == [False, True]
    assert out.s.isna().tolist() == [False, True]


def test_bool_from_csv_strings():
    out = enforce(pd.DataFrame({"f": ["True", "False"]}), {"f": "bool"}, "t")
    assert out.f.tolist() == [True, False]


@pytest.mark.parametrize("field", ["international_caps", "contract_expiration_date", "current_club_id"])
def test_snapshot_fields_never_enter_contracts(field):
    for schema in [*TM_RAW.values(), *STAGING.values()]:
        assert field not in schema
