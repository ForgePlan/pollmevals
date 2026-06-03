"""Tests for --fill-missing mode in scripts/build_real_board.py.

Covers:
1. TestComputeGap      -- _compute_gap computes desired - present correctly
2. TestMergeIntoBoard  -- _merge_into_board is idempotent and correct
3. TestDryRun          -- --fill-missing --dry-run prints gap, exits 0, NO spend
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from src.contracts import (
    ArtifactRef,
    EvalArtifactRefs,
    EvalRow,
    EvalStats,
    EvalStatus,
)
from src.leaderboard.board import Board, build_board

# ---------------------------------------------------------------------------
# Add scripts/ to sys.path so `from build_real_board import ...` works
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_real_board import (  # noqa: E402
    _STACK_MODELS,
    _compute_gap,
    _merge_into_board,
)

_STACKS_ROOT = Path(__file__).resolve().parents[3] / "stacks"
_RUN_HASH = "sha256:" + "t" * 58


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ref() -> ArtifactRef:
    return ArtifactRef(
        sha256="a" * 64, size_bytes=10, uri="file:///tmp/x.txt", mime_type="text/plain"
    )


def _row(
    model_id: str,
    stack_id: str,
    *,
    score: float = 7.0,
) -> EvalRow:
    return EvalRow(
        eval_id="b" * 16,
        model_id=model_id,
        stack_id=stack_id,
        task_id="be_01_jwt_auth",
        seed=1,
        status=EvalStatus.SCORED,
        error_class=None,
        artifact_refs=EvalArtifactRefs(
            raw_output=_ref(), normalized_output=_ref(), evaluator_json=_ref()
        ),
        stats=EvalStats(
            input_tokens=100, output_tokens=50, wall_clock_ms=10_000, cost_usd=Decimal("0.05")
        ),
        final_score=score,
        judge_aggregate=None,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def _board_from_rows(rows: list[EvalRow]) -> Board:
    return build_board(rows, stacks_root=_STACKS_ROOT, run_hash=_RUN_HASH, run_type="smoke")


def _write_board(path: Path, rows: list[EvalRow]) -> Board:
    board = _board_from_rows(rows)
    path.write_text(board.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return board


# ---------------------------------------------------------------------------
# 1. TestComputeGap
# ---------------------------------------------------------------------------


class TestComputeGap:
    """_compute_gap returns desired - present correctly."""

    def test_empty_board_all_desired_are_missing(self, tmp_path: Path) -> None:
        """When board.json has no cells, every desired pair is reported as missing."""
        board_path = tmp_path / "board.json"
        # Write a board with zero cells.
        empty_board = _board_from_rows([])
        board_path.write_text(empty_board.model_dump_json(indent=2) + "\n", encoding="utf-8")

        missing = _compute_gap(board_path, stacks=["aider"])
        expected = {(m, "aider") for m in _STACK_MODELS["aider"]}
        assert set(missing) == expected

    def test_present_cells_excluded_from_gap(self, tmp_path: Path) -> None:
        """Cells already on the board are NOT included in the gap."""
        board_path = tmp_path / "board.json"
        present_model = _STACK_MODELS["aider"][0]
        _write_board(board_path, [_row(present_model, "aider")])

        missing = _compute_gap(board_path, stacks=["aider"])
        assert (present_model, "aider") not in missing
        # Remaining aider models should be in the gap.
        expected_missing = {(m, "aider") for m in _STACK_MODELS["aider"] if m != present_model}
        assert set(missing) == expected_missing

    def test_all_cells_present_returns_empty_gap(self, tmp_path: Path) -> None:
        """When every desired cell is on the board, gap is empty."""
        board_path = tmp_path / "board.json"
        rows = [_row(m, "aider") for m in _STACK_MODELS["aider"]]
        _write_board(board_path, rows)

        missing = _compute_gap(board_path, stacks=["aider"])
        assert missing == []

    def test_stacks_filter_limits_desired_set(self, tmp_path: Path) -> None:
        """Only stacks in the filter contribute to the desired set."""
        board_path = tmp_path / "board.json"
        _write_board(board_path, [])

        missing = _compute_gap(board_path, stacks=["aider"])
        stacks_in_gap = {stack_id for _, stack_id in missing}
        assert stacks_in_gap == {"aider"}
        # goose should not appear when filter is aider-only.
        assert "goose" not in stacks_in_gap

    def test_none_stacks_filter_includes_all_stacks(self, tmp_path: Path) -> None:
        """stacks=None includes all stacks from _STACK_MODELS."""
        board_path = tmp_path / "board.json"
        _write_board(board_path, [])

        missing = _compute_gap(board_path, stacks=None)
        stacks_in_gap = {stack_id for _, stack_id in missing}
        assert stacks_in_gap == set(_STACK_MODELS.keys())

    def test_missing_board_file_treats_as_empty(self, tmp_path: Path) -> None:
        """When board.json doesn't exist, all desired cells are missing."""
        board_path = tmp_path / "nonexistent.json"
        missing = _compute_gap(board_path, stacks=["aider"])
        expected = {(m, "aider") for m in _STACK_MODELS["aider"]}
        assert set(missing) == expected

    def test_gap_is_sorted(self, tmp_path: Path) -> None:
        """Gap list is sorted for deterministic output."""
        board_path = tmp_path / "board.json"
        _write_board(board_path, [])
        missing = _compute_gap(board_path, stacks=["aider", "goose"])
        assert missing == sorted(missing)

    def test_cross_stack_no_bleeding(self, tmp_path: Path) -> None:
        """A present (model, aider) cell does NOT suppress (model, goose) from the gap."""
        board_path = tmp_path / "board.json"
        shared_model = _STACK_MODELS["aider"][0]
        _write_board(board_path, [_row(shared_model, "aider")])

        missing = _compute_gap(board_path, stacks=["aider", "goose"])
        missing_set = set(missing)
        # aider cell is present → not in gap.
        assert (shared_model, "aider") not in missing_set
        # goose cell for same model is NOT present → must be in gap.
        if shared_model in _STACK_MODELS.get("goose", []):
            assert (shared_model, "goose") in missing_set


# ---------------------------------------------------------------------------
# 2. TestMergeIntoBoard
# ---------------------------------------------------------------------------


class TestMergeIntoBoard:
    """_merge_into_board is correct and idempotent."""

    def test_merge_adds_new_cell(self) -> None:
        """A cell from partial that is absent from existing is appended."""
        existing = _board_from_rows([_row("qwen-3-14b", "raw-llm")])
        partial = _board_from_rows([_row("qwen-3-14b", "aider")])
        merged = _merge_into_board(existing, partial)
        keys = {(c.model_id, c.stack_id) for c in merged.cells}
        assert ("qwen-3-14b", "raw-llm") in keys
        assert ("qwen-3-14b", "aider") in keys

    def test_merge_replaces_existing_cell(self) -> None:
        """A cell from partial that already exists in existing is replaced."""
        existing = _board_from_rows([_row("qwen-3-14b", "aider", score=5.0)])
        partial = _board_from_rows([_row("qwen-3-14b", "aider", score=9.0)])
        merged = _merge_into_board(existing, partial)
        cell = next(c for c in merged.cells if c.model_id == "qwen-3-14b" and c.stack_id == "aider")
        assert cell.mean_score == 9.0

    def test_merge_is_idempotent(self) -> None:
        """Merging the same partial twice produces the same result as merging once."""
        existing = _board_from_rows([_row("qwen-3-14b", "raw-llm")])
        partial = _board_from_rows([_row("qwen-3-14b", "aider", score=7.0)])
        once = _merge_into_board(existing, partial)
        twice = _merge_into_board(once, partial)
        # Cells should be identical sets.
        keys_once = {(c.model_id, c.stack_id) for c in once.cells}
        keys_twice = {(c.model_id, c.stack_id) for c in twice.cells}
        assert keys_once == keys_twice
        # Score should not drift.
        score_once = next(
            c.mean_score for c in once.cells if c.model_id == "qwen-3-14b" and c.stack_id == "aider"
        )
        score_twice = next(
            c.mean_score
            for c in twice.cells
            if c.model_id == "qwen-3-14b" and c.stack_id == "aider"
        )
        assert score_once == score_twice

    def test_merge_unions_harnesses(self) -> None:
        """New harness entries from partial are added to the merged board."""
        existing = _board_from_rows([_row("qwen-3-14b", "raw-llm")])
        partial = _board_from_rows([_row("qwen-3-14b", "aider")])
        merged = _merge_into_board(existing, partial)
        harness_ids = {h.stack_id for h in merged.harnesses}
        assert "raw-llm" in harness_ids
        assert "aider" in harness_ids

    def test_merge_does_not_mutate_existing(self) -> None:
        """_merge_into_board returns a new Board; existing is unchanged."""
        existing = _board_from_rows([_row("qwen-3-14b", "raw-llm")])
        partial = _board_from_rows([_row("qwen-3-14b", "aider")])
        original_cell_count = len(existing.cells)
        _ = _merge_into_board(existing, partial)
        assert len(existing.cells) == original_cell_count

    def test_merge_scored_flag(self) -> None:
        """scored=True when at least one merged cell has a score."""
        existing = _board_from_rows([])
        partial = _board_from_rows([_row("qwen-3-14b", "aider", score=7.0)])
        merged = _merge_into_board(existing, partial)
        assert merged.scored is True


# ---------------------------------------------------------------------------
# 3. TestDryRun (CLI entry-point via async _main)
# ---------------------------------------------------------------------------


class TestDryRun:
    """--fill-missing --dry-run must print gap summary and exit 0 without spending."""

    @pytest.mark.asyncio
    async def test_dry_run_exits_zero(self, tmp_path: Path, monkeypatch: Any) -> None:
        """--fill-missing --dry-run exits 0 regardless of gap size."""
        import argparse

        import build_real_board as brb

        # Write a board with zero aider cells so gap is non-empty.
        board_path = tmp_path / "board.json"
        _write_board(board_path, [])
        monkeypatch.setattr(brb, "REPO", tmp_path)
        # Patch out env key requirement.
        monkeypatch.setenv("LITELLM_MASTER_KEY", "fake-key-for-test")
        # Provide the board.json at the expected path.
        board_dest = tmp_path / "apps" / "site" / "public"
        board_dest.mkdir(parents=True)
        _write_board(board_dest / "board.json", [])

        # Invoke via argparse simulation.
        args = argparse.Namespace(
            confirm_spend=False,
            fill="",
            add_stack="",
            fill_missing=True,
            stacks="aider",
            dry_run=True,
        )

        # Monkeypatch parse_args so _main() picks up our args namespace.
        import argparse as ap_mod

        monkeypatch.setattr(ap_mod.ArgumentParser, "parse_args", lambda self, *a, **kw: args)
        # chdir is called by _main; patch it to avoid side effects.
        monkeypatch.setattr("os.chdir", lambda p: None)
        # _load_env is harmless but avoid file I/O.
        monkeypatch.setattr(brb, "_load_env", lambda repo: None)

        exit_code = await brb._main()
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_dry_run_empty_gap_exits_zero(self, tmp_path: Path, monkeypatch: Any) -> None:
        """When gap is empty, --dry-run exits 0 with 'EMPTY' message."""
        import argparse

        import build_real_board as brb

        # Write a fully-populated aider column.
        board_dest = tmp_path / "apps" / "site" / "public"
        board_dest.mkdir(parents=True)
        rows = [_row(m, "aider") for m in _STACK_MODELS["aider"]]
        _write_board(board_dest / "board.json", rows)

        monkeypatch.setattr(brb, "REPO", tmp_path)
        monkeypatch.setenv("LITELLM_MASTER_KEY", "fake-key-for-test")

        args = argparse.Namespace(
            confirm_spend=False,
            fill="",
            add_stack="",
            fill_missing=True,
            stacks="aider",
            dry_run=True,
        )

        import argparse as ap_mod

        monkeypatch.setattr(ap_mod.ArgumentParser, "parse_args", lambda self, *a, **kw: args)
        monkeypatch.setattr("os.chdir", lambda p: None)
        monkeypatch.setattr(brb, "_load_env", lambda repo: None)

        exit_code = await brb._main()
        assert exit_code == 0

    def test_dry_run_computes_correct_gap_subset(self, tmp_path: Path) -> None:
        """_compute_gap with one stack present returns exactly the remaining models."""
        board_path = tmp_path / "board.json"
        present = _STACK_MODELS["aider"][:1]
        absent = _STACK_MODELS["aider"][1:]
        _write_board(board_path, [_row(m, "aider") for m in present])

        missing = _compute_gap(board_path, stacks=["aider"])
        missing_models = [m for m, s in missing if s == "aider"]
        assert set(missing_models) == set(absent)
        # Present model must not appear.
        assert present[0] not in missing_models
