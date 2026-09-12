from datetime import date

import pandas as pd

from srag.utils.epi_weeks import format_epi_week, get_date_from_epi_week, get_epi_week


def test_get_epi_week_standard() -> None:
    # April 10, 2024 (Wednesday) -> SE 15 of 2024
    assert get_epi_week(date(2024, 4, 10)) == (2024, 15)


def test_get_epi_week_sunday() -> None:
    # April 7, 2024 (Sunday) -> Start of SE 15
    assert get_epi_week(date(2024, 4, 7)) == (2024, 15)


def test_get_epi_week_saturday() -> None:
    # April 13, 2024 (Saturday) -> End of SE 15
    assert get_epi_week(date(2024, 4, 13)) == (2024, 15)


def test_get_epi_week_year_transition() -> None:
    # Jan 1, 2024 (Monday) -> Should belong to SE 1 of 2024
    # since Jan 4 is in the same week.
    assert get_epi_week(date(2024, 1, 1)) == (2024, 1)


def test_get_epi_week_previous_year() -> None:
    # Jan 1, 2022 was Saturday -> SE 52 of 2021
    assert get_epi_week(date(2022, 1, 1)) == (2021, 52)


def test_get_epi_week_none() -> None:
    assert get_epi_week(None) == (0, 0)


def test_get_epi_week_pd_nat() -> None:
    assert get_epi_week(pd.NaT) == (0, 0)


def test_get_epi_week_invalid_string() -> None:
    assert get_epi_week("invalid date") == (0, 0)
    assert get_epi_week("") == (0, 0)


def test_get_epi_week_string() -> None:
    assert get_epi_week("2024-04-10") == (2024, 15)


def test_get_epi_week_pd_timestamp() -> None:
    assert get_epi_week(pd.Timestamp("2024-04-10")) == (2024, 15)


def test_get_epi_week_all_days_of_week() -> None:
    # SE 15 of 2024 starts on April 7 (Sunday) and ends on April 13 (Saturday)
    expected = (2024, 15)
    for day in range(7, 14):
        dt = date(2024, 4, day)
        assert get_epi_week(dt) == expected, f"Failed for {dt} (weekday {dt.weekday()})"


def test_get_epi_week_exception_path() -> None:
    # Mutmut mutant 7: change return 0, 0 to 1, 0 in except block
    # We need to trigger a TypeError or ValueError in the first try block
    # pd.isna(object()) might work or passing a list
    assert get_epi_week([1, 2, 3]) == (0, 0)


def test_format_epi_week() -> None:
    assert format_epi_week(2024, 5) == "2024-05"
    assert format_epi_week(2024, 15) == "2024-15"


def test_format_epi_week_zero() -> None:
    assert format_epi_week(0, 0) == "N/A"
    assert format_epi_week(0, 1) == "N/A"


def test_get_date_from_epi_week() -> None:
    assert get_date_from_epi_week(2024, 15) == date(2024, 4, 7)
    assert get_date_from_epi_week(2024, 1) == date(2023, 12, 31)


def test_get_date_from_epi_week_zero() -> None:
    assert get_date_from_epi_week(0, 0) == date(1900, 1, 1)
    assert get_date_from_epi_week(0, 15) == date(1900, 1, 1)
