"""SecretScanEvaluator -- wraps the gitleaks binary for secret detection.

Library-first (CLAUDE.md 2026-05-25):
  gitleaks: Context7 /gitleaks/gitleaks confirmed:
    Current API (v8.x) uses subcommands -- NOT the deprecated `detect --no-git`.
    Correct invocation for scanning a directory without git history:
      gitleaks dir <path> --report-format json --report-path <report_file>
    Exit codes:
      0 = no findings (or --exit-code 0 override)
      1 = findings found (default exit code when leaks detected)
      126/127 = binary not found / not executable
    Report format: JSON array of finding objects with fields:
      {"RuleID": str, "Description": str, "Match": str, "File": str,
       "Line": int, "StartLine": int, "EndLine": int, ...}

  gitleaks is a system binary, NOT a Python package.
  Detection: shutil.which("gitleaks") -- skip gracefully if missing.
  Install: `brew install gitleaks` (macOS) or download from
    github.com/gitleaks/gitleaks/releases

  NOTE: All subprocess calls use argument-list form (no shell=True) to prevent
  shell injection.

Scoring formula (NOTE-004 Section 5, vulnerability_scan_score):
  Binary: any secret found = score 0.0; zero secrets = score 1.0
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import shutil
import tempfile
from typing import Any

from .protocol import EvaluatorResult

logger = logging.getLogger(__name__)

_GITLEAKS_INSTALL_HINT = (
    "gitleaks not installed; install via `brew install gitleaks` (macOS) or "
    "download from github.com/gitleaks/gitleaks/releases"
)


def _get_gitleaks_version() -> str:
    """Return 'gitleaks <version>' or 'gitleaks (not found)' if absent."""
    exe = shutil.which("gitleaks")
    if exe is None:
        return "gitleaks (not found)"
    try:
        import subprocess

        result = subprocess.run(
            ["gitleaks", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version_line = (result.stdout or result.stderr or "").strip()
        return f"gitleaks {version_line}" if version_line else "gitleaks (version unknown)"
    except Exception:
        return "gitleaks (version unknown)"


class SecretScanEvaluator:
    """Automatic secret-detection evaluator using gitleaks.

    name = "secret_scan"

    Score formula:
      0.0 if any secrets found (binary fail -- any secret = disqualifying)
      1.0 if no secrets found

    Requires gitleaks system binary.  Gracefully skips with skip_reason when
    gitleaks is not on PATH.
    """

    name: str = "secret_scan"

    async def evaluate(self, raw_output_path: str, task_id: str) -> EvaluatorResult:
        """Run `gitleaks dir <path>` and return EvaluatorResult.

        Never raises.  Returns skipped=True if gitleaks binary is absent.
        """
        if shutil.which("gitleaks") is None:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.0,
                raw_output="",
                findings_count=0,
                library_version="gitleaks (not found)",
                skipped=True,
                skip_reason=_GITLEAKS_INSTALL_HINT,
            )

        lib_version = _get_gitleaks_version()
        path = pathlib.Path(raw_output_path)

        if not path.exists():
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                raw_output=f"path does not exist: {raw_output_path!r}",
                findings_count=0,
                library_version=lib_version,
                skipped=False,
            )

        # Write report to a temp file so we can parse JSON without mixing with
        # gitleaks stderr/stdout chatter.
        with tempfile.NamedTemporaryFile(
            suffix=".json", prefix="gitleaks-report-", delete=False
        ) as tmp:
            report_path = pathlib.Path(tmp.name)

        try:
            proc = await asyncio.create_subprocess_exec(
                "gitleaks",
                "dir",
                str(path),
                "--report-format",
                "json",
                "--report-path",
                str(report_path),
                "--no-banner",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
        except Exception as exc:
            raw = f"gitleaks subprocess error: {exc}"
            logger.warning("SecretScanEvaluator.evaluate error: %s", exc)
            _cleanup(report_path)
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
        raw_output = (stdout + "\n" + stderr).strip()

        findings_count, report_text = _parse_gitleaks_report(report_path)
        _cleanup(report_path)

        if findings_count > 0:
            raw_output = report_text + "\n" + raw_output
            score = 0.0
        else:
            score = 1.0

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            raw_output=raw_output,
            findings_count=findings_count,
            library_version=lib_version,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_gitleaks_report(report_path: pathlib.Path) -> tuple[int, str]:
    """Parse gitleaks JSON report file and return (findings_count, summary_text).

    gitleaks writes a JSON array of finding objects:
      [{"RuleID": "...", "Description": "...", "Match": "...", "File": "...", ...}, ...]

    Returns (0, "") if file is absent, empty, or contains an empty array.
    """
    if not report_path.exists():
        return 0, ""
    try:
        text = report_path.read_text(encoding="utf-8")
    except OSError:
        return 0, ""

    text = text.strip()
    if not text:
        return 0, ""

    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError:
        logger.debug("gitleaks JSON parse failed; report=%r", text[:200])
        return 0, ""

    if not isinstance(data, list):
        return 0, ""

    findings_count = len(data)
    if findings_count == 0:
        return 0, ""

    # Build a concise summary for the raw_output audit trail.
    lines = [f"gitleaks found {findings_count} secret(s):"]
    for finding in data[:10]:  # cap at 10 to avoid huge raw_output
        if isinstance(finding, dict):
            rule = finding.get("RuleID", "?")
            desc = finding.get("Description", "")
            file_ = finding.get("File", "?")
            lines.append(f"  [{rule}] {desc} in {file_}")
    if findings_count > 10:
        lines.append(f"  ... and {findings_count - 10} more")

    return findings_count, "\n".join(lines)


def _cleanup(path: pathlib.Path) -> None:
    """Remove temp file silently."""
    import contextlib

    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)
