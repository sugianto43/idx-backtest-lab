import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from app.application.ports.strategy_spec_repository import StrategySpecRepository
from app.domain.checksum import canonical_json_bytes, compute_checksum
from app.domain.strategy_spec import (
    STRATEGY_SCHEMA_VERSION,
    SignalPolicy,
    StrategySpecV1,
    build_parameters,
)


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def _default_clock() -> datetime:
    return datetime.now(UTC)


def create_strategy_spec(
    repository: StrategySpecRepository,
    *,
    name: str,
    kind: str,
    parameters: Mapping[str, object],
    signal_time: str,
    eligible_after_bars: int,
    long_only: bool,
    id_factory: Callable[[], str] = _default_id_factory,
    clock: Callable[[], datetime] = _default_clock,
) -> StrategySpecV1:
    built_parameters = build_parameters(kind, parameters)
    signal_policy = SignalPolicy(
        signal_time=signal_time, eligible_after_bars=eligible_after_bars, long_only=long_only
    )

    strategy_id = id_factory()
    version = 1
    created_at = clock()

    canonical = {
        "schema_version": STRATEGY_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "version": version,
        "name": name,
        "kind": kind,
        "parameters": built_parameters.to_canonical_dict(),
        "signal_policy": signal_policy.to_canonical_dict(),
        "created_at_utc": created_at.isoformat().replace("+00:00", "Z"),
    }
    checksum = compute_checksum(canonical)
    canonical_json = canonical_json_bytes(canonical).decode("utf-8")

    spec = StrategySpecV1(
        strategy_id=strategy_id,
        version=version,
        schema_version=STRATEGY_SCHEMA_VERSION,
        name=name,
        kind=kind,
        parameters=built_parameters,
        signal_policy=signal_policy,
        created_at_utc=created_at,
        checksum=checksum,
        canonical_json=canonical_json,
    )
    return repository.create(spec)
