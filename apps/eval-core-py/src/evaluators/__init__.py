"""Automatic evaluators for the three smoke-run task packs.

Task packs: be_01_jwt_auth, fe_01_multistep_form, doc_01_cli_readme.

Phase 2D Slice 1 exports:
  EvaluatorResult     -- Pydantic result model
  Evaluator           -- Protocol (runtime_checkable)
  LintEvaluator       -- ruff (Py) / eslint (TS) wrapper
  ComplexityEvaluator -- lizard cyclomatic complexity wrapper
  SecretScanEvaluator -- gitleaks secret-detection wrapper

Phase 2D Slice 2 (static-only first cut, per NOTE-007):
  TypeSafetyEvaluator -- tsc --noEmit --strict --pretty false wrapper
                         (correctness / coverage deferred to a dedicated
                          Docker-sandbox session)
"""

from .complexity_evaluator import ComplexityEvaluator
from .lint_evaluator import LintEvaluator
from .protocol import Evaluator, EvaluatorResult
from .secret_scan_evaluator import SecretScanEvaluator
from .type_safety_evaluator import TypeSafetyEvaluator

__all__ = [
    "ComplexityEvaluator",
    "Evaluator",
    "EvaluatorResult",
    "LintEvaluator",
    "SecretScanEvaluator",
    "TypeSafetyEvaluator",
]
