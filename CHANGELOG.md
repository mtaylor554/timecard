# Changelog

## 0.1.0 - unreleased

First cut. Everything below exists and is tested; nothing has been
uploaded to PyPI yet.

- `worked_minutes` / `TimeEntry`: minutes worked from a clock-in/clock-out
  pair, correct across overnight shifts and DST transitions because it
  relies on timezone-aware `datetime` subtraction instead of calendar
  math. Raises `OpenShiftError` for a missing clock-out and
  `InvalidShiftError` for bad punches (naive datetimes, clock-out before
  clock-in, a break longer than the shift).
- `round_to_increment`: round a duration to a fixed increment, ties up
  rather than Python's banker's rounding.
- `RoundingRule` / `rounded_worked_minutes`: grace-period punch rounding,
  the way time clock hardware actually applies a rounding policy - snap
  each punch to a grid, not the final duration.
- `split_overtime` / `split_weekly_overtime`: daily and weekly overtime
  splitting, whichever threshold produces more overtime without double
  counting a minute under both.
- `Timesheet`: groups punches by the calendar day they started on and
  applies the overtime split across a pay period.
- `BreakPolicy` / `Timesheet.worked_minutes_with_breaks`: pay out short
  gaps between consecutive punches as rest time instead of an unpaid
  break.
- `read_entries` / `write_entries` / `load_timesheet` / `dump_timesheet`:
  CSV import/export with ISO 8601 timestamps and UTC offsets, so a round
  trip never loses or guesses a timezone.
