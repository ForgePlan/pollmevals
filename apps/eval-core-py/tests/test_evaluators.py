"""Tests for Phase 2D Slice 1 -- Evaluator Protocol + 3 reference implementations.

Coverage:
  TestEvaluatorProtocol        -- runtime_checkable + EvaluatorResult model
  TestLintEvaluatorRuff        -- ruff path: mocked subprocess JSON, score calc
  TestLintEvaluatorEslint      -- eslint path: mocked subprocess JSON
  TestLintEvaluatorSkip        -- no-py/ts file -> skipped=True
  TestComplexityEvaluator      -- lizard Python API mocked, CC scoring
  TestSecretScanEvaluator      -- gitleaks mocked: found/not-found/not-installed
  TestEvaluatorParsers         -- _parse_ruff_json / _parse_eslint_json unit tests
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.evaluators import (
    ComplexityEvaluator,
    Evaluator,
    LintEvaluator,
    SecretScanEvaluator,
)
from src.evaluators.lint_evaluator import _parse_eslint_json, _parse_ruff_json
from src.evaluators.protocol import EvaluatorResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(stdout: str, stderr: str = "", returncode: int = 0) -> AsyncMock:
    """Build an AsyncMock that mimics asyncio.subprocess.Process."""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    return proc


# ---------------------------------------------------------------------------
# TestEvaluatorProtocol
# ---------------------------------------------------------------------------


class TestEvaluatorProtocol:
    """Verify that runtime_checkable + EvaluatorResult model work as expected."""

    def test_lint_evaluator_satisfies_protocol(self) -> None:
        assert isinstance(LintEvaluator(), Evaluator)

    def test_complexity_evaluator_satisfies_protocol(self) -> None:
        assert isinstance(ComplexityEvaluator(), Evaluator)

    def test_secret_scan_evaluator_satisfies_protocol(self) -> None:
        assert isinstance(SecretScanEvaluator(), Evaluator)

    def test_evaluator_result_model_validation(self) -> None:
        r = EvaluatorResult(
            evaluator_name="lint",
            score=0.8,
            raw_output="[]",
            findings_count=2,
            library_version="ruff 0.5.0",
        )
        assert r.score == 0.8
        assert r.findings_count == 2
        assert r.skipped is False
        assert r.skip_reason is None

    def test_evaluator_result_skipped_model(self) -> None:
        r = EvaluatorResult(
            evaluator_name="secret_scan",
            score=0.0,
            raw_output="",
            findings_count=0,
            library_version="gitleaks (not found)",
            skipped=True,
            skip_reason="gitleaks not installed",
        )
        assert r.skipped is True
        assert r.skip_reason == "gitleaks not installed"

    def test_evaluator_result_model_dump(self) -> None:
        r = EvaluatorResult(
            evaluator_name="complexity",
            score=1.0,
            raw_output="max_cc=3",
            findings_count=0,
            library_version="lizard 1.17.10",
        )
        d = r.model_dump(mode="json")
        assert d["evaluator_name"] == "complexity"
        assert d["score"] == 1.0
        assert d["skipped"] is False


# ---------------------------------------------------------------------------
# TestLintEvaluatorRuff
# ---------------------------------------------------------------------------


class TestLintEvaluatorRuff:
    """LintEvaluator -- ruff path via mocked asyncio.create_subprocess_exec."""

    @pytest.mark.asyncio
    async def test_ruff_two_errors_score_0_8(self, tmp_path: Path) -> None:
        """ruff returns 2 findings -> score = 1.0 - 2/10 = 0.8."""
        py_file = tmp_path / "foo.py"
        py_file.write_text("x=1\n")

        ruff_output = json.dumps(
            [
                {"code": "E501", "message": "Line too long", "filename": str(py_file)},
                {"code": "F401", "message": "Unused import", "filename": str(py_file)},
            ]
        )

        with (
            patch("src.evaluators.lint_evaluator.shutil.which", return_value="/usr/bin/ruff"),
            patch(
                "src.evaluators.lint_evaluator._get_ruff_version",
                return_value="ruff 0.5.0",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc(ruff_output),
            ),
        ):
            result = await LintEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.evaluator_name == "lint"
        assert result.findings_count == 2
        assert result.score == pytest.approx(0.8)
        assert result.library_version == "ruff 0.5.0"
        assert result.skipped is False

    @pytest.mark.asyncio
    async def test_ruff_zero_errors_score_1_0(self, tmp_path: Path) -> None:
        """ruff returns 0 findings -> score = 1.0."""
        py_file = tmp_path / "clean.py"
        py_file.write_text("x = 1\n")

        with (
            patch("src.evaluators.lint_evaluator.shutil.which", return_value="/usr/bin/ruff"),
            patch(
                "src.evaluators.lint_evaluator._get_ruff_version",
                return_value="ruff 0.5.0",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc("[]"),
            ),
        ):
            result = await LintEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.score == pytest.approx(1.0)
        assert result.findings_count == 0

    @pytest.mark.asyncio
    async def test_ruff_ten_plus_errors_score_0(self, tmp_path: Path) -> None:
        """ruff returns 12 findings -> score = 1.0 - min(1, 12/10) = 0.0."""
        py_file = tmp_path / "messy.py"
        py_file.write_text("x=1\n")

        findings = [{"code": "E501", "message": "msg", "filename": str(py_file)}] * 12
        ruff_output = json.dumps(findings)

        with (
            patch("src.evaluators.lint_evaluator.shutil.which", return_value="/usr/bin/ruff"),
            patch(
                "src.evaluators.lint_evaluator._get_ruff_version",
                return_value="ruff 0.5.0",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc(ruff_output),
            ),
        ):
            result = await LintEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.score == pytest.approx(0.0)
        assert result.findings_count == 12

    @pytest.mark.asyncio
    async def test_ruff_exit_code_2_returns_skipped(self, tmp_path: Path) -> None:
        """ruff exit code 2 (internal error) -> skipped=True."""
        (tmp_path / "x.py").write_text("")

        with (
            patch("src.evaluators.lint_evaluator.shutil.which", return_value="/usr/bin/ruff"),
            patch(
                "src.evaluators.lint_evaluator._get_ruff_version",
                return_value="ruff 0.5.0",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc("", stderr="config error", returncode=2),
            ),
        ):
            result = await LintEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.skipped is True
        assert result.skip_reason is not None
        assert "code 2" in result.skip_reason


# ---------------------------------------------------------------------------
# TestLintEvaluatorEslint
# ---------------------------------------------------------------------------


class TestLintEvaluatorEslint:
    """LintEvaluator -- eslint path via mocked subprocess."""

    @pytest.mark.asyncio
    async def test_eslint_zero_errors_score_1_0(self, tmp_path: Path) -> None:
        """eslint returns 0 messages -> score = 1.0."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("const x: number = 1;\n")

        eslint_output = json.dumps([{"filePath": str(ts_file), "messages": [], "errorCount": 0}])

        with (
            patch(
                "src.evaluators.lint_evaluator.shutil.which",
                side_effect=lambda b: "/usr/bin/eslint" if b == "eslint" else None,
            ),
            patch(
                "src.evaluators.lint_evaluator._get_eslint_version",
                return_value="v8.57.0",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc(eslint_output),
            ),
        ):
            result = await LintEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")

        assert result.score == pytest.approx(1.0)
        assert result.findings_count == 0

    @pytest.mark.asyncio
    async def test_eslint_three_errors_score_0_7(self, tmp_path: Path) -> None:
        """eslint returns 3 messages -> score = 0.7."""
        ts_file = tmp_path / "form.tsx"
        ts_file.write_text("const x = 1\n")

        eslint_output = json.dumps(
            [
                {
                    "filePath": str(ts_file),
                    "messages": [
                        {"message": "err1"},
                        {"message": "err2"},
                        {"message": "err3"},
                    ],
                }
            ]
        )

        with (
            patch(
                "src.evaluators.lint_evaluator.shutil.which",
                side_effect=lambda b: "/usr/bin/eslint" if b == "eslint" else None,
            ),
            patch(
                "src.evaluators.lint_evaluator._get_eslint_version",
                return_value="v8.57.0",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc(eslint_output),
            ),
        ):
            result = await LintEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")

        assert result.findings_count == 3
        assert result.score == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# TestLintEvaluatorSkip
# ---------------------------------------------------------------------------


class TestLintEvaluatorSkip:
    """LintEvaluator -- skip when no py/ts files and task_id maps to no language."""

    @pytest.mark.asyncio
    async def test_doc_task_no_files_returns_skipped(self, tmp_path: Path) -> None:
        """doc_01 task with no .py/.ts files -> skipped=True."""
        (tmp_path / "README.md").write_text("# Hello\n")

        result = await LintEvaluator().evaluate(str(tmp_path), "doc_01_cli_readme")

        assert result.skipped is True
        assert result.skip_reason is not None

    @pytest.mark.asyncio
    async def test_ruff_not_on_path_returns_skipped(self, tmp_path: Path) -> None:
        """Python files present but ruff not on PATH -> skipped=True."""
        (tmp_path / "main.py").write_text("x = 1\n")

        with patch("src.evaluators.lint_evaluator.shutil.which", return_value=None):
            result = await LintEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.skipped is True
        assert result.skip_reason is not None
        assert "ruff" in result.skip_reason


# ---------------------------------------------------------------------------
# TestComplexityEvaluator
# ---------------------------------------------------------------------------


class TestComplexityEvaluator:
    """ComplexityEvaluator -- lizard Python API mocked."""

    def _make_func(self, name: str, cc: int) -> MagicMock:
        """Create a mock lizard FunctionInfo."""
        f = MagicMock()
        f.name = name
        f.cyclomatic_complexity = cc
        f.location = f"{name}@1-10@mock.py"
        return f

    @pytest.mark.asyncio
    async def test_max_cc_5_returns_score_1_0(self, tmp_path: Path) -> None:
        """max_cc=5 (<=8 threshold) -> score = 1.0."""
        (tmp_path / "simple.py").write_text("def f(): pass\n")

        funcs = [self._make_func("f", 5), self._make_func("g", 3)]

        with (
            patch(
                "src.evaluators.complexity_evaluator._get_lizard_version",
                return_value="lizard 1.17.10",
            ),
            patch("src.evaluators.complexity_evaluator._analyze_path", return_value=funcs),
        ):
            result = await ComplexityEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.score == pytest.approx(1.0)
        assert result.findings_count == 0
        assert result.skipped is False

    @pytest.mark.asyncio
    async def test_max_cc_10_returns_score_0_8(self, tmp_path: Path) -> None:
        """max_cc=10 (>8 by 2) -> score = 1.0 - (10-8)/10 = 0.8."""
        (tmp_path / "complex.py").write_text("")

        funcs = [self._make_func("h", 10), self._make_func("k", 4)]

        with (
            patch(
                "src.evaluators.complexity_evaluator._get_lizard_version",
                return_value="lizard 1.17.10",
            ),
            patch("src.evaluators.complexity_evaluator._analyze_path", return_value=funcs),
        ):
            result = await ComplexityEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.score == pytest.approx(0.8)
        assert result.findings_count == 1  # only h exceeds threshold

    @pytest.mark.asyncio
    async def test_max_cc_18_returns_score_0(self, tmp_path: Path) -> None:
        """max_cc=18 (>8 by 10) -> score = 1.0 - 10/10 = 0.0."""
        (tmp_path / "very_complex.ts").write_text("")

        funcs = [self._make_func("monster", 18)]

        with (
            patch(
                "src.evaluators.complexity_evaluator._get_lizard_version",
                return_value="lizard 1.17.10",
            ),
            patch("src.evaluators.complexity_evaluator._analyze_path", return_value=funcs),
        ):
            result = await ComplexityEvaluator().evaluate(str(tmp_path), "fe_01_multistep_form")

        assert result.score == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_lizard_not_installed_returns_skipped(self, tmp_path: Path) -> None:
        """lizard import fails -> skipped=True."""
        with patch(
            "src.evaluators.complexity_evaluator._get_lizard_version",
            return_value="lizard (not installed)",
        ):
            result = await ComplexityEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.skipped is True
        assert result.skip_reason is not None

    @pytest.mark.asyncio
    async def test_no_functions_returns_score_1_0(self, tmp_path: Path) -> None:
        """No functions analysed (empty dir) -> score = 1.0 (trivially simple)."""
        with (
            patch(
                "src.evaluators.complexity_evaluator._get_lizard_version",
                return_value="lizard 1.17.10",
            ),
            patch("src.evaluators.complexity_evaluator._analyze_path", return_value=[]),
        ):
            result = await ComplexityEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.score == pytest.approx(1.0)
        assert result.findings_count == 0
        assert result.skipped is False


# ---------------------------------------------------------------------------
# TestSecretScanEvaluator
# ---------------------------------------------------------------------------


class TestSecretScanEvaluator:
    """SecretScanEvaluator -- gitleaks mocked."""

    @pytest.mark.asyncio
    async def test_no_secrets_returns_score_1_0(self, tmp_path: Path) -> None:
        """gitleaks finds no secrets -> score = 1.0."""
        (tmp_path / "safe.py").write_text("x = 1\n")

        with (
            patch(
                "src.evaluators.secret_scan_evaluator.shutil.which",
                return_value="/usr/local/bin/gitleaks",
            ),
            patch(
                "src.evaluators.secret_scan_evaluator._get_gitleaks_version",
                return_value="gitleaks 8.18.0",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc("", returncode=0),
            ),
            patch(
                "src.evaluators.secret_scan_evaluator._parse_gitleaks_report",
                return_value=(0, ""),
            ),
        ):
            result = await SecretScanEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.score == pytest.approx(1.0)
        assert result.findings_count == 0
        assert result.skipped is False

    @pytest.mark.asyncio
    async def test_one_secret_returns_score_0_0(self, tmp_path: Path) -> None:
        """gitleaks finds 1 secret -> score = 0.0."""
        (tmp_path / "leaked.py").write_text('API_KEY = "sk-abc123"\n')

        summary = "gitleaks found 1 secret(s):\n  [generic-api-key] API Key in leaked.py"

        with (
            patch(
                "src.evaluators.secret_scan_evaluator.shutil.which",
                return_value="/usr/local/bin/gitleaks",
            ),
            patch(
                "src.evaluators.secret_scan_evaluator._get_gitleaks_version",
                return_value="gitleaks 8.18.0",
            ),
            patch(
                "asyncio.create_subprocess_exec",
                return_value=_make_proc("", returncode=1),
            ),
            patch(
                "src.evaluators.secret_scan_evaluator._parse_gitleaks_report",
                return_value=(1, summary),
            ),
        ):
            result = await SecretScanEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.score == pytest.approx(0.0)
        assert result.findings_count == 1

    @pytest.mark.asyncio
    async def test_gitleaks_not_on_path_returns_skipped(self, tmp_path: Path) -> None:
        """gitleaks binary absent -> skipped=True with install hint."""
        with patch("src.evaluators.secret_scan_evaluator.shutil.which", return_value=None):
            result = await SecretScanEvaluator().evaluate(str(tmp_path), "be_01_jwt_auth")

        assert result.skipped is True
        assert result.skip_reason is not None
        assert "gitleaks" in result.skip_reason
        assert "brew install gitleaks" in result.skip_reason

    @pytest.mark.asyncio
    async def test_path_not_exist_returns_score_1_0(self, tmp_path: Path) -> None:
        """Artifact path does not exist -> skip scan, return score=1.0."""
        nonexistent = str(tmp_path / "does_not_exist")

        with (
            patch(
                "src.evaluators.secret_scan_evaluator.shutil.which",
                return_value="/usr/local/bin/gitleaks",
            ),
            patch(
                "src.evaluators.secret_scan_evaluator._get_gitleaks_version",
                return_value="gitleaks 8.18.0",
            ),
        ):
            result = await SecretScanEvaluator().evaluate(nonexistent, "be_01_jwt_auth")

        # Path does not exist -> treated as clean (nothing to scan).
        assert result.score == pytest.approx(1.0)
        assert result.skipped is False


# ---------------------------------------------------------------------------
# TestEvaluatorParsers (pure unit tests, no I/O)
# ---------------------------------------------------------------------------


class TestEvaluatorParsers:
    """Unit tests for _parse_ruff_json and _parse_eslint_json."""

    # -- ruff --

    def test_parse_ruff_json_empty_string(self) -> None:
        assert _parse_ruff_json("") == 0

    def test_parse_ruff_json_empty_array(self) -> None:
        assert _parse_ruff_json("[]") == 0

    def test_parse_ruff_json_two_items(self) -> None:
        data = [{"code": "E501"}, {"code": "F401"}]
        assert _parse_ruff_json(json.dumps(data)) == 2

    def test_parse_ruff_json_invalid(self) -> None:
        assert _parse_ruff_json("{not-json") == 0

    def test_parse_ruff_json_non_array(self) -> None:
        assert _parse_ruff_json('{"error": "x"}') == 0

    # -- eslint --

    def test_parse_eslint_json_empty_string(self) -> None:
        assert _parse_eslint_json("") == 0

    def test_parse_eslint_json_empty_file_list(self) -> None:
        assert _parse_eslint_json("[]") == 0

    def test_parse_eslint_json_one_file_three_messages(self) -> None:
        data = [{"filePath": "a.ts", "messages": [{"msg": "x"}, {"msg": "y"}, {"msg": "z"}]}]
        assert _parse_eslint_json(json.dumps(data)) == 3

    def test_parse_eslint_json_multiple_files(self) -> None:
        data = [
            {"filePath": "a.ts", "messages": [{"msg": "x"}]},
            {"filePath": "b.ts", "messages": [{"msg": "y"}, {"msg": "z"}]},
        ]
        assert _parse_eslint_json(json.dumps(data)) == 3

    def test_parse_eslint_json_invalid(self) -> None:
        assert _parse_eslint_json("{bad") == 0

    def test_parse_eslint_json_zero_messages(self) -> None:
        data = [{"filePath": "a.ts", "messages": []}]
        assert _parse_eslint_json(json.dumps(data)) == 0
