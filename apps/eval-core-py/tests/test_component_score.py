"""Unit tests for component_score — the deterministic requirement pass-rate formula (RFC-004).

Tests cover:
- Happy path: mixed pass/fail → correct fractional score.
- All passed → 10.0.
- All failed → 0.0.
- Zero auto requirements for the component → None (caller skips, uses tool-based derivation).
- Judge-only requirements for the component → None (no auto = no score derivation).
- Results with extra ids (unrelated components) do not affect the target component.
- Missing result for an auto requirement → treated as not-passed (conservative).
- Single requirement passed / failed.
"""

from __future__ import annotations

import pytest

from src.contracts.task import RequirementResult, TaskRequirement
from src.scoring import component_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _req(id: str, check_type: str, maps_to: str = "correctness") -> TaskRequirement:
    return TaskRequirement(
        id=id,
        text=f"Requirement {id}",
        check_type=check_type,  # type: ignore[arg-type]
        maps_to=maps_to,
        prompt_ref=1,
    )


def _result(id: str, check_type: str, passed: bool | None) -> RequirementResult:
    return RequirementResult(
        id=id,
        check_type=check_type,  # type: ignore[arg-type]
        passed=passed,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestComponentScoreHappyPath:
    def test_half_pass_returns_5(self) -> None:
        reqs = [_req("R1", "auto"), _req("R2", "auto")]
        results = [_result("R1", "auto", True), _result("R2", "auto", False)]
        assert component_score("correctness", reqs, results) == 5.0

    def test_all_pass_returns_10(self) -> None:
        reqs = [_req("R1", "auto"), _req("R2", "auto"), _req("R3", "auto")]
        results = [
            _result("R1", "auto", True),
            _result("R2", "auto", True),
            _result("R3", "auto", True),
        ]
        assert component_score("correctness", reqs, results) == 10.0

    def test_all_fail_returns_0(self) -> None:
        reqs = [_req("R1", "auto"), _req("R2", "auto")]
        results = [_result("R1", "auto", False), _result("R2", "auto", False)]
        assert component_score("correctness", reqs, results) == 0.0

    def test_single_requirement_passed(self) -> None:
        reqs = [_req("R1", "auto")]
        results = [_result("R1", "auto", True)]
        assert component_score("correctness", reqs, results) == 10.0

    def test_single_requirement_failed(self) -> None:
        reqs = [_req("R1", "auto")]
        results = [_result("R1", "auto", False)]
        assert component_score("correctness", reqs, results) == 0.0

    def test_fractional_score_precision(self) -> None:
        # 1 of 3 passed = 10/3 ≈ 3.333...
        reqs = [_req("R1", "auto"), _req("R2", "auto"), _req("R3", "auto")]
        results = [
            _result("R1", "auto", True),
            _result("R2", "auto", False),
            _result("R3", "auto", False),
        ]
        score = component_score("correctness", reqs, results)
        assert score is not None
        assert abs(score - 10.0 / 3.0) < 1e-9


# ---------------------------------------------------------------------------
# Zero auto requirements → None (no derivation from formula)
# ---------------------------------------------------------------------------


class TestComponentScoreNoAutoReqs:
    def test_empty_requirements_returns_none(self) -> None:
        result = component_score("correctness", [], [])
        assert result is None

    def test_judge_only_requirements_returns_none(self) -> None:
        # All requirements for this component are judge-only — no auto, no derivation.
        reqs = [
            _req("R1", "judge", "correctness"),
            _req("R2", "judge", "correctness"),
        ]
        results = [
            _result("R1", "judge", None),
            _result("R2", "judge", None),
        ]
        result = component_score("correctness", reqs, results)
        assert result is None

    def test_auto_reqs_mapped_to_different_component_returns_none(self) -> None:
        # Auto requirements exist, but mapped to a different component.
        reqs = [_req("R1", "auto", "type_safety")]
        results = [_result("R1", "auto", True)]
        result = component_score("correctness", reqs, results)
        assert result is None


# ---------------------------------------------------------------------------
# Isolation: other components / judge requirements do not pollute the score
# ---------------------------------------------------------------------------


class TestComponentScoreIsolation:
    def test_results_from_other_components_ignored(self) -> None:
        reqs = [
            _req("R1", "auto", "correctness"),
            _req("R2", "auto", "type_safety"),  # different component
        ]
        results = [
            _result("R1", "auto", True),
            _result("R2", "auto", False),  # should NOT affect correctness score
        ]
        score = component_score("correctness", reqs, results)
        assert score == 10.0  # only R1 counts, it passed

    def test_judge_requirements_mixed_with_auto_excluded(self) -> None:
        # R1 = auto/correctness, R2 = judge/correctness. Only R1 should count.
        reqs = [
            _req("R1", "auto", "correctness"),
            _req("R2", "judge", "correctness"),
        ]
        results = [
            _result("R1", "auto", True),
            _result("R2", "judge", None),  # judge: recorded-only
        ]
        score = component_score("correctness", reqs, results)
        assert score == 10.0  # only R1 (auto) counts

    def test_extra_result_ids_not_in_requirements_ignored(self) -> None:
        reqs = [_req("R1", "auto")]
        results = [
            _result("R1", "auto", False),
            _result("R99", "auto", True),  # not in requirements list
        ]
        score = component_score("correctness", reqs, results)
        assert score == 0.0  # only R1 counts, it failed


# ---------------------------------------------------------------------------
# Missing result treated as not-passed (conservative)
# ---------------------------------------------------------------------------


class TestComponentScoreMissingResult:
    def test_missing_result_for_auto_requirement_counts_as_fail(self) -> None:
        # R1 has no corresponding entry in results — treated as not-passed.
        reqs = [_req("R1", "auto"), _req("R2", "auto")]
        results = [_result("R2", "auto", True)]  # R1 missing
        score = component_score("correctness", reqs, results)
        # R1 = fail (missing), R2 = pass → 1/2 = 5.0
        assert score == 5.0

    def test_all_results_missing_returns_0(self) -> None:
        reqs = [_req("R1", "auto"), _req("R2", "auto")]
        score = component_score("correctness", reqs, [])
        assert score == 0.0


# ---------------------------------------------------------------------------
# Return type is float (not int) when formula yields a whole number
# ---------------------------------------------------------------------------


class TestComponentScoreReturnType:
    def test_all_pass_returns_float_not_int(self) -> None:
        reqs = [_req("R1", "auto")]
        results = [_result("R1", "auto", True)]
        score = component_score("correctness", reqs, results)
        assert isinstance(score, float)

    def test_none_returned_for_zero_auto_reqs(self) -> None:
        result = component_score("correctness", [], [])
        assert result is None


# ---------------------------------------------------------------------------
# Score is bounded [0.0, 10.0]
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_passed,n_total", [(0, 1), (1, 1), (3, 7), (10, 10)])
def test_score_in_valid_range(n_passed: int, n_total: int) -> None:
    reqs = [_req(f"R{i}", "auto") for i in range(1, n_total + 1)]
    results = [
        _result(f"R{i}", "auto", i <= n_passed) for i in range(1, n_total + 1)
    ]
    score = component_score("correctness", reqs, results)
    assert score is not None
    assert 0.0 <= score <= 10.0
