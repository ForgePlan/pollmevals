"""StackExecutorCaller — make a CLI stack usable through the EvalCaller Protocol.

RFC-006 Phase 4b. GridRunner dispatches one ``EvalCaller`` per (model, stack,
task, seed). ``raw-llm`` uses ``InspectEvalCaller`` (model completion); this
adapter lets every ``repository_patch`` stack (aider, …) flow through the SAME
interface: resolve the stack adapter → seed a candidate snapshot → run the
harness (StackExecutor) → bridge the patch to an ``EvalResult`` (stack_scoring).

GridRunner's judge hook then scores the produced submission exactly as it does
for raw-llm — no special-casing downstream.

Snapshot + prompt providers are injected so the adapter is unit-testable
offline (FakeHarnessLauncher + fakes), and the real wiring lives in
``make_stack_executor_caller``.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from src.contracts import ErrorClass, EvalRow, EvalStats, EvalStatus
from src.orchestrator.auto_metrics import run_auto_evaluators
from src.orchestrator.eval_caller import (
    EvalRequest,
    EvalResult,
    _make_stub_artifact_refs,
    compute_eval_id,
)
from src.orchestrator.stack_executor import (
    ExecStatus,
    StackAdapter,
    StackExecRequest,
    StackExecResult,
    StackExecutor,
)
from src.orchestrator.stack_scoring import exec_result_to_eval_result

# ExecStatus (Half A terminal) → ErrorClass (manifest error taxonomy).
_EXEC_ERROR_CLASS: dict[ExecStatus, ErrorClass] = {
    ExecStatus.TIMEOUT: ErrorClass.TIMEOUT,
    ExecStatus.FAILED: ErrorClass.SANDBOX_FAILURE,
    ExecStatus.NO_PATCH: ErrorClass.SANDBOX_FAILURE,
    ExecStatus.UNSUPPORTED: ErrorClass.SANDBOX_FAILURE,
}


def default_model_alias(model_id: str) -> str:
    """Heuristic provider-route → proxy alias: the segment after the last '/'.

    e.g. ``openrouter/qwen/qwen-3-14b`` → ``qwen-3-14b``. The proxy
    (litellm-config.yaml) keys on these short aliases. Inject a different
    mapping when the route does not follow this shape.
    """
    return model_id.rsplit("/", 1)[-1]


@dataclass
class StackExecutorCaller:
    """EvalCaller adapter wrapping StackExecutor + the Half A→B bridge.

    Args:
        executor: the StackExecutor (carries launcher + proxy + pricing).
        stacks_root: dir holding ``<stack_id>/stack.yaml`` adapters.
        snapshot_provider: ``(task_id, dest) -> None`` — seed the candidate
            working dir (the harness edits this). Must NOT include gold/tests.
        prompt_provider: ``task_id -> str`` — the task prompt for the harness.
        log_dir: where the bridge writes submission artifacts.
        run_hash: the run's content hash (passed to the bridge for eval_id).
        model_alias_for: ``model_id -> proxy alias`` (default: last path segment).
    """

    executor: StackExecutor
    stacks_root: Path
    snapshot_provider: Callable[[str, Path], None]
    prompt_provider: Callable[[str], str]
    log_dir: Path
    run_hash: str = "sha256:" + "5" * 64
    model_alias_for: Callable[[str], str] = default_model_alias

    async def call(self, request: EvalRequest) -> EvalResult:
        started_at = datetime.now(UTC)
        adapter = StackAdapter.from_yaml_path(self.stacks_root / request.stack_id / "stack.yaml")

        snapshot = Path(tempfile.mkdtemp(prefix=f"pollmevals-{request.stack_id}-"))
        self.snapshot_provider(request.task_id, snapshot)

        exec_request = StackExecRequest(
            eval_id=request.eval_id,
            model_id=request.model_id,
            model_alias=self.model_alias_for(request.model_id),
            stack=adapter,
            task_id=request.task_id,
            task_prompt=self.prompt_provider(request.task_id),
            repo_snapshot_dir=snapshot,
            seed=request.seed,
            timeout_s=request.timeout_s,
        )
        exec_result = await self.executor.execute(exec_request)

        if exec_result.status is ExecStatus.OK:
            eval_result = exec_result_to_eval_result(
                exec_result, log_dir=self.log_dir, run_hash=self.run_hash
            )
            # Run lint + type_safety on the real filesystem snapshot produced by
            # the harness.  The submission dir is the repo_snapshot_dir that the
            # harness wrote its changes into (not the concatenated text blob).
            # Evaluators self-skip gracefully when binaries are absent.
            assert eval_result.eval_row is not None
            auto_metrics = await run_auto_evaluators(
                str(exec_request.repo_snapshot_dir), request.task_id
            )
            import dataclasses

            eval_result = dataclasses.replace(
                eval_result,
                eval_row=eval_result.eval_row.model_copy(
                    update={"automatic_metrics": auto_metrics}
                ),
            )
            return eval_result
        return self._failed_result(request, exec_result, started_at)

    def _failed_result(
        self,
        request: EvalRequest,
        exec_result: StackExecResult,
        started_at: datetime,
    ) -> EvalResult:
        """Map a non-OK execution to a graceful FAILED EvalResult (FR-009)."""
        eval_id = compute_eval_id(
            self.run_hash, request.model_id, request.stack_id, request.task_id, request.seed
        )
        error_class = _EXEC_ERROR_CLASS.get(exec_result.status, ErrorClass.SANDBOX_FAILURE)
        completed_at = datetime.now(UTC)
        row = EvalRow(
            eval_id=eval_id,
            model_id=request.model_id,
            stack_id=request.stack_id,
            task_id=request.task_id,
            seed=request.seed,
            status=EvalStatus.FAILED,
            error_class=error_class,
            error_detail=exec_result.error_detail or f"executor status={exec_result.status}",
            artifact_refs=_make_stub_artifact_refs(eval_id),
            stats=EvalStats(
                input_tokens=exec_result.input_tokens,
                output_tokens=exec_result.output_tokens,
                wall_clock_ms=exec_result.wall_ms,
                cost_usd=exec_result.cost_usd,
            ),
            started_at=started_at,
            completed_at=completed_at,
        )
        return EvalResult(
            request=request,
            eval_row=row,
            exception=None,
            started_at=started_at,
            completed_at=completed_at,
        )


# ---------------------------------------------------------------------------
# Real-wiring factory + default providers (repo-path aware)
# ---------------------------------------------------------------------------


def make_task_prompt_provider(repo_root: Path) -> Callable[[str], str]:
    """Read ``evals/task-packs/<task_id>/task.yaml`` → ``prompt_template``."""

    def _provider(task_id: str) -> str:
        pack = repo_root / "evals" / "task-packs" / task_id / "task.yaml"
        data = yaml.safe_load(pack.read_text(encoding="utf-8"))
        return str(data["prompt_template"])

    return _provider


# Per-task wall-clock budget by declared difficulty. Different tasks need
# different time — a quick README (easy) vs a full backend middleware (medium)
# vs a multi-file refactor (hard). Tune here, or override per task in GridSpec.
_DIFFICULTY_TIMEOUT_S: dict[str, int] = {"easy": 300, "medium": 600, "hard": 1200}


def make_task_timeout_provider(repo_root: Path) -> Callable[[str], int]:
    """``task_id -> wall-clock seconds`` from the task's declared difficulty."""

    def _provider(task_id: str) -> int:
        data = yaml.safe_load(
            (repo_root / "evals" / "task-packs" / task_id / "task.yaml").read_text(encoding="utf-8")
        )
        difficulty = str(data.get("difficulty", "medium")) if isinstance(data, dict) else "medium"
        return _DIFFICULTY_TIMEOUT_S.get(difficulty, 600)

    return _provider


def make_be01_snapshot_provider(repo_root: Path) -> Callable[[str, Path], None]:
    """Seed a be_01 candidate workspace: pinned deps only — NO gold, NO tests.

    Other tasks need their own provider; this is the first-slice default. A
    future convention (a ``candidate/`` scaffold dir per pack) generalises it.
    """
    gold = repo_root / "evals" / "task-packs" / "be_01_jwt_auth" / "gold"

    def _provider(task_id: str, dest: Path) -> None:
        import shutil

        for f in ("package.json", "tsconfig.json"):
            shutil.copy(gold / f, dest / f)
        (dest / "solution.ts").write_text(
            "// Implement the Express JWT auth middleware here (see the task prompt).\n",
            encoding="utf-8",
        )

    return _provider
