"""Tests for orchestrator/auto_metrics.py — evaluator wiring + final_score formula.

Coverage:
  TestRunAutoEvaluators    -- lint + type_safety scores appear in automatic_metrics
                              for a TS snippet with known errors (non-zero scores)
  TestRunAutoEvaluatorsSkip-- evaluators skip gracefully when binaries absent
  TestComputeFinalScore    -- formula: metrics + judge pattern_match -> correct result
  TestComputeFinalScoreEdges-- None when nothing, partial when some components present
  TestLintTaskLangMap      -- be_ task no longer defaults to python fallback
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.contracts import EvalArtifactRefs, EvalStats, EvalStatus
from src.contracts.artifact_ref import ArtifactRef
from src.contracts.eval_row import EvalRow
from src.contracts.judge import JudgeAggregation
from src.orchestrator.auto_metrics import (
    _CODING_WEIGHTS,
    compute_final_score,
    run_auto_evaluators,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(stdout: str, stderr: str = "", returncode: int = 0) -> AsyncMock:
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    return proc


def _minimal_artifact_refs() -> EvalArtifactRefs:
    ref = ArtifactRef(
        sha256="a" * 64, size_bytes=1, uri="file:///tmp/x", mime_type="text/plain"
    )
    return EvalArtifactRefs(raw_output=ref, normalized_output=ref, evaluator_json=ref)


def _minimal_row(automatic_metrics: dict | None = None, judge_aggregate=None) -> EvalRow:
    return EvalRow(
        eval_id="abcdef0123456789",
        model_id="openrouter/qwen/qwen-3-14b",
        stack_id="aider",
        task_id="be_01_jwt_auth",
        seed=1,
        status=EvalStatus.SCORED,
        artifact_refs=_minimal_artifact_refs(),
        stats=EvalStats(input_tokens=100, output_tokens=200, wall_clock_ms=1000, cost_usd=0),
        automatic_metrics=automatic_metrics or {},
        judge_aggregate=judge_aggregate,
    )


# ---------------------------------------------------------------------------
# TestRunAutoEvaluators — TS snippet, eslint + tsc produce non-trivial scores
# ---------------------------------------------------------------------------


class TestRunAutoEvaluators:
    """Verify that lint+type_safety scores flow through run_auto_evaluators."""

    @pytest.mark.asyncio
    async def test_ts_snippet_with_lint_errors_returns_nonzero_scores(
        self, tmp_path: Path
    ) -> None:
        """A .ts file with eslint warnings produces lint < 1.0 and type_safety = 1.0."""
        ts_file = tmp_path / "solution.ts"
        ts_file.write_text("var x = 1;\n")  # deliberate: var is a lint finding

        # eslint reports 3 messages (simulating var, no-unused-vars, etc.)
        eslint_out = json.dumps(
            [{"filePath": str(ts_file), "messages": [{"m": "1"}, {"m": "2"}, {"m": "3"}]}]
        )
        # tsc reports 0 errors
        tsc_out = ""

        def _which(bin_name: str) -> str | None:
            return f"/usr/bin/{bin_name}" if bin_name in ("eslint", "tsc") else None

        async def _fake_exec(*args: str, **_kw: object) -> AsyncMock:
            if args[0] == "eslint":
                return _make_proc(eslint_out, returncode=1)
            else:  # tsc
                return _make_proc(tsc_out, returncode=0)

        with (
            patch("src.evaluators.lint_evaluator.shutil.which", side_effect=_which),
            patch("src.evaluators.type_safety_evaluator.shutil.which", side_effect=_which),
            patch("src.evaluators.lint_evaluator._get_eslint_version", return_value="v9.0.0"),
            patch("src.evaluators.type_safety_evaluator._get_tsc_version", return_value="v5.5.0"),
            patch("asyncio.create_subprocess_exec", side_effect=_fake_exec),
        ):
            metrics = await run_auto_evaluators(str(tmp_path), "be_01_jwt_auth")

        # lint: 3 findings -> 1.0 - 3/10 = 0.7
        assert metrics["lint"] == pytest.approx(0.7)
        assert metrics["lint_skipped"] is False
        # type_safety: 0 errors -> 1.0
        assert metrics["type_safety"] == pytest.approx(1.0)
        assert metrics["type_safety_skipped"] is False

    @pytest.mark.asyncio
    async def test_ts_snippet_with_type_errors_returns_nonzero_type_safety(
        self, tmp_path: Path
    ) -> None:
        """A .ts file with tsc errors produces type_safety < 1.0."""
        ts_file = tmp_path / "bad.ts"
        ts_file.write_text("const x: number = 'wrong';\n")

        # eslint: clean
        eslint_out = json.dumps([{"filePath": str(ts_file), "messages": []}])
        # tsc: 2 type errors
        tsc_out = (
            "bad.ts(1,7): error TS2322: Type 'string' is not assignable to type 'number'.\n"
            "bad.ts(1,9): error TS2304: Cannot find name 'wrong'.\n"
        )

        def _which(bin_name: str) -> str | None:
            return f"/usr/bin/{bin_name}" if bin_name in ("eslint", "tsc") else None

        async def _fake_exec(*args: str, **_kw: object) -> AsyncMock:
            if args[0] == "eslint":
                return _make_proc(eslint_out, returncode=0)
            else:
                return _make_proc(tsc_out, returncode=1)

        with (
            patch("src.evaluators.lint_evaluator.shutil.which", side_effect=_which),
            patch("src.evaluators.type_safety_evaluator.shutil.which", side_effect=_which),
            patch("src.evaluators.lint_evaluator._get_eslint_version", return_value="v9.0.0"),
            patch("src.evaluators.type_safety_evaluator._get_tsc_version", return_value="v5.5.0"),
            patch("asyncio.create_subprocess_exec", side_effect=_fake_exec),
        ):
            metrics = await run_auto_evaluators(str(tmp_path), "be_01_jwt_auth")

        # lint: 0 findings -> 1.0
        assert metrics["lint"] == pytest.approx(1.0)
        # type_safety: 2 errors -> 1.0 - 2/10 = 0.8
        assert metrics["type_safety"] == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_keys_present_even_when_skipped(self, tmp_path: Path) -> None:
        """All four keys (lint, lint_skipped, type_safety, type_safety_skipped) always present."""
        # No TS/Py files, no binaries available
        with (
            patch("src.evaluators.lint_evaluator.shutil.which", return_value=None),
            patch("src.evaluators.type_safety_evaluator.shutil.which", return_value=None),
        ):
            metrics = await run_auto_evaluators(str(tmp_path), "doc_01_cli_readme")

        assert "lint" in metrics
        assert "lint_skipped" in metrics
        assert "type_safety" in metrics
        assert "type_safety_skipped" in metrics
        assert metrics["lint"] == 0.0
        assert metrics["type_safety"] == 0.0


# ---------------------------------------------------------------------------
# TestRunAutoEvaluatorsSkip — graceful degradation when binaries absent
# ---------------------------------------------------------------------------


class TestRunAutoEvaluatorsSkip:
    @pytest.mark.asyncio
    async def test_scores_default_zero_when_both_binaries_absent(
        self, tmp_path: Path
    ) -> None:
        """lint=0.0, type_safety=0.0, both marked skipped when binaries absent."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("const x = 1;\n")

        with (
            patch("src.evaluators.lint_evaluator.shutil.which", return_value=None),
            patch("src.evaluators.type_safety_evaluator.shutil.which", return_value=None),
        ):
            metrics = await run_auto_evaluators(str(tmp_path), "be_01_jwt_auth")

        assert metrics["lint"] == 0.0
        assert metrics["lint_skipped"] is True
        assert metrics["type_safety"] == 0.0
        assert metrics["type_safety_skipped"] is True


# ---------------------------------------------------------------------------
# TestComputeFinalScore — coding-task weighted formula
# ---------------------------------------------------------------------------


class TestComputeFinalScore:
    def test_all_components_present_correct_weighted_sum(self) -> None:
        """Full metrics + judge pattern_match → formula result."""
        auto = {
            "correctness": 0.8,
            "coverage": 0.6,
            "complexity": 1.0,
            "lint": 0.7,
            "type_safety": 0.9,
        }
        agg = JudgeAggregation(
            n_judges_used=3,
            judge_status="OK",
            median_per_criterion={"pattern_match": 8.0},  # 0-10 range
        )
        row = _minimal_row(automatic_metrics=auto, judge_aggregate=agg)
        result = compute_final_score(row)
        assert result is not None

        # Manual: (0.40*0.8 + 0.15*0.6 + 0.10*1.0 + 0.10*0.7 + 0.10*0.9 + 0.15*(8.0/10)) * 10
        expected_01 = (
            0.40 * 0.8
            + 0.15 * 0.6
            + 0.10 * 1.0
            + 0.10 * 0.7
            + 0.10 * 0.9
            + 0.15 * (8.0 / 10.0)
        )
        expected = round(expected_01 * 10.0, 4)
        assert result == pytest.approx(expected, abs=1e-3)

    def test_lint_and_type_safety_contribute_to_score(self) -> None:
        """Non-zero lint + type_safety scores shift the result vs zero baseline."""
        auto_zero = {"lint": 0.0, "type_safety": 0.0}
        auto_nonzero = {"lint": 0.8, "type_safety": 0.9}

        row_zero = _minimal_row(automatic_metrics=auto_zero)
        row_nonzero = _minimal_row(automatic_metrics=auto_nonzero)

        score_zero = compute_final_score(row_zero)
        score_nonzero = compute_final_score(row_nonzero)

        assert score_zero is not None
        assert score_nonzero is not None
        # lint weight=0.10, type_safety weight=0.10 → 0.17 difference in 0-10 range
        assert score_nonzero > score_zero

    def test_weights_sum_respected(self) -> None:
        """All components at 1.0 → final_score = 10.0 (perfect score)."""
        auto = {
            "correctness": 1.0,
            "coverage": 1.0,
            "complexity": 1.0,
            "lint": 1.0,
            "type_safety": 1.0,
        }
        agg = JudgeAggregation(
            n_judges_used=3,
            judge_status="OK",
            median_per_criterion={"pattern_match": 10.0},
        )
        row = _minimal_row(automatic_metrics=auto, judge_aggregate=agg)
        result = compute_final_score(row)
        assert result == pytest.approx(10.0, abs=1e-3)

    def test_all_zero_components_returns_zero(self) -> None:
        """All components 0.0 → final_score = 0.0."""
        auto = {
            "correctness": 0.0,
            "coverage": 0.0,
            "complexity": 0.0,
            "lint": 0.0,
            "type_safety": 0.0,
        }
        agg = JudgeAggregation(
            n_judges_used=3,
            judge_status="OK",
            median_per_criterion={"pattern_match": 0.0},
        )
        row = _minimal_row(automatic_metrics=auto, judge_aggregate=agg)
        assert compute_final_score(row) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# TestComputeFinalScoreEdges — None / partial / clamping
# ---------------------------------------------------------------------------


class TestComputeFinalScoreEdges:
    def test_returns_none_when_no_metrics_and_no_judge(self) -> None:
        """Empty row (no auto_metrics, no judge) → None (nothing to score)."""
        row = _minimal_row()
        assert compute_final_score(row) is None

    def test_partial_metrics_only_no_judge(self) -> None:
        """Only lint+type_safety present; other components default to 0 but score computed."""
        auto = {"lint": 1.0, "type_safety": 1.0}
        row = _minimal_row(automatic_metrics=auto)
        result = compute_final_score(row)
        assert result is not None
        # Only lint(0.10) + type_safety(0.10) contribute → 0.20 * 10 = 2.0
        assert result == pytest.approx(2.0, abs=1e-3)

    def test_judge_only_no_auto_metrics(self) -> None:
        """Only judge pattern_match present → partial score from that term."""
        agg = JudgeAggregation(
            n_judges_used=3,
            judge_status="OK",
            median_per_criterion={"pattern_match": 10.0},
        )
        row = _minimal_row(judge_aggregate=agg)
        result = compute_final_score(row)
        assert result is not None
        # Only pattern_match(0.15) contributes → 0.15 * (10.0/10.0) * 10 = 1.5
        assert result == pytest.approx(1.5, abs=1e-3)

    def test_score_clamped_to_10(self) -> None:
        """Formula result > 10.0 is clamped (defensive — correct weights sum to exactly 1)."""
        auto = {k: 2.0 for k in ("correctness", "coverage", "complexity", "lint", "type_safety")}
        agg = JudgeAggregation(
            n_judges_used=3,
            judge_status="OK",
            median_per_criterion={"pattern_match": 20.0},
        )
        row = _minimal_row(automatic_metrics=auto, judge_aggregate=agg)
        result = compute_final_score(row)
        assert result is not None
        assert result <= 10.0


# ---------------------------------------------------------------------------
# TestLintTaskLangMap — be_ prefix no longer defaults to python
# ---------------------------------------------------------------------------


class TestLintTaskLangMap:
    def test_be_task_with_ts_files_uses_eslint_not_ruff(self, tmp_path: Path) -> None:
        """be_ task with a .ts file → LintEvaluator uses eslint, not ruff."""
        from src.evaluators.lint_evaluator import _detect_language

        ts_file = tmp_path / "solution.ts"
        ts_file.write_text("export const x = 1;\n")

        lang = _detect_language(tmp_path, "be_01_jwt_auth")
        assert lang == "typescript"

    def test_be_task_empty_dir_not_forced_to_python(self, tmp_path: Path) -> None:
        """be_ task with empty dir → does NOT fall back to python (old broken behaviour)."""
        from src.evaluators.lint_evaluator import _detect_language

        lang = _detect_language(tmp_path, "be_01_jwt_auth")
        # No files → "none" (not "python")
        assert lang == "none"

    def test_fe_task_still_falls_back_to_typescript(self, tmp_path: Path) -> None:
        """fe_ task with no files → still falls back to typescript via map."""
        from src.evaluators.lint_evaluator import _detect_language

        lang = _detect_language(tmp_path, "fe_01_multistep_form")
        assert lang == "typescript"

    def test_doc_task_maps_to_none(self, tmp_path: Path) -> None:
        """doc_ task → none (no linting applicable)."""
        from src.evaluators.lint_evaluator import _detect_language

        lang = _detect_language(tmp_path, "doc_01_cli_readme")
        assert lang == "none"
