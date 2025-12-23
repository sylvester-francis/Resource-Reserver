from datetime import UTC, datetime, timedelta

from app.schemas import (
    RecurrenceEndType,
    RecurrenceFrequency,
    RecurrenceRuleCreate,
)

MAX_OCCURRENCES = 100


def add_months(dt: datetime, months: int) -> datetime:
    """Add months to a datetime, clamping day to end-of-month if needed."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(
        dt.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return dt.replace(year=year, month=month, day=day)


def _normalize(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def generate_occurrences(
    start_time: datetime, end_time: datetime, rule: RecurrenceRuleCreate
) -> list[tuple[datetime, datetime]]:
    """Generate occurrences based on recurrence rule."""
    start_time = _normalize(start_time)
    end_time = _normalize(end_time)
    if end_time <= start_time:
        raise ValueError("End time must be after start time")

    duration = end_time - start_time
    occurrences: list[tuple[datetime, datetime]] = []

    def should_continue(next_start: datetime, count: int) -> bool:
        if count >= MAX_OCCURRENCES:
            return False
        if rule.end_type == RecurrenceEndType.after_count:
            return count < (rule.occurrence_count or 0)
        if rule.end_type == RecurrenceEndType.on_date and rule.end_date:
            return next_start <= _normalize(rule.end_date)
        # never: cap by MAX_OCCURRENCES to avoid runaway
        return count < MAX_OCCURRENCES

    if rule.frequency == RecurrenceFrequency.daily:
        current_start = start_time
        count = 0
        while should_continue(current_start, count):
            occurrences.append((current_start, current_start + duration))
            count += 1
            current_start = current_start + timedelta(days=rule.interval)

    elif rule.frequency == RecurrenceFrequency.weekly:
        days = rule.days_of_week or [start_time.weekday()]
        days = sorted(set(days))
        current_week_start = start_time
        count = 0

        while should_continue(current_week_start, count):
            for day in days:
                occurrence_start = current_week_start + timedelta(
                    days=day - current_week_start.weekday()
                )
                if occurrence_start < start_time:
                    continue
                if not should_continue(occurrence_start, count):
                    break
                occurrences.append((occurrence_start, occurrence_start + duration))
                count += 1
            current_week_start = current_week_start + timedelta(weeks=rule.interval)

    elif rule.frequency == RecurrenceFrequency.monthly:
        current_start = start_time
        count = 0
        while should_continue(current_start, count):
            occurrences.append((current_start, current_start + duration))
            count += 1
            current_start = add_months(current_start, rule.interval)

    else:
        raise ValueError("Unsupported frequency")

    # Apply end_date cap for series generated above
    if rule.end_type == RecurrenceEndType.on_date and rule.end_date:
        end_cap = _normalize(rule.end_date)
        occurrences = [occ for occ in occurrences if occ[0] <= end_cap]

    if rule.end_type == RecurrenceEndType.after_count and rule.occurrence_count:
        occurrences = occurrences[: rule.occurrence_count]

    if not occurrences:
        raise ValueError("No occurrences generated for the given rule")

    return occurrences[:MAX_OCCURRENCES]
