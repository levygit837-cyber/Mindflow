"""Date and time utilities for MindFlow backend.

Functions for formatting, parsing, and manipulating dates and times.
"""

from datetime import datetime, timedelta, UTC
from typing import Optional, Union
import re


def format_datetime_iso(dt: datetime) -> str:
    """Format datetime in ISO format."""
    return dt.isoformat()


def format_datetime_human(dt: datetime) -> str:
    """Format datetime in human readable format."""
    now = datetime.now(UTC)
    diff = now - dt
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime("%b %d, %Y")


def format_datetime_short(dt: datetime) -> str:
    """Format datetime in short format."""
    return dt.strftime("%Y-%m-%d %H:%M")


def format_datetime_long(dt: datetime) -> str:
    """Format datetime in long format."""
    return dt.strftime("%A, %B %d, %Y at %I:%M %p")


def parse_datetime_iso(dt_str: str) -> Optional[datetime]:
    """Parse ISO datetime string."""
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        return None


def parse_datetime_flexible(dt_str: str) -> Optional[datetime]:
    """Parse datetime string in various formats."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%d %B %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    
    # Try ISO format as last resort
    return parse_datetime_iso(dt_str)


def parse_relative_time(relative_str: str) -> Optional[datetime]:
    """Parse relative time strings like '2 hours ago', '3 days ago'."""
    now = datetime.now(UTC)
    
    # Pattern for "X units ago"
    pattern = r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago'
    match = re.search(pattern, relative_str.lower())
    
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        
        deltas = {
            'second': timedelta(seconds=amount),
            'minute': timedelta(minutes=amount),
            'hour': timedelta(hours=amount),
            'day': timedelta(days=amount),
            'week': timedelta(weeks=amount),
            'month': timedelta(days=amount * 30),  # Approximation
            'year': timedelta(days=amount * 365),  # Approximation
        }
        
        return now - deltas.get(unit, timedelta(0))
    
    return None


def get_timestamp(dt: Optional[datetime] = None) -> float:
    """Get Unix timestamp."""
    if dt is None:
        dt = datetime.now(UTC)
    return dt.timestamp()


def get_timestamp_ms(dt: Optional[datetime] = None) -> int:
    """Get Unix timestamp in milliseconds."""
    return int(get_timestamp(dt) * 1000)


def from_timestamp(timestamp: float) -> datetime:
    """Create datetime from Unix timestamp."""
    return datetime.fromtimestamp(timestamp, UTC)


def from_timestamp_ms(timestamp_ms: int) -> datetime:
    """Create datetime from Unix timestamp in milliseconds."""
    return from_timestamp(timestamp_ms / 1000.0)


def add_time(dt: datetime, **kwargs) -> datetime:
    """Add time to datetime."""
    return dt + timedelta(**kwargs)


def subtract_time(dt: datetime, **kwargs) -> datetime:
    """Subtract time from datetime."""
    return dt - timedelta(**kwargs)


def get_age(dt: datetime) -> timedelta:
    """Get age of datetime."""
    return datetime.now(UTC) - dt


def get_age_in_days(dt: datetime) -> int:
    """Get age in days."""
    return get_age(dt).days


def get_age_in_hours(dt: datetime) -> float:
    """Get age in hours."""
    return get_age(dt).total_seconds() / 3600


def get_age_in_minutes(dt: datetime) -> float:
    """Get age in minutes."""
    return get_age(dt).total_seconds() / 60


def is_future(dt: datetime) -> bool:
    """Check if datetime is in the future."""
    return dt > datetime.now(UTC)


def is_past(dt: datetime) -> bool:
    """Check if datetime is in the past."""
    return dt < datetime.now(UTC)


def is_today(dt: datetime) -> bool:
    """Check if datetime is today."""
    now = datetime.now(UTC)
    return dt.date() == now.date()


def is_yesterday(dt: datetime) -> bool:
    """Check if datetime is yesterday."""
    yesterday = datetime.now(UTC).date() - timedelta(days=1)
    return dt.date() == yesterday


def is_this_week(dt: datetime) -> bool:
    """Check if datetime is this week."""
    now = datetime.now(UTC)
    week_start = now.date() - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start <= dt.date() <= week_end


def is_this_month(dt: datetime) -> bool:
    """Check if datetime is this month."""
    now = datetime.now(UTC)
    return dt.year == now.year and dt.month == now.month


def is_this_year(dt: datetime) -> bool:
    """Check if datetime is this year."""
    return dt.year == datetime.now(UTC).year


def get_start_of_day(dt: datetime) -> datetime:
    """Get start of day for given datetime."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_end_of_day(dt: datetime) -> datetime:
    """Get end of day for given datetime."""
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def get_start_of_week(dt: datetime) -> datetime:
    """Get start of week for given datetime (Monday)."""
    days_since_monday = dt.weekday()
    start_of_week = dt - timedelta(days=days_since_monday)
    return get_start_of_day(start_of_week)


def get_end_of_week(dt: datetime) -> datetime:
    """Get end of week for given datetime (Sunday)."""
    days_until_sunday = 6 - dt.weekday()
    end_of_week = dt + timedelta(days=days_until_sunday)
    return get_end_of_day(end_of_week)


def get_start_of_month(dt: datetime) -> datetime:
    """Get start of month for given datetime."""
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_end_of_month(dt: datetime) -> datetime:
    """Get end of month for given datetime."""
    if dt.month == 12:
        next_month = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        next_month = dt.replace(month=dt.month + 1, day=1)
    
    return next_month - timedelta(microseconds=1)


def get_start_of_year(dt: datetime) -> datetime:
    """Get start of year for given datetime."""
    return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def get_end_of_year(dt: datetime) -> datetime:
    """Get end of year for given datetime."""
    return dt.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)


def get_timezone_aware(dt: datetime, tz_str: str) -> datetime:
    """Make datetime timezone-aware."""
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(tz_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(tz)
        return dt
    except (ImportError, Exception):
        # Fallback: assume UTC if zoneinfo is not available
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt


def get_datetime_range(start: datetime, end: datetime, interval: timedelta) -> list[datetime]:
    """Get list of datetimes between start and end at given interval."""
    datetimes = []
    current = start
    
    while current <= end:
        datetimes.append(current)
        current += interval
    
    return datetimes


def truncate_to_minute(dt: datetime) -> datetime:
    """Truncate datetime to minute precision."""
    return dt.replace(second=0, microsecond=0)


def truncate_to_hour(dt: datetime) -> datetime:
    """Truncate datetime to hour precision."""
    return dt.replace(minute=0, second=0, microsecond=0)


def truncate_to_day(dt: datetime) -> datetime:
    """Truncate datetime to day precision."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def format_duration_iso(duration: timedelta) -> str:
    """Format duration in ISO format (PT...)."""
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}H")
    if minutes > 0:
        parts.append(f"{minutes}M")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}S")
    
    return f"PT{''.join(parts)}"


def parse_duration_iso(duration_str: str) -> Optional[timedelta]:
    """Parse ISO duration format (PT...)."""
    if not duration_str.startswith('PT'):
        return None
    
    duration_str = duration_str[2:]  # Remove 'PT'
    
    hours = 0
    minutes = 0
    seconds = 0
    
    # Parse hours
    if 'H' in duration_str:
        parts = duration_str.split('H')
        hours = int(parts[0])
        duration_str = parts[1] if len(parts) > 1 else ''
    
    # Parse minutes
    if 'M' in duration_str:
        parts = duration_str.split('M')
        minutes = int(parts[0])
        duration_str = parts[1] if len(parts) > 1 else ''
    
    # Parse seconds
    if 'S' in duration_str:
        parts = duration_str.split('S')
        seconds = int(parts[0])
    
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def get_business_days(start: datetime, end: datetime) -> int:
    """Count business days between two dates."""
    if start > end:
        start, end = end, start
    
    business_days = 0
    current = start.date()
    end_date = end.date()
    
    while current <= end_date:
        if current.weekday() < 5:  # Monday to Friday
            business_days += 1
        current += timedelta(days=1)
    
    return business_days


def add_business_days(dt: datetime, days: int) -> datetime:
    """Add business days to datetime."""
    result = dt
    added_days = 0
    
    while added_days < days:
        result += timedelta(days=1)
        if result.weekday() < 5:  # Monday to Friday
            added_days += 1
    
    return result


def get_quarter(dt: datetime) -> int:
    """Get quarter of year (1-4)."""
    return (dt.month - 1) // 3 + 1


def get_week_of_year(dt: datetime) -> int:
    """Get ISO week number of year."""
    return dt.isocalendar()[1]


def get_day_of_year(dt: datetime) -> int:
    """Get day of year (1-366)."""
    return dt.timetuple().tm_yday
