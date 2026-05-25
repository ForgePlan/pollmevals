"""Tests for CorrectnessEvaluator (vitest in sandbox).

Real Docker is NOT required: SandboxRun is replaced with a fake that
returns a SandboxResult with a programmed vitest JSON document on stdout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.evaluators import CorrectnessEvaluator, Evaluator
from src.evaluators.sandbox import SandboxConfig, SandboxResult


class _FakeSandbox:
    """Fake SandboxRun -- returns a programmed SandboxResult."""

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


def _make_vitest_report(
    *,
    total: int = 4,
    passed: int = 4,
    failed: int = 0,
) -> str:
    report: dict[str, Any] = {
        "numTotalTestSuites": 1,
        "numTotalTests": total,
        "numPassedTests": passed,
        "numFailedTests": failed,
        "numPendingTests": 0,
        "success": failed == 0,
        "testResults": [],
        "coverageMap": {},
    }
    return json.dumps(report)


class TestCorrectnessProtocol:
    def test_satisfies_evaluator_protocol(self) -> None:
        assert isinstance(CorrectnessEvaluator(sandbox_run=_FakeSandbox()), Evaluator)  # type: ignore[arg-type]

    def test_name(self) -> None:
        ev = CorrectnessEvaluator(sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        assert ev.name == "correctness"


class TestCorrectnessSkipPaths:
    @pytest.mark.asyncio
    async def test_skip_when_path_does_not_exist(self) -> None:
        ev = CorrectnessEvaluator(sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        result = await ev.evaluate("/nonexistent/path", "fe_01_multistep_form")
        assert result.skipped is True
        assert "does not exist" in (result.skip_reason or "")

    @pytest.mark.asyncio
    async def test_skip_when_task_prefix_not_runnable(self, tmp_path: Path) -> None:
        ev = CorrectnessEvaluator(sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        result = await ev.evaluate(str(tmp_path), "doc_01_cli_readme")
        assert result.skipped is True
        assert "TS-runnable" in (result.skip_reason or "")

    @pytest.mark.asyncio
    async def test_skip_when_docker_sdk_missing(self, tmp_path: Path) -> None:
        ev = CorrectnessEvaluator(
            sandbox_run=_FakeSandbox(raise_exc=ImportError("docker not installed"))  # type: ignore[arg-type]
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is True
        assert "docker" in (result.skip_reason or "").lower()

    @pytest.mark.asyncio
    async def test_skip_on_sandbox_timeout(self, tmp_path: Path) -> None:
        ev = CorrectnessEvaluator(sandbox_run=_FakeSandbox(timed_out=True))  # type: ignore[arg-type]
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is True
        assert "timed out" in (result.skip_reason or "")

    @pytest.mark.asyncio
    async def test_skip_on_unexpected_sandbox_exception(self, tmp_path: Path) -> None:
        ev = CorrectnessEvaluator(
            sandbox_run=_FakeSandbox(raise_exc=RuntimeError("daemon crashed"))  # type: ignore[arg-type]
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is True
        assert "RuntimeError" in (result.skip_reason or "")


class TestCorrectnessScoring:
    @pytest.mark.asyncio
    async def test_all_pass_score_1_0(self, tmp_path: Path) -> None:
        ev = CorrectnessEvaluator(
            sandbox_run=_FakeSandbox(stdout=_make_vitest_report(total=4, passed=4))  # type: ignore[arg-type]
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is False
        assert result.score == pytest.approx(1.0)
        assert result.findings_count == 0

    @pytest.mark.asyncio
    async def test_partial_pass_score_proportional(self, tmp_path: Path) -> None:
        ev = CorrectnessEvaluator(
            sandbox_run=_FakeSandbox(  # type: ignore[arg-type]
                stdout=_make_vitest_report(total=10, passed=7, failed=3),
                exit_code=1,  # vitest exits 1 on test failure (still valid JSON)
            )
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.score == pytest.approx(0.7)
        assert result.findings_count == 3

    @pytest.mark.asyncio
    async def test_zero_tests_collected_score_1_0(self, tmp_path: Path) -> None:
        """Empty suite -- vacuously correct."""
        ev = CorrectnessEvaluator(
            sandbox_run=_FakeSandbox(stdout=_make_vitest_report(total=0, passed=0))  # type: ignore[arg-type]
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.score == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_no_json_on_stdout_is_skip(self, tmp_path: Path) -> None:
        ev = CorrectnessEvaluator(
            sandbox_run=_FakeSandbox(  # type: ignore[arg-type]
                stdout="garbage non-json output", stderr="vitest crashed", exit_code=2
            )
        )
        result = await ev.evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is True
        assert "no JSON report" in (result.skip_reason or "")


class TestCorrectnessSandboxInvocation:
    @pytest.mark.asyncio
    async def test_uses_workspace_mount_and_command(self, tmp_path: Path) -> None:
        sandbox = _FakeSandbox(stdout=_make_vitest_report())
        ev = CorrectnessEvaluator(sandbox_run=sandbox)  # type: ignore[arg-type]
        await ev.evaluate(str(tmp_path), "fe_01_multistep_form")

        assert sandbox.last_config is not None
        assert sandbox.last_config.mount_dir == tmp_path
        assert sandbox.last_config.workdir == "/workspace"
        # Command should run vitest in non-watch mode with JSON reporter
        full_cmd = " ".join(sandbox.last_config.command)
        assert "vitest run" in full_cmd
        assert "--reporter=json" in full_cmd
