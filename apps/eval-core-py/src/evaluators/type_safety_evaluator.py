"""TypeSafetyEvaluator -- wraps `tsc --noEmit --strict --pretty false`.

Phase 2D Slice 2 (first cut -- static analysis only). Per NOTE-007:
TypeScript's `tsc` performs type-checking without code execution, so this
evaluator runs **directly on the host**, NOT inside the Docker sandbox.
Dynamic Slice 2 evaluators (correctness, coverage via vitest) live in a
separate session because they execute candidate code.

Library-first (CLAUDE.md 2026-05-25):
  tsc: Context7 /microsoft/typescript confirmed:
    - Invocation:   `tsc --noEmit --strict --pretty false`
                    (`--pretty false` produces machine-readable diagnostics
                     without ANSI codes).
    - Exit code:    0 = no type errors; non-zero = errors found.
    - Output line:  `<file>(<line>,<col>): error TS<code>: <message>`
                    (or `error TS<code>: <message>` for non-file-scoped errors).
    - Project mode: `tsc -p <dir>` uses the tsconfig.json in that directory.
    - File mode:    `tsc <file.ts> ...` ignores tsconfig and applies CLI flags.

  Subprocess safety: all invocations use argument-list form (no shell=True)
  via `asyncio.create_subprocess_exec` / `subprocess.run` -- safe by
  construction (no shell injection surface).

Scoring formula (scoring.md type_safety_score, criterion "0 type errors"):
  score = 1.0 - min(1.0, findings_count / 10.0)
  10+ errors -> score = 0.0;  0 errors -> score = 1.0
"""

from __future__ import annotations

import asyncio
import logging
import pathlib
import re
import shutil
import subprocess

from .protocol import EvaluatorResult

logger = logging.getLogger(__name__)

# Task-id prefix -> indicates TS code is expected (mirrors lint_evaluator heuristic).
_TS_TASK_PREFIXES: frozenset[str] = frozenset({"fe_", "ts_", "fs_"})
# File extensions that indicate TypeScript source.
_TS_EXTENSIONS: frozenset[str] = frozenset({".ts", ".tsx", ".mts", ".cts"})

# Regex matching one tsc diagnostic line. Both file-scoped and global errors
# always contain `error TS<digits>:` somewhere on the line.
_TS_ERROR_RE = re.compile(r"error TS\d+:")

# Score formula constants.
_SCORE_SLOPE = 10.0


def _get_tsc_version() -> str:
    """Return 'tsc <version>' or 'tsc (not found)' if not on PATH."""
    exe = shutil.which("tsc")
    if exe is None:
        return "tsc (not found)"
    try:
        result = subprocess.run(
            ["tsc", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "tsc unknown"
    except Exception:
        return "tsc unknown"


def _find_ts_files(path: pathlib.Path) -> list[pathlib.Path]:
    """Return TS source files under *path*; empty list if path missing or no TS files."""
    if not path.exists():
        return []
    if path.is_file():
        return [path] if path.suffix.lower() in _TS_EXTENSIONS else []
    return sorted(f for f in path.rglob("*") if f.is_file() and f.suffix.lower() in _TS_EXTENSIONS)


def _is_ts_task(task_id: str) -> bool:
    """Return True when the task_id prefix indicates a TS-flavoured task."""
    return any(task_id.startswith(p) for p in _TS_TASK_PREFIXES)


class TypeSafetyEvaluator:
    """Automatic type-safety evaluator using `tsc --noEmit --strict --pretty false`.

    name = "type_safety"

    Static analysis only -- runs on the host, no sandbox required (per NOTE-007
    static/dynamic execution-boundary rule).

    Skip semantics (returns skipped=True with score=0.0):
      - tsc is not on PATH (Node.js / TypeScript not installed).
      - No .ts/.tsx files found under raw_output_path AND task_id prefix is
        not in the TS-task set.
      - tsc subprocess crashed before producing output.

    Score formula: 1.0 - min(1.0, findings_count / 10)
    """

    name: str = "type_safety"

    async def evaluate(self, raw_output_path: str, task_id: str) -> EvaluatorResult:
        """Type-check the artifact and return an EvaluatorResult. Never raises."""
        path = pathlib.Path(raw_output_path)

        ts_files = _find_ts_files(path)
        if not ts_files and not _is_ts_task(task_id):
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output="",
                findings_count=0,
                library_version="n/a",
                skipped=True,
                skip_reason=(
                    f"No .ts/.tsx files at {raw_output_path!r} and task_id "
                    f"{task_id!r} prefix is not TS-flavoured."
                ),
            )

        if shutil.which("tsc") is None:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output="",
                findings_count=0,
                library_version="tsc (not found)",
                skipped=True,
                skip_reason=(
                    "tsc not on PATH; install TypeScript globally "
                    "(`npm install -g typescript`) or via the workspace package.json."
                ),
            )

        return await self._run_tsc(path, ts_files)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _run_tsc(self, path: pathlib.Path, ts_files: list[pathlib.Path]) -> EvaluatorResult:
        """Run tsc in project mode (if tsconfig.json present) or file mode.

        Project mode honours the candidate's own tsconfig.json (libs, target,
        moduleResolution, etc.) which produces fewer false positives. File mode
        is the fallback when no tsconfig.json is present -- adds --strict to
        enforce a baseline.
        """
        lib_version = _get_tsc_version()
        has_project = path.is_dir() and (path / "tsconfig.json").exists()

        if has_project:
            args = ["tsc", "-p", str(path), "--noEmit", "--pretty", "false"]
        elif ts_files:
            args = [
                "tsc",
                "--noEmit",
                "--strict",
                "--pretty",
                "false",
                *(str(f) for f in ts_files),
            ]
        else:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output="",
                findings_count=0,
                library_version=lib_version,
                skipped=True,
                skip_reason=(
                    "Task prefix suggested TS but no .ts/.tsx files found; "
                    "tsc would have nothing to type-check."
                ),
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
        except Exception as exc:
            raw = f"tsc subprocess error: {exc}"
            logger.warning("TypeSafetyEvaluator subprocess error: %s", exc)
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output=raw,
                findings_count=0,
                library_version=lib_version,
                skipped=True,
                skip_reason=raw,
            )

        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")
        raw_output = stdout + ("\n" + stderr if stderr.strip() else "")

        findings_count = len(_TS_ERROR_RE.findall(raw_output))
        score = 1.0 - min(1.0, findings_count / _SCORE_SLOPE)

        return EvaluatorResult(
            evaluator_name=self.name,
            score=round(score, 6),
            raw_output=raw_output,
            findings_count=findings_count,
            library_version=lib_version,
        )
