"""Test cases for core datetime utilities."""

import pytest
from datetime import datetime, timedelta
from mindflow_backend.utils.core import (
    format_datetime_iso,
    format_datetime_human,
    parse_datetime_iso,
    get_timestamp,
    from_timestamp,
    add_time,
    is_today,
    is_past,
    get_start_of_day,
)


class TestDatetimeUtilities:
    """Test core datetime utility functions."""

    def test_format_datetime_iso(self):
        """Test ISO datetime formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = format_datetime_iso(dt)
        assert result == "2024-01-15T10:30:45"

    def test_format_datetime_human(self):
        """Test human-readable datetime formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = format_datetime_human(dt)
        assert "Jan 15, 2024" in result
        assert "10:30" in result

    def test_parse_datetime_iso(self):
        """Test ISO datetime parsing."""
        iso_string = "2024-01-15T10:30:45"
        result = parse_datetime_iso(iso_string)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_get_timestamp(self):
        """Test timestamp generation."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = get_timestamp(dt)
        assert isinstance(result, float)
        assert result > 0

    def test_from_timestamp(self):
        """Test datetime from timestamp."""
        timestamp = 1705316245.0  # Jan 15, 2024 10:30:45 UTC
        result = from_timestamp(timestamp)
        assert result.year == 2024
        assert result.month == 1

    def test_add_time(self):
        """Test time addition."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = add_time(dt, days=1, hours=2)
        assert result.day == 16
        assert result.hour == 12

    def test_is_today(self):
        """Test today check."""
        today = datetime.now()
        assert is_today(today) is True
        yesterday = today - timedelta(days=1)
        assert is_today(yesterday) is False

    def test_is_past(self):
        """Test past datetime check."""
        past = datetime.now() - timedelta(hours=1)
        assert is_past(past) is True
        future = datetime.now() + timedelta(hours=1)
        assert is_past(future) is False

    def test_get_start_of_day(self):
        """Test start of day calculation."""
        dt = datetime(2024, 1, 15, 15, 30, 45)
        result = get_start_of_day(dt)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.day == 15

    def test_format_datetime_iso_none(self):
        """Test ISO formatting with None."""
        result = format_datetime_iso(None)
        assert result == ""

    def test_parse_datetime_iso_invalid(self):
        """Test ISO parsing with invalid string."""
        result = parse_datetime_iso("invalid-date")
        assert result is None
