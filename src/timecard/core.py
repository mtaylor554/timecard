"""Compute worked time from clock-in/clock-out punches.

The hard part of timesheet math isn't the addition, it's the edge cases:
shifts that cross midnight, shifts that cross a daylight saving change,
breaks that eat the whole shift, punches that never got a clock-out. This
module tries to get those right instead of assuming every day is a tidy
24 hours.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


class OpenShiftError(ValueError):
    """Raised when a shift has no clock-out time yet."""


class InvalidShiftError(ValueError):
    """Raised when a shift's punches don't make sense (bad order, break longer than the shift, missing tzinfo, etc.)."""


@dataclass
class TimeEntry:
    clock_in: datetime
    clock_out: datetime | None
    unpaid_break_minutes: int = 0
    note: str = ""


def worked_minutes(entry: TimeEntry) -> int:
    """Minutes actually worked, after subtracting the unpaid break.

    Both punches must be timezone-aware. We lean on datetime's own
    UTC-normalized subtraction to get overnight shifts and DST
    transitions right, rather than doing calendar math by hand.
    """
    if entry.clock_out is None:
        raise OpenShiftError(f"shift starting {entry.clock_in.isoformat()} has no clock-out")

    if entry.clock_in.tzinfo is None or entry.clock_out.tzinfo is None:
        raise InvalidShiftError("clock_in and clock_out must be timezone-aware")

    span = entry.clock_out - entry.clock_in
    if span < timedelta(0):
        raise InvalidShiftError(
            f"clock_out ({entry.clock_out.isoformat()}) is before "
            f"clock_in ({entry.clock_in.isoformat()})"
        )

    raw_minutes = span.total_seconds() / 60
    worked = raw_minutes - entry.unpaid_break_minutes
    if worked < 0:
        raise InvalidShiftError(
            f"unpaid break ({entry.unpaid_break_minutes}m) is longer than "
            f"the shift ({raw_minutes:.0f}m)"
        )

    return round(worked)


@dataclass
class Timesheet:
    """A worker's punches for a pay period, in the order they happened.

    This is a thin wrapper over a list of TimeEntry rows. Its job is
    grouping punches by the calendar day they started on, since that's
    the unit daily overtime rules and payroll reports operate on - an
    overnight shift is attributed entirely to the day it started.
    """

    entries: list[TimeEntry] = field(default_factory=list)

    def add(self, entry: TimeEntry) -> None:
        self.entries.append(entry)

    def daily_worked_minutes(self) -> list[tuple[date, int]]:
        """Worked minutes per calendar day, sorted chronologically.

        Sorted order matters to callers like overtime(), which feeds
        this into split_weekly_overtime and needs the days in the
        order they happened.
        """
        totals: dict[date, int] = {}
        for entry in self.entries:
            day = entry.clock_in.date()
            totals[day] = totals.get(day, 0) + worked_minutes(entry)
        return sorted(totals.items())

    def total_worked_minutes(self) -> int:
        return sum(worked_minutes(entry) for entry in self.entries)

    def overtime(
        self,
        daily_threshold_minutes: int = 8 * 60,
        weekly_threshold_minutes: int = 40 * 60,
    ) -> list[tuple[date, int, int]]:
        """Per-day (date, regular, overtime), honoring daily and weekly thresholds.

        See split_weekly_overtime for how the two thresholds interact.
        """
        daily = self.daily_worked_minutes()
        splits = split_weekly_overtime(
            [minutes for _, minutes in daily], daily_threshold_minutes, weekly_threshold_minutes
        )
        return [(day, regular, overtime) for (day, _), (regular, overtime) in zip(daily, splits)]


def round_to_increment(minutes: float, increment: int = 15) -> int:
    """Round to the nearest increment, rounding an exact tie up.

    Payroll systems round shift length to fixed increments (7 and 15
    minutes are both common). Python's built-in round() uses
    banker's rounding, which quietly rounds a tie like 7.5 down to
    the nearest even multiple instead of up - the opposite of what a
    payroll clerk expects.
    """
    if increment <= 0:
        raise ValueError("increment must be positive")
    if minutes < 0:
        raise ValueError("minutes must not be negative")
    steps = minutes / increment
    return int(steps + 0.5) * increment


def split_overtime(worked: int, daily_threshold_minutes: int = 8 * 60) -> tuple[int, int]:
    """Split worked minutes into (regular, overtime) using a daily threshold."""
    if worked <= daily_threshold_minutes:
        return worked, 0
    return daily_threshold_minutes, worked - daily_threshold_minutes


def split_weekly_overtime(
    daily_worked: list[int],
    daily_threshold_minutes: int = 8 * 60,
    weekly_threshold_minutes: int = 40 * 60,
) -> list[tuple[int, int]]:
    """Split each day's worked minutes into (regular, overtime), applying both a
    daily and a weekly threshold the way most US state rules do: overtime is
    whichever is bigger, hours past the daily threshold or hours past the
    weekly threshold, without double-counting the same minute under both.

    Order matters - the list should be in the same order the days happened
    in, since the weekly threshold is applied against a running total.
    """
    if daily_threshold_minutes <= 0:
        raise ValueError("daily_threshold_minutes must be positive")
    if weekly_threshold_minutes <= 0:
        raise ValueError("weekly_threshold_minutes must be positive")

    results = []
    regular_total = 0
    for worked in daily_worked:
        day_regular, day_overtime = split_overtime(worked, daily_threshold_minutes)

        remaining_weekly_capacity = weekly_threshold_minutes - regular_total
        if remaining_weekly_capacity <= 0:
            week_overtime = day_regular
            day_regular = 0
        elif day_regular > remaining_weekly_capacity:
            week_overtime = day_regular - remaining_weekly_capacity
            day_regular = remaining_weekly_capacity
        else:
            week_overtime = 0

        regular_total += day_regular
        results.append((day_regular, day_overtime + week_overtime))

    return results
