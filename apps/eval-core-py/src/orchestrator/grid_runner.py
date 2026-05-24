"""Smoke-run grid scheduler: 45-eval grid with crash-safe journal + cost gate.

Per RFC-001 § Concurrency strategy:
- asyncio.Semaphore(3) — global concurrency limit per ADR-001
- asyncio.gather(*, return_exceptions=True) — preserves failures (FR-009 invariant)
- Each completed eval → JournalWriter.append (NOTE-001)
- After each eval, recompute running total; if >= 80% budget → stop scheduling new (AC-3)
- Crash recovery: out of scope this module (resume.py in Phase 2A-B); journal makes it possible

Concurrency is OUTSIDE EvalCaller — see eval_caller.py for the Protocol seam.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

from src.contracts import EvalStatus
from src.orchestrator.cost import BudgetGate, PricingTuple, compute_cost
from src.orchestrator.eval_caller import (
    EvalCaller,
    EvalRequest,
    EvalResult,
    compute_eval_id,
)
from src.orchestrator.journal import JournalWriter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (per ADR-001 and AC-3)
# ---------------------------------------------------------------------------

MAX_CONCURRENT_EVALS: int = 3
BUDGET_ABORT_PCT: Decimal = Decimal("0.80")


# ---------------------------------------------------------------------------
# GridSpec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GridSpec:
    """Specification of the Cartesian product to evaluate.

    Generates one EvalRequest per (model x task x stack x seed) combination.
    For the smoke run: 5 models x 3 tasks x 1 stack x 3 seeds = 45 evals.

    Ordering: outer->inner: model -> task -> stack -> seed.  This is deterministic
    and matches RFC-001 S Implementation tasks item 6 (grid_runner).
    """

    run_hash: str
    models: list[str]  # provider_route_ids e.g. "openrouter/anthropic/claude-sonnet-4-6"
    tasks: list[str]  # task_ids e.g. "be_01_jwt_auth"
    stacks: list[str]  # stack_ids e.g. "raw-llm"
    seeds: list[int]

    def total_evals(self) -> int:
        """Number of evals the grid will attempt (before budget gating)."""
        return len(self.models) * len(self.tasks) * len(self.stacks) * len(self.seeds)

    def iter_requests(
        self,
        timeout_s: int = 300,
        max_retries: int = 2,
    ) -> Iterator[EvalRequest]:
        """Yield EvalRequest objects for every (model, task, stack, seed) combination.

        eval_id is computed via ``compute_eval_id`` to ensure a deterministic,
        collision-free identifier.  Iterating the same GridSpec twice produces
        identical eval_ids in identical order — this is the invariant the
        resume command (out of scope this module) depends on.

        Args:
            timeout_s: Per-eval wall-clock timeout (NFR-002).
            max_retries: Retry budget for transient failures.

        Yields:
            EvalRequest with the deterministic eval_id pre-computed.
        """
        for model_id in self.models:
            for task_id in self.tasks:
                for stack_id in self.stacks:
                    for seed in self.seeds:
                        eval_id = compute_eval_id(self.run_hash, model_id, stack_id, task_id, seed)
                        yield EvalRequest(
                            eval_id=eval_id,
                            model_id=model_id,
                            stack_id=stack_id,
                            task_id=task_id,
                            seed=seed,
                            timeout_s=timeout_s,
                            max_retries=max_retries,
                        )


# ---------------------------------------------------------------------------
# GridRunResult
# ---------------------------------------------------------------------------


@dataclass
class GridRunResult:
    """Aggregated outcome of a complete grid run.

    ``results`` contains one entry per scheduled request (possibly fewer than
    ``spec.total_evals()`` if budget gating skipped some).  Failed entries are
    preserved as BaseException objects in the list per ``return_exceptions=True``
    semantics (FR-009 invariant — failed evals must not be dropped).

    Note: ``None`` values (from budget-gated requests that returned early
    without attempting the eval) are filtered out BEFORE this dataclass is
    populated.  Only attempted results (EvalResult or BaseException) are stored.
    """

    results: list[EvalResult | BaseException]
    total_cost_usd: Decimal
    budget_breach: bool

    def succeeded(self) -> list[EvalResult]:
        """Return only EvalResult entries with status == SCORED."""
        out: list[EvalResult] = []
        for r in self.results:
            if (
                isinstance(r, EvalResult)
                and r.eval_row is not None
                and r.eval_row.status == EvalStatus.SCORED
            ):
                out.append(r)
        return out

    def failed(self) -> list[EvalResult | BaseException]:
        """Return entries that are NOT a successfully scored EvalResult.

        Includes:
        - BaseException objects (gather returned an exception)
        - EvalResult whose eval_row.status != SCORED (e.g. FAILED, SKIPPED)
        - EvalResult with eval_row == None (should not occur normally)
        """
        out: list[EvalResult | BaseException] = []
        for r in self.results:
            if isinstance(r, BaseException) or (
                isinstance(r, EvalResult)
                and (r.eval_row is None or r.eval_row.status != EvalStatus.SCORED)
            ):
                out.append(r)
        return out


# ---------------------------------------------------------------------------
# GridRunner
# ---------------------------------------------------------------------------


class GridRunner:
    """Async orchestrator for the (model x task x stack x seed) evaluation grid.

    Responsibilities:
    1. Enforce MAX_CONCURRENT_EVALS concurrency via asyncio.Semaphore.
    2. Check BudgetGate before attempting each eval — skip (return None) if
       the budget abort threshold is reached.
    3. Call EvalCaller.call() within the semaphore context.
    4. On success: update the running cost total; append the EvalRow to the
       JournalWriter for crash-safety (NOTE-001).
    5. Return all results (including failures) via asyncio.gather
       return_exceptions=True — FR-009 invariant.

    The caller (orchestrator entrypoint) owns journal lifecycle (open/close).
    GridRunner does not open or close the JournalWriter — it receives an
    already-open writer.

    Args:
        caller: Any EvalCaller implementation (InspectEvalCaller or FakeEvalCaller).
        journal_writer: Open JournalWriter ready for append calls.
        budget_gate: BudgetGate configured with the run's budget cap.
        pricing_snapshot: Dict mapping model_id → PricingTuple, captured at
            run start (RFC-001 Invariant #3 — never updated mid-run).
        max_concurrent: Semaphore limit (default MAX_CONCURRENT_EVALS=3 per ADR-001).
    """

    def __init__(
        self,
        *,
        caller: EvalCaller,
        journal_writer: JournalWriter,
        budget_gate: BudgetGate,
        pricing_snapshot: dict[str, PricingTuple],
        max_concurrent: int = MAX_CONCURRENT_EVALS,
    ) -> None:
        self._caller = caller
        self._journal_writer = journal_writer
        self._budget_gate = budget_gate
        self._pricing_snapshot = pricing_snapshot
        self._semaphore = asyncio.Semaphore(max_concurrent)
        # Running cost accumulator.  Single event loop — no concurrent mutation
        # (asyncio is cooperative; only one coroutine runs at a time between
        # await points, so this is safe without a lock).
        self._running_total: Decimal = Decimal("0")

    async def _run_single(self, request: EvalRequest) -> EvalResult | None:
        """Execute one eval, journaling the result if successful.

        Returns:
            EvalResult on success (scored or gracefully-failed).
            None if the budget gate fired before acquiring the semaphore —
            this request was not attempted and should NOT appear in the journal.

        Raises:
            Any exception propagated from EvalCaller.call() — these are
            captured by asyncio.gather(return_exceptions=True) and NOT
            re-raised here so that the gather loop can continue.

        Budget check rationale: we check BEFORE acquiring the semaphore so
        that a budget breach immediately stops queuing further work rather
        than waiting for a semaphore slot.  In-flight coroutines that already
        hold the semaphore are allowed to complete (AC-3: "in-flight complete").
        """
        # AC-3: abort before attempting the eval if budget is exhausted.
        if not self._budget_gate.should_continue(self._running_total):
            logger.info(
                "Budget gate fired for eval_id=%s model=%s — skipping.",
                request.eval_id,
                request.model_id,
            )
            return None

        async with self._semaphore:
            # Second budget check inside the semaphore: another coroutine may
            # have exhausted the budget while we were waiting for a slot.
            if not self._budget_gate.should_continue(self._running_total):
                logger.info(
                    "Budget gate fired (post-semaphore) for eval_id=%s — skipping.",
                    request.eval_id,
                )
                return None

            result = await self._caller.call(request)

            # Journal + cost attribution for any eval that produced an EvalRow
            # (both scored and gracefully-failed rows are journaled — FR-009).
            if result.eval_row is not None:
                # Update running cost total from the EvalRow's recorded cost_usd.
                # The FakeEvalCaller already populates stats.cost_usd with
                # _DEFAULT_COST_USD; for the real caller (Phase 2B), InspectEvalCaller
                # fills this from the token counts x pricing snapshot.
                # We also compute the cost independently via compute_cost() for
                # cross-verification when pricing_snapshot covers this model.
                row_cost = result.eval_row.stats.cost_usd
                if request.model_id in self._pricing_snapshot:
                    expected = compute_cost(
                        result.eval_row.stats,
                        self._pricing_snapshot[request.model_id],
                    )
                    if expected != row_cost:
                        logger.debug(
                            "Cost delta for eval_id=%s: row_cost=%s compute_cost=%s "
                            "(using row_cost as authoritative)",
                            result.eval_row.eval_id,
                            row_cost,
                            expected,
                        )

                self._running_total += row_cost

                # Persist the row to the append-only journal (NOTE-001).
                self._journal_writer.append(result.eval_row.model_dump(mode="json"))

            return result

    async def run(self, spec: GridSpec) -> GridRunResult:
        """Execute the full evaluation grid defined by *spec*.

        All requests are scheduled concurrently (bounded by the semaphore).
        Failures are preserved as BaseException entries in the raw results list
        (``return_exceptions=True`` is the FR-009 invariant — NEVER remove it).

        Budget-gated requests (where ``_run_single`` returns None) are excluded
        from the final results; only attempted evals appear in GridRunResult.

        Args:
            spec: GridSpec defining the Cartesian product to evaluate.

        Returns:
            GridRunResult with all attempted results and aggregated cost.
        """
        requests = list(spec.iter_requests())
        logger.info(
            "GridRunner.run: scheduling %d evals (max_concurrent=%d)",
            len(requests),
            self._semaphore._value,
        )

        coros = [self._run_single(req) for req in requests]
        raw: list[EvalResult | BaseException | None] = list(
            await asyncio.gather(*coros, return_exceptions=True)
        )

        # Filter out None (budget-skipped, not attempted) entries.
        # BaseException entries from gather are kept — they represent failed
        # evals that must appear in the manifest denominator (FR-009).
        attempted: list[EvalResult | BaseException] = [r for r in raw if r is not None]

        # Determine budget breach: True if running_total reached or exceeded
        # the abort threshold OR if any requests were skipped (None in raw).
        skipped_count = sum(1 for r in raw if r is None)
        budget_breach = (
            not self._budget_gate.should_continue(self._running_total) or skipped_count > 0
        )

        if budget_breach:
            logger.warning(
                "Budget gate triggered: running_total=$%s, skipped=%d evals, attempted=%d evals.",
                self._running_total,
                skipped_count,
                len(attempted),
            )

        return GridRunResult(
            results=attempted,
            total_cost_usd=self._running_total,
            budget_breach=budget_breach,
        )


# ---------------------------------------------------------------------------
# Convenience factory for the standard smoke-run grid
# ---------------------------------------------------------------------------

# Smoke run constants per RFC-001 § Implementation tasks and ADR-003.
SMOKE_MODELS: list[str] = [
    "openrouter/anthropic/claude-sonnet-4-6",
    "openrouter/openai/gpt-4o-mini",
    "openrouter/google/gemini-flash-1-5",
    "openrouter/qwen/qwen-2-5-14b",
    "openrouter/meta-llama/llama-4-70b",
]
SMOKE_TASKS: list[str] = [
    "be_01_jwt_auth",
    "fe_01_multistep_form",
    "doc_01_cli_readme",
]
SMOKE_STACKS: list[str] = ["raw-llm"]
SMOKE_SEEDS: list[int] = [1, 2, 3]


def make_smoke_grid_spec(run_hash: str) -> GridSpec:
    """Return the canonical 45-eval smoke run GridSpec.

    5 models x 3 tasks x 1 stack x 3 seeds = 45 evals (RFC-001 S Context).

    Args:
        run_hash: Content-addressed hash for this run (used in eval_id derivation).

    Returns:
        GridSpec with the standard smoke run configuration.
    """
    return GridSpec(
        run_hash=run_hash,
        models=SMOKE_MODELS,
        tasks=SMOKE_TASKS,
        stacks=SMOKE_STACKS,
        seeds=SMOKE_SEEDS,
    )
