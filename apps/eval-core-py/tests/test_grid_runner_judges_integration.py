"""RFC-002 Slice E — full-grid integration tests (AC #1-#4).

Goes one level above test_grid_runner_judges.py (which exercises _run_single):
these run the COMPLETE 45-eval grid (5 models x 3 tasks x 3 seeds) end-to-end
through GridRunner.run() with a JudgePanel-shaped stand-in.

AC coverage (from RFC-002 § Slice E acceptance criteria):
- AC #1: 3 working judges -> all 45 rows judge_status=OK, judge_panel_breach=False.
- AC #2: 1 of 45 evals gets DEGRADED panel (1-of-3 judge unavailable)
         -> 1/45 = 2.2% < 20% threshold -> breach=False, run continues.
- AC #3: 12 of 45 evals DEGRADED -> 12/45 = 26.7% > 20% -> breach=True.
- AC #4: Cost dry-run: 45 x ($0.0125 candidate + $0.15 judge estimate)
         = $7.31 well within $50 NFR-001 envelope.

No respx / no real HTTP. The RFC-002 Test Plan explicitly authorises a
"FakeJudgeCaller (Protocol mirror of FakeEvalCaller)" pattern — that's
what `_FakePanel` provides here, programmed per test.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from src.contracts import (
    JudgeAggregation,
    Judgment,
)
from src.orchestrator.cost import BudgetGate, PricingTuple
from src.orchestrator.eval_caller import (
    EvalResult,
    FakeEvalCaller,
)
from src.orchestrator.grid_runner import (
    GridRunner,
    GridSpec,
)
from src.orchestrator.journal import JournalWriter
from src.orchestrator.judge_panel import (
    JudgePanel,
    JudgeUnavailableError,
)

# ---------------------------------------------------------------------------
# Test grid — 5 x 3 x 3 = 45 evals (RFC-002 Slice E baseline)
# ---------------------------------------------------------------------------

_RUN_HASH = "sha256:" + "d" * 64
_UNLIMITED_BUDGET = BudgetGate(cap_usd=Decimal("50"))  # NFR-001
_DEFAULT_PRICING: dict[str, PricingTuple] = {}

_MODELS = [
    "openrouter/anthropic/claude-sonnet-4-6",
    "openrouter/openai/gpt-4o-mini",
    "openrouter/google/gemini-flash-1-5",
    "openrouter/qwen/qwen-2-5-14b",
    "openrouter/meta-llama/llama-4-70b",
]
_TASKS = ["be_01_jwt_auth", "fe_01_multistep_form", "doc_01_cli_readme"]
_SEEDS = [1, 2, 3]


def _make_grid_spec() -> GridSpec:
    """The canonical 45-eval smoke grid from PRD-001."""
    return GridSpec(
        run_hash=_RUN_HASH,
        models=_MODELS,
        tasks=_TASKS,
        stacks=["raw-llm"],
        seeds=_SEEDS,
    )


def _make_judgment(judge_id: str, order: int, total: float = 8.0) -> Judgment:
    return Judgment(
        judge_model_id=judge_id,
        judge_order=order,
        rubric_version="1.0",
        rubric_scores={"overall": total},
        total_score=total,
        raw_explanation="fake explanation",
        latency_ms=100,
        tokens_in=10,
        tokens_out=10,
        cost_usd=Decimal("0.05"),  # 3 judges x 0.05 = 0.15 (matches estimate)
    )


# ---------------------------------------------------------------------------
# Fake panel — duck-typed JudgePanel substitute (RFC-002 Test Plan pattern)
# ---------------------------------------------------------------------------


class _FakePanel:
    """Programmable JudgePanel stand-in.

    Constructor flags decide per-eval behaviour:
      degraded_keys: set of (model_id, task_id, seed) -> emit only 2 judgments
                     (panel sees < N_REQUESTED and raises JudgeUnavailableError;
                      GridRunner then routes to the DEGRADED path).
    """

    N_REQUESTED = 3

    def __init__(self, degraded_keys: set[tuple[str, str, int]] | None = None) -> None:
        self._degraded = degraded_keys or set()
        self.score_calls = 0
        self.aggregate_calls = 0

    async def score(self, er: EvalResult, task_id: str) -> list[Judgment]:
        self.score_calls += 1
        key = (er.request.model_id, task_id, er.request.seed)
        if key in self._degraded:
            partial = [
                _make_judgment("openrouter/anthropic/claude-sonnet-4-6", 0),
                _make_judgment("openrouter/openai/gpt-4o-mini", 1),
            ]
            raise JudgeUnavailableError(
                "google/gemini timeout",
                partial_judgments=partial,
                n_judges_requested=self.N_REQUESTED,
            )
        return [
            _make_judgment("openrouter/anthropic/claude-sonnet-4-6", 0),
            _make_judgment("openrouter/openai/gpt-4o-mini", 1),
            _make_judgment("openrouter/google/gemini-flash-1-5", 2),
        ]

    def aggregate(self, judgments: list[Judgment]) -> JudgeAggregation:
        self.aggregate_calls += 1
        if len(judgments) < self.N_REQUESTED:
            return JudgeAggregation(
                median_per_criterion={"overall": 8.0},
                alpha_point=None,
                alpha_ci_lower=None,
                alpha_ci_upper=None,
                judge_status="DEGRADED",
                n_judges_used=len(judgments),
            )
        return JudgeAggregation(
            median_per_criterion={"overall": 8.0},
            alpha_point=0.85,
            alpha_ci_lower=0.75,
            alpha_ci_upper=0.92,
            judge_status="OK",
            n_judges_used=len(judgments),
        )


def _make_runner(tmp_path: Path, panel: _FakePanel | None) -> GridRunner:
    journal = JournalWriter(tmp_path / "grid.journal.ndjson")
    return GridRunner(
        caller=FakeEvalCaller(),
        journal_writer=journal,
        budget_gate=_UNLIMITED_BUDGET,
        pricing_snapshot=_DEFAULT_PRICING,
        judge_panel=cast(JudgePanel | None, panel),
    )


# ---------------------------------------------------------------------------
# AC #1 — 3 working judges, 45-eval grid, all FULL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac1_full_panel_all_45_evals_ok(tmp_path: Path) -> None:
    panel = _FakePanel()
    runner = _make_runner(tmp_path, panel)
    spec = _make_grid_spec()

    grid = await runner.run(spec)

    assert len(grid.results) == 45
    assert panel.score_calls == 45  # one panel call per SCORED candidate
    assert grid.judge_panel_breach is False
    assert grid.budget_breach is False

    judged = [r for r in grid.results if isinstance(r, EvalResult) and r.eval_row is not None]
    assert len(judged) == 45
    for r in judged:
        assert r.eval_row is not None
        assert r.eval_row.judge_aggregate is not None
        assert r.eval_row.judge_aggregate.judge_status == "OK"
        assert r.eval_row.judgments is not None
        assert len(r.eval_row.judgments) == 3


# ---------------------------------------------------------------------------
# AC #2 — 1 of 45 DEGRADED, run continues, no breach (2.2% < 20%)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac2_one_degraded_no_breach(tmp_path: Path) -> None:
    # Mark exactly 1 specific (model, task, seed) tuple as degraded.
    degraded = {(_MODELS[0], _TASKS[0], _SEEDS[0])}
    panel = _FakePanel(degraded_keys=degraded)
    runner = _make_runner(tmp_path, panel)
    spec = _make_grid_spec()

    grid = await runner.run(spec)

    assert len(grid.results) == 45
    assert grid.judge_panel_breach is False, "1/45 = 2.2% must NOT trigger > 20% threshold"

    judged = [r for r in grid.results if isinstance(r, EvalResult) and r.eval_row is not None]
    degraded_rows = [
        r
        for r in judged
        if r.eval_row is not None
        and r.eval_row.judge_aggregate is not None
        and r.eval_row.judge_aggregate.judge_status == "DEGRADED"
    ]
    assert len(degraded_rows) == 1
    assert degraded_rows[0].eval_row is not None
    assert degraded_rows[0].eval_row.judge_aggregate is not None
    assert degraded_rows[0].eval_row.judge_aggregate.alpha_point is None
    # Candidate stays SCORED on DEGRADED path (status is preserved)
    from src.contracts import EvalStatus

    assert degraded_rows[0].eval_row.status == EvalStatus.SCORED


# ---------------------------------------------------------------------------
# AC #3 — 12 of 45 DEGRADED (~27%), breach=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac3_twelve_degraded_triggers_breach(tmp_path: Path) -> None:
    # Pick 12 specific tuples — first 12 in iteration order (model->task->seed).
    spec = _make_grid_spec()
    requests = list(spec.iter_requests())
    degraded = {(r.model_id, r.task_id, r.seed) for r in requests[:12]}
    assert len(degraded) == 12

    panel = _FakePanel(degraded_keys=degraded)
    runner = _make_runner(tmp_path, panel)

    grid = await runner.run(spec)

    assert len(grid.results) == 45
    # 12 / 45 = 0.2667 > 0.20 -> breach trips
    assert grid.judge_panel_breach is True

    judged = [r for r in grid.results if isinstance(r, EvalResult) and r.eval_row is not None]
    n_degraded = sum(
        1
        for r in judged
        if r.eval_row is not None
        and r.eval_row.judge_aggregate is not None
        and r.eval_row.judge_aggregate.judge_status == "DEGRADED"
    )
    assert n_degraded == 12


# ---------------------------------------------------------------------------
# AC #4 — Cost envelope: 45 x (candidate + judges) << $50 NFR-001
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac4_cost_within_nfr001_envelope(tmp_path: Path) -> None:
    panel = _FakePanel()
    runner = _make_runner(tmp_path, panel)
    spec = _make_grid_spec()

    grid = await runner.run(spec)

    # Each eval: FakeEvalCaller cost = $0.0125 (candidate) + 3 x $0.05 (judges) = $0.1625.
    # 45 evals -> 45 x 0.1625 = $7.3125.
    expected_total = Decimal("45") * (Decimal("0.0125") + Decimal("0.15"))
    assert grid.total_cost_usd == expected_total, (
        f"expected {expected_total}, got {grid.total_cost_usd}"
    )
    assert grid.total_cost_usd <= Decimal("50"), "NFR-001: must stay ≤ $50 per run"
    assert grid.total_cost_usd <= Decimal("15"), (
        "PRD-002 NFR-001: smoke with judges = $12 ± $3 envelope"
    )
    assert grid.budget_breach is False
