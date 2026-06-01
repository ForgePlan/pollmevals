"""pass@k (capability ceiling) and pass^k (reliability) over N independent runs.

Prior art — SWE-rebench (Nebius, 2026): their leaderboard reports **pass@k**
(a task counts if solved in AT LEAST ONE of k independent runs — the capability
ceiling) *and* the article reports **pass^k** (a task counts only if solved in
ALL k runs — reliability / consistency). The gap between them is the "flakiness"
band: tasks a stack solves *sometimes* but not *every* time — i.e. it got lucky.

These pair with the best-of-N capability aggregates (PRD-009):
    - pass@k   = ceiling  (best-of-k; rewards "can it ever do it")
    - pass^k   = floor    (reliability; rewards "does it do it consistently")
    - flaky    = pass@k - pass^k  (the got-lucky-once band)

A "cell" is the list of per-seed solved/not-solved booleans for ONE
(model, stack, task) across k independent runs (seeds). What counts as *solved*
is task-type-dependent and decided by the CALLER (e.g. all auto-MUST
requirements passed, or final_score >= threshold, or SWE-bench FAIL_TO_PASS
green) — these functions take the booleans and do only the aggregation, so the
metric stays orthogonal to the scoring policy.

Not a methodology-policy change on its own: the *decision* to publish pass^k and
any threshold live in the methodology (ADR + MethodologyVersion). This module is
the pure math those policies call.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

__all__ = [
    "flaky_fraction",
    "pass_at_k",
    "pass_at_k_estimator",
    "pass_hat_k",
    "solved_at_least_once",
    "solved_every_time",
]


# ---------------------------------------------------------------------------
# Cell-level predicates (one (model, stack, task) across its k seeds)
# ---------------------------------------------------------------------------


def solved_at_least_once(per_seed_solved: Sequence[bool]) -> bool:
    """pass@k at the cell level: solved in >= 1 of the k runs (capability ceiling).

    Empty input -> False (a cell with no runs was not solved).
    """
    return any(per_seed_solved)


def solved_every_time(per_seed_solved: Sequence[bool]) -> bool:
    """pass^k at the cell level: solved in ALL k runs (reliability).

    Empty input -> False (cannot claim consistency with zero runs; ``all([])`` is
    vacuously True, which would over-credit a cell that never ran).
    """
    return len(per_seed_solved) > 0 and all(per_seed_solved)


# ---------------------------------------------------------------------------
# Set-level aggregates (over many cells = a task set)
# ---------------------------------------------------------------------------


def pass_at_k(cells: Sequence[Sequence[bool]]) -> float:
    """Fraction of cells solved at least once (the leaderboard 'Pass@k', 0.0-1.0)."""
    if not cells:
        return 0.0
    return sum(1 for cell in cells if solved_at_least_once(cell)) / len(cells)


def pass_hat_k(cells: Sequence[Sequence[bool]]) -> float:
    """Fraction of cells solved EVERY time (reliability — SWE-rebench 'pass^k', 0.0-1.0)."""
    if not cells:
        return 0.0
    return sum(1 for cell in cells if solved_every_time(cell)) / len(cells)


def flaky_fraction(cells: Sequence[Sequence[bool]]) -> float:
    """``pass@k - pass^k``: fraction of cells that are FLAKY (solved sometimes, not always).

    The "got lucky once" band. High value => the stack relies on luck rather than
    consistent capability. Always >= 0 (every all-solved cell is also solved-once).
    """
    return pass_at_k(cells) - pass_hat_k(cells)


# ---------------------------------------------------------------------------
# Unbiased pass@k estimator (Chen et al. 2021 / SWE-bench / HumanEval)
# ---------------------------------------------------------------------------


def pass_at_k_estimator(n: int, c: int, k: int) -> float:
    """Unbiased pass@k for ``n`` samples with ``c`` correct, choosing ``k`` (k <= n).

    Use this when you generated ``n`` samples but want to report pass@k for a
    smaller k (reduces variance vs the naive any-of-k over a single draw). For
    ``n == k`` it collapses to ``1.0 if c > 0 else 0.0`` (== a single
    :func:`solved_at_least_once` over all k).

    Formula (Chen et al. 2021, "Evaluating LLMs Trained on Code"):
        pass@k = 1 - C(n - c, k) / C(n, k)

    Args:
        n: total independent samples generated for the cell (n >= 1).
        c: number of those samples that were correct (0 <= c <= n).
        k: the k to report (1 <= k <= n).

    Returns:
        Unbiased probability in [0.0, 1.0] that a random k-subset contains a
        correct sample.

    Raises:
        ValueError: if the constraints ``0 < k <= n`` or ``0 <= c <= n`` are violated.
    """
    if not (0 < k <= n):
        raise ValueError(f"require 0 < k <= n; got n={n}, k={k}")
    if not (0 <= c <= n):
        raise ValueError(f"require 0 <= c <= n; got c={c}, n={n}")
    # If fewer than k samples are wrong, every k-subset must contain a correct one.
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)
