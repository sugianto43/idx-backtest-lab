# Strategy Authoring UX Contract

## Purpose

The strategy workflow lets researchers create and inspect versioned declarative strategy specifications. It must teach the v1 behavior and constraints instead of making a rule appear more expressive or executable than it is.

## Routes

| Route | Purpose |
| --- | --- |
| `/strategies` | Paginated strategy/version list with status and empty state. |
| `/strategies/new` | Create a v1 `sma_crossover` specification. |
| `/strategies/{strategy_id}/versions/{version}` | Immutable specification detail, checksum, and assumptions. |

## V1 authoring form

Expose only fields defined by `BACKTEST_MANIFEST_CONTRACT.md`:

- Strategy name.
- Fast and slow SMA windows.
- Price field fixed to `close` unless backend supports another allowed enum.
- Signal policy displayed as read-only: evaluate at bar close, eligible after slow window, long-only.

The form must explain that an upward crossover enters long and a downward crossover exits a current long position. It must state that strategy signals do not guarantee execution; run manifest execution uses next-bar-open fills.

## Validation and submission

Use client validation for immediate ergonomics (positive integers and `fast_window < slow_window`) while treating backend validation as authoritative. Inline errors must be associated with fields. Before submit, show a concise immutable-version notice. After success, route to immutable detail and show version/checksum returned by API.

Use safe error display/correlation ID behavior from TASK-009. Preserve safe user input after failure. A version conflict or unsupported field is not silently retried or transformed.

## Detail/list behavior

Show version, kind, parameters, signal policy, creation timestamp, checksum, and a plain-language semantics summary. Use structured data display for canonical specification without an editable control. List cards/rows never label a strategy as profitable, active, or executable until a specific completed run proves only that run’s behavior.

## Accessibility and integrity

Controls need labels, help text, focus/error management, keyboard operation, and non-color-only validation. Display formula/window descriptions without performing or previewing calculated signals. No browser-side strategy code evaluation, bar processing, chart, parameter sweep, or performance estimate.
