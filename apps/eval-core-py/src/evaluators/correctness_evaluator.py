"""CorrectnessEvaluator -- runs vitest inside the Docker sandbox.

Phase 2D Slice 2 part 2 (dynamic evaluator, per NOTE-007).

Library-first (CLAUDE.md, 2026-05-25):
  vitest: Context7 /vitest-dev/vitest + web research confirmed:
    - `vitest run --reporter=json` -- one-shot test run (no watch).
      Emits a Jest-compatible JSON document with fields:
        numTotalTests, numPassedTests, numFailedTests, numPendingTests, success.
    - `--coverage` (with @vitest/coverage-v8) embeds `coverageMap` in the
      same JSON document since vitest 3.x. ONE invocation -- both metrics.
      (CoverageEvaluator reads the same artifact this evaluator produces.)
    - Exit code: 0 = all tests passed; 1 = test failures; >1 = vitest error.

  Pinned versions inside the sandbox image (infra/docker/eval-ts/package.json):
    typescript 5.9.3, vitest 3.2.4, @vitest/coverage-v8 3.2.4.

Sandbox invocation: SandboxRun applies the frozen v0.1.0 policy (network=none,
read-only, tmpfs, mem/cpu/pids limits, cap_drop ALL, hard timeout). The
candidate's raw_output is mounted read-only at /workspace.

Score formula (scoring.md correctness criterion):
  pass_rate = numPassedTests / numTotalTests (1.0 if 0 tests collected)
  score     = pass_rate
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

from .protocol import EvaluatorResult
from .sandbox import SandboxConfig, SandboxResult, SandboxRun

logger = logging.getLogger(__name__)

# Tasks that have an executable JS/TS test surface (frontend, full-stack).
# Defensive: doc/be can also be TS but typically don't ship tests in candidate output.
_TS_RUNNABLE_PREFIXES: frozenset[str] = frozenset({"fe_", "ts_", "fs_"})

_SANDBOX_IMAGE_DEFAULT = "pollmevals-eval-ts:0.1.0"
_VITEST_REPORT_FILENAME = "vitest-report.json"
_DEFAULT_TIMEOUT_S = 90  # vitest install-skipped run -- 90s ample for smoke tasks


def _is_runnable_task(task_id: str) -> bool:
    return any(task_id.startswith(p) for p in _TS_RUNNABLE_PREFIXES)


def _parse_vitest_json(stdout: str) -> dict[str, Any] | None:
    """Extract the vitest JSON document from stdout.

    vitest with `--reporter=json` writes the JSON document to stdout when
    no `outputFile` is configured. We accept either a clean stdout (JSON only)
    or a mixed log + JSON tail by finding the last balanced top-level object.
    Returns None when no JSON document can be located.
    """
    text = stdout.strip()
    if not text:
        return None

    # Fast path: stdout IS the JSON document.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Slow path: find the last `{...}` that parses cleanly.
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


class CorrectnessEvaluator:
    """Run vitest inside the sandbox; report pass-rate as the correctness score.

    name = "correctness"

    Dynamic evaluator -- requires Docker. Skip semantics:
      - task_id prefix is not a runnable TS task (be_/doc_/...).
      - raw_output dir is empty / does not exist.
      - Docker daemon unreachable (ImportError or DockerException from SDK).
      - Sandbox image absent on host (image="..." not pulled and network=none
        forbids pull -- the image MUST be pre-built).

    Score formula: pass_rate = passed / total (1.0 if 0 collected tests).
    """

    name: str = "correctness"

    def __init__(
        self,
        *,
        sandbox_image: str = _SANDBOX_IMAGE_DEFAULT,
        timeout_s: int = _DEFAULT_TIMEOUT_S,
        sandbox_run: SandboxRun | None = None,
    ) -> None:
        self._image = sandbox_image
        self._timeout_s = timeout_s
        # Allow injection for testability (FakeSandboxRun in unit tests).
        self._sandbox = sandbox_run or SandboxRun()

    async def evaluate(self, raw_output_path: str, task_id: str) -> EvaluatorResult:
        """Run vitest on the candidate output; report pass-rate. Never raises."""
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
            # `npx vitest run` ensures one-shot mode (no watch). --reporter=json
            # emits the report on stdout; we let vitest auto-discover tests
            # under /workspace.
            command=["cd /workspace && npx --no vitest run --reporter=json"],
            mount_dir=path,
            workdir="/workspace",
            timeout_s=self._timeout_s,
        )

        try:
            sandbox_result = await self._sandbox.run(config)
        except ImportError as exc:
            return self._skip("docker (not installed)", str(exc))
        except Exception as exc:
            logger.warning("CorrectnessEvaluator sandbox error: %s", exc)
            return self._skip(
                "sandbox-error",
                f"Docker sandbox invocation failed: {type(exc).__name__}: {exc}",
            )

        return self._score(sandbox_result)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _score(self, sandbox_result: SandboxResult) -> EvaluatorResult:
        """Translate a SandboxResult into the EvaluatorResult score."""
        if sandbox_result.timed_out:
            return self._skip(
                f"vitest@{self._image}",
                f"sandbox timed out after {self._timeout_s}s",
            )

        # vitest exit codes: 0 = pass, 1 = test failures (still produces JSON),
        # other = vitest internal error (no JSON guaranteed).
        report = _parse_vitest_json(sandbox_result.stdout)

        if report is None:
            # No JSON -- container errored out. Capture stderr for diagnostics.
            return self._skip(
                f"vitest@{self._image}",
                f"no JSON report on stdout (exit={sandbox_result.exit_code}); "
                f"stderr tail: {sandbox_result.stderr[-400:]!r}",
            )

        total = int(report.get("numTotalTests", 0))
        passed = int(report.get("numPassedTests", 0))
        failed = int(report.get("numFailedTests", 0))

        # no tests collected -- vacuously correct (pass_rate = 1.0)
        pass_rate = 1.0 if total == 0 else passed / total

        score = round(pass_rate, 6)
        raw_lines = [
            f"image={self._image} exit={sandbox_result.exit_code}",
            f"tests: total={total} passed={passed} failed={failed} pass_rate={pass_rate:.4f}",
            f"wall_ms={sandbox_result.wall_ms}",
        ]

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            raw_output="\n".join(raw_lines) + "\n\n" + sandbox_result.stdout,
            findings_count=failed,
            library_version=f"vitest@{self._image}",
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
