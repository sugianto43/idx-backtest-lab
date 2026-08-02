from datetime import date
from decimal import Decimal

import pytest

from app.domain.optimization import (
    CandidateSelectionInput,
    OptimizationValidationError,
    canonicalize_grid,
    is_valid_candidate_pair,
    select_candidate,
    validate_candidate_count,
    validate_grid_inputs,
    validate_objective_metric,
    validate_partition_bar_coverage,
    validate_partitions,
)


def test_canonicalize_grid_is_sorted_lexicographic_and_deduped() -> None:
    pairs = canonicalize_grid([5, 2, 2], [10, 3])

    assert pairs == [(2, 3), (2, 10), (5, 3), (5, 10)]


def test_canonicalize_grid_is_independent_of_input_order() -> None:
    assert canonicalize_grid([5, 2], [10, 3]) == canonicalize_grid([2, 5], [3, 10])


def test_validate_grid_inputs_rejects_empty_lists() -> None:
    with pytest.raises(OptimizationValidationError) as exc:
        validate_grid_inputs([], [3])
    assert exc.value.code == "invalid_grid"


def test_validate_grid_inputs_rejects_non_positive_window() -> None:
    with pytest.raises(OptimizationValidationError):
        validate_grid_inputs([0, 2], [3])


def test_is_valid_candidate_pair_requires_fast_less_than_slow() -> None:
    assert is_valid_candidate_pair(2, 3) is True
    assert is_valid_candidate_pair(3, 3) is False
    assert is_valid_candidate_pair(5, 3) is False


def test_validate_partitions_accepts_chronological_non_overlapping_ranges() -> None:
    validate_partitions(
        train_start=date(2020, 1, 1),
        train_end=date(2020, 6, 30),
        validation_start=date(2020, 7, 1),
        validation_end=date(2020, 9, 30),
        holdout_start=date(2020, 10, 1),
        holdout_end=date(2020, 12, 31),
    )


def test_validate_partitions_rejects_overlap() -> None:
    with pytest.raises(OptimizationValidationError) as exc:
        validate_partitions(
            train_start=date(2020, 1, 1),
            train_end=date(2020, 7, 15),
            validation_start=date(2020, 7, 1),
            validation_end=date(2020, 9, 30),
            holdout_start=date(2020, 10, 1),
            holdout_end=date(2020, 12, 31),
        )
    assert exc.value.code == "invalid_partitions"


def test_validate_partitions_rejects_reversed_dates() -> None:
    with pytest.raises(OptimizationValidationError):
        validate_partitions(
            train_start=date(2020, 6, 30),
            train_end=date(2020, 1, 1),
            validation_start=date(2020, 7, 1),
            validation_end=date(2020, 9, 30),
            holdout_start=date(2020, 10, 1),
            holdout_end=date(2020, 12, 31),
        )


def test_validate_objective_metric_rejects_unsupported_key() -> None:
    with pytest.raises(OptimizationValidationError) as exc:
        validate_objective_metric("sharpe_ratio")
    assert exc.value.code == "unsupported_objective"


def test_validate_objective_metric_accepts_documented_key() -> None:
    validate_objective_metric("total_return")


def test_validate_candidate_count_rejects_oversized_grid() -> None:
    with pytest.raises(OptimizationValidationError) as exc:
        validate_candidate_count(51, 50)
    assert exc.value.code == "candidate_grid_too_large"


def test_validate_partition_bar_coverage_rejects_insufficient_bars() -> None:
    with pytest.raises(OptimizationValidationError) as exc:
        validate_partition_bar_coverage(partition_name="train", bar_count=5, largest_slow_window=10)
    assert exc.value.code == "insufficient_partition_coverage"


def test_validate_partition_bar_coverage_accepts_exact_minimum() -> None:
    validate_partition_bar_coverage(partition_name="train", bar_count=12, largest_slow_window=10)


def test_select_candidate_returns_none_when_no_objective_available() -> None:
    candidates = [
        CandidateSelectionInput(
            candidate_id="c1", fast_window=2, slow_window=3, objective_value=None
        ),
    ]
    assert select_candidate(candidates) is None


def test_select_candidate_picks_highest_objective_value() -> None:
    candidates = [
        CandidateSelectionInput(
            candidate_id="c1", fast_window=2, slow_window=3, objective_value=Decimal("0.05")
        ),
        CandidateSelectionInput(
            candidate_id="c2", fast_window=4, slow_window=6, objective_value=Decimal("0.12")
        ),
        CandidateSelectionInput(
            candidate_id="c3", fast_window=2, slow_window=5, objective_value=None
        ),
    ]
    selected = select_candidate(candidates)
    assert selected is not None
    assert selected.candidate_id == "c2"


def test_select_candidate_tie_break_prefers_lower_slow_window_then_lower_fast_window() -> None:
    candidates = [
        CandidateSelectionInput(
            candidate_id="c-high-slow",
            fast_window=2,
            slow_window=10,
            objective_value=Decimal("0.10"),
        ),
        CandidateSelectionInput(
            candidate_id="c-low-slow-high-fast",
            fast_window=5,
            slow_window=6,
            objective_value=Decimal("0.10"),
        ),
        CandidateSelectionInput(
            candidate_id="c-low-slow-low-fast",
            fast_window=2,
            slow_window=6,
            objective_value=Decimal("0.10"),
        ),
    ]
    selected = select_candidate(candidates)
    assert selected is not None
    assert selected.candidate_id == "c-low-slow-low-fast"


def test_select_candidate_final_tie_break_is_candidate_id() -> None:
    candidates = [
        CandidateSelectionInput(
            candidate_id="c2", fast_window=2, slow_window=6, objective_value=Decimal("0.10")
        ),
        CandidateSelectionInput(
            candidate_id="c1", fast_window=2, slow_window=6, objective_value=Decimal("0.10")
        ),
    ]
    selected = select_candidate(candidates)
    assert selected is not None
    assert selected.candidate_id == "c1"
