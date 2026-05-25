"""Tests for CoverageEvaluator (vitest --coverage in sandbox).

Same Fake-sandbox pattern as test_correctness_evaluator.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.evaluators import CoverageEvaluator, Evaluator
from src.evaluators.sandbox import SandboxConfig, SandboxResult


class _FakeSandbox:
    def __init__(
        self,
        *,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        timed_out: bool = False,
        raise_exc: Exception | None = None,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.timed_out = timed_out
        self._raise_exc = raise_exc
        self.last_config: SandboxConfig | None = None

    async def run(self, config: SandboxConfig) -> SandboxResult:
        self.last_config = config
        if self._raise_exc is not None:
            raise self._raise_exc
        return SandboxResult(
            exit_code=self.exit_code,
            stdout=self.stdout,
            stderr=self.stderr,
            timed_out=self.timed_out,
            wall_ms=42,
        )


def _make_vitest_report_with_coverage(
    *,
    files: dict[str, tuple[int, int]] | None = None,
    omit_coverage_map: bool = False,
) -> str:
    """Build a vitest JSON document with a coverageMap.

    files: { absolute_path: (lines_covered, lines_total) }
    """
    coverage_map: dict[str, Any] = {}
    if not omit_coverage_map:
        for path, (covered, total) in (files or {}).items():
            coverage_map[path] = {
                "path": path,
                "lines": {"total": total, "covered": covered, "skipped": 0},
            }
    report: dict[str, Any] = {
        "numTotalTests": 1,
        "numPassedTests": 1,
        "numFailedTests": 0,
        "success": True,
        "testResults": [],
        "coverageMap": coverage_map,
    }
    return json.dumps(report)


class TestCoverageProtocol:
    def test_satisfies_evaluator_protocol(self) -> None:
        assert isinstance(CoverageEvaluator(sandbox_run=_FakeSandbox()), Evaluator)  # type: ignore[arg-type]

    def test_name(self) -> None:
        ev = CoverageEvaluator(sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        assert ev.name == "coverage"


class TestCoverageSkipPaths:
    @pytest.mark.asyncio
    async def test_skip_when_path_missing(self) -> None:
        ev = CoverageEvaluator(sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        result = await ev.evaluate("/no/such/path", "fe_01_multistep_form")
        assert result.skipped is True

    @pytest.mark.asyncio
    async def test_skip_when_task_non_runnable(self, tmp_path: Path) -> None:
        ev = CoverageEvaluator(sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        result = await ev.evaluate(str(tmp_path), "doc_01_cli_readme")
        assert result.skipped is True

    @pytest.mark.asyncio
    async def test_skip_when_coverage_map_absent(self, tmp_path: Path) -> None:
        ev = CoverageEvaluator(
            sandbox_run=_FakeSandbox(  # type: ignore[arg-type]
                stdout=_make_vitest_report_with_coverage(omit_coverage_map=True)
            )
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is True
        assert "coverageMap absent" in (result.skip_reason or "")

    @pytest.mark.asyncio
    async def test_skip_on_timeout(self, tmp_path: Path) -> None:
        ev = CoverageEvaluator(sandbox_run=_FakeSandbox(timed_out=True))  # type: ignore[arg-type]
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is True


class TestCoverageScoring:
    @pytest.mark.asyncio
    async def test_full_coverage_score_1_0(self, tmp_path: Path) -> None:
        ev = CoverageEvaluator(
            sandbox_run=_FakeSandbox(  # type: ignore[arg-type]
                stdout=_make_vitest_report_with_coverage(
                    files={"/workspace/src/a.ts": (10, 10), "/workspace/src/b.ts": (5, 5)}
                )
            )
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.score == pytest.approx(1.0)
        assert result.findings_count == 0

    @pytest.mark.asyncio
    async def test_partial_coverage_score_proportional(self, tmp_path: Path) -> None:
        ev = CoverageEvaluator(
            sandbox_run=_FakeSandbox(  # type: ignore[arg-type]
                stdout=_make_vitest_report_with_coverage(
                    # 7 of 10 covered + 3 of 5 = 10 / 15 = 0.6667
                    files={"/workspace/src/a.ts": (7, 10), "/workspace/src/b.ts": (3, 5)}
                )
            )
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.score == pytest.approx(10 / 15, abs=1e-5)
        assert result.findings_count == 5  # uncovered lines

    @pytest.mark.asyncio
    async def test_zero_lines_total_score_1_0(self, tmp_path: Path) -> None:
        """No instrumentable lines -- vacuously full coverage."""
        ev = CoverageEvaluator(
            sandbox_run=_FakeSandbox(  # type: ignore[arg-type]
                stdout=_make_vitest_report_with_coverage(files={"/workspace/src/a.ts": (0, 0)})
            )
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.score == pytest.approx(1.0)


class TestCoverageInvocation:
    @pytest.mark.asyncio
    async def test_uses_coverage_flag(self, tmp_path: Path) -> None:
        sandbox = _FakeSandbox(
            stdout=_make_vitest_report_with_coverage(files={"/workspace/src/a.ts": (1, 1)})
        )
        ev = CoverageEvaluator(sandbox_run=sandbox)  # type: ignore[arg-type]
        await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert sandbox.last_config is not None
        full_cmd = " ".join(sandbox.last_config.command)
        assert "--coverage" in full_cmd
        assert "--reporter=json" in full_cmd
