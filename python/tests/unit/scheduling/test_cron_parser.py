"""Tests for the cron parser module."""

from __future__ import annotations

from datetime import datetime

import pytest

from mindflow_backend.scheduling.cron_parser import (
    CronParseError,
    cron_to_human,
    next_cron_run,
    parse_cron_expression,
)


class TestParseCronExpression:
    """Tests for parse_cron_expression."""

    def test_every_minute(self) -> None:
        fields = parse_cron_expression("* * * * *")
        assert fields.minutes == tuple(range(0, 60))
        assert fields.hours == tuple(range(0, 24))
        assert fields.days_of_month == tuple(range(1, 32))
        assert fields.months == tuple(range(1, 13))
        assert fields.days_of_week == tuple(range(0, 7))

    def test_every_5_minutes(self) -> None:
        fields = parse_cron_expression("*/5 * * * *")
        assert fields.minutes == (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)

    def test_specific_time(self) -> None:
        fields = parse_cron_expression("30 14 * * *")
        assert fields.minutes == (30,)
        assert fields.hours == (14,)

    def test_range(self) -> None:
        fields = parse_cron_expression("0 9-17 * * *")
        assert fields.minutes == (0,)
        assert fields.hours == tuple(range(9, 18))

    def test_list(self) -> None:
        fields = parse_cron_expression("0 0 1,15 * *")
        assert fields.days_of_month == (1, 15)

    def test_named_months(self) -> None:
        fields = parse_cron_expression("0 0 1 jan,dec *")
        assert fields.months == (1, 12)

    def test_named_days(self) -> None:
        fields = parse_cron_expression("0 0 * * mon,fri")
        assert fields.days_of_week == (1, 5)

    def test_day_of_week_7_normalized(self) -> None:
        fields = parse_cron_expression("0 0 * * 7")
        assert fields.days_of_week == (0,)

    def test_empty_expression(self) -> None:
        with pytest.raises(CronParseError, match="Empty cron expression"):
            parse_cron_expression("")

    def test_wrong_field_count(self) -> None:
        with pytest.raises(CronParseError, match="Expected 5 fields"):
            parse_cron_expression("*/5 * *")

    def test_invalid_value(self) -> None:
        with pytest.raises(CronParseError, match="out of bounds"):
            parse_cron_expression("60 * * * *")

    def test_invalid_range(self) -> None:
        with pytest.raises(CronParseError, match="out of bounds"):
            parse_cron_expression("0 25 * * *")

    def test_invalid_step(self) -> None:
        with pytest.raises(CronParseError, match="Step must be >= 1"):
            parse_cron_expression("*/0 * * * *")


class TestNextCronRun:
    """Tests for next_cron_run."""

    def test_every_minute_next(self) -> None:
        after = datetime(2026, 3, 31, 10, 0, 0)
        result = next_cron_run("* * * * *", after=after)
        assert result is not None
        assert result == datetime(2026, 3, 31, 10, 1, 0)

    def test_specific_time_next(self) -> None:
        after = datetime(2026, 3, 31, 10, 0, 0)
        result = next_cron_run("30 14 * * *", after=after)
        assert result is not None
        assert result == datetime(2026, 3, 31, 14, 30, 0)

    def test_next_day(self) -> None:
        after = datetime(2026, 3, 31, 23, 59, 0)
        result = next_cron_run("0 9 * * *", after=after)
        assert result is not None
        assert result == datetime(2026, 4, 1, 9, 0, 0)

    def test_every_5_minutes(self) -> None:
        after = datetime(2026, 3, 31, 10, 3, 0)
        result = next_cron_run("*/5 * * * *", after=after)
        assert result is not None
        assert result == datetime(2026, 3, 31, 10, 5, 0)

    def test_weekdays_only(self) -> None:
        # 2026-03-31 is a Tuesday (weekday=1)
        after = datetime(2026, 3, 31, 8, 0, 0)
        result = next_cron_run("0 9 * * 1-5", after=after)
        assert result is not None
        assert result == datetime(2026, 3, 31, 9, 0, 0)
        assert result.weekday() in range(0, 5)  # Mon-Fri


class TestCronToHuman:
    """Tests for cron_to_human."""

    def test_every_minute(self) -> None:
        assert cron_to_human("* * * * *") == "Every minute"

    def test_every_hour(self) -> None:
        assert cron_to_human("0 * * * *") == "Every hour"

    def test_every_5_minutes(self) -> None:
        assert cron_to_human("*/5 * * * *") == "Every 5 minutes"

    def test_specific_time_daily(self) -> None:
        result = cron_to_human("30 14 * * *")
        assert "14:30" in result
        assert "every day" in result

    def test_specific_time_weekdays(self) -> None:
        result = cron_to_human("0 9 * * 1-5")
        assert "09:00" in result
        assert "weekdays" in result

    def test_invalid_cron(self) -> None:
        assert "Invalid cron" in cron_to_human("invalid")