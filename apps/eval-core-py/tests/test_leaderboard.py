"""Tests for src.leaderboard.aggregate — manifest → publishable leaderboard."""

from __future__ import annotations

import glob
import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.contracts import (
    ArtifactRef,
    CountsByStatus,
    EvalArtifactRefs,
    EvalRow,
    EvalStats,
    EvalStatus,
    Manifest,
    ModelPin,
    PricingSnapshot,
    RunAggregates,
    RunStatus,
    RunType,
    StackPin,
    TaskPin,
)
from src.leaderboard import build_leaderboard

_SHA = "a" * 64


def _ref(label: str) -> ArtifactRef:
    return ArtifactRef(
        sha256=_SHA, size_bytes=1, uri=f"file:///tmp/{label}.txt", mime_type="text/plain"
    )


def _row(
    i: int,
    model: str,
    task: str,
    seed: int,
    *,
    score: float | None,
    cost: str = "0.01",
    tokens_out: int = 100,
    wall_ms: int = 1000,
    status: EvalStatus = EvalStatus.SCORED,
) -> EvalRow:
    return EvalRow(
        eval_id=f"{i:016x}",
        model_id=model,
        stack_id="raw-llm",
        task_id=task,
        seed=seed,
        status=status,
        artifact_refs=EvalArtifactRefs(
            raw_output=_ref("raw"),
            normalized_output=_ref("norm"),
            evaluator_json=_ref("ev"),
        ),
        stats=EvalStats(
            input_tokens=50,
            output_tokens=tokens_out,
            wall_clock_ms=wall_ms,
            cost_usd=Decimal(cost),
        ),
        final_score=score,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def _manifest(rows: list[EvalRow]) -> Manifest:
    return Manifest(
        schema_version="pollmevals.run_manifest.v1.0.0",
        run_hash="sha256:" + "b" * 64,
        run_type=RunType.SMOKE,
        methodology_version="v0.1.0",
        created_at=datetime.now(UTC),
        published_at=datetime.now(UTC),
        stack_pins=[StackPin(stack_id="raw-llm", stack_version="0.1.0", stack_yaml_sha256=_SHA)],
        model_pins=[
            ModelPin(
                model_id="m",
                provider_id="openrouter",
                provider_route_id="r",
                pricing_snapshot=PricingSnapshot(
                    input_per_mtoken_usd=Decimal("1"),
                    output_per_mtoken_usd=Decimal("2"),
                    snapshot_at=datetime.now(UTC),
                ),
            )
        ],
        task_pins=[TaskPin(task_id="be_01_jwt_auth", task_version="1.0.0", task_pack_sha256=_SHA)],
        seed_set=[1, 2, 3],
        evals=rows,
        aggregates=RunAggregates(
            counts_by_status=CountsByStatus(
                scored=sum(1 for r in rows if r.status == EvalStatus.SCORED),
                failed=sum(1 for r in rows if r.status == EvalStatus.FAILED),
                skipped=0,
            ),
            total_cost_usd=sum((r.stats.cost_usd for r in rows), Decimal(0)),
            total_wall_clock_ms=sum(r.stats.wall_clock_ms for r in rows),
        ),
        status=RunStatus.PUBLISHED,
    )


# ---------------------------------------------------------------------------
# Unscored run — quality fields must be None, cost/latency present
# ---------------------------------------------------------------------------


class TestUnscoredRun:
    def test_quality_none_cost_present(self) -> None:
        rows = [_row(i, "claude", "be_01_jwt_auth", s, score=None) for i, s in enumerate([1, 2, 3])]
        lb = build_leaderboard(_manifest(rows))
        assert lb.scored is False
        assert len(lb.entries) == 1
        e = lb.entries[0]
        # cost/latency present
        assert e.total_cost_usd == Decimal("0.03")
        assert e.mean_latency_ms == 1000.0
        assert e.total_tokens_out == 300
        # quality fields None (not fabricated)
        assert e.mean_score is None
        assert e.pass_at_1 is None
        assert e.pass_at_k is None
        assert e.pass_hat_k is None
        assert e.flaky is None


# ---------------------------------------------------------------------------
# Scored run — pass@1 / pass@k / pass^k / flaky computed
# ---------------------------------------------------------------------------


class TestScoredRun:
    def test_all_solved(self) -> None:
        # one model, one task, 3 seeds, all score 8 (>= 6 threshold)
        rows = [_row(i, "claude", "be_01_jwt_auth", s, score=8.0) for i, s in enumerate([1, 2, 3])]
        lb = build_leaderboard(_manifest(rows))
        assert lb.scored is True
        e = lb.entries[0]
        assert e.mean_score == pytest.approx(8.0)
        assert e.pass_at_1 == pytest.approx(1.0)
        assert e.pass_at_k == pytest.approx(1.0)  # task cell [T,T,T] solved once
        assert e.pass_hat_k == pytest.approx(1.0)  # solved every seed
        assert e.flaky == pytest.approx(0.0)

    def test_flaky_task(self) -> None:
        # one task, seeds score 8/3/8 → solved T/F/T → flaky (pass@k=1, pass^k=0)
        rows = [
            _row(0, "claude", "be_01_jwt_auth", 1, score=8.0),
            _row(1, "claude", "be_01_jwt_auth", 2, score=3.0),
            _row(2, "claude", "be_01_jwt_auth", 3, score=8.0),
        ]
        lb = build_leaderboard(_manifest(rows))
        e = lb.entries[0]
        assert e.pass_at_1 == pytest.approx(2 / 3)  # 2 of 3 evals solved
        assert e.pass_at_k == pytest.approx(1.0)  # solved at least once
        assert e.pass_hat_k == pytest.approx(0.0)  # NOT solved every seed
        assert e.flaky == pytest.approx(1.0)  # the got-lucky band

    def test_never_solved(self) -> None:
        rows = [_row(i, "weak", "be_01_jwt_auth", s, score=2.0) for i, s in enumerate([1, 2, 3])]
        lb = build_leaderboard(_manifest(rows))
        e = lb.entries[0]
        assert e.pass_at_1 == pytest.approx(0.0)
        assert e.pass_at_k == pytest.approx(0.0)
        assert e.pass_hat_k == pytest.approx(0.0)

    def test_threshold_respected(self) -> None:
        rows = [_row(i, "m", "be_01_jwt_auth", s, score=5.0) for i, s in enumerate([1, 2, 3])]
        lb_low = build_leaderboard(_manifest(rows), solved_threshold=4.0)
        lb_high = build_leaderboard(_manifest(rows), solved_threshold=6.0)
        assert lb_low.entries[0].pass_at_1 == pytest.approx(1.0)  # 5 >= 4
        assert lb_high.entries[0].pass_at_1 == pytest.approx(0.0)  # 5 < 6
        assert lb_low.solved_threshold == 4.0


# ---------------------------------------------------------------------------
# Grouping, sorting, multi-model
# ---------------------------------------------------------------------------


class TestGroupingSorting:
    def test_one_entry_per_model_stack(self) -> None:
        rows = [_row(i, "a", "be_01_jwt_auth", s, score=9.0) for i, s in enumerate([1, 2, 3])] + [
            _row(i + 3, "b", "be_01_jwt_auth", s, score=4.0) for i, s in enumerate([1, 2, 3])
        ]
        lb = build_leaderboard(_manifest(rows))
        assert len(lb.entries) == 2
        assert lb.n_models == 2

    def test_sorted_by_score_desc(self) -> None:
        rows = [_row(i, "low", "be_01_jwt_auth", s, score=4.0) for i, s in enumerate([1, 2, 3])] + [
            _row(i + 3, "high", "be_01_jwt_auth", s, score=9.0) for i, s in enumerate([1, 2, 3])
        ]
        lb = build_leaderboard(_manifest(rows))
        assert [e.model_id for e in lb.entries] == ["high", "low"]

    def test_per_task_cells_for_reliability(self) -> None:
        # 2 tasks x 3 seeds; task A always solved, task B flaky
        rows = []
        for i, s in enumerate([1, 2, 3]):
            rows.append(_row(i, "m", "task_a", s, score=9.0))
        rows.append(_row(10, "m", "task_b", 1, score=9.0))
        rows.append(_row(11, "m", "task_b", 2, score=2.0))
        rows.append(_row(12, "m", "task_b", 3, score=9.0))
        lb = build_leaderboard(_manifest(rows))
        e = lb.entries[0]
        # 2 task cells: A=[T,T,T] solved-every, B=[T,F,T] flaky
        assert e.pass_at_k == pytest.approx(1.0)  # both solved at least once
        assert e.pass_hat_k == pytest.approx(0.5)  # only A solved every seed
        assert e.flaky == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Real manifest integration — load whatever real runs exist on disk
# ---------------------------------------------------------------------------


class TestRealManifest:
    def test_loads_real_run_if_present(self) -> None:
        paths = glob.glob("artifacts/runs/*/manifest.json")
        if not paths:
            pytest.skip("no real run manifests on disk")

        def _n_evals(p: str) -> int:
            with open(p, encoding="utf-8") as fh:
                return len(json.load(fh).get("evals", []))

        best = max(paths, key=_n_evals)  # the manifest with the most evals
        with open(best, encoding="utf-8") as fh:
            m = Manifest.model_validate(json.load(fh))
        lb = build_leaderboard(m)
        assert lb.run_type == "smoke"
        assert len(lb.entries) >= 1
        # every entry has cost/latency; quality may be None (unscored smoke)
        for e in lb.entries:
            assert e.n_evals >= 1
            assert e.mean_latency_ms >= 0
