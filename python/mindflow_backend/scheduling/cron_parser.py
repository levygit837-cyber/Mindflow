"""Cron expression parser for 5-field standard cron syntax.

Adapted from Claude Code CLI's src/utils/cron.ts pattern.
Parses standard 5-field cron expressions: minute hour day-of-month month day-of-week.

Supports:
- Wildcards: *
- Ranges: 1-5
- Steps: */5, 1-5/2
- Lists: 1,3,5
- Named months/days: jan, mon, etc.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class CronParseError(Exception):
    """Raised when a cron expression cannot be parsed."""


# Named month/day mappings
_MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_DAY_NAMES = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
}

# Aliases: 7 → 0 (Sunday) for day-of-week
_DOW_ALIASES = {"7": "0", "0": "0"}


@dataclass(frozen=True)
class CronFields:
    """Parsed cron expression fields.

    Each field is a sorted tuple of integers representing the matched values.
    """

    minutes: tuple[int, ...]
    hours: tuple[int, ...]
    days_of_month: tuple[int, ...]
    months: tuple[int, ...]
    days_of_week: tuple[int, ...]


def _normalize_name(token: str, mapping: dict[str, int]) -> str:
    """Replace named tokens (jan, mon) with their numeric equivalents."""
    lower = token.lower()
    for name, value in mapping.items():
        if name in lower:
            lower = lower.replace(name, str(value))
    return lower


def _parse_field(field: str, min_val: int, max_val: int, name_map: dict[str, int] | None = None) -> tuple[int, ...]:
    """Parse a single cron field into a sorted tuple of matching integers.

    Args:
        field: The cron field string (e.g. "*/5", "1-3", "1,3,5", "*").
        min_val: Minimum valid value for this field.
        max_val: Maximum valid value for this field.
        name_map: Optional mapping of named values (e.g. month names).

    Returns:
        Sorted tuple of matching integers.

    Raises:
        CronParseError: If the field is invalid.
    """
    if name_map:
        field = _normalize_name(field, name_map)

    values: set[int] = set()

    for part in field.split(","):
        part = part.strip()
        if not part:
            raise CronParseError(f"Empty sub-expression in field '{field}'")

        # Handle step: */5, 1-10/2, 5/3
        step = 1
        if "/" in part:
            parts = part.split("/", 1)
            if len(parts) != 2 or not parts[1]:
                raise CronParseError(f"Invalid step expression '{part}'")
            try:
                step = int(parts[1])
            except ValueError:
                raise CronParseError(f"Invalid step value '{parts[1]}' in '{part}'")
            if step < 1:
                raise CronParseError(f"Step must be >= 1, got {step}")
            part = parts[0]

        # Handle wildcard
        if part == "*":
            values.update(range(min_val, max_val + 1, step))
            continue

        # Handle range: 1-5
        if "-" in part:
            range_parts = part.split("-", 1)
            try:
                start = int(range_parts[0])
                end = int(range_parts[1])
            except ValueError:
                raise CronParseError(f"Invalid range '{part}'")
            if start < min_val or end > max_val:
                raise CronParseError(
                    f"Range {start}-{end} out of bounds [{min_val}-{max_val}]"
                )
            if start > end:
                raise CronParseError(f"Range start {start} > end {end}")
            values.update(range(start, end + 1, step))
            continue

        # Handle single value
        try:
            val = int(part)
        except ValueError:
            raise CronParseError(f"Invalid value '{part}' in cron field")
        if val < min_val or val > max_val:
            raise CronParseError(
                f"Value {val} out of bounds [{min_val}-{max_val}]"
            )
        if step > 1:
            # Single value with step: "5/3" means 5, 8, 11, ... up to max
            values.update(range(val, max_val + 1, step))
        else:
            values.add(val)

    if not values:
        raise CronParseError(f"Field '{field}' produced no values")

    return tuple(sorted(values))


def parse_cron_expression(expr: str) -> CronFields:
    """Parse a 5-field cron expression into CronFields.

    Args:
        expr: Standard 5-field cron string: "M H DoM Mon DoW"
             e.g. "*/5 * * * *", "30 14 28 2 *"

    Returns:
        CronFields with parsed field values.

    Raises:
        CronParseError: If the expression is invalid.
    """
    if not expr or not expr.strip():
        raise CronParseError("Empty cron expression")

    fields = expr.strip().split()
    if len(fields) != 5:
        raise CronParseError(
            f"Expected 5 fields, got {len(fields)}: '{expr}'"
        )

    try:
        minutes = _parse_field(fields[0], 0, 59)
        hours = _parse_field(fields[1], 0, 23)
        days_of_month = _parse_field(fields[2], 1, 31)
        months = _parse_field(fields[3], 1, 12, _MONTH_NAMES)
        days_of_week = _parse_field(fields[4], 0, 6, _DAY_NAMES)

        # Normalize day-of-week: 7 → 0
        dow_set = set(days_of_week)
        if 7 in dow_set:
            dow_set.discard(7)
            dow_set.add(0)
        days_of_week = tuple(sorted(dow_set))

        return CronFields(
            minutes=minutes,
            hours=hours,
            days_of_month=days_of_month,
            months=months,
            days_of_week=days_of_week,
        )
    except CronParseError:
        raise
    except Exception as e:
        raise CronParseError(f"Failed to parse '{expr}': {e}") from e


def _matches(dt: datetime, fields: CronFields) -> bool:
    """Check if a datetime matches the cron fields."""
    return (
        dt.minute in fields.minutes
        and dt.hour in fields.hours
        and dt.day in fields.days_of_month
        and dt.month in fields.months
        and dt.weekday() in _weekday_to_cron(fields.days_of_week)
    )


def _weekday_to_cron(dows: tuple[int, ...]) -> tuple[int, ...]:
    """Convert cron day-of-week (0=Sun) to Python weekday (0=Mon).

    Cron: 0=Sun, 1=Mon, ..., 6=Sat
    Python: 0=Mon, 1=Tue, ..., 6=Sun
    """
    # cron 0 (Sun) → Python 6
    # cron 1 (Mon) → Python 0
    # cron 6 (Sat) → Python 5
    mapping = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
    return tuple(sorted(mapping[d] for d in dows))


def next_cron_run(cron: str, after: datetime | None = None) -> datetime | None:
    """Calculate the next run time for a cron expression.

    Args:
        cron: 5-field cron expression.
        after: Reference datetime (defaults to now). The next run will be
               strictly after this time.

    Returns:
        The next matching datetime, or None if no match found within 1 year.

    Raises:
        CronParseError: If the cron expression is invalid.
    """
    fields = parse_cron_expression(cron)
    if after is None:
        after = datetime.utcnow()

    # Start checking from the next minute
    current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # Limit search to 1 year to avoid infinite loops
    limit = after + timedelta(days=365)

    py_dows = _weekday_to_cron(fields.days_of_week)

    while current <= limit:
        if current.month not in fields.months:
            # Jump to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1, hour=0, minute=0)
            else:
                current = current.replace(month=current.month + 1, day=1, hour=0, minute=0)
            continue

        if current.day not in fields.days_of_month or current.weekday() not in py_dows:
            # Jump to next day
            current = current.replace(hour=0, minute=0) + timedelta(days=1)
            continue

        if current.hour not in fields.hours:
            # Jump to next hour
            current = current.replace(minute=0) + timedelta(hours=1)
            continue

        if current.minute not in fields.minutes:
            # Find next valid minute in this hour
            valid_minutes = [m for m in fields.minutes if m > current.minute]
            if valid_minutes:
                current = current.replace(minute=valid_minutes[0])
            else:
                # No more valid minutes this hour, jump to next hour
                current = current.replace(minute=0) + timedelta(hours=1)
            continue

        return current

    _logger.warning("no_cron_match_found", cron=cron, after=after.isoformat())
    return None


def cron_to_human(cron: str) -> str:
    """Convert a cron expression to a human-readable description.

    Args:
        cron: 5-field cron expression.

    Returns:
        Human-readable schedule description.
    """
    try:
        fields = parse_cron_expression(cron)
    except CronParseError:
        return f"Invalid cron: {cron}"

    # Special patterns
    if fields.minutes == tuple(range(0, 60)) and fields.hours == tuple(range(0, 24)):
        if fields.days_of_month == tuple(range(1, 32)) and fields.months == tuple(range(1, 13)):
            dow = _dow_names(fields.days_of_week)
            if dow == "every day":
                return "Every minute"
            return f"Every minute on {dow}"

    if fields.minutes == (0,) and fields.hours == tuple(range(0, 24)):
        if fields.days_of_month == tuple(range(1, 32)) and fields.months == tuple(range(1, 13)):
            dow = _dow_names(fields.days_of_week)
            if dow == "every day":
                return "Every hour"
            return f"Every hour on {dow}"

    # Every N minutes
    if len(fields.minutes) > 1 and fields.hours == tuple(range(0, 24)):
        step = fields.minutes[1] - fields.minutes[0]
        if all(fields.minutes[i + 1] - fields.minutes[i] == step for i in range(len(fields.minutes) - 1)):
            return f"Every {step} minutes"

    # Specific time
    if len(fields.hours) == 1 and len(fields.minutes) == 1:
        h = fields.hours[0]
        m = fields.minutes[0]
        time_str = f"{h:02d}:{m:02d}"
        dow = _dow_names(fields.days_of_week)
        dom = _dom_names(fields.days_of_month)
        month = _month_names(fields.months)
        parts = [f"At {time_str}"]
        if dow != "every day":
            parts.append(f"on {dow}")
        if dom != "every day of month":
            parts.append(f"on day {dom}")
        if month != "every month":
            parts.append(f"in {month}")
        return " ".join(parts)

    # Fallback
    return cron


def _dow_names(dows: tuple[int, ...]) -> str:
    """Format days-of-week as human-readable string."""
    names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    if dows == tuple(range(0, 7)):
        return "every day"
    if dows == tuple(range(1, 6)):
        return "weekdays"
    if dows == (0, 6):
        return "weekends"
    return ", ".join(names[d] for d in dows)


def _dom_names(doms: tuple[int, ...]) -> str:
    """Format days-of-month as human-readable string."""
    if doms == tuple(range(1, 32)):
        return "every day of month"
    return ", ".join(str(d) for d in doms)


def _month_names(months: tuple[int, ...]) -> str:
    """Format months as human-readable string."""
    names = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    if months == tuple(range(1, 13)):
        return "every month"
    return ", ".join(names[m] for m in months)