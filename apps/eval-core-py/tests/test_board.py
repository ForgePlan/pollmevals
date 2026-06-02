"""Unit tests for the harness x model Board emitter (RFC-006 Phase 4c).

Offline — synthetic EvalRows, no run/judges. Derives harness metadata from the
real ``stacks/`` dir (raw-llm + aider exist).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from src.contracts import (
    ArtifactRef,
    ErrorClass,
    EvalArtifactRefs,
    EvalRow,
    EvalStats,
    EvalStatus,
    JudgeAggregation,
)
from src.leaderboard.board import build_board

_STACKS_ROOT = Path(__file__).resolve().parents[3] / "stacks"


def _ref() -> ArtifactRef:
    return ArtifactRef(
        sha256="a" * 64, size_bytes=10, uri="file:///tmp/x.txt", mime_type="text/plain"
    )


def _row(
    model_id: str,
    stack_id: str,
    task_id: str,
    *,
    score: float | None = None,
    agg: JudgeAggregation | None = None,
    cost: str = "0.05",
    status: EvalStatus = EvalStatus.SCORED,
    wall_ms: int = 50_000,
) -> EvalRow:
    return EvalRow(
        eval_id="a" * 16,
        model_id=model_id,
        stack_id=stack_id,
        task_id=task_id,
        seed=1,
        status=status,
        error_class=ErrorClass.SANDBOX_FAILURE if status is EvalStatus.FAILED else None,
        artifact_refs=EvalArtifactRefs(
            raw_output=_ref(), normalized_output=_ref(), evaluator_json=_ref()
        ),
        stats=EvalStats(
            input_tokens=100, output_tokens=50, wall_clock_ms=wall_ms, cost_usd=Decimal(cost)
        ),
        final_score=score,
        judge_aggregate=agg,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def _build(rows: list[EvalRow]):
    return build_board(rows, stacks_root=_STACKS_ROOT, run_hash="sha256:" + "1" * 58)


class TestBoardShape:
    def test_top_level_fields(self) -> None:
        board = _build([_row("qwen-3-14b", "aider", "be_01_jwt_auth", score=7.0)])
        assert board.run_type == "weekly"
        assert board.methodology_version == "v0.1.0"
        assert board.illustrative is False
        assert board.scored is True
        assert board.tasks == ["be_01_jwt_auth"]

    def test_harness_metadata_derived_from_yaml(self) -> None:
        board = _build(
            [
                _row("qwen-3-14b", "raw-llm", "be_01_jwt_auth", score=5.0),
                _row("qwen-3-14b", "aider", "be_01_jwt_auth", score=7.0),
            ]
        )
        by_stack = {h.stack_id: h for h in board.harnesses}
        assert by_stack["raw-llm"].family == "baseline"
        assert by_stack["raw-llm"].level == 0
        assert by_stack["aider"].family == "agnostic"
        # aider declares L1+L2+L4 → level is the highest (L4 → index 4)
        assert by_stack["aider"].level == 4
        assert "L2_tools" in by_stack["aider"].layers

    def test_model_registry(self) -> None:
        board = _build([_row("openrouter/qwen/qwen-3-14b", "aider", "be_01_jwt_auth", score=7.0)])
        m = board.models[0]
        assert m.name == "Qwen 3 14B"
        assert m.tier == "cheap"


class TestCells:
    def test_cell_score_cost_and_qpd(self) -> None:
        board = _build([_row("qwen-3-14b", "aider", "be_01_jwt_auth", score=7.0, cost="0.05")])
        cell = board.cells[0]
        assert cell.mean_score == 7.0
        assert cell.mean_cost_usd == 0.05
        assert cell.quality_per_dollar == 140.0  # 7.0 / 0.05
        assert cell.per_task["be_01_jwt_auth"].score == 7.0

    def test_score_from_judge_aggregate(self) -> None:
        agg = JudgeAggregation(
            median_per_criterion={"correctness": 7.0, "clarity": 9.0},
            n_judges_used=3,
            judge_status="OK",
        )
        board = _build([_row("qwen-3-14b", "aider", "be_01_jwt_auth", agg=agg)])
        assert board.cells[0].mean_score == 8.0  # mean(7,9)

    def test_failed_row_null_score_keeps_cost(self) -> None:
        board = _build(
            [_row("qwen-3-14b", "aider", "be_01_jwt_auth", status=EvalStatus.FAILED, cost="0.01")]
        )
        cell = board.cells[0]
        assert cell.mean_score is None
        assert cell.quality_per_dollar is None
        assert cell.mean_cost_usd == 0.01
        assert board.scored is False

    def test_one_cell_per_model_stack(self) -> None:
        board = _build(
            [
                _row("qwen-3-14b", "raw-llm", "be_01_jwt_auth", score=5.0),
                _row("qwen-3-14b", "aider", "be_01_jwt_auth", score=7.0),
            ]
        )
        assert len(board.cells) == 2
        keys = {(c.model_id, c.stack_id) for c in board.cells}
        assert keys == {("qwen-3-14b", "raw-llm"), ("qwen-3-14b", "aider")}
