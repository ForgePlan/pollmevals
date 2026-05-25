"""Tests for Phase 2D Slice 2 -- TypeSafetyEvaluator (tsc wrapper).

Mirrors test_evaluators.py patterns: asyncio.create_subprocess_exec is mocked
via AsyncMock so tests do not require a real tsc on PATH.

Coverage:
  TestTypeSafetyProtocol     -- runtime_checkable satisfaction
  TestTypeSafetySkip         -- no TS files, no tsc binary, defensive skip paths
  TestTypeSafetyScoring      -- 0 / 3 / 12+ errors -> 1.0 / 0.7 / 0.0
  TestTypeSafetyInvocation   -- project mode vs file mode argument list
  TestTypeSafetySubprocessError -- crashed subprocess returns skipped
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.evaluators import Evaluator, TypeSafetyEvaluator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(stdout: str, stderr: str = "", returncode: int = 0) -> AsyncMock:
    """Build an AsyncMock that mimics asyncio.subprocess.Process."""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    return proc


def _write_ts_file(tmp: Path, name: str = "app.ts", body: str = "const x: number = 1;\n") -> Path:
    f = tmp / name
    f.write_text(body)
    return f


# ---------------------------------------------------------------------------
# Protocol satisfaction
# ---------------------------------------------------------------------------


class TestTypeSafetyProtocol:
    def test_typesafety_satisfies_evaluator_protocol(self) -> None:
        assert isinstance(TypeSafetyEvaluator(), Evaluator)

    def test_name_is_type_safety(self) -> None:
        assert TypeSafetyEvaluator().name == "type_safety"


# ---------------------------------------------------------------------------
# Skip paths
# ---------------------------------------------------------------------------


class TestTypeSafetySkip:
    @pytest.mark.asyncio
    async def test_skip_no_ts_files_and_non_ts_task(self, tmp_path: Path) -> None:
        """Empty dir + doc_ task -> skipped (no TS source, non-TS task)."""
        result = await TypeSafetyEvaluator().evaluate(str(tmp_path), "doc_01_cli_readme")
        assert result.skipped is True
        assert "No .ts/.tsx files" in (result.skip_reason or "")
        assert result.score == 0.0
        assert result.findings_count == 0

    @pytest.mark.asyncio
    async def test_skip_when_tsc_not_on_path(self, tmp_path: Path) -> None:
        """ts file present but tsc missing -> skipped with install hint."""
        _write_ts_file(tmp_path)
        with patch(
            "src.evaluators.type_safety_evaluator.shutil.which",
            return_value=None,
        ):
            result = await TypeSafetyEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is True
        assert "tsc not on PATH" in (result.skip_reason or "")
        assert result.library_version == "tsc (not found)"

    @pytest.mark.asyncio
    async def test_ts_task_prefix_with_no_files_falls_through_to_defensive_skip(
        self, tmp_path: Path
    ) -> None:
        """fe_ task but no .ts/.tsx files -> tsc present but defensive skip."""
        with (
            patch(
                "src.evaluators.type_safety_evaluator.shutil.which",
                return_value="/usr/bin/tsc",
            ),
            patch(
                "src.evaluators.type_safety_evaluator._get_tsc_version",
                return_value="Version 5.9.2",
            ),
        ):
            result = await TypeSafetyEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is True
        assert "no .ts/.tsx files" in (result.skip_reason or "").lower()


# ---------------------------------------------------------------------------
# Scoring formula
# ---------------------------------------------------------------------------


class TestTypeSafetyScoring:
    @pytest.mark.asyncio
    async def test_zero_errors_score_1_0(self, tmp_path: Path) -> None:
        _write_ts_file(tmp_path)
        with (
            patch(
                "src.evaluators.type_safety_evaluator.shutil.which",
                return_value="/usr/bin/tsc",
            ),
            patch(
                "src.evaluators.type_safety_evaluator._get_tsc_version",
                return_value="Version 5.9.2",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc("", returncode=0),
            ),
        ):
            result = await TypeSafetyEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is False
        assert result.findings_count == 0
        assert result.score == pytest.approx(1.0)
        assert result.library_version == "Version 5.9.2"

    @pytest.mark.asyncio
    async def test_three_errors_score_0_7(self, tmp_path: Path) -> None:
        _write_ts_file(tmp_path)
        stdout = (
            "src/app.ts(5,9): error TS2304: Cannot find name 'foo'.\n"
            "src/app.ts(7,11): error TS2322: Type 'string' is not assignable to type 'number'.\n"
            "src/util.ts(2,3): error TS7006: Parameter 'x' implicitly has an 'any' type.\n"
        )
        with (
            patch(
                "src.evaluators.type_safety_evaluator.shutil.which",
                return_value="/usr/bin/tsc",
            ),
            patch(
                "src.evaluators.type_safety_evaluator._get_tsc_version",
                return_value="Version 5.9.2",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc(stdout, returncode=1),
            ),
        ):
            result = await TypeSafetyEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.findings_count == 3
        assert result.score == pytest.approx(0.7)

    @pytest.mark.asyncio
    async def test_ten_plus_errors_score_0(self, tmp_path: Path) -> None:
        _write_ts_file(tmp_path)
        stdout = "\n".join(
            f"src/file{i}.ts(1,1): error TS2304: Cannot find name 'x'." for i in range(12)
        )
        with (
            patch(
                "src.evaluators.type_safety_evaluator.shutil.which",
                return_value="/usr/bin/tsc",
            ),
            patch(
                "src.evaluators.type_safety_evaluator._get_tsc_version",
                return_value="Version 5.9.2",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc(stdout, returncode=1),
            ),
        ):
            result = await TypeSafetyEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.findings_count == 12
        assert result.score == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_errors_in_stderr_also_counted(self, tmp_path: Path) -> None:
        """tsc sometimes writes diagnostics to stderr; both streams must count."""
        _write_ts_file(tmp_path)
        with (
            patch(
                "src.evaluators.type_safety_evaluator.shutil.which",
                return_value="/usr/bin/tsc",
            ),
            patch(
                "src.evaluators.type_safety_evaluator._get_tsc_version",
                return_value="Version 5.9.2",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc(
                    "src/a.ts(1,1): error TS2304: Cannot find name 'x'.\n",
                    stderr="error TS5055: Cannot write file.\n",
                    returncode=1,
                ),
            ),
        ):
            result = await TypeSafetyEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.findings_count == 2


# ---------------------------------------------------------------------------
# Invocation mode (project vs file)
# ---------------------------------------------------------------------------


class TestTypeSafetyInvocation:
    @pytest.mark.asyncio
    async def test_project_mode_when_tsconfig_present(self, tmp_path: Path) -> None:
        """tsconfig.json present -> uses `tsc -p <dir> --noEmit --pretty false`."""
        _write_ts_file(tmp_path)
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {"strict": true}}')

        called_args: list[str] = []

        async def capture(*args: str, **_kwargs: object) -> MagicMock:
            called_args.extend(args)
            proc = _make_proc("", returncode=0)
            return proc

        with (
            patch(
                "src.evaluators.type_safety_evaluator.shutil.which",
                return_value="/usr/bin/tsc",
            ),
            patch(
                "src.evaluators.type_safety_evaluator._get_tsc_version",
                return_value="Version 5.9.2",
            ),
            patch("asyncio.create_subprocess_exec", side_effect=capture),
        ):
            await TypeSafetyEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")

        assert called_args[0] == "tsc"
        assert "-p" in called_args
        assert str(tmp_path) in called_args
        assert "--noEmit" in called_args
        assert "--pretty" in called_args
        # Project mode does NOT pass individual files
        assert not any(a.endswith(".ts") for a in called_args)

    @pytest.mark.asyncio
    async def test_file_mode_when_no_tsconfig(self, tmp_path: Path) -> None:
        """no tsconfig.json -> uses file mode with --strict + explicit files."""
        f = _write_ts_file(tmp_path)

        called_args: list[str] = []

        async def capture(*args: str, **_kwargs: object) -> MagicMock:
            called_args.extend(args)
            proc = _make_proc("", returncode=0)
            return proc

        with (
            patch(
                "src.evaluators.type_safety_evaluator.shutil.which",
                return_value="/usr/bin/tsc",
            ),
            patch(
                "src.evaluators.type_safety_evaluator._get_tsc_version",
                return_value="Version 5.9.2",
            ),
            patch("asyncio.create_subprocess_exec", side_effect=capture),
        ):
            await TypeSafetyEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")

        assert called_args[0] == "tsc"
        assert "--strict" in called_args
        assert "--noEmit" in called_args
        assert str(f) in called_args
        # File mode does NOT use -p
        assert "-p" not in called_args


# ---------------------------------------------------------------------------
# Subprocess error path
# ---------------------------------------------------------------------------


class TestTypeSafetySubprocessError:
    @pytest.mark.asyncio
    async def test_subprocess_exception_returns_skipped(self, tmp_path: Path) -> None:
        _write_ts_file(tmp_path)
        with (
            patch(
                "src.evaluators.type_safety_evaluator.shutil.which",
                return_value="/usr/bin/tsc",
            ),
            patch(
                "src.evaluators.type_safety_evaluator._get_tsc_version",
                return_value="Version 5.9.2",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=OSError("disk full"),
            ),
        ):
            result = await TypeSafetyEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")
        assert result.skipped is True
        assert "subprocess error" in (result.skip_reason or "").lower()
        assert "disk full" in (result.skip_reason or "")
