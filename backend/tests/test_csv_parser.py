from decimal import Decimal

import pytest

from app.application.errors import CsvContractViolation
from app.infrastructure.ingestion.csv_parser import parse_csv

HEADER = "timestamp,instrument_identifier,open,high,low,close,volume"


def _csv(*lines: str) -> bytes:
    return "\n".join((HEADER, *lines)).encode("utf-8")


def test_valid_daily_csv_parses_all_rows() -> None:
    parsed = parse_csv(
        _csv(
            "2026-01-01,BBCA,100,105,99,104,1000",
            "2026-01-02,BBCA,104,110,103,109,1500",
        ),
        bar_interval="1d",
        timezone_name="Asia/Jakarta",
    )

    assert len(parsed.rows) == 2
    first = parsed.rows[0]
    assert first.instrument_identifier == "BBCA"
    assert first.open == Decimal("100")
    assert first.timestamp_utc.isoformat() == "2025-12-31T17:00:00+00:00"
    assert first.zero_volume is False


def test_zero_volume_row_is_flagged_not_rejected() -> None:
    parsed = parse_csv(
        _csv("2026-01-01,BBCA,100,105,99,104,0"),
        bar_interval="1d",
        timezone_name="UTC",
    )

    assert parsed.rows[0].zero_volume is True


def test_offset_timestamp_accepted_for_intraday_interval() -> None:
    parsed = parse_csv(
        _csv("2026-01-01T09:00:00+07:00,BBCA,100,105,99,104,1000"),
        bar_interval="5m",
        timezone_name="Asia/Jakarta",
    )

    assert parsed.rows[0].timestamp_utc.isoformat() == "2026-01-01T02:00:00+00:00"


def test_unparseable_timestamp_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(
            _csv("not-a-timestamp,BBCA,100,105,99,104,1000"),
            bar_interval="1d",
            timezone_name="UTC",
        )
    assert excinfo.value.code == "invalid_timestamp"


def test_date_only_timestamp_rejected_for_non_daily_interval() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(
            _csv("2026-01-01,BBCA,100,105,99,104,1000"), bar_interval="5m", timezone_name="UTC"
        )
    assert excinfo.value.code == "invalid_timestamp"


def test_timestamp_without_offset_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(
            _csv("2026-01-01T09:00:00,BBCA,100,105,99,104,1000"),
            bar_interval="5m",
            timezone_name="UTC",
        )
    assert excinfo.value.code == "invalid_timestamp"


def test_unknown_timezone_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(
            _csv("2026-01-01,BBCA,100,105,99,104,1000"),
            bar_interval="1d",
            timezone_name="Not/AZone",
        )
    assert excinfo.value.code == "invalid_timezone"


def test_missing_header_column_rejected() -> None:
    text = "timestamp,instrument_identifier,open,high,low,close\n2026-01-01,BBCA,100,105,99,104"
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(text.encode("utf-8"), bar_interval="1d", timezone_name="UTC")
    assert excinfo.value.code == "invalid_header"


def test_extra_unexpected_column_rejected() -> None:
    text = HEADER + ",unexpected\n2026-01-01,BBCA,100,105,99,104,1000,x"
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(text.encode("utf-8"), bar_interval="1d", timezone_name="UTC")
    assert excinfo.value.code == "unexpected_column"


def test_non_utf8_bytes_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(b"\xff\xfe not utf-8", bar_interval="1d", timezone_name="UTC")
    assert excinfo.value.code == "unsupported_encoding"


def test_empty_file_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(b"", bar_interval="1d", timezone_name="UTC")
    assert excinfo.value.code == "empty_file"


def test_no_data_rows_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(HEADER.encode("utf-8"), bar_interval="1d", timezone_name="UTC")
    assert excinfo.value.code == "empty_file"


def test_malformed_row_rejected() -> None:
    text = HEADER + "\n2026-01-01,BBCA,100,105,99,104"
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(text.encode("utf-8"), bar_interval="1d", timezone_name="UTC")
    assert excinfo.value.code == "malformed_row"


def test_empty_instrument_identifier_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(_csv("2026-01-01,,100,105,99,104,1000"), bar_interval="1d", timezone_name="UTC")
    assert excinfo.value.code == "invalid_instrument_identifier"


@pytest.mark.parametrize("value", ["abc", "-1", "0", "NaN", "Infinity"])
def test_invalid_decimal_rejected(value: str) -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(
            _csv(f"2026-01-01,BBCA,{value},105,99,104,1000"),
            bar_interval="1d",
            timezone_name="UTC",
        )
    assert excinfo.value.code == "invalid_decimal"


def test_invalid_ohlc_relationship_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(
            _csv("2026-01-01,BBCA,100,101,99,200,1000"), bar_interval="1d", timezone_name="UTC"
        )
    assert excinfo.value.code == "invalid_ohlc_relationship"


@pytest.mark.parametrize("value", ["-1", "1.5", "abc"])
def test_invalid_volume_rejected(value: str) -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(
            _csv(f"2026-01-01,BBCA,100,105,99,104,{value}"),
            bar_interval="1d",
            timezone_name="UTC",
        )
    assert excinfo.value.code == "invalid_volume"


def test_duplicate_row_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(
            _csv(
                "2026-01-01,BBCA,100,105,99,104,1000",
                "2026-01-01,BBCA,100,105,99,104,1000",
            ),
            bar_interval="1d",
            timezone_name="UTC",
        )
    assert excinfo.value.code == "duplicate_row"


def test_unsorted_rows_rejected() -> None:
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(
            _csv(
                "2026-01-02,BBCA,100,105,99,104,1000",
                "2026-01-01,BBCA,100,105,99,104,1000",
            ),
            bar_interval="1d",
            timezone_name="UTC",
        )
    assert excinfo.value.code == "unsorted_rows"


def test_optional_columns_are_captured() -> None:
    text = HEADER + ",source_row_id,currency\n2026-01-01,BBCA,100,105,99,104,1000,row-1,IDR"
    parsed = parse_csv(text.encode("utf-8"), bar_interval="1d", timezone_name="UTC")

    assert parsed.rows[0].source_row_id == "row-1"
    assert parsed.rows[0].currency == "IDR"


def test_row_number_reported_is_one_indexed_including_header() -> None:
    text = HEADER + "\n2026-01-01,BBCA,100,105,99,104,1000\n2026-01-02,BBCA,bad,105,99,104,1000"
    with pytest.raises(CsvContractViolation) as excinfo:
        parse_csv(text.encode("utf-8"), bar_interval="1d", timezone_name="UTC")
    assert excinfo.value.row_number == 3
