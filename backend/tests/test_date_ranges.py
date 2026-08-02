from datetime import date

import pytest

from app.domain.date_ranges import date_ranges_overlap


@pytest.mark.parametrize(
    ("a_from", "a_to", "b_from", "b_to", "expected"),
    [
        (date(2020, 1, 1), date(2020, 12, 31), date(2021, 1, 1), None, False),
        (date(2020, 1, 1), date(2020, 12, 31), date(2020, 12, 31), None, True),
        (date(2020, 1, 1), None, date(2025, 1, 1), None, True),
        (date(2020, 1, 1), date(2020, 6, 30), date(2020, 7, 1), date(2020, 12, 31), False),
        (date(2020, 1, 1), date(2020, 6, 30), date(2020, 6, 30), date(2020, 12, 31), True),
        (date(2020, 1, 1), date(2020, 12, 31), date(2020, 3, 1), date(2020, 4, 1), True),
    ],
)
def test_date_ranges_overlap(
    a_from: date, a_to: date | None, b_from: date, b_to: date | None, expected: bool
) -> None:
    assert date_ranges_overlap(a_from, a_to, b_from, b_to) is expected
    assert date_ranges_overlap(b_from, b_to, a_from, a_to) is expected
