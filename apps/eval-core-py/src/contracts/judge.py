"""Pydantic v2 contracts for judge-panel scoring (RFC-002 Slice A).

Judgment     -- one judge model's score on one normalised submission.
JudgeAggregation -- aggregated result across the panel (median + alpha).

These models are stubs for Slice A; the full computation lives in
JudgePanel.aggregate() (Slice C). Fields are defined here so the
orchestrator can import the types without depending on the JudgePanel
implementation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Judgment -- per-judge score record
# ---------------------------------------------------------------------------


class Judgment(BaseModel):
    """One judge model's score on one normalised candidate submission.

    judge_order: 0-indexed randomised position in the panel for this eval
                 call (H2 position-bias mitigation per RFC-002 Slice B).
    rubric_scores: per-criterion scores keyed by criterion name (0-10 each).
    total_score: weighted median per docs/02-methodology/scoring.md.
    raw_explanation: judge's chain-of-thought text (for audit / EVID).
    latency_ms: wall-clock for this judge call only (not panel total).
    tokens_in / tokens_out: OpenRouter-reported token counts.
    cost_usd: Decimal to avoid float accumulation errors (like EvalStats).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    judge_model_id: str
    judge_order: int = Field(ge=0)
    rubric_version: str
    rubric_scores: dict[str, float]
    total_score: Annotated[float, Field(ge=0.0, le=10.0)]
    raw_explanation: str
    latency_ms: int = Field(ge=0)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=Decimal(0))


# ---------------------------------------------------------------------------
# JudgeAggregation -- panel-level result
# ---------------------------------------------------------------------------


class JudgeAggregation(BaseModel):
    """Aggregated result across the judge panel for one eval.

    median_per_criterion: median (NOT mean — EVID-001, methodology v0.1.0)
        across judges, keyed by criterion name.
    alpha_point: Krippendorff's alpha point estimate (ordinal level).
        None when judge_status=DEGRADED (per PRD-002 Q3 policy).
    alpha_ci_lower / alpha_ci_upper: bootstrap 95% CI bounds
        (2000 resamples per PRD-002 SC-1). None when DEGRADED.
    judge_status: "OK" when all N judges responded; "DEGRADED" when N-1
        responded (one judge dropped per Q3 policy).
    n_judges_used: number of judges whose scores are in this aggregation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    median_per_criterion: dict[str, float]
    alpha_point: float | None = None
    alpha_ci_lower: float | None = None
    alpha_ci_upper: float | None = None
    judge_status: Literal["OK", "DEGRADED"]
    n_judges_used: int = Field(ge=1)
