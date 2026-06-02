"""Unit tests for StackExecutorCaller + GridRunner dispatch-by-stack (Phase 4b).

Offline — FakeHarnessLauncher + FakeEvalCaller, no Docker / judges / network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from src.contracts import EvalStatus
from src.orchestrator.cost import BudgetGate
from src.orchestrator.eval_caller import EvalRequest, EvalResult, FakeEvalCaller
from src.orchestrator.grid_runner import GridRunner, GridSpec
from src.orchestrator.journal import JournalWriter
from src.orchestrator.stack_caller import StackExecutorCaller, default_model_alias
from src.orchestrator.stack_executor import (
    FakeHarnessLauncher,
    HarnessRunOutcome,
    StackExecutor,
)

_AIDER_STACK_YAML = """
slug: aider
agent_cli: aider
execution:
  mode: repository_patch
  command: aider
  args: [--yes]
limits:
  max_wall_clock_seconds: 600
"""

_PATCH = (
    "diff --git a/solution.ts b/solution.ts\n"
    "--- a/solution.ts\n+++ b/solution.ts\n@@ -1 +1 @@\n+export const ok = 1;\n"
)


def _stacks_root(tmp_path: Path) -> Path:
    root = tmp_path / "stacks"
    (root / "aider").mkdir(parents=True)
    (root / "aider" / "stack.yaml").write_text(_AIDER_STACK_YAML)
    return root


def _seed_solution(task_id: str, dest: Path) -> None:
    (dest / "solution.ts").write_text("export const ok = 1;\n")


def _caller(tmp_path: Path, *, outcome: HarnessRunOutcome | None = None) -> StackExecutorCaller:
    launcher = FakeHarnessLauncher(outcome=outcome) if outcome else FakeHarnessLauncher()
    return StackExecutorCaller(
        executor=StackExecutor(launcher=launcher),
        stacks_root=_stacks_root(tmp_path),
        snapshot_provider=_seed_solution,
        prompt_provider=lambda t: "implement it",
        log_dir=tmp_path / "artifacts",
    )


def _request(stack_id: str = "aider") -> EvalRequest:
    return EvalRequest(
        eval_id="abcdef0123456789",
        model_id="openrouter/qwen/qwen-3-14b",
        stack_id=stack_id,
        task_id="be_01_jwt_auth",
        seed=1,
    )


class TestStackExecutorCaller:
    @pytest.mark.asyncio
    async def test_ok_run_produces_scored_eval_result(self, tmp_path: Path) -> None:
        outcome = HarnessRunOutcome(0, _PATCH, "trace", "", 100, 50, 0, 1000, False)
        result = await _caller(tmp_path, outcome=outcome).call(_request())
        assert result.eval_row is not None
        assert result.eval_row.status is EvalStatus.SCORED
        assert result.eval_row.stack_id == "aider"
        # submission artifact carries the changed solution.ts content
        uri = result.eval_row.artifact_refs.raw_output.uri
        assert Path(uri[len("file://") :]).read_text().find("export const ok = 1;") != -1

    @pytest.mark.asyncio
    async def test_no_patch_run_is_failed_not_dropped(self, tmp_path: Path) -> None:
        outcome = HarnessRunOutcome(0, "", "trace", "", 10, 5, 0, 100, False)  # empty patch
        result = await _caller(tmp_path, outcome=outcome).call(_request())
        assert result.eval_row is not None
        assert result.eval_row.status is EvalStatus.FAILED
        assert result.eval_row.error_class is not None

    @pytest.mark.asyncio
    async def test_carries_cost_and_alias(self, tmp_path: Path) -> None:
        outcome = HarnessRunOutcome(0, _PATCH, "t", "", 1000, 500, 0, 2000, False)
        # no pricing snapshot on the executor → cost 0, but tokens carry over
        result = await _caller(tmp_path, outcome=outcome).call(_request())
        assert result.eval_row is not None
        assert result.eval_row.stats.input_tokens == 1000

    def test_default_model_alias(self) -> None:
        assert default_model_alias("openrouter/qwen/qwen-3-14b") == "qwen-3-14b"
        assert default_model_alias("qwen-3-14b") == "qwen-3-14b"


@dataclass
class _SpyCaller:
    """Records the stack_ids it was asked to run; delegates to FakeEvalCaller."""

    seen: list[str] = field(default_factory=list)
    inner: FakeEvalCaller = field(default_factory=FakeEvalCaller)

    async def call(self, request: EvalRequest) -> EvalResult:
        self.seen.append(request.stack_id)
        return await self.inner.call(request)


class TestGridRunnerDispatchByStack:
    @pytest.mark.asyncio
    async def test_routes_caller_per_stack(self, tmp_path: Path) -> None:
        writer = JournalWriter(tmp_path / "j.ndjson")
        raw_spy, cli_spy = _SpyCaller(), _SpyCaller()

        def caller_for(stack_id: str) -> _SpyCaller:
            return cli_spy if stack_id == "aider" else raw_spy

        runner = GridRunner(
            caller=raw_spy,  # default (unused when caller_for_stack is set)
            caller_for_stack=caller_for,
            journal_writer=writer,
            budget_gate=BudgetGate(cap_usd=Decimal("9999")),
            pricing_snapshot={},
        )
        spec = GridSpec(
            run_hash="sha256:" + "a" * 64,
            models=["m"],
            tasks=["be_01_jwt_auth"],
            stacks=["raw-llm", "aider"],
            seeds=[1],
        )
        await runner.run(spec)

        assert cli_spy.seen == ["aider"]
        assert raw_spy.seen == ["raw-llm"]

    @pytest.mark.asyncio
    async def test_falls_back_to_single_caller(self, tmp_path: Path) -> None:
        # No caller_for_stack → every stack uses the single caller (back-compat).
        writer = JournalWriter(tmp_path / "j.ndjson")
        spy = _SpyCaller()
        runner = GridRunner(
            caller=spy,
            journal_writer=writer,
            budget_gate=BudgetGate(cap_usd=Decimal("9999")),
            pricing_snapshot={},
        )
        spec = GridSpec(
            run_hash="sha256:" + "b" * 64,
            models=["m"],
            tasks=["t"],
            stacks=["raw-llm", "aider"],
            seeds=[1],
        )
        await runner.run(spec)
        assert sorted(spy.seen) == ["aider", "raw-llm"]
