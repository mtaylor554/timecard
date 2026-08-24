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

from timecard import TimeEntry, worked_minutes, round_to_increment, split_overtime

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
```

Clock-in and clock-out must be timezone-aware `datetime` objects. A
naive datetime raises `InvalidShiftError` rather than silently
guessing what timezone you meant.

## Status

Early. The core duration math, rounding, and a daily overtime split
are in place. See `tests/test_core.py` for the table of edge cases
this is meant to handle correctly, including shifts that cross a
spring-forward and a fall-back DST transition.

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
