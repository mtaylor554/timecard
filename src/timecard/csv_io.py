"""Read and write punches as CSV.

The format is deliberately flat and boring: one row per TimeEntry, ISO
8601 timestamps with their UTC offset so a round trip never loses or
guesses a timezone. An open shift (no clock-out yet) is written as an
empty clock_out field rather than skipped, so exporting a Timesheet
that still has someone clocked in doesn't silently drop that row.
"""

import csv
from datetime import datetime
from typing import IO, Iterable

from .core import TimeEntry, Timesheet

FIELDNAMES = ["clock_in", "clock_out", "unpaid_break_minutes", "note"]


class CsvFormatError(ValueError):
    """Raised when a CSV row can't be parsed into a TimeEntry."""


def write_entries(entries: Iterable[TimeEntry], f: IO[str]) -> None:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for entry in entries:
        writer.writerow(
            {
                "clock_in": entry.clock_in.isoformat(),
                "clock_out": entry.clock_out.isoformat() if entry.clock_out is not None else "",
                "unpaid_break_minutes": entry.unpaid_break_minutes,
                "note": entry.note,
            }
        )


def read_entries(f: IO[str]) -> list[TimeEntry]:
    reader = csv.DictReader(f)
    missing = [name for name in ("clock_in", "clock_out") if name not in (reader.fieldnames or ())]
    if missing:
        raise CsvFormatError(f"missing required column(s): {', '.join(missing)}")

    entries = []
    for row_number, row in enumerate(reader, start=2):  # header is row 1
        entries.append(_row_to_entry(row, row_number))
    return entries


def _row_to_entry(row: dict, row_number: int) -> TimeEntry:
    clock_in_raw = (row.get("clock_in") or "").strip()
    if not clock_in_raw:
        raise CsvFormatError(f"row {row_number}: clock_in is required")
    try:
        clock_in = _parse_datetime(clock_in_raw)
    except ValueError as exc:
        raise CsvFormatError(f"row {row_number}: invalid clock_in {clock_in_raw!r}: {exc}") from exc

    clock_out_raw = (row.get("clock_out") or "").strip()
    clock_out = None
    if clock_out_raw:
        try:
            clock_out = _parse_datetime(clock_out_raw)
        except ValueError as exc:
            raise CsvFormatError(f"row {row_number}: invalid clock_out {clock_out_raw!r}: {exc}") from exc

    break_raw = (row.get("unpaid_break_minutes") or "").strip()
    if break_raw:
        try:
            unpaid_break_minutes = int(break_raw)
        except ValueError as exc:
            raise CsvFormatError(
                f"row {row_number}: invalid unpaid_break_minutes {break_raw!r}"
            ) from exc
    else:
        unpaid_break_minutes = 0

    return TimeEntry(
        clock_in=clock_in,
        clock_out=clock_out,
        unpaid_break_minutes=unpaid_break_minutes,
        note=row.get("note") or "",
    )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def dump_timesheet(sheet: Timesheet, f: IO[str]) -> None:
    write_entries(sheet.entries, f)


def load_timesheet(f: IO[str]) -> Timesheet:
    return Timesheet(entries=read_entries(f))
