# API Conventions

## Versioning and shape

Product endpoints use `/api/v1`. JSON uses `snake_case`. ISO 8601 timestamps include timezone offsets; UTC is preferred. IDs are opaque strings. Money values are serialized as decimal strings alongside an ISO currency code, never as binary JSON numbers.

## Error contract

All handled errors return:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human-readable explanation.",
    "details": [],
    "correlation_id": "opaque-id"
  }
}
```

Error codes are stable, documented, and suitable for UI behavior. Do not expose stack traces or credentials.

## Resource rules

- Dataset and run artifacts are immutable once created.
- Create operations return a resource ID and the persisted manifest/version.
- Collection endpoints paginate and enforce validated limits.
- Destructive or mutable operations require a later explicit lifecycle policy; none are assumed in v1.

## Planned resources

`datasets`, `instruments`, `strategies`, `backtest-runs`, `artifacts`, and `comparisons`. Their exact payloads must be introduced task-by-task with contract tests.
