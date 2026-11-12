from datetime import date

import pytest

from fairvalue.calendar import last_completed_season, season_label, season_of, window_of


@pytest.mark.parametrize(
    "d, expected",
    [
        (date(2024, 7, 1), 2024),  # first day of a new season
        (date(2024, 6, 30), 2023),  # last day of the previous one
        (date(2025, 1, 31), 2024),  # winter window belongs to the running season
        (date(2020, 7, 26), 2020),  # calendar rule; fixtures must use official season
    ],
)
def test_season_of(d, expected):
    assert season_of(d) == expected


def test_season_label():
    assert season_label(2024) == "2024/25"
    assert season_label(1999) == "1999/00"


@pytest.mark.parametrize(
    "d, expected",
    [
        (date(2023, 8, 31), "summer"),
        (date(2024, 1, 15), "winter"),
        (date(2023, 12, 1), "winter"),
        (date(2024, 3, 10), "other"),
    ],
)
def test_window_of(d, expected):
    assert window_of(d) == expected


def test_last_completed_season_never_includes_running_season():
    # A January 2026 transfer may only use 2024/25 season totals.
    assert last_completed_season(date(2026, 1, 15)) == 2024
    # A summer 2025 transfer may use the just-finished 2024/25 season.
    assert last_completed_season(date(2025, 7, 10)) == 2024
