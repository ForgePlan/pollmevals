"""Automatic evaluators for the three smoke-run task packs.

Task packs: be_01_jwt_auth, fe_01_multistep_form, doc_01_cli_readme.

Phase 2D Slice 1 exports:
  EvaluatorResult     -- Pydantic result model
  Evaluator           -- Protocol (runtime_checkable)
  LintEvaluator       -- ruff (Py) / eslint (TS) wrapper
  ComplexityEvaluator -- lizard cyclomatic complexity wrapper
  SecretScanEvaluator -- gitleaks secret-detection wrapper

Phase 2D Slice 2 (per NOTE-007 static/dynamic boundary):
  TypeSafetyEvaluator   -- static, host-side: tsc --noEmit --strict
  CorrectnessEvaluator  -- dynamic, sandboxed: vitest run --reporter=json
  CoverageEvaluator     -- dynamic, sandboxed: vitest run --coverage --reporter=json
"""

from .complexity_evaluator import ComplexityEvaluator
from .correctness_evaluator import CorrectnessEvaluator
from .coverage_evaluator import CoverageEvaluator
from .lint_evaluator import LintEvaluator
from .protocol import Evaluator, EvaluatorResult
from .secret_scan_evaluator import SecretScanEvaluator
from .type_safety_evaluator import TypeSafetyEvaluator

__all__ = [
    "ComplexityEvaluator",
    "CorrectnessEvaluator",
    "CoverageEvaluator",
    "Evaluator",
    "EvaluatorResult",
    "LintEvaluator",
    "SecretScanEvaluator",
    "TypeSafetyEvaluator",
]
