"""ComplexityEvaluator -- wraps lizard >=1.17,<2 for cyclomatic complexity.

Library-first (CLAUDE.md 2026-05-25):
  lizard: Context7 /terryyin/lizard confirmed:
    - CLI: `lizard --csv <path>` writes one row per function with columns:
        NLOC, CCN, token, PARAM, length, location, file, function, long_name, start, end
      The CCN column (index 1) is the cyclomatic complexity number.
    - Python API: `lizard.analyze_file(filename)` returns FileInformation with
      `.function_list` where each func has `.cyclomatic_complexity`.
    - Multi-language: Python, TypeScript, JavaScript, Go, Rust, Java, C, C++, and more.
    - Version pinned: lizard>=1.17,<2 in pyproject.toml (Library-first rule).

  Implementation uses the Python API (import lizard) rather than subprocess for
  reliability -- no PATH dependency, exact version pinned in deps.

Scoring formula (scoring.md complexity_score, criterion "CC <= 8"):
  max_cc = max cyclomatic complexity across all functions in the artifact
  score = 1.0                           if max_cc <= 8
        = max(0.0, 1.0 - (max_cc - 8) / 10)  if max_cc > 8
  CC = 18 -> score = 0.0;  CC = 8 -> score = 1.0;  CC = 13 -> score = 0.5
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

from .protocol import EvaluatorResult

logger = logging.getLogger(__name__)

# Threshold from scoring.md "CC <= 8" criterion.
_CC_THRESHOLD = 8
# Slope: 10 points above threshold drives score to 0.
_CC_SLOPE = 10.0

# ---------------------------------------------------------------------------
# Optional lizard import -- graceful degradation when not installed.
# lizard has no type stubs; suppress mypy import-untyped at module level only.
# ---------------------------------------------------------------------------


def _import_lizard() -> Any:
    """Return the lizard module or None if not installed.

    Deferred import so tests can monkeypatch _analyze_path without needing
    lizard installed.  The return type is Any to avoid mypy import-untyped
    errors cascading through the call sites.
    """
    try:
        import lizard  # type: ignore[import-untyped]

        return lizard
    except ImportError:
        return None


def _get_lizard_version() -> str:
    """Return 'lizard <version>' or 'lizard (not installed)' if absent."""
    lizard = _import_lizard()
    if lizard is None:
        return "lizard (not installed)"
    ver = getattr(lizard, "version", None) or getattr(lizard, "__version__", None)
    return f"lizard {ver}" if ver else "lizard (version unknown)"


def _analyze_path(path: pathlib.Path) -> list[Any]:
    """Walk *path* and return all FunctionInfo objects from lizard.

    Returns an empty list if lizard is not installed or path is empty.
    """
    lizard = _import_lizard()
    if lizard is None:
        return []

    functions: list[Any] = []
    targets: list[pathlib.Path] = []

    if path.is_file():
        targets = [path]
    elif path.is_dir():
        targets = [f for f in path.rglob("*") if f.is_file()]
    # If path does not exist, targets stays empty.

    for file_path in targets:
        try:
            file_info = lizard.analyze_file(str(file_path))
            functions.extend(file_info.function_list)
        except Exception as exc:
            logger.debug("lizard failed on %s: %s", file_path, exc)

    return functions


class ComplexityEvaluator:
    """Automatic cyclomatic complexity evaluator using lizard.

    name = "complexity"

    Requires lizard>=1.17,<2 in pyproject.toml (already pinned).
    Uses the Python API rather than subprocess to avoid PATH dependency.

    Score formula (scoring.md "CC <= 8"):
      max_cc = max cyclomatic complexity across all functions
      score  = 1.0 if max_cc <= 8 else max(0.0, 1.0 - (max_cc - 8) / 10)
    """

    name: str = "complexity"

    async def evaluate(self, raw_output_path: str, task_id: str) -> EvaluatorResult:
        """Analyse cyclomatic complexity of all source files in *raw_output_path*.

        Never raises.  Returns skipped=True if lizard is not importable.
        """
        lib_version = _get_lizard_version()

        if "not installed" in lib_version:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output="",
                findings_count=0,
                library_version=lib_version,
                skipped=True,
                skip_reason=(
                    "lizard not installed; add `lizard>=1.17,<2` to pyproject.toml "
                    "dependencies and run `uv sync`."
                ),
            )

        path = pathlib.Path(raw_output_path)
        functions = _analyze_path(path)

        if not functions:
            # No analysable source files -- treat as perfectly simple (no complexity).
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                raw_output="No functions found.",
                findings_count=0,
                library_version=lib_version,
                skipped=False,
            )

        complexities = [int(getattr(f, "cyclomatic_complexity", 1)) for f in functions]
        max_cc = max(complexities)
        # findings_count = number of functions that exceed the threshold.
        findings_count = sum(1 for cc in complexities if cc > _CC_THRESHOLD)

        if max_cc <= _CC_THRESHOLD:
            score = 1.0
        else:
            score = max(0.0, 1.0 - (max_cc - _CC_THRESHOLD) / _CC_SLOPE)

        raw_lines = [
            f"functions_analysed={len(functions)}, "
            f"max_cc={max_cc}, "
            f"functions_over_threshold={findings_count}"
        ]
        # Include per-function detail for high-complexity findings (audit trail).
        for func in functions:
            cc_val = int(getattr(func, "cyclomatic_complexity", 1))
            if cc_val > _CC_THRESHOLD:
                name = getattr(func, "name", "?")
                loc = getattr(func, "location", "?")
                raw_lines.append(f"  {name}@{loc}: CCN={cc_val}")

        return EvaluatorResult(
            evaluator_name=self.name,
            score=round(score, 6),
            raw_output="\n".join(raw_lines),
            findings_count=findings_count,
            library_version=lib_version,
        )
