"""Evaluator Protocol — testability seam for automatic code-quality metrics.

Mirrors the EvalCaller / FakeEvalCaller pattern from
src/orchestrator/eval_caller.py (Phase 2A).

Implementors (Phase 2D Slice 1):
  - LintEvaluator      -- wraps ruff (Py) / eslint (TS) via subprocess JSON output
  - ComplexityEvaluator -- wraps lizard >=1.17,<2 CSV output (multi-language)
  - SecretScanEvaluator -- wraps gitleaks `dir` subcommand JSON report

Context7 API source: /astral-sh/ruff, /terryyin/lizard, /gitleaks/gitleaks
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class EvaluatorResult(BaseModel):
    """Output of one Evaluator run on one EvalRow's raw_output artifact path.

    Fields:
        evaluator_name:  Canonical name key, e.g. "lint", "complexity", "secret_scan".
        score:           Normalised 0.0 (worst) - 1.0 (best). Formula is evaluator-specific.
        raw_output:      Full stdout/stderr / library output for traceability and audit.
        findings_count:  Number of issues (lint errors, complexity violations, secrets found).
        library_version: The exact library version string used, e.g. "ruff 0.5.0".
        skipped:         True when the evaluator is not applicable to this artifact.
        skip_reason:     Human-readable explanation when skipped=True (None otherwise).
    """

    evaluator_name: str
    score: float
    raw_output: str
    findings_count: int
    library_version: str
    skipped: bool = False
    skip_reason: str | None = None


# ---------------------------------------------------------------------------
# Protocol — the testability seam
# ---------------------------------------------------------------------------


@runtime_checkable
class Evaluator(Protocol):
    """Protocol for running one automatic code-quality check on a raw artifact.

    Implementors depend on external binaries (ruff, lizard, gitleaks) invoked
    via subprocess.  They must not raise on missing binaries — instead they
    must return EvaluatorResult(skipped=True, skip_reason=...) with a
    score=0.0 and findings_count=0.

    name:             Canonical key used in EvalRow.automatic_metrics dict.
    evaluate(path, task_id):
        path:     Absolute path to the directory or file containing the raw
                  model output to be evaluated.
        task_id:  Task identifier (e.g. "be_01_jwt_auth").  Used by language-
                  detection heuristics when file extensions are ambiguous.
        Returns:  EvaluatorResult — never raises.
    """

    name: str

    async def evaluate(self, raw_output_path: str, task_id: str) -> EvaluatorResult: ...
