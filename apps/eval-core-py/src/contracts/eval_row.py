"""Pydantic v2 models for a single eval execution row.

One EvalRow represents the full lifecycle record of one LLM invocation:
  (model, stack, task, seed, region) → output + scores + stats.

Key invariant: failed evals MUST be stored, NOT dropped from the denominator
(PRD-001 FR-009). The model_validator below enforces that a failed status
always carries an error_class.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .artifact_ref import ArtifactRef
from .judge import JudgeAggregation, Judgment

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EvalStatus(StrEnum):
    """Lifecycle states of a single eval execution."""

    PENDING = "pending"
    RUNNING = "running"
    SCORED = "scored"
    FAILED = "failed"
    SKIPPED = "skipped"


class ErrorClass(StrEnum):
    """Taxonomy of failure modes for failed evals.

    Python identifiers cannot start with a digit, so SERVER_5XX and
    CLIENT_4XX use the safe attribute names; the string *values* match the
    JSON schema enum ("5xx_server", "4xx_client") so serialization is
    transparent.
    """

    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    SERVER_5XX = "5xx_server"
    CLIENT_4XX = "4xx_client"
    TIMEOUT = "timeout"
    CONTRACT_VIOLATION = "contract_violation"
    SANDBOX_FAILURE = "sandbox_failure"
    # Judge-layer crash (RFC-002 Slice E). The candidate produced output OK
    # but the judge panel call or aggregation raised an unexpected exception
    # (network, JSON parse, krippendorff failure, etc.). The row is preserved
    # with status=FAILED instead of vanishing through asyncio.gather — FR-009.
    JUDGE_FAILURE = "judge_failure"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class EvalArtifactRefs(BaseModel):
    """Artifact references for one eval — required outputs plus optional ones.

    raw_output, normalized_output, and evaluator_json are always produced
    (even for failed evals — see FR-009). stdout, stderr, and trace_json are
    only present for Stacks with L2+ scaffolding.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_output: ArtifactRef
    normalized_output: ArtifactRef
    evaluator_json: ArtifactRef
    stdout: ArtifactRef | None = None
    stderr: ArtifactRef | None = None
    trace_json: ArtifactRef | None = None


class EvalStats(BaseModel):
    """Token-usage and cost statistics for one eval invocation.

    cost_usd uses Decimal to avoid float accumulation errors across large
    run aggregations. Computed as:
      input_tokens * pricing_snapshot.input_per_mtoken_usd / 1_000_000
      + output_tokens * pricing_snapshot.output_per_mtoken_usd / 1_000_000
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    wall_clock_ms: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=Decimal(0))


# ---------------------------------------------------------------------------
# EvalRow
# ---------------------------------------------------------------------------

_EvalId = Annotated[str, Field(pattern=r"^[a-f0-9]{16}$")]


class EvalRow(BaseModel):
    """Complete record for one (model, stack, task, seed) execution.

    Immutable once created (frozen=True). Any correction creates a new Run
    that supersedes the original (ADR-0002).

    eval_id is the first 16 hex chars of
      sha256(run_hash + ":" + model_id + ":" + stack_id + ":" + task_id + ":" + str(seed)).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    eval_id: _EvalId
    model_id: str
    stack_id: str
    task_id: str
    seed: int
    status: EvalStatus
    error_class: ErrorClass | None = None
    error_detail: str | None = None
    artifact_refs: EvalArtifactRefs
    final_score: float | None = None
    automatic_metrics: dict[str, Any] = Field(default_factory=dict)
    stats: EvalStats
    started_at: datetime | None = None
    completed_at: datetime | None = None
    # Judge layer (RFC-002 Slice E). Both default-None: a smoke run without a
    # configured JudgePanel still produces valid EvalRow objects.
    judgments: list[Judgment] | None = None
    judge_aggregate: JudgeAggregation | None = None

    @field_validator("final_score", mode="before")
    @classmethod
    def _validate_final_score(cls, v: Any) -> Any:
        """Enforce 0 ≤ final_score ≤ 10 when not None."""
        if v is not None:
            score = float(v)
            if not (0.0 <= score <= 10.0):
                raise ValueError(f"final_score must be in [0, 10], got {score}")
        return v

    @model_validator(mode="after")
    def _failed_requires_error_class(self) -> EvalRow:
        """Invariant: status=failed MUST carry an error_class (FR-009)."""
        if self.status == EvalStatus.FAILED and self.error_class is None:
            raise ValueError("error_class must be set when status is 'failed' (PRD-001 FR-009)")
        return self
