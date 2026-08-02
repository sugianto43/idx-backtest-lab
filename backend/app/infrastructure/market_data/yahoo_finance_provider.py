import json
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

CSV_HEADER = "timestamp,instrument_identifier,open,high,low,close,volume"

# Personal, non-commercial research use only -- see ADR-010. Never caller-editable.
YAHOO_FINANCE_SOURCE_NAME = "Yahoo Finance"
YAHOO_FINANCE_LICENSE_REFERENCE = (
    "Yahoo Finance Terms of Service (personal, non-commercial use only; "
    "redistribution prohibited): https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html"
)
YAHOO_FINANCE_ADJUSTMENT_POLICY = "split_adjusted"

_CHART_URL_TEMPLATE = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


class YahooFinanceFetchError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _default_fetch(ticker: str, start: date, end: date) -> bytes:
    period1 = int(datetime(start.year, start.month, start.day, tzinfo=UTC).timestamp())
    period2 = int(datetime(end.year, end.month, end.day, tzinfo=UTC).timestamp()) + 86400
    url = (
        f"{_CHART_URL_TEMPLATE.format(ticker=ticker)}"
        f"?period1={period1}&period2={period2}&interval=1d&events=history"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read()  # type: ignore[no-any-return]
    except urllib.error.URLError as exc:
        raise YahooFinanceFetchError(
            "fetch_failed", f"Could not reach Yahoo Finance: {exc}"
        ) from exc


def _format_decimal(value: float) -> str:
    """Formats a value exactly as received from Yahoo's JSON payload -- Yahoo itself already
    serializes OHLC as floats, so no more precision than that is recoverable; this performs no
    arithmetic, only string formatting of the value already given."""
    return format(Decimal(str(value)), "f")


def _parse_chart_payload(raw: bytes) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise YahooFinanceFetchError(
            "malformed_response", "Yahoo Finance returned a response that could not be parsed."
        ) from exc

    try:
        result: dict[str, Any] = payload["chart"]["result"][0]
    except (KeyError, IndexError, TypeError) as exc:
        error = payload.get("chart", {}).get("error") if isinstance(payload, dict) else None
        description = error.get("description") if isinstance(error, dict) else None
        message = (
            str(description)
            if description
            else "Yahoo Finance returned no data for this ticker/date range."
        )
        raise YahooFinanceFetchError("no_data", message) from exc
    return result


def fetch_daily_ohlcv_csv(
    ticker: str,
    instrument_identifier: str,
    start: date,
    end: date,
    *,
    fetch: Callable[[str, date, date], bytes] = _default_fetch,
) -> bytes:
    """Fetches daily OHLCV bars for `ticker` and returns them as bytes conforming exactly to
    docs/CSV_INGESTION_CONTRACT.md, ready to pass to the existing dataset import use case."""
    result = _parse_chart_payload(fetch(ticker, start, end))

    timestamps: list[int] = result.get("timestamp") or []
    quote: dict[str, list[float | None]] = result["indicators"]["quote"][0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    lines = [CSV_HEADER]
    for index, ts in enumerate(timestamps):
        o, h, low_, c, v = opens[index], highs[index], lows[index], closes[index], volumes[index]
        if o is None or h is None or low_ is None or c is None or v is None:
            # Yahoo returns null OHLCV for non-trading placeholder timestamps; skip rather
            # than fabricate a bar.
            continue
        bar_date = datetime.fromtimestamp(ts, tz=UTC).date().isoformat()
        lines.append(
            f"{bar_date},{instrument_identifier},{_format_decimal(o)},{_format_decimal(h)},"
            f"{_format_decimal(low_)},{_format_decimal(c)},{int(v)}"
        )

    if len(lines) == 1:
        raise YahooFinanceFetchError(
            "no_data", "Yahoo Finance returned no trading bars for this ticker/date range."
        )

    return ("\n".join(lines) + "\n").encode("utf-8")
