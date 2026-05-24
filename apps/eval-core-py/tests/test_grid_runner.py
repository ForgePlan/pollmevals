"""Tests for orchestrator.grid_runner: asyncio gather + Semaphore + journal + cost gate.

Covers:
1. TestGridSpec        -- total_evals(), iter_requests() count + determinism
2. TestRunSingle       -- happy path, budget gate, caller exception propagation
3. TestRunGrid45Evals  -- full 45-eval grid happy path
4. TestRunGridWithFailures -- 1 failure in 45, FR-009 preservation
5. TestACSeven         -- explicit AC-7: 1/5 raises -> 5 manifest rows
6. TestBudgetGate      -- AC-3: cost cap abort, skipped requests omitted from journal
7. TestConcurrencyLimit -- Semaphore(3) max parallel enforcement
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from src.contracts import ArtifactRef, ErrorClass, EvalArtifactRefs, EvalRow, EvalStats, EvalStatus
from src.orchestrator.cost import BudgetGate, PricingTuple
from src.orchestrator.eval_caller import (
    _DEFAULT_COST_USD,
    EvalRequest,
    EvalResult,
    FakeEvalCaller,
    compute_eval_id,
)
from src.orchestrator.grid_runner import (
    MAX_CONCURRENT_EVALS,
    GridRunner,
    GridRunResult,
    GridSpec,
    make_smoke_grid_spec,
)
from src.orchestrator.journal import JournalReader, JournalWriter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN_HASH = "sha256:" + "b" * 64
_UNLIMITED_BUDGET = BudgetGate(cap_usd=Decimal("9999"))
_DEFAULT_PRICING: dict[str, PricingTuple] = {}  # no per-model pricing overrides


def _make_simple_spec(
    *,
    n_models: int = 1,
    n_tasks: int = 1,
    n_stacks: int = 1,
    n_seeds: int = 1,
    run_hash: str = _RUN_HASH,
) -> GridSpec:
    return GridSpec(
        run_hash=run_hash,
        models=[f"model-{i}" for i in range(n_models)],
        tasks=[f"task-{i}" for i in range(n_tasks)],
        stacks=[f"stack-{i}" for i in range(n_stacks)],
        seeds=list(range(n_seeds)),
    )


def _make_journal(
    tmp_path: Path, *, name: str = "test.journal.ndjson"
) -> tuple[Path, JournalWriter]:
    journal_path = tmp_path / name
    writer = JournalWriter(journal_path)
    return journal_path, writer


def _count_journal_rows(journal_path: Path) -> int:
    return JournalReader(journal_path).count()


def _read_journal_rows(journal_path: Path) -> list[dict[str, Any]]:
    return list(JournalReader(journal_path).read_all())


# ---------------------------------------------------------------------------
# 1. TestGridSpec
# ---------------------------------------------------------------------------


class TestGridSpec:
    def test_total_evals_product(self) -> None:
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["m1", "m2", "m3", "m4", "m5"],
            tasks=["t1", "t2", "t3"],
            stacks=["s1"],
            seeds=[1, 2, 3],
        )
        assert spec.total_evals() == 45  # 5 x 3 x 1 x 3

    def test_total_evals_single(self) -> None:
        spec = _make_simple_spec()
        assert spec.total_evals() == 1

    def test_total_evals_matches_iter_count(self) -> None:
        spec = _make_simple_spec(n_models=3, n_tasks=2, n_stacks=2, n_seeds=4)
        reqs = list(spec.iter_requests())
        assert len(reqs) == spec.total_evals()

    def test_iter_requests_yields_unique_eval_ids(self) -> None:
        spec = _make_simple_spec(n_models=2, n_tasks=3, n_stacks=1, n_seeds=3)
        reqs = list(spec.iter_requests())
        eval_ids = [r.eval_id for r in reqs]
        assert len(eval_ids) == len(set(eval_ids)), "Duplicate eval_ids in grid"

    def test_iter_requests_determinism(self) -> None:
        spec = _make_simple_spec(n_models=2, n_tasks=2, n_seeds=2)
        ids_first = [r.eval_id for r in spec.iter_requests()]
        ids_second = [r.eval_id for r in spec.iter_requests()]
        assert ids_first == ids_second

    def test_iter_requests_eval_id_matches_compute(self) -> None:
        spec = _make_simple_spec(n_models=1, n_tasks=1, n_stacks=1, n_seeds=1)
        req = next(spec.iter_requests())
        expected_id = compute_eval_id(
            spec.run_hash,
            req.model_id,
            req.stack_id,
            req.task_id,
            req.seed,
        )
        assert req.eval_id == expected_id

    def test_iter_requests_timeout_default(self) -> None:
        spec = _make_simple_spec()
        req = next(spec.iter_requests())
        assert req.timeout_s == 300

    def test_iter_requests_timeout_custom(self) -> None:
        spec = _make_simple_spec()
        req = next(spec.iter_requests(timeout_s=120))
        assert req.timeout_s == 120

    def test_smoke_grid_spec_factory(self) -> None:
        spec = make_smoke_grid_spec(run_hash=_RUN_HASH)
        assert spec.total_evals() == 45
        assert len(spec.models) == 5
        assert len(spec.tasks) == 3
        assert len(spec.stacks) == 1
        assert len(spec.seeds) == 3


# ---------------------------------------------------------------------------
# 2. TestRunSingle
# ---------------------------------------------------------------------------


class TestRunSingle:
    @pytest.mark.asyncio
    async def test_happy_path_returns_eval_result(self, tmp_path: Path) -> None:
        _journal_path, writer = _make_journal(tmp_path)
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        spec = _make_simple_spec()
        req = next(spec.iter_requests())

        result = await runner._run_single(req)

        writer.close()
        assert isinstance(result, EvalResult)
        assert result.eval_row is not None
        assert result.eval_row.status == EvalStatus.SCORED

    @pytest.mark.asyncio
    async def test_happy_path_appends_to_journal(self, tmp_path: Path) -> None:
        journal_path, writer = _make_journal(tmp_path)
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        spec = _make_simple_spec()
        req = next(spec.iter_requests())

        await runner._run_single(req)
        writer.close()

        assert _count_journal_rows(journal_path) == 1

    @pytest.mark.asyncio
    async def test_happy_path_updates_running_total(self, tmp_path: Path) -> None:
        _journal_path, writer = _make_journal(tmp_path)
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        spec = _make_simple_spec()
        req = next(spec.iter_requests())

        assert runner._running_total == Decimal("0")
        await runner._run_single(req)
        writer.close()
        assert runner._running_total == _DEFAULT_COST_USD

    @pytest.mark.asyncio
    async def test_budget_exhausted_returns_none(self, tmp_path: Path) -> None:
        """When budget is already exhausted, _run_single returns None without calling caller."""
        journal_path, writer = _make_journal(tmp_path)
        # Cap of $0.001 with abort at 80% = $0.0008 threshold.
        # Set running_total to above threshold so gate fires immediately.
        tiny_gate = BudgetGate(cap_usd=Decimal("0.001"))
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=tiny_gate,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        # Pre-exhaust the budget.
        runner._running_total = Decimal("0.001")

        spec = _make_simple_spec()
        req = next(spec.iter_requests())

        result = await runner._run_single(req)
        writer.close()

        assert result is None
        # Journal must NOT have any entries (request was skipped).
        assert _count_journal_rows(journal_path) == 0

    @pytest.mark.asyncio
    async def test_budget_exhausted_no_caller_call(self, tmp_path: Path) -> None:
        """Verify caller.call() is never invoked when budget gate fires."""
        call_count = 0

        class CountingCaller:
            async def call(self, request: EvalRequest) -> EvalResult:
                nonlocal call_count
                call_count += 1
                return await FakeEvalCaller().call(request)

        _journal_path, writer = _make_journal(tmp_path)
        tiny_gate = BudgetGate(cap_usd=Decimal("0.001"))
        runner = GridRunner(
            caller=CountingCaller(),
            journal_writer=writer,
            budget_gate=tiny_gate,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        runner._running_total = Decimal("0.001")  # already at cap

        spec = _make_simple_spec()
        req = next(spec.iter_requests())
        await runner._run_single(req)
        writer.close()

        assert call_count == 0

    @pytest.mark.asyncio
    async def test_caller_raises_propagates(self, tmp_path: Path) -> None:
        """If caller.call() raises, the exception propagates out of _run_single."""

        class ExplodingCaller:
            async def call(self, request: EvalRequest) -> EvalResult:
                raise ValueError("simulated explosion")

        _journal_path, writer = _make_journal(tmp_path)
        runner = GridRunner(
            caller=ExplodingCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        spec = _make_simple_spec()
        req = next(spec.iter_requests())

        with pytest.raises(ValueError, match="simulated explosion"):
            await runner._run_single(req)
        writer.close()

    @pytest.mark.asyncio
    async def test_failed_eval_still_journaled(self, tmp_path: Path) -> None:
        """A gracefully-failed EvalRow (status=FAILED) must be journaled (FR-009)."""
        journal_path, writer = _make_journal(tmp_path)
        caller = FakeEvalCaller(simulate_failures={("stack-0", "task-0", 0): "rate_limit"})
        runner = GridRunner(
            caller=caller,
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        spec = _make_simple_spec()
        req = next(spec.iter_requests())

        result = await runner._run_single(req)
        writer.close()

        assert result is not None
        assert result.eval_row is not None
        assert result.eval_row.status == EvalStatus.FAILED
        assert _count_journal_rows(journal_path) == 1
        rows = _read_journal_rows(journal_path)
        assert rows[0]["status"] == "failed"
        assert rows[0]["error_class"] == "rate_limit"


# ---------------------------------------------------------------------------
# 3. TestRunGrid45Evals
# ---------------------------------------------------------------------------


class TestRunGrid45Evals:
    @pytest.mark.asyncio
    async def test_full_45_eval_grid_happy_path(self, tmp_path: Path) -> None:
        journal_path, writer = _make_journal(tmp_path)
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=[f"model-{i}" for i in range(5)],
            tasks=[f"task-{i}" for i in range(3)],
            stacks=["raw-llm"],
            seeds=[1, 2, 3],
        )
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )

        run_result = await runner.run(spec)
        writer.close()

        assert len(run_result.results) == 45
        assert len(run_result.succeeded()) == 45
        assert len(run_result.failed()) == 0
        assert run_result.budget_breach is False
        assert run_result.total_cost_usd > Decimal("0")
        assert _count_journal_rows(journal_path) == 45

    @pytest.mark.asyncio
    async def test_total_cost_matches_n_evals_times_default(self, tmp_path: Path) -> None:
        _journal_path, writer = _make_journal(tmp_path)
        spec = _make_simple_spec(n_models=2, n_tasks=2, n_seeds=2)  # 8 evals
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )

        run_result = await runner.run(spec)
        writer.close()

        expected_total = _DEFAULT_COST_USD * 8
        assert run_result.total_cost_usd == expected_total

    @pytest.mark.asyncio
    async def test_all_journal_rows_have_eval_id(self, tmp_path: Path) -> None:
        journal_path, writer = _make_journal(tmp_path)
        spec = _make_simple_spec(n_models=3, n_tasks=3, n_seeds=3)
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )

        await runner.run(spec)
        writer.close()

        rows = _read_journal_rows(journal_path)
        for row in rows:
            assert "eval_id" in row
            assert isinstance(row["eval_id"], str)
            assert len(row["eval_id"]) == 16

    @pytest.mark.asyncio
    async def test_no_duplicate_eval_ids_in_journal(self, tmp_path: Path) -> None:
        journal_path, writer = _make_journal(tmp_path)
        spec = _make_simple_spec(n_models=3, n_tasks=3, n_seeds=3)  # 27 evals
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )

        await runner.run(spec)
        writer.close()

        rows = _read_journal_rows(journal_path)
        eval_ids = [r["eval_id"] for r in rows]
        assert len(eval_ids) == len(set(eval_ids)), "Duplicate eval_ids in journal"


# ---------------------------------------------------------------------------
# 4. TestRunGridWithFailures
# ---------------------------------------------------------------------------


class TestRunGridWithFailures:
    @pytest.mark.asyncio
    async def test_one_failure_in_45_fr009_preserved(self, tmp_path: Path) -> None:
        """FR-009: failed eval must NOT be dropped from results denominator.

        FakeEvalCaller simulate_failures key is (stack_id, task_id, seed).
        This key matches ONE combination: raw-llm x task-0 x seed=1.
        With 5 models, all using the same stack_id="raw-llm", the key matches
        all 5 models' task-0/seed=1 entries (5 failures, not 1).
        To inject exactly 1 failure we use a custom caller that matches on
        model_id as well.
        """
        journal_path, writer = _make_journal(tmp_path)

        # Custom caller that fails exactly 1 (model, stack, task, seed) tuple.
        class OneFailureCaller:
            _inner = FakeEvalCaller()

            async def call(self, request: EvalRequest) -> EvalResult:
                # Fail only the very first model's task-0/seed=1 combination.
                if (
                    request.model_id == "model-0"
                    and request.task_id == "task-0"
                    and request.seed == 1
                ):
                    inner = FakeEvalCaller(
                        simulate_failures={("raw-llm", "task-0", 1): "rate_limit"}
                    )
                    return await inner.call(request)
                return await self._inner.call(request)

        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=[f"model-{i}" for i in range(5)],
            tasks=[f"task-{i}" for i in range(3)],
            stacks=["raw-llm"],
            seeds=[1, 2, 3],
        )
        runner = GridRunner(
            caller=OneFailureCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )

        run_result = await runner.run(spec)
        writer.close()

        assert len(run_result.results) == 45
        succeeded = run_result.succeeded()
        failed = run_result.failed()
        assert len(succeeded) == 44
        assert len(failed) == 1
        assert _count_journal_rows(journal_path) == 45

    @pytest.mark.asyncio
    async def test_failed_row_has_correct_error_class(self, tmp_path: Path) -> None:
        _journal_path, writer = _make_journal(tmp_path)
        caller = FakeEvalCaller(simulate_failures={("raw-llm", "task-0", 1): "rate_limit"})
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1, 2, 3],
        )
        runner = GridRunner(
            caller=caller,
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )

        run_result = await runner.run(spec)
        writer.close()

        failed = run_result.failed()
        assert len(failed) == 1
        failed_item = failed[0]
        assert isinstance(failed_item, EvalResult)
        assert failed_item.eval_row is not None
        assert failed_item.eval_row.status == EvalStatus.FAILED
        assert failed_item.eval_row.error_class == ErrorClass.RATE_LIMIT


# ---------------------------------------------------------------------------
# 5. TestACSeven -- AC-7 explicit
# ---------------------------------------------------------------------------


class TestACSeven:
    """AC-7: 1 of 5 coroutines raises -> 5 manifest rows produced with failing
    one's error_class populated.

    RFC-001 AC-7: 'Given a grid runner unit test, when 1 of 5 coroutines raises,
    then 5 manifest rows produced with the failing one's error_class populated.'

    In POLLMEVALS, FakeEvalCaller handles failures gracefully, returning an
    EvalRow with status=FAILED rather than raising a Python exception.  This is
    the FR-009 compliant path.  The test verifies that all 5 rows appear in the
    journal, including the failed one with error_class populated.
    """

    @pytest.mark.asyncio
    async def test_1_of_5_failure_produces_5_rows(self, tmp_path: Path) -> None:
        journal_path, writer = _make_journal(tmp_path)
        # Grid: 1 model x 1 task x 1 stack x 5 seeds = 5 evals.
        # Seed 2 simulates a rate_limit failure.
        caller = FakeEvalCaller(simulate_failures={("raw-llm", "task-0", 2): "rate_limit"})
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[0, 1, 2, 3, 4],
        )
        runner = GridRunner(
            caller=caller,
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )

        run_result = await runner.run(spec)
        writer.close()

        # 5 results total (no eval dropped).
        assert len(run_result.results) == 5
        # 5 journal rows.
        rows = _read_journal_rows(journal_path)
        assert len(rows) == 5

        # 4 succeeded, 1 failed.
        assert len(run_result.succeeded()) == 4
        assert len(run_result.failed()) == 1

    @pytest.mark.asyncio
    async def test_ac7_failed_row_error_class_in_journal(self, tmp_path: Path) -> None:
        """The failing row in the journal must carry a populated error_class."""
        journal_path, writer = _make_journal(tmp_path)
        caller = FakeEvalCaller(simulate_failures={("raw-llm", "task-0", 2): "rate_limit"})
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[0, 1, 2, 3, 4],
        )
        runner = GridRunner(
            caller=caller,
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )

        await runner.run(spec)
        writer.close()

        rows = _read_journal_rows(journal_path)
        # Count by status in journal.
        statuses = [r["status"] for r in rows]
        error_classes = [r.get("error_class") for r in rows]

        assert statuses.count("scored") == 4
        assert statuses.count("failed") == 1
        # The failed row must have error_class = "rate_limit".
        assert "rate_limit" in error_classes

    @pytest.mark.asyncio
    async def test_ac7_exception_from_caller_still_tracked(self, tmp_path: Path) -> None:
        """When caller.call() raises (uncaught exception path), gather captures it.

        FR-009 requires all evals to appear; here the exception is the failure record.
        This variant simulates a truly unexpected Python exception (not a graceful
        EvalRow with status=FAILED).
        """

        class RaisingOnSeedTwo:
            async def call(self, request: EvalRequest) -> EvalResult:
                if request.seed == 2:
                    raise RuntimeError("unexpected caller explosion")
                return await FakeEvalCaller().call(request)

        journal_path, writer = _make_journal(tmp_path)
        runner = GridRunner(
            caller=RaisingOnSeedTwo(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[0, 1, 2, 3, 4],
        )

        run_result = await runner.run(spec)
        writer.close()

        # Gather captures the exception: 5 entries in results.
        assert len(run_result.results) == 5

        # 1 entry is a BaseException (the raised RuntimeError).
        exceptions = [r for r in run_result.results if isinstance(r, BaseException)]
        assert len(exceptions) == 1
        assert "unexpected caller explosion" in str(exceptions[0])

        # 4 entries are EvalResult.
        eval_results = [r for r in run_result.results if isinstance(r, EvalResult)]
        assert len(eval_results) == 4

        # Journal has 4 rows (exception path produces no EvalRow to journal).
        assert _count_journal_rows(journal_path) == 4


# ---------------------------------------------------------------------------
# 6. TestBudgetGate -- AC-3
# ---------------------------------------------------------------------------


class TestBudgetGateIntegration:
    """AC-3: budget abort at 80% of cap.

    FakeEvalCaller default cost = $0.0125 per eval.

    Scenarios:
    - Cap=$0.10, threshold=$0.08: 6 evals x $0.0125 = $0.075 (still under);
      7th eval -> $0.0875 (over threshold, gate fires for 8th+).
      Gate checks BEFORE each eval. After 6 evals running_total=$0.075; 0.075 < 0.08
      -> 7th is scheduled. After 7: $0.0875 >= 0.08 -> 8th is skipped.
    """

    @pytest.mark.asyncio
    async def test_5_evals_under_budget(self, tmp_path: Path) -> None:
        """5 evals x $0.0125 = $0.0625; threshold=$0.08; all 5 complete."""
        journal_path, writer = _make_journal(tmp_path)
        gate = BudgetGate(cap_usd=Decimal("0.10"))
        assert gate.abort_threshold_usd == Decimal("0.080")

        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=gate,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        spec = _make_simple_spec(n_models=1, n_tasks=1, n_stacks=1, n_seeds=5)

        run_result = await runner.run(spec)
        writer.close()

        assert len(run_result.succeeded()) == 5
        assert run_result.budget_breach is False
        assert _count_journal_rows(journal_path) == 5

    @pytest.mark.asyncio
    async def test_skipped_requests_absent_from_journal(self, tmp_path: Path) -> None:
        """Requests skipped due to budget gate MUST NOT appear in the journal."""
        journal_path, writer = _make_journal(tmp_path)
        # Cap=$0.05, threshold=$0.04; default cost=$0.0125.
        # After 3 evals: $0.0375 < $0.04 -> 4th attempted; after 4: $0.05 >= $0.04 -> 5th+ skipped.
        gate = BudgetGate(cap_usd=Decimal("0.05"))

        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=gate,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        # 10 evals to ensure gate fires.
        spec = _make_simple_spec(n_models=1, n_tasks=1, n_stacks=1, n_seeds=10)

        run_result = await runner.run(spec)
        writer.close()

        rows = _read_journal_rows(journal_path)
        # Skipped requests produced None in raw results and were filtered out.
        # Journal only contains attempted evals.
        attempted_count = len(run_result.results)
        assert len(rows) == attempted_count
        # Budget breach was triggered.
        assert run_result.budget_breach is True

    @pytest.mark.asyncio
    async def test_budget_breach_flag_set(self, tmp_path: Path) -> None:
        """budget_breach=True when running_total reaches the abort threshold."""
        _journal_path, writer = _make_journal(tmp_path)
        gate = BudgetGate(cap_usd=Decimal("0.02"))  # threshold=$0.016; 2nd eval tips over

        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=gate,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        spec = _make_simple_spec(n_models=1, n_tasks=1, n_stacks=1, n_seeds=5)

        run_result = await runner.run(spec)
        writer.close()

        assert run_result.budget_breach is True

    @pytest.mark.asyncio
    async def test_budget_not_breached_flag_false(self, tmp_path: Path) -> None:
        """budget_breach=False when the total never reaches the threshold."""
        _journal_path, writer = _make_journal(tmp_path)
        gate = BudgetGate(cap_usd=Decimal("100.0"))  # huge cap

        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=gate,
            pricing_snapshot=_DEFAULT_PRICING,
        )
        spec = _make_simple_spec(n_models=1, n_tasks=1, n_stacks=1, n_seeds=3)

        run_result = await runner.run(spec)
        writer.close()

        assert run_result.budget_breach is False


# ---------------------------------------------------------------------------
# 7. TestConcurrencyLimit -- Semaphore(3)
# ---------------------------------------------------------------------------


class TestConcurrencyLimit:
    @pytest.mark.asyncio
    async def test_max_concurrent_default_is_three(self) -> None:
        assert MAX_CONCURRENT_EVALS == 3

    @pytest.mark.asyncio
    async def test_semaphore_limits_parallelism(self, tmp_path: Path) -> None:
        """Max in-flight callers at any point must not exceed MAX_CONCURRENT_EVALS."""
        max_concurrent_observed = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        class TrackingCaller:
            async def call(self, request: EvalRequest) -> EvalResult:
                nonlocal max_concurrent_observed, current_concurrent
                async with lock:
                    current_concurrent += 1
                    if current_concurrent > max_concurrent_observed:
                        max_concurrent_observed = current_concurrent
                # Yield control so other coroutines can run.
                await asyncio.sleep(0)
                result = await FakeEvalCaller().call(request)
                async with lock:
                    current_concurrent -= 1
                return result

        _journal_path, writer = _make_journal(tmp_path)
        runner = GridRunner(
            caller=TrackingCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
            max_concurrent=3,
        )
        # 12 evals: enough to exercise the semaphore queue.
        spec = _make_simple_spec(n_models=4, n_tasks=1, n_stacks=1, n_seeds=3)

        await runner.run(spec)
        writer.close()

        assert max_concurrent_observed <= 3, (
            f"Expected max_concurrent <= 3 but observed {max_concurrent_observed}"
        )

    @pytest.mark.asyncio
    async def test_custom_max_concurrent_one(self, tmp_path: Path) -> None:
        """max_concurrent=1 means strictly serial execution."""
        max_concurrent_observed = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        class TrackingCaller:
            async def call(self, request: EvalRequest) -> EvalResult:
                nonlocal max_concurrent_observed, current_concurrent
                async with lock:
                    current_concurrent += 1
                    if current_concurrent > max_concurrent_observed:
                        max_concurrent_observed = current_concurrent
                await asyncio.sleep(0)
                result = await FakeEvalCaller().call(request)
                async with lock:
                    current_concurrent -= 1
                return result

        _journal_path, writer = _make_journal(tmp_path)
        runner = GridRunner(
            caller=TrackingCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
            max_concurrent=1,
        )
        spec = _make_simple_spec(n_models=1, n_tasks=1, n_stacks=1, n_seeds=5)

        await runner.run(spec)
        writer.close()

        assert max_concurrent_observed == 1

    @pytest.mark.asyncio
    async def test_runner_uses_configured_semaphore_limit(self, tmp_path: Path) -> None:
        """GridRunner._semaphore has the correct initial value."""
        _journal_path, writer = _make_journal(tmp_path)
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=writer,
            budget_gate=_UNLIMITED_BUDGET,
            pricing_snapshot=_DEFAULT_PRICING,
            max_concurrent=7,
        )
        writer.close()
        # asyncio.Semaphore stores the initial value as _value.
        assert runner._semaphore._value == 7


# ---------------------------------------------------------------------------
# 8. TestGridRunResult helpers
# ---------------------------------------------------------------------------


class TestGridRunResult:
    def _make_scored_result(self) -> EvalResult:
        dummy_eval_id = "a" * 16
        sha = hashlib.sha256(b"x").hexdigest()
        ref = ArtifactRef(sha256=sha, size_bytes=1, uri="file://x", mime_type="text/plain")
        refs = EvalArtifactRefs(raw_output=ref, normalized_output=ref, evaluator_json=ref)
        stats = EvalStats(
            input_tokens=100,
            output_tokens=50,
            wall_clock_ms=1000,
            cost_usd=Decimal("0.01"),
        )
        row = EvalRow(
            eval_id=dummy_eval_id,
            model_id="m",
            stack_id="s",
            task_id="t",
            seed=1,
            status=EvalStatus.SCORED,
            artifact_refs=refs,
            stats=stats,
        )
        req = EvalRequest(
            eval_id=dummy_eval_id,
            model_id="m",
            stack_id="s",
            task_id="t",
            seed=1,
        )
        now = datetime.now(UTC)
        return EvalResult(
            request=req,
            eval_row=row,
            exception=None,
            started_at=now,
            completed_at=now,
        )

    def test_succeeded_filters_to_scored(self) -> None:
        scored = self._make_scored_result()
        exc = RuntimeError("boom")
        result = GridRunResult(
            results=[scored, exc],
            total_cost_usd=Decimal("0.01"),
            budget_breach=False,
        )
        assert result.succeeded() == [scored]

    def test_failed_includes_exceptions(self) -> None:
        scored = self._make_scored_result()
        exc = RuntimeError("boom")
        result = GridRunResult(
            results=[scored, exc],
            total_cost_usd=Decimal("0.01"),
            budget_breach=False,
        )
        failed = result.failed()
        assert exc in failed
        assert scored not in failed
