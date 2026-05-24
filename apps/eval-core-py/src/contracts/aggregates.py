"""Pydantic v2 models for run-level aggregated statistics.

Aggregates are computed at the aggregating step of the run lifecycle (see
Manifest.status state machine). They close FR-006 noted by architect-reviewer
#2 — the thin v1 schema had no aggregate block.

All cost fields use Decimal to avoid float accumulation errors.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CountsByStatus(BaseModel):
    """Counts of EvalRows grouped by their terminal status.

    scored, failed, skipped are always present (required). pending and running
    are only present during a live run (optional, default 0).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    scored: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    pending: int = Field(default=0, ge=0)
    running: int = Field(default=0, ge=0)

    @property
    def total(self) -> int:
        """Sum of all status buckets."""
        return self.scored + self.failed + self.skipped + self.pending + self.running


class RunAggregates(BaseModel):
    """Run-level aggregate statistics computed at status=aggregating.

    counts_by_error_class maps ErrorClass string values → count of evals with
    that error_class. For example: {"timeout": 2, "rate_limit": 1}.

    per_task_metrics maps task_id → metric_key → statistics dict:
      {"be_01_jwt_auth": {"test_pass_rate": {"mean": 0.9, "median": 1.0,
                                              "p95": 1.0, "sample_count": 12}}}

    Smoke runs have no final_score aggregates (no judges in PRD-001); judges
    aggregate in PRD-002+.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    counts_by_status: CountsByStatus
    counts_by_error_class: dict[str, int] = Field(default_factory=dict)
    total_cost_usd: Decimal = Field(ge=Decimal(0))
    total_wall_clock_ms: int = Field(ge=0)
    per_task_metrics: dict[str, dict[str, dict[str, float | int]]] = Field(
        default_factory=dict,
        description=(
            "task_id → metric_key → {mean, median, p95, sample_count}. "
            "Smoke has no final_score aggregates (no judges)."
        ),
    )
    budget_breach: bool = False
    available_models_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Distinct model_ids with ≥1 scored eval. < 3 triggers status=degraded transition."
        ),
    )
