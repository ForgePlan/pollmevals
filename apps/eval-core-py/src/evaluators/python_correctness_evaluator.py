"""PythonCorrectnessEvaluator — runs a Python ``unittest`` suite in the sandbox.

Phase 5 (RFC-006 follow-up): makes the imported BigCodeBench packs (``bcb-*``)
runnable. Unlike the TS path (``CorrectnessEvaluator`` → vitest), BigCodeBench
tasks are single pure-Python modules graded by a ``unittest.TestCase`` suite.

Execution shape (per evals/task-packs/bcb-*/NOTE.md):
  - the candidate produces ``solution.py`` (the ``task_func`` implementation);
  - the pack's ``gold/test.py`` is the HIDDEN suite — it calls ``task_func(...)``
    as a BARE free name (no import, no ``__main__`` block);
  - so the evaluator wires the two into one namespace and runs the suite.

Because the sandbox mounts ``/workspace`` READ-ONLY (frozen policy), the
evaluator assembles a small dir on the host — ``solution.py`` (candidate) +
``test_run.py`` (``from solution import *`` + the gold suite) + ``_runner.py``
(emits a vitest-shaped JSON result on stdout) — and mounts THAT read-only.

Score formula (scoring.md correctness criterion, same as the TS path):
  pass_rate = numPassedTests / numTotalTests (1.0 if 0 tests collected)
  score     = pass_rate

NOTE (ADR-014): BigCodeBench is on the ADR-007 Tier-2 allowlist, but no
``bcb-*`` pack may enter a SCORED run until its G4 contamination report exists.
This evaluator only makes them executable; gating stays upstream.
"""

from __future__ import annotations

import json
import logging
import pathlib
import shutil
import tempfile
from typing import Any

from .protocol import EvaluatorResult
from .sandbox import SandboxConfig, SandboxResult, SandboxRun

logger = logging.getLogger(__name__)

# Task packs with an executable Python unittest surface (BigCodeBench imports).
_PY_RUNNABLE_PREFIXES: frozenset[str] = frozenset({"bcb-", "bcb_"})

_SANDBOX_IMAGE_DEFAULT = "pollmevals-eval-py:0.1.0"
_DEFAULT_TIMEOUT_S = 120  # pure-Python unittest; 120s ample (some seed RNG/mocks)

# Programmatic unittest runner — loads test_run, runs it, prints a vitest-shaped
# JSON document on stdout so the score path matches the TS evaluator exactly.
_RUNNER_PY = """\
import json, os, sys, unittest

sys.path.insert(0, "/workspace")
# Some BigCodeBench suites write fixture files (CSVs, images) relative to the
# CWD. /workspace is mounted read-only, so run from the writable tmpfs instead.
os.chdir("/tmp")
try:
    import test_run  # imports solution via `from solution import *`
except BaseException as exc:  # collection/import error → 0 passed, 1 failed
    print(json.dumps({"numTotalTests": 1, "numPassedTests": 0, "numFailedTests": 1,
                      "error": f"{type(exc).__name__}: {exc}"[:300]}))
    raise SystemExit(0)

suite = unittest.TestLoader().loadTestsFromModule(test_run)
res = unittest.TestResult()
suite.run(res)
total = res.testsRun
failed = len(res.failures) + len(res.errors)
print(json.dumps({
    "numTotalTests": total,
    "numPassedTests": total - failed,
    "numFailedTests": failed,
    "details": [str(e[1]).strip().splitlines()[-1][:160] for e in (res.failures + res.errors)][:3],
}))
"""


def _is_runnable_task(task_id: str) -> bool:
    return any(task_id.startswith(p) for p in _PY_RUNNABLE_PREFIXES)


def _parse_result_json(stdout: str) -> dict[str, Any] | None:
    """Extract the runner's JSON document from stdout (last balanced object)."""
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


def _read_candidate_solution(path: pathlib.Path) -> str | None:
    """The candidate's solution.py text, whether path is the file or its dir."""
    if path.is_file() and path.suffix == ".py":
        return path.read_text(encoding="utf-8")
    if path.is_dir():
        sol = path / "solution.py"
        if sol.exists():
            return sol.read_text(encoding="utf-8")
        pys = sorted(path.glob("*.py"))
        if pys:
            return pys[0].read_text(encoding="utf-8")
    return None


class PythonCorrectnessEvaluator:
    """Run a BigCodeBench ``unittest`` suite in the sandbox; report pass-rate.

    name = "correctness" — same key as the TS evaluator; only ONE correctness
    evaluator runs per task (selected by language), so the key does not clash.

    Dynamic evaluator — requires Docker + a pre-built ``pollmevals-eval-py``
    image carrying the task's third-party libs. Skip semantics mirror the TS
    evaluator: non-runnable prefix, missing candidate/gold, Docker unreachable,
    image absent. Never raises.
    """

    name: str = "correctness"

    def __init__(
        self,
        *,
        packs_root: pathlib.Path,
        sandbox_image: str = _SANDBOX_IMAGE_DEFAULT,
        timeout_s: int = _DEFAULT_TIMEOUT_S,
        sandbox_run: SandboxRun | None = None,
    ) -> None:
        self._packs_root = pathlib.Path(packs_root)
        self._image = sandbox_image
        self._timeout_s = timeout_s
        self._sandbox = sandbox_run or SandboxRun()

    async def evaluate(self, raw_output_path: str, task_id: str) -> EvaluatorResult:
        """Run the gold unittest suite against the candidate solution.py."""
        if not _is_runnable_task(task_id):
            return self._skip(
                "n/a",
                f"task_id {task_id!r} prefix not in Python-runnable set "
                f"{sorted(_PY_RUNNABLE_PREFIXES)}.",
            )

        solution = _read_candidate_solution(pathlib.Path(raw_output_path))
        if solution is None:
            return self._skip("n/a", f"no candidate solution.py under {raw_output_path!r}.")

        gold = self._packs_root / task_id / "gold"
        test_src = gold / "test.py"
        if not test_src.exists():
            return self._skip("n/a", f"gold test.py missing at {test_src}.")
        entry = self._entry_point(gold)

        workdir = pathlib.Path(tempfile.mkdtemp(prefix=f"pollmevals-bcb-{task_id}-"))
        try:
            self._assemble(workdir, solution, test_src.read_text(encoding="utf-8"), entry)
            config = SandboxConfig(
                image=self._image,
                command=["python", "/workspace/_runner.py"],
                mount_dir=workdir,
                workdir="/workspace",
                # /workspace is read-only → keep Python from trying to cache .pyc.
                environment={"PYTHONDONTWRITEBYTECODE": "1"},
                timeout_s=self._timeout_s,
            )
            try:
                sandbox_result = await self._sandbox.run(config)
            except ImportError as exc:
                return self._skip("docker (not installed)", str(exc))
            except Exception as exc:
                logger.warning("PythonCorrectnessEvaluator sandbox error: %s", exc)
                return self._skip(
                    "sandbox-error",
                    f"Docker sandbox invocation failed: {type(exc).__name__}: {exc}",
                )
            return self._score(sandbox_result)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _entry_point(self, gold: pathlib.Path) -> str:
        meta = gold / "meta.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                ep = data.get("entry_point")
                if isinstance(ep, str) and ep:
                    return ep
            except json.JSONDecodeError:
                pass
        return "task_func"  # BigCodeBench convention

    def _assemble(self, workdir: pathlib.Path, solution: str, test_src: str, entry: str) -> None:
        """Write solution.py + test_run.py (gold suite, namespace-wired) + runner."""
        (workdir / "solution.py").write_text(solution, encoding="utf-8")
        # `from solution import *` exposes the bare `task_func` the gold suite
        # calls; the explicit entry import is a belt-and-suspenders fallback.
        header = (
            "from solution import *  # noqa: F401,F403\n"
            f"from solution import {entry}  # noqa: F401\n\n"
        )
        (workdir / "test_run.py").write_text(header + test_src, encoding="utf-8")
        (workdir / "_runner.py").write_text(_RUNNER_PY, encoding="utf-8")

    def _score(self, sandbox_result: SandboxResult) -> EvaluatorResult:
        if sandbox_result.timed_out:
            return self._skip(
                f"unittest@{self._image}",
                f"sandbox timed out after {self._timeout_s}s",
            )
        report = _parse_result_json(sandbox_result.stdout)
        if report is None:
            return self._skip(
                f"unittest@{self._image}",
                f"no JSON result on stdout (exit={sandbox_result.exit_code}); "
                f"stderr tail: {sandbox_result.stderr[-400:]!r}",
            )

        total = int(report.get("numTotalTests", 0))
        passed = int(report.get("numPassedTests", 0))
        failed = int(report.get("numFailedTests", 0))
        pass_rate = 1.0 if total == 0 else passed / total

        raw_lines = [
            f"image={self._image} exit={sandbox_result.exit_code}",
            f"tests: total={total} passed={passed} failed={failed} pass_rate={pass_rate:.4f}",
            f"wall_ms={sandbox_result.wall_ms}",
        ]
        if report.get("details"):
            raw_lines.append("fail details: " + " | ".join(report["details"]))
        if report.get("error"):
            raw_lines.append("import error: " + str(report["error"]))

        return EvaluatorResult(
            evaluator_name=self.name,
            score=round(pass_rate, 6),
            raw_output="\n".join(raw_lines) + "\n\n" + sandbox_result.stdout,
            findings_count=failed,
            library_version=f"unittest@{self._image}",
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
