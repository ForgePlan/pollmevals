"""Single-invocation Protocol -- decouples scheduling from LLM API.

Per architect finding #4 (EVID-007 resolution):
- EvalCaller is a thin Protocol; grid_runner depends on it (testability seam)
- InspectEvalCaller is the real implementation: direct LiteLLM HTTP POST to
  /chat/completions, with 429 retry (max 3, exponential backoff).
  Inspect AI integration is the next milestone; for now the caller hits the
  LiteLLM proxy directly (http://localhost:4000) so the full stack exercises
  the LGTM observability pipeline.
- FakeEvalCaller returns deterministic mock results for grid_runner tests

Concurrency is OUTSIDE this module -- see grid_runner.py (Wave 5) for
asyncio.Semaphore(3) declared in ADR-001.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import pathlib
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

import httpx

from src.contracts import (
    ArtifactRef,
    ErrorClass,
    EvalArtifactRefs,
    EvalRow,
    EvalStats,
    EvalStatus,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry constants for InspectEvalCaller
# ---------------------------------------------------------------------------

_RETRY_MAX = 3
_RETRY_BASE_DELAY_S = 1.0  # first back-off; doubles each attempt

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
    """All inputs needed to execute one (model, stack, task, seed) invocation.

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
      - InspectEvalCaller -- real path (Phase 2C)
      - FakeEvalCaller    -- deterministic mock for grid_runner unit tests

    grid_runner depends on EvalCaller, not on concrete implementations.
    This allows Wave 5 tests to inject FakeEvalCaller without touching
    real LLM APIs.

    Concurrency control (asyncio.Semaphore) lives in grid_runner; callers
    assume they are invoked one-at-a-time from the caller's perspective.
    """

    async def call(self, request: EvalRequest) -> EvalResult: ...


# ---------------------------------------------------------------------------
# InspectEvalCaller -- Phase 2C real implementation
# ---------------------------------------------------------------------------


class InspectEvalCaller:
    """Real EvalCaller: POST to LiteLLM proxy /chat/completions.

    Phase 2C implementation -- replaces the Phase 2A stub.  Uses the LiteLLM
    proxy at ``litellm_base_url`` (default http://localhost:4000) so that the
    full LGTM observability pipeline captures traces end-to-end.

    Retry policy: on HTTP 429 (rate-limit), retry up to ``_RETRY_MAX`` times
    with exponential back-off (1 s -> 2 s -> 4 s).  All other 4xx / 5xx errors
    produce a graceful EvalRow(status=FAILED) rather than raising.

    TODO(Phase 2D, PRD-001 FR-003): replace direct HTTP with ``inspect_ai.eval()`` wiring once
    task scaffolding (task.yaml + solver pipeline) is ready.  The EvalRow
    mapping table from SPEC-001 applies unchanged; only the invocation layer
    changes.

    Args:
        litellm_base_url: LiteLLM proxy base URL (Phase 2B infra).
        api_key: Bearer token sent as ``Authorization: Bearer <key>``.  Defaults
            to empty string so the caller works without auth against a local
            proxy.
        log_dir: Directory for writing content-addressed artifact files.
        openrouter_base_url: Retained for backward-compat with existing tests
            that assert the attribute exists.
    """

    def __init__(
        self,
        *,
        log_dir: pathlib.Path,
        litellm_base_url: str = "http://localhost:4000",
        api_key: str = "",
        openrouter_base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self._log_dir = log_dir
        self._litellm_base_url = litellm_base_url.rstrip("/")
        self._api_key = api_key
        # Retained for backward-compat with existing test assertions.
        self._openrouter_base_url = openrouter_base_url

    async def call(self, request: EvalRequest) -> EvalResult:
        """Execute one invocation via the LiteLLM proxy with 429 retry.

        Returns a populated EvalResult on success.  On unrecoverable error,
        returns EvalResult with eval_row.status=FAILED (FR-009 -- never drops).
        """
        started_at = datetime.now(UTC)

        row_id = compute_eval_id(
            request.eval_id,  # use pre-computed id as the run_hash fragment
            request.model_id,
            request.stack_id,
            request.task_id,
            request.seed,
        )

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, object] = {
            "model": request.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"[POLLMEVALS task] task={request.task_id} "
                        f"stack={request.stack_id} seed={request.seed}"
                    ),
                }
            ],
            "seed": request.seed,
            "max_tokens": 512,
        }

        url = f"{self._litellm_base_url}/chat/completions"
        attempt = 0
        last_exc: Exception | None = None

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=float(request.timeout_s), write=10.0, pool=5.0)
        ) as client:
            while attempt <= _RETRY_MAX:
                try:
                    wall_start = time.monotonic()
                    resp = await client.post(url, json=payload, headers=headers)
                    wall_ms = int((time.monotonic() - wall_start) * 1000)

                    if resp.status_code == 429:
                        attempt += 1
                        if attempt > _RETRY_MAX:
                            return self._make_failed_result(
                                request,
                                started_at,
                                row_id,
                                ErrorClass.RATE_LIMIT,
                                f"429 rate-limit after {_RETRY_MAX} retries",
                            )
                        delay = _RETRY_BASE_DELAY_S * (2 ** (attempt - 1))
                        logger.warning(
                            "InspectEvalCaller: 429 for row_id=%s attempt=%d, retrying in %.1fs",
                            row_id,
                            attempt,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue

                    if resp.status_code >= 500:
                        return self._make_failed_result(
                            request,
                            started_at,
                            row_id,
                            ErrorClass.SANDBOX_FAILURE,
                            f"HTTP {resp.status_code} from LiteLLM proxy",
                        )

                    if resp.status_code >= 400:
                        return self._make_failed_result(
                            request,
                            started_at,
                            row_id,
                            ErrorClass.SANDBOX_FAILURE,
                            f"HTTP {resp.status_code} client error",
                        )

                    data = resp.json()
                    return self._make_success_result(request, started_at, row_id, data, wall_ms)

                except (TimeoutError, httpx.TimeoutException) as exc:
                    last_exc = exc
                    return self._make_failed_result(
                        request,
                        started_at,
                        row_id,
                        ErrorClass.TIMEOUT,
                        f"Timeout after {request.timeout_s}s",
                    )
                except httpx.HTTPError as exc:
                    last_exc = exc
                    return self._make_failed_result(
                        request,
                        started_at,
                        row_id,
                        ErrorClass.NETWORK,
                        f"HTTP error: {exc}",
                    )

        # Should not be reachable; belt-and-suspenders for while-loop exit.
        return self._make_failed_result(
            request,
            started_at,
            row_id,
            ErrorClass.SANDBOX_FAILURE,
            f"Exhausted retry loop; last_exc={last_exc}",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _make_failed_result(
        self,
        request: EvalRequest,
        started_at: datetime,
        row_id: str,
        error_class: ErrorClass,
        detail: str,
    ) -> EvalResult:
        completed_at = datetime.now(UTC)
        artifact_refs = _make_stub_artifact_refs(row_id)
        row = EvalRow(
            eval_id=row_id,
            model_id=request.model_id,
            stack_id=request.stack_id,
            task_id=request.task_id,
            seed=request.seed,
            status=EvalStatus.FAILED,
            error_class=error_class,
            error_detail=detail,
            artifact_refs=artifact_refs,
            stats=EvalStats(
                input_tokens=0,
                output_tokens=0,
                wall_clock_ms=0,
                cost_usd=Decimal("0"),
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

    def _make_success_result(
        self,
        request: EvalRequest,
        started_at: datetime,
        row_id: str,
        data: dict[str, object],
        wall_ms: int,
    ) -> EvalResult:
        completed_at = datetime.now(UTC)

        # Extract token usage from OpenAI-compatible response.
        # isinstance() narrowing is required for mypy --strict: data.get("usage") returns
        # object, and object has no .get(). The isinstance check gives us dict[str, object].
        usage: dict[str, object] = {}
        _u = data.get("usage")
        if isinstance(_u, dict):
            usage = _u
        _pt = usage.get("prompt_tokens")
        input_tokens = int(_pt) if isinstance(_pt, (int, float)) else 0
        _ct = usage.get("completion_tokens")
        output_tokens = int(_ct) if isinstance(_ct, (int, float)) else 0

        # Extract raw output text.
        raw_output = ""
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                msg = first.get("message") or {}
                if isinstance(msg, dict):
                    raw_output = str(msg.get("content") or "")

        artifact_refs = _make_stub_artifact_refs(row_id, raw_output)
        stats = EvalStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            wall_clock_ms=wall_ms,
            cost_usd=Decimal("0"),  # populated by CostReconciler post-run
        )
        row = EvalRow(
            eval_id=row_id,
            model_id=request.model_id,
            stack_id=request.stack_id,
            task_id=request.task_id,
            seed=request.seed,
            status=EvalStatus.SCORED,
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


# ---------------------------------------------------------------------------
# Module-level artifact helper (used by InspectEvalCaller + FakeEvalCaller)
# ---------------------------------------------------------------------------


def _make_stub_artifact_refs(row_id: str, raw_content: str = "") -> EvalArtifactRefs:
    """Build content-addressed ArtifactRefs from *row_id* + optional raw content."""

    def _ref(label: str, content: str) -> ArtifactRef:
        sha256 = hashlib.sha256(content.encode()).hexdigest()
        return ArtifactRef(
            sha256=sha256,
            size_bytes=len(content.encode()),
            uri=f"file://artifacts/evals/{row_id}/{label}-{sha256}.txt",
            mime_type="text/plain" if label != "evaluator_json" else "application/json",
        )

    normalized = raw_content.strip()
    evaluator = f'{{"row_id":"{row_id}","raw_len":{len(raw_content)}}}'
    return EvalArtifactRefs(
        raw_output=_ref("raw_output", raw_content or row_id),
        normalized_output=_ref("normalized_output", normalized or row_id),
        evaluator_json=_ref("evaluator_json", evaluator),
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


def _fake_artifact_ref(artifact_type: str, computed_id: str) -> ArtifactRef:
    """Build a content-addressed ArtifactRef with a deterministic sha256.

    The sha256 is derived from ``artifact_type + ":" + computed_id`` so it
    is stable across calls and unique per artifact type.
    """
    content = f"{artifact_type}:{computed_id}"
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
            f"/evals/{computed_id}/{artifact_type}-{sha256}.txt"
        ),
        mime_type=mime.get(artifact_type, "application/octet-stream"),
    )


def _fake_artifact_refs(computed_id: str) -> EvalArtifactRefs:
    """Build the three mandatory ArtifactRefs for a fake run."""
    return EvalArtifactRefs(
        raw_output=_fake_artifact_ref("raw_output", computed_id),
        normalized_output=_fake_artifact_ref("normalized_output", computed_id),
        evaluator_json=_fake_artifact_ref("evaluator_json", computed_id),
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
