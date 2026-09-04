# timecard

A small library for turning clock-in/clock-out punches into worked
hours, without getting tripped up by the cases that make timesheet
math annoying: shifts that cross midnight, shifts that cross a
daylight saving change, breaks that eat the whole shift, and punches
that never got closed out.

Zero dependencies. Standard library only.

## Why

Most of this logic looks trivial until you hit the edge cases. Naive
subtraction of two local timestamps gets the wrong answer on the two
days a year the clocks change, and it's easy to write code that
"works" for months before someone works a shift on one of those days.
This library is built around timezone-aware `datetime` objects and
lets Python's own UTC-normalized subtraction do the hard part.

## Usage

```python
from datetime import datetime, timedelta, timezone

from timecard import TimeEntry, Timesheet, worked_minutes, round_to_increment, split_overtime, split_weekly_overtime

est = timezone(timedelta(hours=-5))

# A shift with a 30-minute unpaid lunch.
shift = TimeEntry(
    clock_in=datetime(2026, 1, 5, 9, 0, tzinfo=est),
    clock_out=datetime(2026, 1, 5, 17, 0, tzinfo=est),
    unpaid_break_minutes=30,
)
worked_minutes(shift)  # 450

# Overnight shifts just work, since we're subtracting real instants,
# not wall-clock times on the same calendar day.
overnight = TimeEntry(
    clock_in=datetime(2026, 1, 5, 22, 0, tzinfo=est),
    clock_out=datetime(2026, 1, 6, 6, 0, tzinfo=est),
)
worked_minutes(overnight)  # 480

# Round to the nearest 15 minutes the way payroll expects (ties round
# up, not to even like Python's built-in round()).
round_to_increment(97, increment=15)  # 90

# Split a day's worked minutes into regular and overtime.
split_overtime(worked=500, daily_threshold_minutes=480)  # (480, 20)

# Split a week's worth of daily totals, honoring both the daily threshold
# and a weekly one (whichever produces more overtime wins, without
# double-counting the same minute under both rules).
split_weekly_overtime(
    daily_worked=[480, 480, 480, 480, 480, 480],
    daily_threshold_minutes=480,
    weekly_threshold_minutes=40 * 60,
)  # [(480, 0), (480, 0), (480, 0), (480, 0), (480, 0), (0, 480)]

# Timesheet groups a period's punches by the calendar day they started
# on and applies the daily/weekly overtime split for you.
sheet = Timesheet()
sheet.add(TimeEntry(clock_in=datetime(2026, 1, 5, 9, 0, tzinfo=est), clock_out=datetime(2026, 1, 5, 17, 0, tzinfo=est)))
sheet.add(TimeEntry(clock_in=datetime(2026, 1, 6, 9, 0, tzinfo=est), clock_out=datetime(2026, 1, 6, 17, 0, tzinfo=est)))

sheet.daily_worked_minutes()  # [(date(2026, 1, 5), 480), (date(2026, 1, 6), 480)]
sheet.total_worked_minutes()  # 960
sheet.overtime(daily_threshold_minutes=480, weekly_threshold_minutes=2400)
# [(date(2026, 1, 5), 480, 0), (date(2026, 1, 6), 480, 0)]
```

Clock-in and clock-out must be timezone-aware `datetime` objects. A
naive datetime raises `InvalidShiftError` rather than silently
guessing what timezone you meant.

### CSV import/export

```python
from timecard import dump_timesheet, load_timesheet

with open("punches.csv", "w", newline="") as f:
    dump_timesheet(sheet, f)

with open("punches.csv") as f:
    sheet = load_timesheet(f)
```

The format is one row per punch: `clock_in,clock_out,unpaid_break_minutes,note`.
Timestamps are ISO 8601 with a UTC offset, so a round trip never loses
or guesses a timezone. An open shift (no clock-out yet) round-trips as
an empty `clock_out` field. A malformed row - unparsable timestamp,
non-integer break minutes, or a missing `clock_in`/`clock_out` column -
raises `CsvFormatError` naming the offending row. `write_entries` and
`read_entries` work directly on a list of `TimeEntry` if you don't want
a `Timesheet`.

## Status

Early. The core duration math, rounding, daily/weekly overtime
splits, the `Timesheet` container that groups punches into days, and
CSV import/export are in place. See `tests/test_core.py` for the
table of edge cases this is meant to handle correctly, including
shifts that cross a spring-forward and a fall-back DST transition.

## Install

Not published anywhere yet. Clone it and install in editable mode:

```
pip install -e .
```

## Running the tests

```
python -m unittest discover -s tests
```

## License

MIT, see `LICENSE`.
