from datetime import date

import pandas as pd
import pytest

from fairvalue.asof import (
    LeakageError,
    assert_no_future_rows,
    assert_no_snapshot_fields,
    rows_before,
)


@pytest.fixture
def valuations():
    return pd.DataFrame(
        {
            "player_id": [1, 1, 1, 1],
            "date": ["2024-01-10", "2024-06-01", "2024-07-15", "2025-01-01"],
            "value": [10, 12, 30, 35],
        }
    )


def test_rows_before_excludes_same_day_and_future(valuations):
    out = rows_before(valuations, "date", date(2024, 7, 15))
    assert list(out.value) == [10, 12]


def test_future_spike_does_not_change_filtered_rows(valuations):
    # Inject an absurd value after as_of: the as-of view must be identical.
    spiked = pd.concat(
        [valuations, pd.DataFrame({"player_id": [1], "date": ["2024-08-01"], "value": [10_000]})]
    )
    as_of = date(2024, 7, 1)
    pd.testing.assert_frame_equal(rows_before(valuations, "date", as_of), rows_before(spiked, "date", as_of))


def test_assert_no_future_rows_raises(valuations):
    with pytest.raises(LeakageError, match="2 row"):
        assert_no_future_rows(valuations, "date", date(2024, 7, 15))
    assert_no_future_rows(valuations, "date", date(2025, 1, 2))  # no error


def test_snapshot_fields_blocked():
    with pytest.raises(LeakageError, match="international_caps"):
        assert_no_snapshot_fields(["age", "international_caps"])
    assert_no_snapshot_fields(["age", "minutes", "npxg_p90"])  # no error
