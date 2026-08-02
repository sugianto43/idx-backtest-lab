import json
from datetime import date

import pytest

from app.infrastructure.market_data.yahoo_finance_provider import (
    YAHOO_FINANCE_ADJUSTMENT_POLICY,
    YAHOO_FINANCE_LICENSE_REFERENCE,
    YAHOO_FINANCE_SOURCE_NAME,
    YahooFinanceFetchError,
    fetch_daily_ohlcv_csv,
)

# 2026-01-01T00:00:00Z and 2026-01-02T00:00:00Z
DAY1_EPOCH = 1767225600
DAY2_EPOCH = 1767312000


def _chart_payload(
    timestamps: list[int],
    opens: list[float | None],
    highs: list[float | None],
    lows: list[float | None],
    closes: list[float | None],
    volumes: list[int | None],
) -> bytes:
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": opens,
                                "high": highs,
                                "low": lows,
                                "close": closes,
                                "volume": volumes,
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    return json.dumps(payload).encode("utf-8")


def test_fetch_daily_ohlcv_csv_converts_to_exact_contract_format() -> None:
    def fake_fetch(ticker: str, start: date, end: date) -> bytes:
        assert ticker == "BBCA.JK"
        return _chart_payload(
            [DAY1_EPOCH, DAY2_EPOCH],
            [100.0, 104.0],
            [105.0, 110.0],
            [99.0, 103.0],
            [104.0, 109.0],
            [1000, 1500],
        )

    csv_bytes = fetch_daily_ohlcv_csv(
        "BBCA.JK", "BBCA", date(2026, 1, 1), date(2026, 1, 2), fetch=fake_fetch
    )

    assert csv_bytes == (
        b"timestamp,instrument_identifier,open,high,low,close,volume\n"
        b"2026-01-01,BBCA,100.0,105.0,99.0,104.0,1000\n"
        b"2026-01-02,BBCA,104.0,110.0,103.0,109.0,1500\n"
    )


def test_fetch_daily_ohlcv_csv_skips_null_placeholder_rows_without_fabricating() -> None:
    def fake_fetch(ticker: str, start: date, end: date) -> bytes:
        return _chart_payload(
            [DAY1_EPOCH, DAY2_EPOCH],
            [100.0, None],
            [105.0, None],
            [99.0, None],
            [104.0, None],
            [1000, None],
        )

    csv_bytes = fetch_daily_ohlcv_csv(
        "BBCA.JK", "BBCA", date(2026, 1, 1), date(2026, 1, 2), fetch=fake_fetch
    )

    assert csv_bytes == (
        b"timestamp,instrument_identifier,open,high,low,close,volume\n"
        b"2026-01-01,BBCA,100.0,105.0,99.0,104.0,1000\n"
    )


def test_fetch_daily_ohlcv_csv_raises_no_data_when_all_rows_are_null() -> None:
    def fake_fetch(ticker: str, start: date, end: date) -> bytes:
        return _chart_payload([DAY1_EPOCH], [None], [None], [None], [None], [None])

    with pytest.raises(YahooFinanceFetchError) as exc:
        fetch_daily_ohlcv_csv(
            "BBCA.JK", "BBCA", date(2026, 1, 1), date(2026, 1, 1), fetch=fake_fetch
        )
    assert exc.value.code == "no_data"


def test_fetch_daily_ohlcv_csv_raises_no_data_for_unknown_ticker() -> None:
    def fake_fetch(ticker: str, start: date, end: date) -> bytes:
        payload = {
            "chart": {
                "result": None,
                "error": {
                    "code": "Not Found",
                    "description": "No data found, symbol may be delisted",
                },
            }
        }
        return json.dumps(payload).encode("utf-8")

    with pytest.raises(YahooFinanceFetchError) as exc:
        fetch_daily_ohlcv_csv(
            "DOESNOTEXIST", "DOESNOTEXIST", date(2026, 1, 1), date(2026, 1, 1), fetch=fake_fetch
        )
    assert exc.value.code == "no_data"
    assert "delisted" in exc.value.message


def test_fetch_daily_ohlcv_csv_raises_malformed_response_on_invalid_json() -> None:
    def fake_fetch(ticker: str, start: date, end: date) -> bytes:
        return b"not json"

    with pytest.raises(YahooFinanceFetchError) as exc:
        fetch_daily_ohlcv_csv(
            "BBCA.JK", "BBCA", date(2026, 1, 1), date(2026, 1, 1), fetch=fake_fetch
        )
    assert exc.value.code == "malformed_response"


def test_license_and_source_constants_are_specific_and_non_empty() -> None:
    assert YAHOO_FINANCE_SOURCE_NAME == "Yahoo Finance"
    assert "non-commercial" in YAHOO_FINANCE_LICENSE_REFERENCE
    assert YAHOO_FINANCE_ADJUSTMENT_POLICY == "split_adjusted"
