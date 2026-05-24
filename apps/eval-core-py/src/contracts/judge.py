"""Pydantic v2 contracts for judge-panel scoring (RFC-002 Slices A + D).

Judgment         -- one judge model's score on one normalised submission.
JudgeAggregation -- aggregated result across the panel (median + alpha).
JudgeCalibration -- per-judge calibration metrics (MAD + rank correlation).
CalibrationResult -- full calibration run outcome for one task.
ProbeResult      -- identification probe result (SC-4 anonymisation check).
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


# ---------------------------------------------------------------------------
# JudgeCalibration -- per-judge calibration metrics (RFC-002 Slice D)
# ---------------------------------------------------------------------------


class JudgeCalibration(BaseModel):
    """Per-judge calibration metrics computed over a set of gold-scored samples.

    Produced by JudgePanel.run_calibration() for each judge model.

    mad: mean absolute deviation from gold scores (0-10 scale).
         PRD-002 SC-3 threshold: MAD ≤ 1.5.
    rank_correlation: Spearman rank correlation between judge score order and
                      gold order (perfect agreement = 1.0, no agreement = 0.0,
                      systematic reversal = -1.0). Computed via numpy ranking.
    samples_evaluated: number of calibration samples this judge scored.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    judge_id: str
    mad: float = Field(ge=0.0)
    rank_correlation: float = Field(ge=-1.0, le=1.0)
    samples_evaluated: int = Field(ge=0)


# ---------------------------------------------------------------------------
# CalibrationResult -- full calibration run outcome for one task (Slice D)
# ---------------------------------------------------------------------------


class CalibrationResult(BaseModel):
    """Outcome of running all judges over a task's calibration sample set.

    Produced by JudgePanel.run_calibration(task_id).

    task_id: eval task identifier (e.g. "be_01_jwt_auth").
    judge_calibrations: per-judge MAD + rank_correlation keyed by judge_id.
    passed: True iff all judges have MAD ≤ mad_threshold (PRD-002 SC-3).
    gold_scores: gold score per quality level from calibration.yaml.
    calibration_hash: SHA-256 of (gold_scores YAML content + all sample file
                      contents sorted by path) — stable across reruns of the
                      same content; changes when samples or gold scores change.
                      Stored in the run manifest for drift detection (RFC-002 R4).
    mad_threshold: the MAD threshold used when computing passed (default 1.5
                   per PRD-002 SC-3; taken from calibration.yaml if present).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    judge_calibrations: dict[str, JudgeCalibration]
    passed: bool
    gold_scores: dict[str, float]
    calibration_hash: str
    mad_threshold: float = Field(default=1.5, ge=0.0)


# ---------------------------------------------------------------------------
# ProbeResult -- identification probe result (RFC-002 Slice D, PRD-002 SC-4)
# ---------------------------------------------------------------------------


class ProbeResult(BaseModel):
    """Outcome of the model-identification probe for one task.

    Produced by JudgePanel.run_identification_probe(task_id).

    PRD-002 SC-4: identification accuracy ≤ 30% across all judges.
    The probe presents each judge with an anonymised sample output and asks
    it to guess which model family produced it (one-word forced choice from
    a fixed list of 5 families). Accuracy at chance = 1/5 = 20%.

    task_id: eval task identifier.
    judges_used: list of judge model IDs that participated.
    n_samples: total number of (judge x sample) pairs scored.
    per_judge_accuracy: accuracy per judge model (correct guesses / total samples).
    overall_accuracy: accuracy across all judge-sample pairs.
    passed: True iff overall_accuracy ≤ 0.30 (PRD-002 SC-4).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    judges_used: list[str]
    n_samples: int = Field(ge=0)
    per_judge_accuracy: dict[str, float]
    overall_accuracy: float = Field(ge=0.0, le=1.0)
    passed: bool
