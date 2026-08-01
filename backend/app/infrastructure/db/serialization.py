from datetime import UTC, datetime


def to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC).replace(tzinfo=None)


def from_naive_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC)
