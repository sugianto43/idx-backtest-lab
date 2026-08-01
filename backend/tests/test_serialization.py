from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.infrastructure.db.serialization import from_naive_utc, to_naive_utc


def test_to_naive_utc_converts_non_utc_timezone_correctly() -> None:
    jakarta = timezone(timedelta(hours=7))
    aware = datetime(2026, 1, 1, 19, 0, 0, tzinfo=jakarta)

    naive = to_naive_utc(aware)

    assert naive == datetime(2026, 1, 1, 12, 0, 0)
    assert naive.tzinfo is None


def test_from_naive_utc_reattaches_utc_tzinfo() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)

    aware = from_naive_utc(naive)

    assert aware == datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_to_naive_utc_rejects_naive_input() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        to_naive_utc(datetime(2026, 1, 1))
