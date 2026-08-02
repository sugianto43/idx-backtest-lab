from datetime import date


def date_ranges_overlap(a_from: date, a_to: date | None, b_from: date, b_to: date | None) -> bool:
    a_end = a_to or date.max
    b_end = b_to or date.max
    return a_from <= b_end and b_from <= a_end
