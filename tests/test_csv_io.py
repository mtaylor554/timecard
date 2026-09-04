import io
import unittest
from datetime import datetime, timedelta, timezone

from timecard import (
    CsvFormatError,
    TimeEntry,
    Timesheet,
    dump_timesheet,
    load_timesheet,
    read_entries,
    write_entries,
)

EST = timezone(timedelta(hours=-5))


def dt(*args):
    return datetime(*args, tzinfo=EST)


class WriteEntriesTests(unittest.TestCase):
    def test_writes_header_and_rows(self):
        entries = [
            TimeEntry(clock_in=dt(2026, 1, 5, 9, 0), clock_out=dt(2026, 1, 5, 17, 0), unpaid_break_minutes=30, note="lunch"),
        ]
        buf = io.StringIO()
        write_entries(entries, buf)
        lines = buf.getvalue().splitlines()
        self.assertEqual(lines[0], "clock_in,clock_out,unpaid_break_minutes,note")
        self.assertEqual(
            lines[1],
            "2026-01-05T09:00:00-05:00,2026-01-05T17:00:00-05:00,30,lunch",
        )

    def test_open_shift_writes_empty_clock_out(self):
        entries = [TimeEntry(clock_in=dt(2026, 1, 5, 9, 0), clock_out=None)]
        buf = io.StringIO()
        write_entries(entries, buf)
        self.assertIn("2026-01-05T09:00:00-05:00,,0,", buf.getvalue())


class ReadEntriesTests(unittest.TestCase):
    def test_round_trip_through_write_and_read(self):
        entries = [
            TimeEntry(clock_in=dt(2026, 1, 5, 9, 0), clock_out=dt(2026, 1, 5, 17, 0), unpaid_break_minutes=30, note="lunch"),
            TimeEntry(clock_in=dt(2026, 1, 6, 22, 0), clock_out=dt(2026, 1, 7, 6, 0)),
        ]
        buf = io.StringIO()
        write_entries(entries, buf)
        buf.seek(0)
        result = read_entries(buf)
        self.assertEqual(result, entries)

    def test_open_shift_reads_back_as_none(self):
        buf = io.StringIO("clock_in,clock_out,unpaid_break_minutes,note\n2026-01-05T09:00:00-05:00,,0,\n")
        result = read_entries(buf)
        self.assertEqual(result, [TimeEntry(clock_in=dt(2026, 1, 5, 9, 0), clock_out=None)])

    def test_missing_unpaid_break_minutes_defaults_to_zero(self):
        buf = io.StringIO("clock_in,clock_out\n2026-01-05T09:00:00-05:00,2026-01-05T17:00:00-05:00\n")
        result = read_entries(buf)
        self.assertEqual(result, [TimeEntry(clock_in=dt(2026, 1, 5, 9, 0), clock_out=dt(2026, 1, 5, 17, 0))])

    def test_missing_clock_in_column_raises(self):
        buf = io.StringIO("clock_out\n2026-01-05T17:00:00-05:00\n")
        with self.assertRaises(CsvFormatError):
            read_entries(buf)

    def test_blank_clock_in_raises(self):
        buf = io.StringIO("clock_in,clock_out\n,2026-01-05T17:00:00-05:00\n")
        with self.assertRaises(CsvFormatError):
            read_entries(buf)

    def test_unparsable_clock_in_raises_with_row_number(self):
        buf = io.StringIO("clock_in,clock_out\nnot-a-date,2026-01-05T17:00:00-05:00\n")
        with self.assertRaisesRegex(CsvFormatError, "row 2"):
            read_entries(buf)

    def test_non_integer_unpaid_break_minutes_raises(self):
        buf = io.StringIO(
            "clock_in,clock_out,unpaid_break_minutes\n"
            "2026-01-05T09:00:00-05:00,2026-01-05T17:00:00-05:00,thirty\n"
        )
        with self.assertRaises(CsvFormatError):
            read_entries(buf)


class TimesheetRoundTripTests(unittest.TestCase):
    def test_dump_and_load_preserve_entries(self):
        sheet = Timesheet(
            entries=[
                TimeEntry(clock_in=dt(2026, 1, 5, 9, 0), clock_out=dt(2026, 1, 5, 17, 0)),
                TimeEntry(clock_in=dt(2026, 1, 6, 9, 0), clock_out=dt(2026, 1, 6, 17, 0), unpaid_break_minutes=15),
            ]
        )
        buf = io.StringIO()
        dump_timesheet(sheet, buf)
        buf.seek(0)
        loaded = load_timesheet(buf)
        self.assertEqual(loaded.entries, sheet.entries)


if __name__ == "__main__":
    unittest.main()
