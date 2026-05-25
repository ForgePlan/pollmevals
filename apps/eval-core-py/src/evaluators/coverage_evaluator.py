"""CoverageEvaluator -- runs vitest --coverage inside the Docker sandbox.

Phase 2D Slice 2 part 2 (dynamic evaluator, per NOTE-007).

Design note: per Vitest 3.x (web research 2026-05-25), the JSON reporter
embeds `coverageMap` in the SAME document produced by --coverage. In
principle CorrectnessEvaluator could compute coverage too -- they share
the output. But they're split because:

  1. Each evaluator owns ONE score in scoring.md. Mixing would couple
     correctness and coverage scoring in one row -- harder to audit.
  2. Some tasks may run tests without instrumenting (correctness-only) or
     instrument without strict pass-rate gating (coverage-only).
  3. The split mirrors LintEvaluator vs ComplexityEvaluator: each evaluator
     is a thin wrapper around ONE measurable quantity.

The sandbox invocation runs `vitest run --coverage --reporter=json` -- both
metrics are gathered, but each evaluator extracts only its own slice.

Score formula (scoring.md coverage criterion):
  coverage_pct = (lines_covered / lines_total) when total > 0 else 1.0
  score        = coverage_pct  (already in [0, 1])
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

from .protocol import EvaluatorResult
from .sandbox import SandboxConfig, SandboxResult, SandboxRun

logger = logging.getLogger(__name__)

_TS_RUNNABLE_PREFIXES: frozenset[str] = frozenset({"fe_", "ts_", "fs_"})

_SANDBOX_IMAGE_DEFAULT = "pollmevals-eval-ts:0.1.0"
_DEFAULT_TIMEOUT_S = 120  # coverage instrumentation adds overhead vs plain run


def _is_runnable_task(task_id: str) -> bool:
    return any(task_id.startswith(p) for p in _TS_RUNNABLE_PREFIXES)


def _parse_vitest_json(stdout: str) -> dict[str, Any] | None:
    """Extract the vitest JSON document from stdout (mirrors CorrectnessEvaluator)."""
    text = stdout.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = text.rfind("{")
    while start != -1:
        try:
            parsed = json.loads(text[start:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        start = text.rfind("{", 0, start)
    return None


def _extract_coverage_pct(report: dict[str, Any]) -> tuple[int, int] | None:
    """Extract (lines_covered, lines_total) from the vitest JSON document.

    The shape of `coverageMap` is per-file:
      {"/abs/path/file.ts": {"path": "...", "lines": {"total": N, "covered": M}, ...}, ...}
    We sum lines.total and lines.covered across all files. When `coverageMap`
    is absent (coverage flag not passed) returns None.
    """
    coverage_map = report.get("coverageMap")
    if not isinstance(coverage_map, dict) or not coverage_map:
        return None

    total = 0
    covered = 0
    for file_data in coverage_map.values():
        if not isinstance(file_data, dict):
            continue
        lines = file_data.get("lines")
        if isinstance(lines, dict):
            total += int(lines.get("total", 0))
            covered += int(lines.get("covered", 0))
    return covered, total


class CoverageEvaluator:
    """Run vitest --coverage in the sandbox; report line coverage.

    name = "coverage"

    Dynamic evaluator -- same skip semantics as CorrectnessEvaluator.

    Score formula: covered / total (1.0 when total=0, i.e. no instrumentable lines).
    """

    name: str = "coverage"

    def __init__(
        self,
        *,
        sandbox_image: str = _SANDBOX_IMAGE_DEFAULT,
        timeout_s: int = _DEFAULT_TIMEOUT_S,
        sandbox_run: SandboxRun | None = None,
    ) -> None:
        self._image = sandbox_image
        self._timeout_s = timeout_s
        self._sandbox = sandbox_run or SandboxRun()

    async def evaluate(self, raw_output_path: str, task_id: str) -> EvaluatorResult:
        """Run vitest --coverage on the candidate output. Never raises."""
        path = pathlib.Path(raw_output_path)

        if not path.exists():
            return self._skip("n/a", f"raw_output_path {raw_output_path!r} does not exist.")
        if not _is_runnable_task(task_id):
            return self._skip(
                "n/a",
                f"task_id {task_id!r} prefix is not in TS-runnable set "
                f"{sorted(_TS_RUNNABLE_PREFIXES)}.",
            )

        config = SandboxConfig(
            image=self._image,
            command=["cd /workspace && npx --no vitest run --coverage --reporter=json"],
            mount_dir=path,
            workdir="/workspace",
            timeout_s=self._timeout_s,
        )

        try:
            sandbox_result = await self._sandbox.run(config)
        except ImportError as exc:
            return self._skip("docker (not installed)", str(exc))
        except Exception as exc:
            logger.warning("CoverageEvaluator sandbox error: %s", exc)
            return self._skip(
                "sandbox-error",
                f"Docker sandbox invocation failed: {type(exc).__name__}: {exc}",
            )

        return self._score(sandbox_result)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _score(self, sandbox_result: SandboxResult) -> EvaluatorResult:
        if sandbox_result.timed_out:
            return self._skip(
                f"vitest+v8@{self._image}",
                f"sandbox timed out after {self._timeout_s}s",
            )

        report = _parse_vitest_json(sandbox_result.stdout)
        if report is None:
            return self._skip(
                f"vitest+v8@{self._image}",
                f"no JSON report on stdout (exit={sandbox_result.exit_code}); "
                f"stderr tail: {sandbox_result.stderr[-400:]!r}",
            )

        coverage = _extract_coverage_pct(report)
        if coverage is None:
            return self._skip(
                f"vitest+v8@{self._image}",
                "coverageMap absent in vitest JSON (was --coverage propagated?).",
            )

        covered, total = coverage
        coverage_pct = 1.0 if total == 0 else covered / total
        score = round(coverage_pct, 6)
        # findings_count = uncovered lines (lower is better).
        findings_count = max(0, total - covered)

        raw_lines = [
            f"image={self._image} exit={sandbox_result.exit_code}",
            f"lines: total={total} covered={covered} coverage_pct={coverage_pct:.4f}",
            f"wall_ms={sandbox_result.wall_ms}",
        ]

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            raw_output="\n".join(raw_lines),
            findings_count=findings_count,
            library_version=f"vitest+v8@{self._image}",
        )

    def _skip(self, lib_version: str, reason: str) -> EvaluatorResult:
        return EvaluatorResult(
            evaluator_name=self.name,
            score=0.0,
            raw_output="",
            findings_count=0,
            library_version=lib_version,
            skipped=True,
            skip_reason=reason,
        )
