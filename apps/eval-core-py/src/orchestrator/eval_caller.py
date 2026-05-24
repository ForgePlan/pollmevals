"""Single-eval invocation Protocol -- decouples scheduling from LLM API.

Per architect finding #4 (EVID-007 resolution):
- EvalCaller is a thin Protocol; grid_runner depends on it (testability seam)
- InspectEvalCaller is the real implementation wrapping inspect_ai.eval
  (STUB in Phase 2A -- full wiring lands in Phase 2B with real LLM keys)
- FakeEvalCaller returns deterministic mock results for grid_runner tests

Concurrency is OUTSIDE this module -- see grid_runner.py (Wave 5) for
asyncio.Semaphore(3) declared in ADR-001.
"""

from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from src.contracts import (
    ArtifactRef,
    ErrorClass,
    EvalArtifactRefs,
    EvalRow,
    EvalStats,
    EvalStatus,
)

# ---------------------------------------------------------------------------
# Module-level helper -- exported so grid_runner can use the same function
# ---------------------------------------------------------------------------


def compute_eval_id(
    run_hash: str,
    model_id: str,
    stack_id: str,
    task_id: str,
    seed: int,
) -> str:
    """Return the first 16 hex chars of sha256(concatenated inputs).

    Matches SPEC-001 EvalRow eval_id pattern ``^[a-f0-9]{16}$``.

    The separator ":" prevents ambiguity between adjacent fields
    (e.g. model_id="a:b" vs model_id="a", stack_id="b").
    """
    material = f"{run_hash}:{model_id}:{stack_id}:{task_id}:{seed}"
    return hashlib.sha256(material.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Request / Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvalRequest:
    """All inputs needed to execute one (model, stack, task, seed) eval.

    timeout_s: per-eval wall-clock limit (NFR-002: <= 5 min = 300 s).
    max_retries: number of retry attempts on transient failures (rate-limit,
        5xx, network blips) before recording the eval as failed.
    """

    eval_id: str
    model_id: str  # e.g. "openrouter/anthropic/claude-sonnet-4-6"
    stack_id: str  # e.g. "raw-llm"
    task_id: str  # e.g. "be_01_jwt_auth"
    seed: int
    timeout_s: int = 300  # NFR-002
    max_retries: int = 2


@dataclass(frozen=True)
class EvalResult:
    """Outcome of one EvalCaller.call() invocation.

    Exactly one of eval_row / exception will be non-None in practice, but
    both may coexist if the caller fills eval_row with a failure record after
    catching a known exception (graceful degradation path).

    eval_row:  populated on success OR graceful failure (status=FAILED +
               error_class set).  None only on completely unexpected errors.
    exception: populated when the caller could not produce a valid EvalRow
               at all (e.g. Protocol contract violation).  The grid_runner
               wraps this into a SANDBOX_FAILURE EvalRow itself.
    """

    request: EvalRequest
    eval_row: EvalRow | None
    exception: Exception | None
    started_at: datetime
    completed_at: datetime


# ---------------------------------------------------------------------------
# Protocol -- the testability seam (EVID-007 finding #4)
# ---------------------------------------------------------------------------


@runtime_checkable
class EvalCaller(Protocol):
    """Protocol for executing a single invocation of one LLM eval task.

    Implementors:
      - InspectEvalCaller -- real path (Phase 2B)
      - FakeEvalCaller    -- deterministic mock for grid_runner unit tests

    grid_runner depends on EvalCaller, not on concrete implementations.
    This allows Wave 5 tests to inject FakeEvalCaller without touching
    real LLM APIs.

    Concurrency control (asyncio.Semaphore) lives in grid_runner; callers
    assume they are invoked one-at-a-time from the caller's perspective.
    """

    async def call(self, request: EvalRequest) -> EvalResult: ...


# ---------------------------------------------------------------------------
# InspectEvalCaller -- STUB for Phase 2A
# ---------------------------------------------------------------------------


class InspectEvalCaller:
    """Real EvalCaller wrapping ``inspect_ai.eval``.

    STUB in Phase 2A -- raises NotImplementedError on any call.  Full wiring
    lands in Phase 2B once OPENROUTER_API_KEY and LiteLLM proxy are live.

    Phase 2B implementation plan (left as TODO markers):
    -------------------------------------------------------
    1. Call ``inspect_ai.eval(task, model=request.model_id,
           seed=request.seed, log_dir=str(self._log_dir),
           max_connections=1)`` inside an ``asyncio.wait_for``
           with ``timeout=request.timeout_s``.
    2. Parse the resulting ``.eval`` binary log (opaque per RFC-001 RR-7)
       -- only project the fields declared in SPEC-001 EvalRow mapping table
       into POLLMEVALS EvalRow:
         - ``EvalLog.results.scores`` -> ``automatic_metrics``
         - ``EvalLog.stats.model_usage`` -> ``EvalStats``
         - ``EvalLog.status`` -> ``EvalStatus``
    3. Compute artifact sha256s and write content-addressed files under
       ``log_dir / eval_id /`` before constructing ArtifactRef objects.
    4. Upload artifacts to R2 when ``POLLMEVALS_STORAGE_DRIVER=r2``
       (Phase 2C).
    5. On ``TimeoutError`` -> return EvalRow(status=FAILED,
       error_class=ErrorClass.TIMEOUT).
    6. On rate-limit 429 -> retry up to request.max_retries times with
       exponential backoff, then record RATE_LIMIT.
    7. On 5xx -> SANDBOX_FAILURE (provider infra issue).
    """

    def __init__(
        self,
        *,
        log_dir: pathlib.Path,
        openrouter_base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self._log_dir = log_dir
        self._openrouter_base_url = openrouter_base_url

    async def call(self, request: EvalRequest) -> EvalResult:
        # TODO(Phase 2B): remove this stub and implement real inspect_ai wiring.
        raise NotImplementedError(
            "InspectEvalCaller real wiring deferred to Phase 2B -- "
            "needs OPENROUTER_API_KEY + LiteLLM proxy live. "
            "Use FakeEvalCaller for tests."
        )


# ---------------------------------------------------------------------------
# FakeEvalCaller -- deterministic mock for grid_runner tests
# ---------------------------------------------------------------------------

# Default fake values used when no override is provided.
_DEFAULT_INPUT_TOKENS = 1000
_DEFAULT_OUTPUT_TOKENS = 500
_DEFAULT_WALL_CLOCK_MS = 2000
_DEFAULT_COST_USD = Decimal("0.0125")
_DEFAULT_AUTOMATIC_METRICS: dict[str, float] = {"test_pass_rate": 1.0}

# Sentinel run_hash used internally by FakeEvalCaller when composing eval_id.
# Grid_runner owns the real run_hash; Fake needs a stable value for
# deterministic eval_id generation that tests can predict.
_FAKE_RUN_HASH = "sha256:" + "f" * 64


def _fake_artifact_ref(artifact_type: str, computed_eval_id: str) -> ArtifactRef:
    """Build a content-addressed ArtifactRef with a deterministic sha256.

    The sha256 is derived from ``artifact_type + ":" + computed_eval_id`` so it
    is stable across calls and unique per artifact type.
    """
    content = f"{artifact_type}:{computed_eval_id}"
    sha256 = hashlib.sha256(content.encode()).hexdigest()  # 64 hex chars
    mime: dict[str, str] = {
        "raw_output": "text/plain",
        "normalized_output": "text/plain",
        "evaluator_json": "application/json",
    }
    return ArtifactRef(
        sha256=sha256,
        size_bytes=len(content),
        uri=(
            f"file://artifacts/runs/{_FAKE_RUN_HASH}"
            f"/evals/{computed_eval_id}/{artifact_type}-{sha256}.txt"
        ),
        mime_type=mime.get(artifact_type, "application/octet-stream"),
    )


def _fake_artifact_refs(computed_eval_id: str) -> EvalArtifactRefs:
    """Build the three mandatory ArtifactRefs for a fake run."""
    return EvalArtifactRefs(
        raw_output=_fake_artifact_ref("raw_output", computed_eval_id),
        normalized_output=_fake_artifact_ref("normalized_output", computed_eval_id),
        evaluator_json=_fake_artifact_ref("evaluator_json", computed_eval_id),
    )


def _fake_stats() -> EvalStats:
    return EvalStats(
        input_tokens=_DEFAULT_INPUT_TOKENS,
        output_tokens=_DEFAULT_OUTPUT_TOKENS,
        wall_clock_ms=_DEFAULT_WALL_CLOCK_MS,
        cost_usd=_DEFAULT_COST_USD,
    )


@dataclass
class FakeEvalCaller:
    """Deterministic mock EvalCaller for grid_runner unit tests.

    Design guarantees (critical for Wave 5 grid_runner tests):
    - Same (stack_id, task_id, seed) tuple always produces the same eval_id
      and the same artifact sha256 hashes.
    - FakeEvalCaller never makes network calls.
    - Failed simulations still produce a valid EvalRow (FR-009).

    Args:
        deterministic_outputs: map of ``(stack_id, task_id, seed)`` tuple
            to a dict of EvalRow field overrides.  Currently only
            ``automatic_metrics`` is applied from overrides; extend as
            needed without breaking the frozen EvalRow invariants.
        simulate_failures: map of ``(stack_id, task_id, seed)`` tuple to
            an ``ErrorClass`` value string (e.g. "rate_limit", "timeout").
            Matched calls return EvalRow(status=FAILED, error_class=...).
    """

    deterministic_outputs: dict[tuple[str, str, int], dict[str, object]] = field(
        default_factory=dict
    )
    simulate_failures: dict[tuple[str, str, int], str] = field(default_factory=dict)

    async def call(self, request: EvalRequest) -> EvalResult:
        started_at = datetime.now(UTC)

        key = (request.stack_id, request.task_id, request.seed)
        computed_id = compute_eval_id(
            _FAKE_RUN_HASH,
            request.model_id,
            request.stack_id,
            request.task_id,
            request.seed,
        )
        artifact_refs = _fake_artifact_refs(computed_id)
        stats = _fake_stats()

        # --- Failure simulation path ---
        if key in self.simulate_failures:
            error_class_str = self.simulate_failures[key]
            error_class = ErrorClass(error_class_str)
            completed_at = datetime.now(UTC)
            row = EvalRow(
                eval_id=computed_id,
                model_id=request.model_id,
                stack_id=request.stack_id,
                task_id=request.task_id,
                seed=request.seed,
                status=EvalStatus.FAILED,
                error_class=error_class,
                error_detail="simulated by FakeEvalCaller for test",
                artifact_refs=artifact_refs,
                stats=stats,
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

        # --- Success path (with optional deterministic overrides) ---
        override = self.deterministic_outputs.get(key, {})
        automatic_metrics: dict[str, object] = dict(_DEFAULT_AUTOMATIC_METRICS)
        if "automatic_metrics" in override:
            raw = override["automatic_metrics"]
            if isinstance(raw, dict):
                automatic_metrics = dict(raw)

        completed_at = datetime.now(UTC)
        row = EvalRow(
            eval_id=computed_id,
            model_id=request.model_id,
            stack_id=request.stack_id,
            task_id=request.task_id,
            seed=request.seed,
            status=EvalStatus.SCORED,
            error_class=None,
            error_detail=None,
            artifact_refs=artifact_refs,
            automatic_metrics=automatic_metrics,
            stats=stats,
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
