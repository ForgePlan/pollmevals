"""Run deterministic automatic evaluators and compute the coding-task final_score.

Two responsibilities kept in one module (they share the same weight table):

1. ``run_auto_evaluators(submission_path, task_id)``
   Runs LintEvaluator + TypeSafetyEvaluator on a real filesystem path (the
   candidate's produced file tree). Returns a dict suitable for
   EvalRow.automatic_metrics.  Evaluators self-report skipped=True when their
   binary is absent — those components default to 0.0.

2. ``compute_final_score(eval_row)``
   Applies the frozen coding-task formula from docs/02-methodology/scoring.md:

     final_score = 0.40*correctness + 0.15*coverage + 0.10*complexity
                 + 0.10*lint       + 0.10*type_safety
                 + 0.15*pattern_match

   Reads ``automatic_metrics`` for the deterministic components; reads
   ``judge_aggregate.median_per_criterion["pattern_match"]`` for the judge term
   (already normalised to 0-10 by JudgePanel.aggregate).

   Returns ``None`` when neither automatic_metrics nor a judge aggregate is
   present (raw-llm evals without a judge panel — no score possible yet).
   Returns a partial score when some components are present and others are not
   (skipped evaluators contribute 0.0 to their weight slot — the formula is
   still computed, just with those slots zeroed out).

   The result is in [0.0, 10.0].

Usage:
  # In stack_scoring.exec_result_to_eval_result (after writing submission to disk)
  automatic_metrics = await run_auto_evaluators(str(submission_path), task_id)
  # In grid_runner._invoke_judge_panel (after JudgePanel.aggregate)
  final_row = compute_final_score(eval_row_with_judge_and_auto_metrics)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.contracts.eval_row import EvalRow
from src.evaluators.lint_evaluator import LintEvaluator
from src.evaluators.type_safety_evaluator import TypeSafetyEvaluator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Coding-task weight table (frozen — docs/02-methodology/scoring.md v0.1.0)
# ---------------------------------------------------------------------------

_CODING_WEIGHTS: dict[str, float] = {
    "correctness": 0.40,
    "coverage": 0.15,
    "complexity": 0.10,
    "lint": 0.10,
    "type_safety": 0.10,
    "pattern_match": 0.15,
}

# Evaluators that run on the host (static analysis, no sandbox).
_LINT_EVALUATOR = LintEvaluator()
_TYPE_SAFETY_EVALUATOR = TypeSafetyEvaluator()


# ---------------------------------------------------------------------------
# 1. run_auto_evaluators
# ---------------------------------------------------------------------------


async def run_auto_evaluators(submission_path: str, task_id: str) -> dict[str, Any]:
    """Run lint + type_safety on *submission_path* and return automatic_metrics dict.

    Both evaluators self-report skipped=True when their binary is absent or
    inapplicable — those slots carry score=0.0, which is the correct
    contribution to the final_score formula (no score invented, no bias).

    The dict shape matches EvalRow.automatic_metrics expectations:
      {
        "lint": 0.8,             # 0.0..1.0  (0-1 range, not 0-10)
        "lint_skipped": false,
        "lint_skip_reason": null,
        "type_safety": 0.7,
        "type_safety_skipped": false,
        "type_safety_skip_reason": null,
      }

    Args:
        submission_path: Absolute path to the candidate's file tree or a single
            source file.  For CLI stacks this is the snapshot dir written by
            stack_scoring.extract_submission.  For raw-llm (text blob) callers
            should pass the path to the raw_output file; evaluators will try
            the file-extension detection and skip gracefully if no TS/Py found.
        task_id: e.g. "be_01_jwt_auth".  Drives language detection fallback.

    Returns:
        dict suitable for EvalRow.automatic_metrics.  Never raises.
    """
    lint_res, ts_res = await asyncio.gather(
        _LINT_EVALUATOR.evaluate(submission_path, task_id),
        _TYPE_SAFETY_EVALUATOR.evaluate(submission_path, task_id),
    )

    if lint_res.skipped:
        logger.debug(
            "LintEvaluator skipped for task=%s path=%s reason=%s",
            task_id,
            submission_path,
            lint_res.skip_reason,
        )
    if ts_res.skipped:
        logger.debug(
            "TypeSafetyEvaluator skipped for task=%s path=%s reason=%s",
            task_id,
            submission_path,
            ts_res.skip_reason,
        )

    return {
        "lint": lint_res.score,
        "lint_skipped": lint_res.skipped,
        "lint_skip_reason": lint_res.skip_reason,
        "type_safety": ts_res.score,
        "type_safety_skipped": ts_res.skipped,
        "type_safety_skip_reason": ts_res.skip_reason,
    }


# ---------------------------------------------------------------------------
# 2. compute_final_score
# ---------------------------------------------------------------------------


def compute_final_score(row: EvalRow) -> float | None:
    """Apply the frozen coding-task weighted formula and return final_score.

    Formula (docs/02-methodology/scoring.md):
      final_score_01 =
        0.40 * correctness + 0.15 * coverage + 0.10 * complexity
        + 0.10 * lint       + 0.10 * type_safety
        + 0.15 * pattern_match

      final_score_10 = final_score_01 * 10

    Component sources:
      - correctness, coverage, complexity, lint, type_safety:
        ``row.automatic_metrics`` (values in 0-1 range).
      - pattern_match:
        ``row.judge_aggregate.median_per_criterion["pattern_match"]``
        (value in 0-10 range; divided by 10 to normalise).

    Missing components default to 0.0 (contributes 0 * weight to the total).
    Returns None only when BOTH automatic_metrics and judge_aggregate are
    absent, meaning there is genuinely nothing to score yet.

    Args:
        row: An EvalRow with status=SCORED and any combination of
             automatic_metrics / judge_aggregate already set.

    Returns:
        float in [0.0, 10.0], or None when no scoring material exists at all.
    """
    metrics = row.automatic_metrics
    agg = row.judge_aggregate

    has_metrics = bool(metrics)
    has_judge = agg is not None and bool(agg.median_per_criterion)

    if not has_metrics and not has_judge:
        return None

    def _get(key: str) -> float:
        """Fetch a 0-1 value from automatic_metrics; default 0.0 if absent."""
        v = metrics.get(key, 0.0)
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    def _judge_crit(key: str) -> float:
        """Fetch a 0-10 judge criterion, normalise to 0-1; default 0.0."""
        if agg is None or agg.median_per_criterion is None:
            return 0.0
        v = agg.median_per_criterion.get(key, 0.0)
        try:
            return float(v) / 10.0
        except (TypeError, ValueError):
            return 0.0

    score_01 = (
        _CODING_WEIGHTS["correctness"] * _get("correctness")
        + _CODING_WEIGHTS["coverage"] * _get("coverage")
        + _CODING_WEIGHTS["complexity"] * _get("complexity")
        + _CODING_WEIGHTS["lint"] * _get("lint")
        + _CODING_WEIGHTS["type_safety"] * _get("type_safety")
        + _CODING_WEIGHTS["pattern_match"] * _judge_crit("pattern_match")
    )

    return round(max(0.0, min(10.0, score_01 * 10.0)), 4)
