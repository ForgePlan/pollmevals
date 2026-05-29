"""Deterministic component score derived from atomic binary requirements (RFC-004).

Formula (from RFC-004 §3 "Deterministic component derivation"):

    A_c = { r in requirements : r.check_type == "auto" and r.maps_to == component }
    P_c = { r in A_c : requirement_results[r.id].passed == True }
    component_score(component) = 10 * |P_c| / |A_c|

Applies only to components that have ≥1 auto requirement mapped to them.
A component with zero mapped auto requirements is NOT derived from this formula —
it keeps its existing tool-based derivation (coverage tool, lizard, eslint, etc.).

The weighted-sum formula in docs/04-runbook/08-scoring-contract.md is UNCHANGED.
This function derives the 0-10 value for one deterministic component slot only;
the caller assembles the final score via the unchanged weighted sum.

This is a pure function with no I/O or side effects — testable in isolation.
"""

from __future__ import annotations

from src.contracts.task import RequirementResult, TaskRequirement


def component_score(
    component: str,
    requirements: list[TaskRequirement],
    results: list[RequirementResult],
) -> float | None:
    """Compute the 0-10 score for one deterministic scoring component.

    Uses the binary pass-rate of all ``auto`` requirements that map to
    ``component``.  Returns ``None`` when no ``auto`` requirement maps to the
    given component — callers must fall back to the existing tool-based
    derivation in that case.

    Parameters
    ----------
    component:
        The weight_components key being scored, e.g. ``"correctness"``.
    requirements:
        All ``TaskRequirement`` items for this task version (from ``task.yaml``).
    results:
        All ``RequirementResult`` items produced by the evaluator for this eval
        (from ``evaluator_json.requirement_results``).

    Returns
    -------
    float | None
        A value in [0.0, 10.0] when ≥1 auto requirement maps to the component.
        ``None`` when no auto requirement maps to the component — the caller
        should skip this function and use the existing tool-based score.

    Examples
    --------
    >>> from src.contracts.task import TaskRequirement, RequirementResult
    >>> reqs = [
    ...     TaskRequirement(id="R1", text="t", check_type="auto",
    ...                     maps_to="correctness", prompt_ref=1),
    ...     TaskRequirement(id="R2", text="t", check_type="auto",
    ...                     maps_to="correctness", prompt_ref=1),
    ... ]
    >>> results = [
    ...     RequirementResult(id="R1", check_type="auto", passed=True),
    ...     RequirementResult(id="R2", check_type="auto", passed=False),
    ... ]
    >>> component_score("correctness", reqs, results)
    5.0
    """
    # A_c: auto requirements mapped to this component
    auto_reqs = [r for r in requirements if r.check_type == "auto" and r.maps_to == component]

    if not auto_reqs:
        # No auto requirements for this component — caller uses tool-based derivation.
        return None

    # Index results by id for O(1) lookup.
    result_by_id: dict[str, RequirementResult] = {res.id: res for res in results}

    # P_c: auto requirements that passed.
    passed_count = sum(
        1
        for req in auto_reqs
        if result_by_id.get(req.id) is not None and result_by_id[req.id].passed is True
    )

    # Score = 10 × |P_c| / |A_c|.  |A_c| >= 1 guaranteed by the guard above.
    return 10.0 * passed_count / len(auto_reqs)
