"""LintEvaluator -- wraps ruff (Python) and eslint (TypeScript/JavaScript).

Library-first (CLAUDE.md 2026-05-25):
  ruff:   Context7 /astral-sh/ruff confirmed `ruff check --output-format json`
          returns a JSON array of finding objects.  Each object has:
            {"code": str, "message": str, "filename": str, "location": {...}, ...}
          Exit code 0 = no findings; exit code 1 = findings found; exit code 2 = error.
          Invocation: ruff check --output-format json <path>

  eslint: Standard JSON output via `eslint --format=json <path>`.
          Returns an array of file result objects, each with a `messages` array.
          Exit code 0 = no findings; exit code 1 = findings found; exit code 2 = error.
          Invocation: eslint --format=json <path>

  NOTE: All subprocess calls use argument-list form (no shell=True) to prevent
  shell injection.  asyncio.create_subprocess_exec is the async equivalent of
  subprocess.run with a list -- safe by construction.

Scoring formula (scoring.md lint_score):
  score = 1.0 - min(1.0, findings_count / 10)
  10+ errors -> score = 0.0;  0 errors -> score = 1.0
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import shutil
import subprocess
from typing import Any

from .protocol import EvaluatorResult

logger = logging.getLogger(__name__)

# Task-id prefix -> canonical language (when file extension is absent/ambiguous).
# NOTE: "be_" is intentionally absent — the reference be_01_jwt_auth task is
# TypeScript (Express), and the file-extension scan already handles it correctly
# when real files are present.  Including a Python fallback here would cause
# LintEvaluator to invoke ruff on a TypeScript submission when the path is a
# text blob with no extension, silently producing 0 findings rather than calling
# eslint.  When the path is a directory with real .ts files the extension scan
# correctly returns "typescript" without consulting this map.
_TASK_LANG_MAP: dict[str, str] = {
    "fe_": "typescript",  # frontend tasks -- React / TS
    "ts_": "typescript",  # explicit TypeScript tasks
    "fs_": "typescript",  # fullstack tasks (TS frontend + TS backend)
    "doc_": "none",  # documentation tasks -- no linting applicable
}

# File extensions that indicate Python source.
_PY_EXTENSIONS = frozenset({".py", ".pyi"})
# File extensions that indicate TypeScript / JavaScript source.
_TS_EXTENSIONS = frozenset({".ts", ".js", ".tsx", ".jsx", ".mjs", ".cjs"})


def _detect_language(path: pathlib.Path, task_id: str) -> str:
    """Return "python", "typescript", or "none" based on files present in *path*.

    Falls back to task_id prefix heuristic when no source files are found.
    """
    if path.is_dir():
        extensions = {f.suffix.lower() for f in path.rglob("*") if f.is_file()}
    elif path.is_file():
        extensions = {path.suffix.lower()}
    else:
        extensions = set()

    if extensions & _PY_EXTENSIONS:
        return "python"
    if extensions & _TS_EXTENSIONS:
        return "typescript"

    # Fallback: task_id prefix heuristic.
    for prefix, lang in _TASK_LANG_MAP.items():
        if task_id.startswith(prefix):
            return lang

    return "none"


def _get_ruff_version() -> str:
    """Return 'ruff <version>' or 'ruff unknown' if not on PATH."""
    exe = shutil.which("ruff")
    if exe is None:
        return "ruff (not found)"
    try:
        result = subprocess.run(
            ["ruff", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "ruff unknown"
    except Exception:
        return "ruff unknown"


def _get_eslint_version() -> str:
    """Return 'eslint <version>' or 'eslint unknown' if not on PATH."""
    exe = shutil.which("eslint")
    if exe is None:
        return "eslint (not found)"
    try:
        result = subprocess.run(
            ["eslint", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "eslint unknown"
    except Exception:
        return "eslint unknown"


class LintEvaluator:
    """Automatic lint evaluator using ruff (Python) or eslint (TypeScript/JS).

    name = "lint"

    Score formula: 1.0 - min(1.0, findings_count / 10)
    """

    name: str = "lint"

    async def evaluate(self, raw_output_path: str, task_id: str) -> EvaluatorResult:
        """Run ruff or eslint on *raw_output_path* and return EvaluatorResult.

        Never raises.  Returns skipped=True when:
        - No Python or TypeScript/JS files are detected.
        - The required binary (ruff / eslint) is not on PATH.
        """
        path = pathlib.Path(raw_output_path)
        lang = _detect_language(path, task_id)

        if lang == "none":
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output="",
                findings_count=0,
                library_version="n/a",
                skipped=True,
                skip_reason=(
                    f"No Python or TypeScript/JS files found at {raw_output_path!r} "
                    f"and task_id={task_id!r} prefix maps to no lintable language."
                ),
            )

        if lang == "python":
            return await self._run_ruff(path)
        else:
            return await self._run_eslint(path)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _run_ruff(self, path: pathlib.Path) -> EvaluatorResult:
        """Run `ruff check --output-format json <path>` asynchronously."""
        if shutil.which("ruff") is None:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output="",
                findings_count=0,
                library_version="ruff (not found)",
                skipped=True,
                skip_reason=(
                    "ruff not installed; install via `pip install ruff` or `uv add ruff`."
                ),
            )

        lib_version = _get_ruff_version()
        try:
            proc = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                "--output-format",
                "json",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
        except Exception as exc:
            raw = f"ruff subprocess error: {exc}"
            logger.warning("LintEvaluator._run_ruff error: %s", exc)
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

        # Exit code 2 means ruff itself errored (bad config, bad path, etc.)
        if proc.returncode == 2:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output=raw_output,
                findings_count=0,
                library_version=lib_version,
                skipped=True,
                skip_reason=f"ruff exited with code 2 (internal error): {stderr.strip()}",
            )

        findings_count = _parse_ruff_json(stdout)
        score = 1.0 - min(1.0, findings_count / 10.0)
        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            raw_output=raw_output,
            findings_count=findings_count,
            library_version=lib_version,
        )

    async def _run_eslint(self, path: pathlib.Path) -> EvaluatorResult:
        """Run `eslint --format=json <path>` asynchronously."""
        if shutil.which("eslint") is None:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output="",
                findings_count=0,
                library_version="eslint (not found)",
                skipped=True,
                skip_reason=(
                    "eslint not installed; install via `npm install -g eslint` or "
                    "add to package.json devDependencies."
                ),
            )

        lib_version = _get_eslint_version()
        try:
            proc = await asyncio.create_subprocess_exec(
                "eslint",
                "--format=json",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
        except Exception as exc:
            raw = f"eslint subprocess error: {exc}"
            logger.warning("LintEvaluator._run_eslint error: %s", exc)
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

        findings_count = _parse_eslint_json(stdout)
        score = 1.0 - min(1.0, findings_count / 10.0)
        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            raw_output=raw_output,
            findings_count=findings_count,
            library_version=lib_version,
        )


# ---------------------------------------------------------------------------
# JSON parsers (extracted for testability)
# ---------------------------------------------------------------------------


def _parse_ruff_json(stdout: str) -> int:
    """Parse ruff --output-format json output and return findings count.

    ruff JSON output is a JSON array of finding objects:
      [{"code": "E501", "message": "Line too long", "filename": "...", ...}, ...]

    Returns 0 on any parse error.
    """
    stdout = stdout.strip()
    if not stdout:
        return 0
    try:
        data: Any = json.loads(stdout)
        if isinstance(data, list):
            return len(data)
        return 0
    except json.JSONDecodeError:
        logger.debug("ruff JSON parse failed; stdout=%r", stdout[:200])
        return 0


def _parse_eslint_json(stdout: str) -> int:
    """Parse eslint --format=json output and return total message count.

    eslint JSON output is an array of file-result objects:
      [{"filePath": "...", "messages": [...], ...}, ...]

    Returns total count of messages across all files.  Returns 0 on parse error.
    """
    stdout = stdout.strip()
    if not stdout:
        return 0
    try:
        data: Any = json.loads(stdout)
        if not isinstance(data, list):
            return 0
        return sum(
            len(file_result.get("messages", []))
            for file_result in data
            if isinstance(file_result, dict)
        )
    except json.JSONDecodeError:
        logger.debug("eslint JSON parse failed; stdout=%r", stdout[:200])
        return 0
