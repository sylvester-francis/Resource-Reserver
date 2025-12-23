from datetime import UTC, datetime, timedelta

from app.schemas import RecurrenceEndType, RecurrenceFrequency, RecurrenceRuleCreate
from app.utils.recurrence import generate_occurrences


def test_generate_daily_occurrences():
    start = datetime(2030, 1, 1, 9, 0, tzinfo=UTC)
    end = start + timedelta(hours=1)
    rule = RecurrenceRuleCreate(
        frequency=RecurrenceFrequency.daily,
        interval=1,
        end_type=RecurrenceEndType.after_count,
        occurrence_count=3,
    )

    occurrences = generate_occurrences(start, end, rule)
    assert len(occurrences) == 3
    assert occurrences[1][0] == start + timedelta(days=1)


def test_generate_weekly_occurrences_with_days():
    start = datetime(2030, 1, 1, 9, 0, tzinfo=UTC)  # Tuesday
    end = start + timedelta(hours=1)
    rule = RecurrenceRuleCreate(
        frequency=RecurrenceFrequency.weekly,
        interval=1,
        days_of_week=[1, 3],  # Tue and Thu
        end_type=RecurrenceEndType.after_count,
        occurrence_count=2,
    )

    occurrences = generate_occurrences(start, end, rule)
    assert len(occurrences) == 2
    assert occurrences[0][0].weekday() in {1, 3}
