"""Tests for src.scoring.pass_k — pass@k / pass^k / flakiness aggregation."""

from __future__ import annotations

from itertools import pairwise

import pytest

from src.scoring import (
    flaky_fraction,
    pass_at_k,
    pass_at_k_estimator,
    pass_hat_k,
    solved_at_least_once,
    solved_every_time,
)

# Reference cells (one (model, stack, task) across its seeds)
_ALL = [True, True, True]  # solved every time
_FLAKY = [True, False, True]  # solved sometimes (lucky)
_NEVER = [False, False, False]  # never solved
_SINGLE_OK = [True]  # one run, passed
_EMPTY: list[bool] = []  # no runs


# ---------------------------------------------------------------------------
# Cell-level predicates
# ---------------------------------------------------------------------------


class TestSolvedAtLeastOnce:
    def test_all_pass(self) -> None:
        assert solved_at_least_once(_ALL) is True

    def test_flaky_counts(self) -> None:
        assert solved_at_least_once(_FLAKY) is True

    def test_never(self) -> None:
        assert solved_at_least_once(_NEVER) is False

    def test_empty_is_false(self) -> None:
        assert solved_at_least_once(_EMPTY) is False


class TestSolvedEveryTime:
    def test_all_pass(self) -> None:
        assert solved_every_time(_ALL) is True

    def test_flaky_fails(self) -> None:
        assert solved_every_time(_FLAKY) is False

    def test_never(self) -> None:
        assert solved_every_time(_NEVER) is False

    def test_single_ok(self) -> None:
        assert solved_every_time(_SINGLE_OK) is True

    def test_empty_is_false_not_vacuously_true(self) -> None:
        # all([]) is True in Python; we must NOT over-credit a cell that never ran.
        assert solved_every_time(_EMPTY) is False


# ---------------------------------------------------------------------------
# Set-level aggregates
# ---------------------------------------------------------------------------


class TestSetLevel:
    def test_mixed_set(self) -> None:
        cells = [_ALL, _FLAKY, _NEVER]
        assert pass_at_k(cells) == pytest.approx(2 / 3)  # ALL + FLAKY solved once
        assert pass_hat_k(cells) == pytest.approx(1 / 3)  # only ALL every time
        assert flaky_fraction(cells) == pytest.approx(1 / 3)  # FLAKY band

    def test_ceiling_ge_reliability(self) -> None:
        cells = [_ALL, _FLAKY, _NEVER, _SINGLE_OK]
        assert pass_at_k(cells) >= pass_hat_k(cells)
        assert flaky_fraction(cells) >= 0.0

    def test_all_reliable(self) -> None:
        cells = [_ALL, _SINGLE_OK]
        assert pass_at_k(cells) == pytest.approx(1.0)
        assert pass_hat_k(cells) == pytest.approx(1.0)
        assert flaky_fraction(cells) == pytest.approx(0.0)

    def test_empty_set(self) -> None:
        assert pass_at_k([]) == 0.0
        assert pass_hat_k([]) == 0.0
        assert flaky_fraction([]) == 0.0


# ---------------------------------------------------------------------------
# Unbiased pass@k estimator
# ---------------------------------------------------------------------------


class TestPassAtKEstimator:
    def test_zero_correct(self) -> None:
        assert pass_at_k_estimator(n=5, c=0, k=5) == pytest.approx(0.0)

    def test_one_correct_k_equals_n(self) -> None:
        # n-c = 4 < k = 5 -> every 5-subset contains the one correct -> 1.0
        assert pass_at_k_estimator(n=5, c=1, k=5) == pytest.approx(1.0)

    def test_collapses_to_c_gt_0_when_k_equals_n(self) -> None:
        assert pass_at_k_estimator(n=3, c=2, k=3) == pytest.approx(1.0)
        assert pass_at_k_estimator(n=3, c=0, k=3) == pytest.approx(0.0)

    def test_one_correct_k_one(self) -> None:
        # 1 - C(4,1)/C(5,1) = 1 - 4/5 = 0.2  (== c/n for k=1)
        assert pass_at_k_estimator(n=5, c=1, k=1) == pytest.approx(0.2)

    def test_three_correct_k_one(self) -> None:
        assert pass_at_k_estimator(n=5, c=3, k=1) == pytest.approx(0.6)

    def test_known_k_two(self) -> None:
        # 1 - C(9,2)/C(10,2) = 1 - 36/45 = 0.2
        assert pass_at_k_estimator(n=10, c=1, k=2) == pytest.approx(0.2)

    def test_monotonic_in_k(self) -> None:
        # More draws can only help: pass@k non-decreasing in k for fixed (n, c).
        vals = [pass_at_k_estimator(n=8, c=2, k=kk) for kk in range(1, 9)]
        assert all(b >= a - 1e-12 for a, b in pairwise(vals))

    @pytest.mark.parametrize(
        ("n", "c", "k"),
        [(5, 0, 0), (5, 0, 6), (5, 6, 2), (5, -1, 2), (0, 0, 1)],
    )
    def test_invalid_args_raise(self, n: int, c: int, k: int) -> None:
        with pytest.raises(ValueError):
            pass_at_k_estimator(n=n, c=c, k=k)
