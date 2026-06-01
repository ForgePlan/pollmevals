"""RFC-002 Slice E — GridRunner ↔ JudgePanel integration unit tests.

Covers:
1. judge_panel=None preserves PRD-001 behavior (back-compat).
2. SCORED candidate → judge.score() called, judgments + aggregate land on EvalRow.
3. FAILED candidate → judge.score() NOT called.
4. Run-level breach gate:
   - 1/10 DEGRADED → judge_panel_breach=False (10% < 20%).
   - 3/10 DEGRADED → judge_panel_breach=True  (30% > 20%).
5. Error-policy B (decided 2026-05-25):
   - SelfJudgingError → row becomes FAILED with ErrorClass.CONTRACT_VIOLATION.
   - Unknown Exception → row becomes FAILED with ErrorClass.JUDGE_FAILURE.

No real LLM / network — JudgePanel is replaced by a `FakeJudgePanel` that
exposes the same `score`/`aggregate` surface and lets each test program the
outcome it wants.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from src.contracts import (
    ArtifactRef,
    ErrorClass,
    EvalArtifactRefs,
    EvalRow,
    EvalStats,
    EvalStatus,
    JudgeAggregation,
    Judgment,
)
from src.orchestrator.cost import BudgetGate, PricingTuple
from src.orchestrator.eval_caller import (
    EvalRequest,
    EvalResult,
    FakeEvalCaller,
)
from src.orchestrator.grid_runner import (
    GridRunner,
    GridRunResult,
    GridSpec,
)
from src.orchestrator.journal import JournalWriter
from src.orchestrator.judge_panel import (
    JudgePanel,
    JudgeUnavailableError,
    SelfJudgingError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN_HASH = "sha256:" + "c" * 64
_UNLIMITED_BUDGET = BudgetGate(cap_usd=Decimal("9999"))
_DEFAULT_PRICING: dict[str, PricingTuple] = {}


def _make_simple_spec(n_models: int = 1, n_tasks: int = 1, n_seeds: int = 1) -> GridSpec:
    return GridSpec(
        run_hash=_RUN_HASH,
        models=[f"model-{i}" for i in range(n_models)],
        tasks=[f"task-{i}" for i in range(n_tasks)],
        stacks=["stack-0"],
        seeds=list(range(n_seeds)),
    )


def _make_journal(tmp_path: Path) -> JournalWriter:
    return JournalWriter(tmp_path / "test.journal.ndjson")


def _make_judgment(
    *,
    judge_model_id: str = "judge-0",
    judge_order: int = 0,
    total_score: float = 8.0,
    cost_usd: Decimal = Decimal("0.05"),
) -> Judgment:
    return Judgment(
        judge_model_id=judge_model_id,
        judge_order=judge_order,
        rubric_version="1.0",
        rubric_scores={"overall": total_score},
        total_score=total_score,
        raw_explanation="fake explanation",
        latency_ms=100,
        tokens_in=10,
        tokens_out=10,
        cost_usd=cost_usd,
    )


def _full_aggregation(judgments: list[Judgment]) -> JudgeAggregation:
    return JudgeAggregation(
        median_per_criterion={"overall": 8.0},
        alpha_point=0.85,
        alpha_ci_lower=0.75,
        alpha_ci_upper=0.92,
        judge_status="OK",
        n_judges_used=len(judgments),
    )


def _degraded_aggregation(judgments: list[Judgment]) -> JudgeAggregation:
    return JudgeAggregation(
        median_per_criterion={"overall": 8.0},
        alpha_point=None,
        alpha_ci_lower=None,
        alpha_ci_upper=None,
        judge_status="DEGRADED",
        n_judges_used=len(judgments),
    )


def _low_alpha_aggregation(judgments: list[Judgment]) -> JudgeAggregation:
    """G5: a non-DEGRADED aggregation whose alpha CI lower-bound is below 0.70."""
    return JudgeAggregation(
        median_per_criterion={"overall": 8.0},
        alpha_point=0.55,
        alpha_ci_lower=0.50,
        alpha_ci_upper=0.65,
        judge_status="OK",
        n_judges_used=len(judgments),
    )


class FakeJudgePanel:
    """Duck-typed stand-in for JudgePanel. Each test programs its behavior."""

    def __init__(
        self,
        *,
        score_fn: Callable[[EvalResult, str], list[Judgment]] | None = None,
        aggregate_fn: Callable[[list[Judgment]], JudgeAggregation] | None = None,
    ) -> None:
        self.score_calls: list[tuple[EvalResult, str]] = []
        self.aggregate_calls: list[list[Judgment]] = []
        self._score_fn = score_fn or (lambda _r, _t: [_make_judgment()])
        self._aggregate_fn = aggregate_fn or _full_aggregation

    async def score(self, er: EvalResult, task_id: str) -> list[Judgment]:
        self.score_calls.append((er, task_id))
        return self._score_fn(er, task_id)

    def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation:
        self.aggregate_calls.append(judgments)
        return self._aggregate_fn(judgments)


def _make_runner(
    tmp_path: Path,
    *,
    judge_panel: FakeJudgePanel | None,
    caller: FakeEvalCaller | None = None,
) -> GridRunner:
    return GridRunner(
        caller=caller or FakeEvalCaller(),
        journal_writer=_make_journal(tmp_path),
        budget_gate=_UNLIMITED_BUDGET,
        pricing_snapshot=_DEFAULT_PRICING,
        judge_panel=cast(JudgePanel | None, judge_panel),
    )


# ---------------------------------------------------------------------------
# 1. Back-compat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_judge_panel_preserves_prd001_behavior(tmp_path: Path) -> None:
    """judge_panel=None → no hook invocation; eval_row.judgments stays None."""
    runner = _make_runner(tmp_path, judge_panel=None)
    spec = _make_simple_spec()
    req = next(spec.iter_requests())

    result = await runner._run_single(req)

    assert isinstance(result, EvalResult)
    assert result.eval_row is not None
    assert result.eval_row.status == EvalStatus.SCORED
    assert result.eval_row.judgments is None
    assert result.eval_row.judge_aggregate is None


# ---------------------------------------------------------------------------
# 2. Happy path — judge called on SCORED, row carries aggregate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_judge_panel_invoked_on_scored_eval(tmp_path: Path) -> None:
    fake_panel = FakeJudgePanel(
        score_fn=lambda _r, _t: [
            _make_judgment(judge_model_id="j0", judge_order=0),
            _make_judgment(judge_model_id="j1", judge_order=1),
            _make_judgment(judge_model_id="j2", judge_order=2),
        ],
    )
    runner = _make_runner(tmp_path, judge_panel=fake_panel)
    spec = _make_simple_spec()
    req = next(spec.iter_requests())

    result = await runner._run_single(req)

    assert len(fake_panel.score_calls) == 1
    assert fake_panel.score_calls[0][1] == req.task_id
    assert isinstance(result, EvalResult)
    assert result.eval_row is not None
    assert result.eval_row.status == EvalStatus.SCORED
    assert result.eval_row.judgments is not None
    assert len(result.eval_row.judgments) == 3
    assert result.eval_row.judge_aggregate is not None
    assert result.eval_row.judge_aggregate.judge_status == "OK"


# ---------------------------------------------------------------------------
# 3. Skip path — judge NOT called on FAILED candidate
# ---------------------------------------------------------------------------


class _AlwaysFailCaller:
    """FakeEvalCaller variant that produces a graceful FAILED row."""

    async def call(self, request: EvalRequest) -> EvalResult:
        now = datetime.now(UTC)
        stub_ref = ArtifactRef(
            uri="memory://x",
            sha256="0" * 64,
            size_bytes=1,
            mime_type="text/plain",
        )
        return EvalResult(
            request=request,
            eval_row=EvalRow(
                eval_id=request.eval_id,
                model_id=request.model_id,
                stack_id=request.stack_id,
                task_id=request.task_id,
                seed=request.seed,
                status=EvalStatus.FAILED,
                error_class=ErrorClass.TIMEOUT,
                error_detail="forced",
                artifact_refs=EvalArtifactRefs(
                    raw_output=stub_ref,
                    normalized_output=stub_ref,
                    evaluator_json=stub_ref,
                ),
                stats=EvalStats(
                    input_tokens=0,
                    output_tokens=0,
                    wall_clock_ms=100,
                    cost_usd=Decimal("0"),
                ),
                started_at=now,
                completed_at=now,
            ),
            exception=None,
            started_at=now,
            completed_at=now,
        )


@pytest.mark.asyncio
async def test_judge_panel_not_called_on_failed_eval(tmp_path: Path) -> None:
    fake_panel = FakeJudgePanel()
    runner = _make_runner(
        tmp_path, judge_panel=fake_panel, caller=cast(FakeEvalCaller, _AlwaysFailCaller())
    )
    spec = _make_simple_spec()
    req = next(spec.iter_requests())

    result = await runner._run_single(req)

    assert isinstance(result, EvalResult)
    assert result.eval_row is not None
    assert result.eval_row.status == EvalStatus.FAILED
    assert fake_panel.score_calls == []  # skipped
    assert result.eval_row.judgments is None
    assert result.eval_row.judge_aggregate is None


# ---------------------------------------------------------------------------
# 4. Error-policy B — SelfJudgingError → FAILED + CONTRACT_VIOLATION
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_judging_error_marks_row_contract_violation(tmp_path: Path) -> None:
    def _raise_self_judging(_r: EvalResult, _t: str) -> list[Judgment]:
        raise SelfJudgingError("candidate family=anthropic appears in judges")

    fake_panel = FakeJudgePanel(score_fn=_raise_self_judging)
    runner = _make_runner(tmp_path, judge_panel=fake_panel)
    spec = _make_simple_spec()
    req = next(spec.iter_requests())

    result = await runner._run_single(req)

    assert isinstance(result, EvalResult)
    assert result.eval_row is not None
    assert result.eval_row.status == EvalStatus.FAILED
    assert result.eval_row.error_class == ErrorClass.CONTRACT_VIOLATION
    assert "self-judging refused" in (result.eval_row.error_detail or "")
    assert result.eval_row.judgments is None  # never populated


# ---------------------------------------------------------------------------
# 5. Error-policy B — unknown Exception → FAILED + JUDGE_FAILURE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_exception_marks_row_judge_failure(tmp_path: Path) -> None:
    def _raise_runtime(_r: EvalResult, _t: str) -> list[Judgment]:
        raise RuntimeError("inspect_ai returned no logs")

    fake_panel = FakeJudgePanel(score_fn=_raise_runtime)
    runner = _make_runner(tmp_path, judge_panel=fake_panel)
    spec = _make_simple_spec()
    req = next(spec.iter_requests())

    result = await runner._run_single(req)

    assert isinstance(result, EvalResult)
    assert result.eval_row is not None
    assert result.eval_row.status == EvalStatus.FAILED
    assert result.eval_row.error_class == ErrorClass.JUDGE_FAILURE
    assert "RuntimeError" in (result.eval_row.error_detail or "")


# ---------------------------------------------------------------------------
# 6. JudgeUnavailableError → DEGRADED path (status stays SCORED)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_judge_unavailable_uses_partial_judgments_degraded(tmp_path: Path) -> None:
    partial = [
        _make_judgment(judge_model_id="j0", judge_order=0),
        _make_judgment(judge_model_id="j1", judge_order=1),
    ]

    def _raise_unavailable(_r: EvalResult, _t: str) -> list[Judgment]:
        raise JudgeUnavailableError(
            "j2 timed out",
            partial_judgments=partial,
            n_judges_requested=3,
        )

    fake_panel = FakeJudgePanel(score_fn=_raise_unavailable, aggregate_fn=_degraded_aggregation)
    runner = _make_runner(tmp_path, judge_panel=fake_panel)
    spec = _make_simple_spec()
    req = next(spec.iter_requests())

    result = await runner._run_single(req)

    assert isinstance(result, EvalResult)
    assert result.eval_row is not None
    assert result.eval_row.status == EvalStatus.SCORED  # NOT failed — degraded path
    assert result.eval_row.judgments is not None
    assert len(result.eval_row.judgments) == 2  # partial only
    assert result.eval_row.judge_aggregate is not None
    assert result.eval_row.judge_aggregate.judge_status == "DEGRADED"
    assert result.eval_row.judge_aggregate.alpha_point is None


# ---------------------------------------------------------------------------
# 7. Run-level breach gate — under threshold
# ---------------------------------------------------------------------------


class _DegradedSometimes:
    """Fake panel that returns DEGRADED for specified task_ids."""

    def __init__(self, degraded_for_tasks: set[str]) -> None:
        self._degraded = degraded_for_tasks

    async def score(self, er: EvalResult, task_id: str) -> list[Judgment]:
        del er
        if task_id in self._degraded:
            return [_make_judgment(judge_order=0), _make_judgment(judge_order=1)]
        return [
            _make_judgment(judge_order=0),
            _make_judgment(judge_order=1),
            _make_judgment(judge_order=2),
        ]

    def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation:
        return (
            _degraded_aggregation(judgments) if len(judgments) < 3 else _full_aggregation(judgments)
        )


@pytest.mark.asyncio
async def test_degraded_under_20pct_no_breach(tmp_path: Path) -> None:
    # 10 evals, 1 DEGRADED → 10% < 20%
    fake_panel = _DegradedSometimes(degraded_for_tasks={"task-0"})
    runner = _make_runner(tmp_path, judge_panel=cast(FakeJudgePanel, fake_panel))
    spec = _make_simple_spec(n_tasks=10)  # 1 model x 10 tasks x 1 seed = 10 evals

    grid_result = await runner.run(spec)

    assert isinstance(grid_result, GridRunResult)
    assert len(grid_result.results) == 10
    assert grid_result.judge_panel_breach is False


# ---------------------------------------------------------------------------
# 8. Run-level breach gate — over threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_degraded_over_20pct_triggers_breach(tmp_path: Path) -> None:
    # 10 evals, 3 DEGRADED → 30% > 20%
    fake_panel = _DegradedSometimes(degraded_for_tasks={"task-0", "task-1", "task-2"})
    runner = _make_runner(tmp_path, judge_panel=cast(FakeJudgePanel, fake_panel))
    spec = _make_simple_spec(n_tasks=10)

    grid_result = await runner.run(spec)

    assert isinstance(grid_result, GridRunResult)
    assert len(grid_result.results) == 10
    assert grid_result.judge_panel_breach is True


# ---------------------------------------------------------------------------
# 9. G5 — alpha publication gate (ADR-005)
# ---------------------------------------------------------------------------


class _LowAlphaPanel:
    """Fake panel whose aggregate() yields a non-DEGRADED alpha CI lower < 0.70."""

    async def score(self, er: EvalResult, task_id: str) -> list[Judgment]:
        del er, task_id
        return [
            _make_judgment(judge_order=0),
            _make_judgment(judge_order=1),
            _make_judgment(judge_order=2),
        ]

    def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation:
        return _low_alpha_aggregation(judgments)


@pytest.mark.asyncio
async def test_low_alpha_triggers_alpha_gate_breach(tmp_path: Path) -> None:
    # A non-DEGRADED eval with alpha_ci_lower=0.50 < 0.70 must trip the gate.
    runner = _make_runner(tmp_path, judge_panel=cast(FakeJudgePanel, _LowAlphaPanel()))
    spec = _make_simple_spec(n_tasks=3)

    grid_result = await runner.run(spec)

    assert isinstance(grid_result, GridRunResult)
    assert grid_result.alpha_gate_breach is True


@pytest.mark.asyncio
async def test_healthy_alpha_no_gate_breach(tmp_path: Path) -> None:
    # alpha_ci_lower=0.75 >= 0.70 → no breach. Empty degraded set → always full
    # (3 judges) → _full_aggregation with alpha_ci_lower=0.75.
    runner = _make_runner(
        tmp_path, judge_panel=cast(FakeJudgePanel, _DegradedSometimes(degraded_for_tasks=set()))
    )
    spec = _make_simple_spec(n_tasks=3)

    grid_result = await runner.run(spec)

    assert isinstance(grid_result, GridRunResult)
    assert grid_result.alpha_gate_breach is False


@pytest.mark.asyncio
async def test_degraded_alpha_skipped_by_gate(tmp_path: Path) -> None:
    # All-DEGRADED evals have alpha=None → the alpha gate skips them (not a breach).
    fake_panel = _DegradedSometimes(degraded_for_tasks={"task-0", "task-1", "task-2"})
    runner = _make_runner(tmp_path, judge_panel=cast(FakeJudgePanel, fake_panel))
    spec = _make_simple_spec(n_tasks=3)

    grid_result = await runner.run(spec)

    assert isinstance(grid_result, GridRunResult)
    assert grid_result.alpha_gate_breach is False
