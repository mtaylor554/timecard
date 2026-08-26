import unittest
from datetime import datetime, timedelta, timezone

from timecard import (
    InvalidShiftError,
    OpenShiftError,
    TimeEntry,
    round_to_increment,
    split_overtime,
    split_weekly_overtime,
    worked_minutes,
)

EST = timezone(timedelta(hours=-5))
EDT = timezone(timedelta(hours=-4))


def dt(offset, *args):
    return datetime(*args, tzinfo=offset)


# Each case is (description, TimeEntry kwargs, expected minutes or expected exception type).
WORKED_MINUTES_CASES = [
    (
        "plain day shift with a lunch break",
        dict(clock_in=dt(EST, 2026, 1, 5, 9, 0), clock_out=dt(EST, 2026, 1, 5, 17, 0), unpaid_break_minutes=30),
        450,
    ),
    (
        "overnight shift crossing midnight",
        dict(clock_in=dt(EST, 2026, 1, 5, 22, 0), clock_out=dt(EST, 2026, 1, 6, 6, 0)),
        480,
    ),
    (
        "zero-length shift is valid, not an error",
        dict(clock_in=dt(EST, 2026, 1, 5, 9, 0), clock_out=dt(EST, 2026, 1, 5, 9, 0)),
        0,
    ),
    (
        # US spring-forward: wall clock jumps from 01:00 EST straight to 03:00 EDT.
        # A shift spanning that jump is only 90 real minutes, even though the
        # wall-clock punches are 2.5 hours apart.
        "shift crossing a spring-forward DST gap",
        dict(clock_in=dt(EST, 2026, 3, 8, 1, 0), clock_out=dt(EDT, 2026, 3, 8, 3, 30)),
        90,
    ),
    (
        # US fall-back: 01:00-02:00 EDT happens, then the clock resets to 01:00
        # EST and runs again. A shift from 01:00 EDT to 01:30 EST looks like 30
        # wall-clock minutes but is actually 90 minutes of real elapsed time.
        "shift crossing a fall-back DST repeat",
        dict(clock_in=dt(EDT, 2026, 11, 1, 1, 0), clock_out=dt(EST, 2026, 11, 1, 1, 30)),
        90,
    ),
    (
        "break longer than the shift raises",
        dict(clock_in=dt(EST, 2026, 1, 5, 9, 0), clock_out=dt(EST, 2026, 1, 5, 9, 30), unpaid_break_minutes=45),
        InvalidShiftError,
    ),
    (
        "clock_out before clock_in raises",
        dict(clock_in=dt(EST, 2026, 1, 5, 17, 0), clock_out=dt(EST, 2026, 1, 5, 9, 0)),
        InvalidShiftError,
    ),
    (
        "missing clock_out raises OpenShiftError",
        dict(clock_in=dt(EST, 2026, 1, 5, 9, 0), clock_out=None),
        OpenShiftError,
    ),
    (
        "naive clock_out raises InvalidShiftError",
        dict(clock_in=dt(EST, 2026, 1, 5, 9, 0), clock_out=datetime(2026, 1, 5, 17, 0)),
        InvalidShiftError,
    ),
]

ROUNDING_CASES = [
    ("well below the increment rounds down", 7, 15, 0),
    ("just below the increment rounds up", 14.9, 15, 15),
    ("exact tie rounds up, not to even", 7.5, 15, 15),
    ("already on the increment stays put", 30, 15, 30),
    ("zero stays zero", 0, 15, 0),
    ("smaller increment", 4, 5, 5),
]

OVERTIME_CASES = [
    ("under the threshold", 420, 480, (420, 0)),
    ("exactly at the threshold", 480, 480, (480, 0)),
    ("over the threshold", 500, 480, (480, 20)),
    ("zero worked", 0, 480, (0, 0)),
]


class WorkedMinutesTests(unittest.TestCase):
    def test_cases(self):
        for description, kwargs, expected in WORKED_MINUTES_CASES:
            with self.subTest(description):
                entry = TimeEntry(**kwargs)
                if isinstance(expected, type) and issubclass(expected, Exception):
                    with self.assertRaises(expected):
                        worked_minutes(entry)
                else:
                    self.assertEqual(worked_minutes(entry), expected)


class RoundToIncrementTests(unittest.TestCase):
    def test_cases(self):
        for description, minutes, increment, expected in ROUNDING_CASES:
            with self.subTest(description):
                self.assertEqual(round_to_increment(minutes, increment), expected)

    def test_rejects_non_positive_increment(self):
        with self.assertRaises(ValueError):
            round_to_increment(30, 0)

    def test_rejects_negative_minutes(self):
        with self.assertRaises(ValueError):
            round_to_increment(-5, 15)


class SplitOvertimeTests(unittest.TestCase):
    def test_cases(self):
        for description, worked, threshold, expected in OVERTIME_CASES:
            with self.subTest(description):
                self.assertEqual(split_overtime(worked, threshold), expected)


# Each case is (description, daily_worked, daily_threshold, weekly_threshold, expected per-day list).
WEEKLY_OVERTIME_CASES = [
    (
        "under both thresholds every day",
        [420, 420, 420, 420, 420],
        480,
        2400,
        [(420, 0), (420, 0), (420, 0), (420, 0), (420, 0)],
    ),
    (
        "daily overtime only, never touches the weekly threshold",
        [500, 500, 500, 500, 500],
        480,
        2400,
        [(480, 20), (480, 20), (480, 20), (480, 20), (480, 20)],
    ),
    (
        "six full 8-hour days pushes the sixth entirely into weekly overtime",
        [480, 480, 480, 480, 480, 480],
        480,
        2400,
        [(480, 0), (480, 0), (480, 0), (480, 0), (480, 0), (0, 480)],
    ),
    (
        "a day that crosses the weekly threshold mid-day splits regular and overtime",
        [480, 480, 480, 480, 300],
        480,
        2100,
        [(480, 0), (480, 0), (480, 0), (480, 0), (180, 120)],
    ),
    (
        "empty week",
        [],
        480,
        2400,
        [],
    ),
]


class SplitWeeklyOvertimeTests(unittest.TestCase):
    def test_cases(self):
        for description, daily_worked, daily_threshold, weekly_threshold, expected in WEEKLY_OVERTIME_CASES:
            with self.subTest(description):
                self.assertEqual(
                    split_weekly_overtime(daily_worked, daily_threshold, weekly_threshold),
                    expected,
                )

    def test_rejects_non_positive_daily_threshold(self):
        with self.assertRaises(ValueError):
            split_weekly_overtime([480], daily_threshold_minutes=0)

    def test_rejects_non_positive_weekly_threshold(self):
        with self.assertRaises(ValueError):
            split_weekly_overtime([480], weekly_threshold_minutes=0)


if __name__ == "__main__":
    unittest.main()
