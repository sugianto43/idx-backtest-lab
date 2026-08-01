# Instrument and Corporate-Action Contract

## Instrument identity

An `instrument_id` is an opaque immutable internal identifier. A ticker/symbol is an alias, never a primary key. The initial scope supports equities only; instrument type must be explicit and validated as `equity`.

Each instrument record has a display name, currency (when known), status (`active`, `suspended`, `delisted`, `unknown`), source provenance, and created timestamp. Unknown facts must remain unknown; do not derive listing status from absent bars.

## Ticker aliases

An alias has `symbol`, `exchange_code` (initially `IDX` only), `effective_from`, optional `effective_to`, source reference, and confidence/status. Date ranges for a symbol on the same exchange must not overlap across different resolved instruments unless a documented ambiguity record explicitly permits it.

Use source identifiers from a dataset as unresolved aliases first. A mapping resolves an identifier only for its applicable effective date range. A later mapping never rewrites the original raw source identifier.

## Corporate-action records

An event is immutable and belongs to one resolved instrument. Required fields:

| Field | Requirement |
| --- | --- |
| `event_id` | Opaque immutable identifier. |
| `instrument_id` | Resolved internal instrument identity. |
| `event_type` | `cash_dividend`, `stock_dividend`, `stock_split`, `reverse_split`, `rights_issue`, `ticker_change`, `delisting`, or `other`. |
| `effective_date` | Required exchange-local date. |
| `announcement_date` | Optional date; never inferred. |
| `status` | `reported`, `verified`, `superseded`, or `rejected`. |
| `source_name` / `source_reference` | Required provenance, no credentials. |
| `payload_json` | Type-specific values as received/normalized; preserve units/currency and avoid financial defaults. |
| `created_at_utc` | Required UTC timestamp. |

The first implementation records and exposes events only. It does not calculate adjusted prices, dividend cashflows, share changes, rights valuation, or delisting proceeds.

## Integrity rules

- A corporate action cannot be attached to an unresolved/ambiguous instrument.
- A correction is a new superseding event, retaining the prior event and provenance.
- `ticker_change` creates/updates effective-dated aliases only with source evidence and no overlapping mapping.
- Event type-specific fields must be validated structurally but not assigned assumed financial values.
- Dataset metadata must state whether imported bars are raw or pre-adjusted independently of recorded events.
