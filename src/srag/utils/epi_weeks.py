"""Utilities for epidemiological week (SE) calculations."""

from datetime import date, timedelta

import numpy as np
import pandas as pd


def get_epi_week(dt: object) -> tuple[int, int]:
    """Calculate the epidemiological week (SE) and year for a given date.

    In Brazil, SE follows the international standard (Sunday to Saturday),
    but with specific rules for the first week of the year (SE 1 must have
    at least 4 days of the new year).

    Compatible with Python date/datetime and Pandas Timestamps.

    Args:
        dt: The date to calculate for.

    Returns:
        A tuple (year, week_number).
    """
    if dt is None:
        return 0, 0
    try:
        if pd.isna(dt):  # type: ignore
            return 0, 0
    except TypeError, ValueError:
        return 0, 0

    # Ensure we have a datetime.date object
    try:
        date_attr = getattr(dt, "date", None)
        if date_attr and callable(date_attr):
            dt = date_attr()
        elif isinstance(dt, str):
            dt_converted = pd.to_datetime(dt)
            dt = getattr(dt_converted, "date", lambda: None)()
    except TypeError, ValueError, AttributeError, Exception:
        return 0, 0

    if dt is None or pd.isna(dt):  # type: ignore
        return 0, 0

    if not isinstance(dt, date):
        return 0, 0

    # The first SE of the year is the one that contains the first Wednesday
    # of the year (or the one with at least 4 days in January).
    # This is equivalent to the ISO week standard but starting on Sunday.

    # Adjust date to the previous Sunday (start of the week)
    idx = (dt.weekday() + 1) % 7  # Sunday=0, Monday=1, ..., Saturday=6
    sun = dt - timedelta(days=idx)

    # Use the Wednesday of that week to determine the year of the SE
    wed = sun + timedelta(days=3)
    year = wed.year

    # Find the first Sunday of the year's first SE
    # First SE of year 'year' starts on the Sunday of the week containing Jan 4th
    jan4 = date(year, 1, 4)
    first_sun = jan4 - timedelta(days=(jan4.weekday() + 1) % 7)

    week_num = int((sun - first_sun).days / 7) + 1

    # Handle edge case: if week_num is 0, it belongs to the last week of previous year
    if week_num <= 0:
        # Belong to the last week of the previous year
        return get_epi_week(sun - timedelta(days=1))

    return year, week_num


def format_epi_week(year: int, week: int) -> str:
    """Format SE as YYYY-WW string."""
    if year == 0:
        return "N/A"
    return f"{year}-{week:02d}"


def get_date_from_epi_week(year: int, week: int) -> date:
    """Return the start date (Sunday) of a given epidemiological week.

    Inverse of `get_epi_week`.
    """
    if year == 0:
        return date(1900, 1, 1)
    # The first SE of the year is the week containing Jan 4th
    jan4 = date(year, 1, 4)
    first_sun = jan4 - timedelta(days=(jan4.weekday() + 1) % 7)

    return first_sun + timedelta(weeks=week - 1)


def compute_epi_week_columns(
    dates: pd.Series,
) -> pd.DataFrame:
    """Vectorized computation of epidemiological week columns.

    Given a Series of dates, returns a DataFrame with:
      _epi_week      — formatted string "YYYY-WW" (or "N/A")
      _epi_year      — integer year of the epi week (or 0)
      _epi_week_int  — integer week number (or 0)

    Fully vectorized using the .dt accessor — no row-wise .apply.
    """
    s = pd.to_datetime(dates, errors="coerce")
    nan_mask = s.isna()

    # offset so Sunday=0 … Saturday=6
    idx = (s.dt.weekday + 1) % 7
    sun = s - pd.to_timedelta(idx, unit="d")
    wed = sun + pd.to_timedelta(3, unit="d")
    year = wed.dt.year

    jan4 = pd.to_datetime(
        {
            "year": year,
            "month": 1,
            "day": 4,
        }
    )
    first_sun = jan4 - pd.to_timedelta((jan4.dt.weekday + 1) % 7, unit="d")
    week_num = ((sun - first_sun).dt.days // 7) + 1

    # week ≤ 0 → roll to previous year
    roll = week_num <= 0
    if roll.any():
        prev = sun[roll] - pd.to_timedelta(1, unit="d")
        prev_idx = (prev.dt.weekday + 1) % 7
        prev_sun = prev - pd.to_timedelta(prev_idx, unit="d")
        prev_wed = prev_sun + pd.to_timedelta(3, unit="d")
        prev_year = prev_wed.dt.year
        prev_jan4 = pd.to_datetime(
            {
                "year": prev_year,
                "month": 1,
                "day": 4,
            }
        )
        prev_first_sun = prev_jan4 - pd.to_timedelta((prev_jan4.dt.weekday + 1) % 7, unit="d")
        prev_week_num = ((prev_sun - prev_first_sun).dt.days // 7) + 1
        year[roll] = prev_year[roll]
        week_num[roll] = prev_week_num[roll]

    # mask NaT values
    year = year.where(~nan_mask, 0)
    week_num = week_num.where(~nan_mask, 0).astype(int)
    # clip negative to 0
    week_num = np.clip(week_num, 0, None)

    epi_week_str = np.where(
        nan_mask | (year == 0),
        "N/A",
        year.astype(str) + "-" + pd.Series(week_num.astype(str)).str.zfill(2),
    )

    return pd.DataFrame(
        {
            "_epi_week": epi_week_str,
            "_epi_year": year.astype(int),
            "_epi_week_int": week_num,
        },
        index=dates.index,
    )
