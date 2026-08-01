import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.application.errors import CsvContractViolation
from app.application.ports.csv_parser import CsvParser, ParsedImport, ParsedRow

REQUIRED_COLUMNS = ("timestamp", "instrument_identifier", "open", "high", "low", "close", "volume")
OPTIONAL_COLUMNS = ("source_row_id", "currency")


def _decode(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CsvContractViolation("unsupported_encoding", "File must be UTF-8 encoded.") from exc


def _validate_header(header: list[str]) -> None:
    if (
        len(header) < len(REQUIRED_COLUMNS)
        or tuple(header[: len(REQUIRED_COLUMNS)]) != REQUIRED_COLUMNS
    ):
        raise CsvContractViolation(
            "invalid_header",
            f"Header must start with columns: {', '.join(REQUIRED_COLUMNS)}.",
        )
    extra = header[len(REQUIRED_COLUMNS) :]
    if len(extra) != len(set(extra)) or any(column not in OPTIONAL_COLUMNS for column in extra):
        raise CsvContractViolation(
            "unexpected_column",
            "Only source_row_id and currency are allowed as additional columns.",
        )


def _parse_decimal(value: str, field: str, row_number: int) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise CsvContractViolation(
            "invalid_decimal", f"{field} is not a valid decimal value.", row_number
        ) from exc
    if not parsed.is_finite() or parsed <= 0:
        raise CsvContractViolation(
            "invalid_decimal", f"{field} must be a finite positive decimal value.", row_number
        )
    return parsed


def _parse_volume(value: str, row_number: int) -> int:
    if not value.isdigit():
        raise CsvContractViolation(
            "invalid_volume", "volume must be a non-negative whole number.", row_number
        )
    return int(value)


def _parse_date_only_timestamp(
    value: str, *, timezone_name: str, row_number: int
) -> datetime | None:
    try:
        parsed_date = date.fromisoformat(value)
    except ValueError:
        return None

    try:
        tzinfo = UTC if timezone_name == "UTC" else ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise CsvContractViolation(
            "invalid_timezone", f"Unknown timezone: {timezone_name}.", row_number
        ) from exc
    naive_midnight = datetime(parsed_date.year, parsed_date.month, parsed_date.day)
    return naive_midnight.replace(tzinfo=tzinfo).astimezone(UTC)


def _parse_offset_timestamp(value: str, row_number: int) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CsvContractViolation(
            "invalid_timestamp", f"Invalid timestamp: {value}.", row_number
        ) from exc
    if parsed.tzinfo is None:
        raise CsvContractViolation(
            "invalid_timestamp", "Timestamp must include an explicit UTC offset.", row_number
        )
    return parsed.astimezone(UTC)


def _parse_timestamp(
    value: str, *, bar_interval: str, timezone_name: str, row_number: int
) -> datetime:
    if bar_interval == "1d":
        date_only = _parse_date_only_timestamp(
            value, timezone_name=timezone_name, row_number=row_number
        )
        if date_only is not None:
            return date_only
    return _parse_offset_timestamp(value, row_number)


def _require_ohlc_relationship(
    *, open_: Decimal, high: Decimal, low: Decimal, close: Decimal, row_number: int
) -> None:
    if not (low <= open_ <= high and low <= close <= high):
        raise CsvContractViolation(
            "invalid_ohlc_relationship",
            "Row violates low <= open,close <= high.",
            row_number,
        )


def _parse_row(
    row_number: int,
    header: list[str],
    raw_row: list[str],
    *,
    bar_interval: str,
    timezone_name: str,
) -> ParsedRow:
    if len(raw_row) != len(header):
        raise CsvContractViolation(
            "malformed_row", "Row has an unexpected number of columns.", row_number
        )

    values = dict(zip(header, raw_row, strict=True))

    instrument_identifier = values["instrument_identifier"].strip()
    if not instrument_identifier:
        raise CsvContractViolation(
            "invalid_instrument_identifier",
            "instrument_identifier must not be empty.",
            row_number,
        )

    timestamp_utc = _parse_timestamp(
        values["timestamp"],
        bar_interval=bar_interval,
        timezone_name=timezone_name,
        row_number=row_number,
    )

    open_ = _parse_decimal(values["open"], "open", row_number)
    high = _parse_decimal(values["high"], "high", row_number)
    low = _parse_decimal(values["low"], "low", row_number)
    close = _parse_decimal(values["close"], "close", row_number)
    _require_ohlc_relationship(open_=open_, high=high, low=low, close=close, row_number=row_number)

    volume = _parse_volume(values["volume"], row_number)

    return ParsedRow(
        row_number=row_number,
        instrument_identifier=instrument_identifier,
        timestamp_utc=timestamp_utc,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        currency=(values.get("currency") or "").strip() or None,
        source_row_id=(values.get("source_row_id") or "").strip() or None,
        zero_volume=volume == 0,
    )


def _require_unique_and_sorted(
    row: ParsedRow,
    *,
    seen_keys: set[tuple[str, datetime]],
    last_timestamp_by_instrument: dict[str, datetime],
) -> None:
    key = (row.instrument_identifier, row.timestamp_utc)
    if key in seen_keys:
        raise CsvContractViolation(
            "duplicate_row",
            "Duplicate (instrument_identifier, timestamp) row.",
            row.row_number,
        )
    seen_keys.add(key)

    previous_timestamp = last_timestamp_by_instrument.get(row.instrument_identifier)
    if previous_timestamp is not None and row.timestamp_utc <= previous_timestamp:
        raise CsvContractViolation(
            "unsorted_rows",
            "Rows must be strictly chronological per instrument.",
            row.row_number,
        )
    last_timestamp_by_instrument[row.instrument_identifier] = row.timestamp_utc


def parse_csv(raw_bytes: bytes, *, bar_interval: str, timezone_name: str) -> ParsedImport:
    text = _decode(raw_bytes)
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise CsvContractViolation("empty_file", "File has no header row.") from exc

    _validate_header(header)

    rows: list[ParsedRow] = []
    seen_keys: set[tuple[str, datetime]] = set()
    last_timestamp_by_instrument: dict[str, datetime] = {}

    row_number = 1
    for raw_row in reader:
        row_number += 1
        row = _parse_row(
            row_number, header, raw_row, bar_interval=bar_interval, timezone_name=timezone_name
        )
        _require_unique_and_sorted(
            row, seen_keys=seen_keys, last_timestamp_by_instrument=last_timestamp_by_instrument
        )
        rows.append(row)

    if not rows:
        raise CsvContractViolation("empty_file", "File has no data rows.")

    return ParsedImport(rows=rows)


class DelimitedCsvParser(CsvParser):
    def parse(self, raw_bytes: bytes, *, bar_interval: str, timezone_name: str) -> ParsedImport:
        return parse_csv(raw_bytes, bar_interval=bar_interval, timezone_name=timezone_name)
