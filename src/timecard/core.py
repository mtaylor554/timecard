"""Compute worked time from clock-in/clock-out punches.

The hard part of timesheet math isn't the addition, it's the edge cases:
shifts that cross midnight, shifts that cross a daylight saving change,
breaks that eat the whole shift, punches that never got a clock-out. This
module tries to get those right instead of assuming every day is a tidy
24 hours.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta


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
