"""Utility functions for CLI operations."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional
import typer


def parse_aware(dt_str: str) -> datetime:
    dt_naive = datetime.fromisoformat(dt_str)
    return dt_naive.replace(tzinfo=timezone.utc)


def parse_datetime(date_str: str) -> datetime:
    """Parse datetime string with flexible formats."""
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%y %H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Invalid datetime format: {date_str}. Use YYYY-MM-DD HH:MM")  # noqa : E501


def parse_duration(duration_str: str) -> timedelta:
    """Parse duration string like '2h', '30m', '1h30m'."""
    duration_str = duration_str.lower().strip()

    # Match patterns like 2h, 30m, 1h30m
    pattern = r"(?:(\d+)h)?(?:(\d+)m)?"
    match = re.match(pattern, duration_str)

    if not match:
        raise ValueError(
            "Invalid duration format. Use formats like '2h', '30m', '1h30m'"
        )

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)

    if hours == 0 and minutes == 0:
        raise ValueError("Duration must be greater than 0")

    return timedelta(hours=hours, minutes=minutes)


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M")


def format_duration(start: datetime, end: datetime) -> str:
    """Format duration between two datetimes."""
    duration = end - start
    hours = duration.total_seconds() / 3600

    if hours < 1:
        minutes = int(duration.total_seconds() / 60)
        return f"{minutes}m"
    elif hours < 24:
        return f"{hours:.1f}h"
    else:
        days = duration.days
        remaining_hours = (duration.total_seconds() - days * 24 * 3600) / 3600
        return f"{days}d {remaining_hours:.1f}h"


def confirm_action(message: str, default: bool = False) -> bool:
    """Confirm an action with the user."""
    return typer.confirm(message, default=default)


def prompt_for_optional(prompt_text: str) -> Optional[str]:
    """Prompt for optional input, return None if empty."""
    value = typer.prompt(prompt_text, default="", show_default=False)
    return value.strip() if value.strip() else None
