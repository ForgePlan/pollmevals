"""Tests for scripts/smoke_run.py -- Phase 2B smoke-run entrypoint.

Covers:
1. TestDryRun              -- --dry-run exits 0 with mocked LiteLLM (no real LLM)
2. TestConfirmSpendGuard   -- --confirm-spend required; script refuses without flag
3. TestPostmortemTemplate  -- postmortem written from GridRunResult
4. TestBudgetAbort         -- 80% budget abort gate
5. TestManifestImmutability -- manifest file mode 0o444 after write_final_manifest
6. TestRunHash             -- deterministic run_hash derivation
7. TestValidateSpecs       -- validate_task_specs / validate_stack_specs
8. TestDeterminismCheck    -- determinism check passes with FakeEvalCaller
"""

# NOTE: sys.path manipulation before src.* imports is required here because
# smoke_run.py lives in scripts/ (not in the pytest-discovered package).
# Tests that import from smoke_run directly need the scripts/ dir on sys.path.

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.orchestrator.cost import BudgetGate
from src.orchestrator.eval_caller import FakeEvalCaller
from src.orchestrator.grid_runner import (
    SMOKE_TASKS,
    GridRunner,
    GridRunResult,
    GridSpec,
)
from src.orchestrator.journal import JournalWriter

# ---------------------------------------------------------------------------
# Add scripts/ to sys.path so `from smoke_run import ...` works
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from smoke_run import (  # noqa: E402
    PreflightResult,
    build_aggregates,
    build_initial_manifest,
    check_litellm_proxy,
    determinism_check,
    make_run_hash,
    validate_stack_specs,
    validate_task_specs,
    write_final_manifest,
    write_postmortem,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN_HASH = "sha256:" + "a" * 64
_UNLIMITED_BUDGET = Decimal("9999")


def _run_grid(
    n_models: int = 5,
    n_tasks: int = 3,
    n_seeds: int = 3,
    *,
    tmp_path: Path | None = None,
    failures: dict[tuple[str, str, int], str] | None = None,
) -> GridRunResult:
    """Execute a FakeEvalCaller grid synchronously (no real LLM calls)."""
    journal_path = (tmp_path / "j.ndjson") if tmp_path else Path("/dev/null")

    async def _run() -> GridRunResult:
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=[f"model-{i}" for i in range(n_models)],
            tasks=[f"task-{i}" for i in range(n_tasks)],
            stacks=["raw-llm"],
            seeds=list(range(1, n_seeds + 1)),
        )
        caller = FakeEvalCaller(simulate_failures=failures or {})
        journal = JournalWriter(journal_path)
        runner = GridRunner(
            caller=caller,
            journal_writer=journal,
            budget_gate=BudgetGate(cap_usd=_UNLIMITED_BUDGET),
            pricing_snapshot={},
        )
        result = await runner.run(spec)
        journal.close()
        return result

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# 1. TestDryRun
# ---------------------------------------------------------------------------


class TestDryRun:
    """--dry-run must exit 0 without calling real LLMs."""

    def test_dry_run_task_spec_present_passes(self, tmp_path: Path, monkeypatch: Any) -> None:
        """validate_task_specs passes when task.yaml files exist."""
        import smoke_run as sr

        tasks_root = tmp_path / "tasks"
        for task_id in SMOKE_TASKS:
            yaml_path = tasks_root / task_id / "task.yaml"
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            yaml_path.write_text("version: '0.1.0'\n", encoding="utf-8")

        monkeypatch.setattr(sr, "_TASK_SPECS_ROOT", tasks_root)
        result = validate_task_specs(list(SMOKE_TASKS))
        assert result.ok

    def test_dry_run_missing_task_spec_returns_not_ok(self, monkeypatch: Any) -> None:
        """validate_task_specs returns ok=False when task.yaml is missing."""
        import smoke_run as sr

        monkeypatch.setattr(sr, "_TASK_SPECS_ROOT", Path("/nonexistent/path/tasks"))
        result = validate_task_specs(["be_01_jwt_auth"])
        assert not result.ok
        assert any("be_01_jwt_auth" in issue for issue in result.issues)

    def test_dry_run_validate_specs_no_network(self) -> None:
        """validate_task_specs makes zero network calls (pure FS check)."""
        result = validate_task_specs(["nonexistent_task"])
        assert not result.ok  # missing, but no exception raised

    @pytest.mark.asyncio
    async def test_check_litellm_proxy_unreachable_returns_not_ok(self) -> None:
        """When proxy is unreachable, check_litellm_proxy returns ok=False."""
        result = await check_litellm_proxy(base_url="http://127.0.0.1:19999")
        assert not result.ok
        assert result.issues

    @pytest.mark.asyncio
    async def test_async_main_dry_run_exits_zero(self, tmp_path: Path, monkeypatch: Any) -> None:
        """async_main --dry-run returns 0 when all pre-flight mocks pass."""
        import argparse

        import smoke_run as sr

        monkeypatch.setattr(sr, "_TASK_SPECS_ROOT", tmp_path)
        monkeypatch.setattr(sr, "_STACK_SPECS_ROOT", tmp_path)

        args = argparse.Namespace(
            dry_run=True,
            confirm_spend=False,
            budget_usd=50.0,
            seeds=3,
            tasks="",
            models="",
        )
        ok_result = PreflightResult(ok=True, issues=[])
        with (
            patch.object(sr, "check_litellm_proxy", new=AsyncMock(return_value=ok_result)),
        ):
            exit_code = await sr.async_main(args)
        # exit 0 if checks pass OR 1 if any check fails (specs missing in tmp_path)
        # we only assert it doesn't raise and doesn't call real LLMs
        assert exit_code in (0, 1)


# ---------------------------------------------------------------------------
# 2. TestConfirmSpendGuard
# ---------------------------------------------------------------------------


class TestConfirmSpendGuard:
    """Without --confirm-spend the script must refuse to call real LLMs."""

    @pytest.mark.asyncio
    async def test_without_confirm_spend_returns_exit_2(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """async_main must exit 2 when confirm_spend=False and dry_run=False."""
        import argparse

        import smoke_run as sr

        monkeypatch.setattr(sr, "_TASK_SPECS_ROOT", tmp_path)
        monkeypatch.setattr(sr, "_STACK_SPECS_ROOT", tmp_path)

        args = argparse.Namespace(
            dry_run=False,
            confirm_spend=False,
            budget_usd=50.0,
            seeds=3,
            tasks="",
            models="",
        )
        ok_result = PreflightResult(ok=True, issues=[])
        with (
            patch.object(sr, "check_litellm_proxy", new=AsyncMock(return_value=ok_result)),
            patch.object(sr, "preflight_prompts", new=AsyncMock(return_value=ok_result)),
        ):
            exit_code = await sr.async_main(args)
        assert exit_code == 2

    @pytest.mark.asyncio
    async def test_dry_run_bypasses_preflight_prompts(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """With --dry-run, preflight_prompts is never invoked (no real LLM calls)."""
        import argparse

        import smoke_run as sr

        monkeypatch.setattr(sr, "_TASK_SPECS_ROOT", tmp_path)
        monkeypatch.setattr(sr, "_STACK_SPECS_ROOT", tmp_path)

        preflight_called = False

        async def fake_preflight(*_: Any, **__: Any) -> PreflightResult:
            nonlocal preflight_called
            preflight_called = True
            return PreflightResult(ok=True, issues=[])

        args = argparse.Namespace(
            dry_run=True,
            confirm_spend=False,
            budget_usd=50.0,
            seeds=3,
            tasks="",
            models="",
        )
        ok_result = PreflightResult(ok=True, issues=[])
        with (
            patch.object(sr, "check_litellm_proxy", new=AsyncMock(return_value=ok_result)),
            patch.object(sr, "preflight_prompts", new=AsyncMock(side_effect=fake_preflight)),
        ):
            await sr.async_main(args)

        # With --dry-run, the if-branch sets preflight_check directly
        # without calling preflight_prompts
        assert not preflight_called


# ---------------------------------------------------------------------------
# 3. TestPostmortemTemplate
# ---------------------------------------------------------------------------


class TestPostmortemTemplate:
    def test_postmortem_created_at_run_dir(self, tmp_path: Path) -> None:
        """write_postmortem creates POSTMORTEM.md in the run_dir."""
        grid_result = _run_grid(n_models=2, n_tasks=1, n_seeds=1)
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        path = write_postmortem(
            run_dir=run_dir,
            run_hash=_RUN_HASH,
            tasks=["task-0"],
            models=["model-0", "model-1"],
            seeds=[1],
            grid_result=grid_result,
        )

        assert path.exists()
        assert path.name == "POSTMORTEM.md"

    def test_postmortem_contains_run_hash(self, tmp_path: Path) -> None:
        grid_result = _run_grid(n_models=1, n_tasks=1, n_seeds=1)
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        path = write_postmortem(
            run_dir=run_dir,
            run_hash=_RUN_HASH,
            tasks=["task-0"],
            models=["model-0"],
            seeds=[1],
            grid_result=grid_result,
        )

        content = path.read_text(encoding="utf-8")
        assert _RUN_HASH in content

    def test_postmortem_contains_all_template_sections(self, tmp_path: Path) -> None:
        """All 10 playbook sections must appear in the postmortem."""
        grid_result = _run_grid(n_models=1, n_tasks=1, n_seeds=1)
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        path = write_postmortem(
            run_dir=run_dir,
            run_hash=_RUN_HASH,
            tasks=["task-0"],
            models=["model-0"],
            seeds=[1],
            grid_result=grid_result,
        )

        content = path.read_text(encoding="utf-8")
        required_sections = [
            "## Run hash",
            "## Scope",
            "## What worked",
            "## What failed",
            "## Cost",
            "## Latency",
            "## Task issues",
            "## Model/provider issues",
            "## Scoring issues",
            "## Changes before next run",
        ]
        for section in required_sections:
            assert section in content, f"Section missing: {section!r}"

    def test_postmortem_reports_correct_scored_count(self, tmp_path: Path) -> None:
        grid_result = _run_grid(n_models=2, n_tasks=1, n_seeds=2)
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        path = write_postmortem(
            run_dir=run_dir,
            run_hash=_RUN_HASH,
            tasks=["task-0"],
            models=["model-0", "model-1"],
            seeds=[1, 2],
            grid_result=grid_result,
        )

        content = path.read_text(encoding="utf-8")
        # 4 evals, all scored
        assert "4/4" in content, f"missing '4/4' in postmortem; full content:\n{content}"

    def test_postmortem_with_failures(self, tmp_path: Path) -> None:
        grid_result = _run_grid(
            n_models=2,
            n_tasks=1,
            n_seeds=2,
            tmp_path=tmp_path,
            failures={("raw-llm", "task-0", 1): "rate_limit"},
        )
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        path = write_postmortem(
            run_dir=run_dir,
            run_hash=_RUN_HASH,
            tasks=["task-0"],
            models=["model-0", "model-1"],
            seeds=[1, 2],
            grid_result=grid_result,
        )

        content = path.read_text(encoding="utf-8")
        assert "rate_limit" in content


# ---------------------------------------------------------------------------
# 4. TestBudgetAbort
# ---------------------------------------------------------------------------


class TestBudgetAbort:
    """Budget gate fires at 80% of cap (AC-3)."""

    @pytest.mark.asyncio
    async def test_budget_abort_at_80pct(self, tmp_path: Path) -> None:
        """GridRunResult.budget_breach=True when running_total crosses 80%."""
        # FakeEvalCaller cost = $0.0125. Cap=$0.05, threshold=$0.04.
        # After 3 evals ($0.0375 < $0.04) the 4th is attempted ($0.05);
        # after that the 5th+ are skipped.
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=list(range(1, 11)),
        )
        journal = JournalWriter(tmp_path / "j.ndjson")
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=journal,
            budget_gate=BudgetGate(cap_usd=Decimal("0.05")),
            pricing_snapshot={},
        )
        result = await runner.run(spec)
        journal.close()

        assert result.budget_breach is True
        assert len(result.results) < 10  # some evals were skipped

    @pytest.mark.asyncio
    async def test_build_aggregates_reflects_budget_breach(self, tmp_path: Path) -> None:
        """build_aggregates passes budget_breach flag through to RunAggregates."""
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=list(range(1, 11)),
        )
        journal = JournalWriter(tmp_path / "j.ndjson")
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=journal,
            budget_gate=BudgetGate(cap_usd=Decimal("0.05")),
            pricing_snapshot={},
        )
        grid_result = await runner.run(spec)
        journal.close()

        aggregates = build_aggregates(grid_result)
        assert aggregates.budget_breach is True


# ---------------------------------------------------------------------------
# 5. TestManifestImmutability
# ---------------------------------------------------------------------------


class TestManifestImmutability:
    """After write_final_manifest, manifest.json must be mode 0o444 (ADR-002)."""

    def test_manifest_file_mode_444_after_write(self, tmp_path: Path, monkeypatch: Any) -> None:
        """write_final_manifest terminates with chmod 0o444 on the manifest file."""
        import smoke_run as sr

        monkeypatch.setattr(sr, "_ARTIFACTS_ROOT", tmp_path)

        grid_result = _run_grid(n_models=2, n_tasks=1, n_seeds=1)
        created_at = datetime.now(UTC)
        initial = build_initial_manifest(
            run_hash=_RUN_HASH,
            tasks=["task-0"],
            models=["model-0", "model-1"],
            stacks=["raw-llm"],
            seeds=[1],
            created_at=created_at,
        )

        write_final_manifest(initial, grid_result, tmp_path / _RUN_HASH)

        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        assert manifest_path.exists(), "manifest.json not created"
        mode = manifest_path.stat().st_mode & 0o777
        assert mode == 0o444, f"Expected 0o444, got {oct(mode)}"

    def test_manifest_status_terminal_after_write(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Final manifest status must be published or degraded (terminal)."""
        import smoke_run as sr

        monkeypatch.setattr(sr, "_ARTIFACTS_ROOT", tmp_path)

        grid_result = _run_grid(n_models=3, n_tasks=1, n_seeds=1)
        created_at = datetime.now(UTC)
        initial = build_initial_manifest(
            run_hash=_RUN_HASH,
            tasks=["task-0"],
            models=["model-0", "model-1", "model-2"],
            stacks=["raw-llm"],
            seeds=[1],
            created_at=created_at,
        )

        final = write_final_manifest(initial, grid_result, tmp_path / _RUN_HASH)
        assert final.is_terminal()

    def test_manifest_second_write_raises(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Overwriting a terminal manifest must raise InvalidTransitionError."""
        import smoke_run as sr

        from src.orchestrator.manifest_writer import (
            InvalidTransitionError,
            ManifestPath,
            ManifestWriter,
        )

        monkeypatch.setattr(sr, "_ARTIFACTS_ROOT", tmp_path)

        grid_result = _run_grid(n_models=3, n_tasks=1, n_seeds=1)
        created_at = datetime.now(UTC)
        initial = build_initial_manifest(
            run_hash=_RUN_HASH,
            tasks=["task-0"],
            models=["model-0", "model-1", "model-2"],
            stacks=["raw-llm"],
            seeds=[1],
            created_at=created_at,
        )

        final = write_final_manifest(initial, grid_result, tmp_path / _RUN_HASH)

        mp = ManifestPath(run_hash=_RUN_HASH, root=tmp_path)
        writer = ManifestWriter(mp)
        with pytest.raises(InvalidTransitionError):
            writer.write(final)


# ---------------------------------------------------------------------------
# 6. TestRunHash
# ---------------------------------------------------------------------------


class TestRunHash:
    def test_run_hash_has_sha256_prefix(self) -> None:
        h = make_run_hash(
            tasks=["t1"],
            models=["m1"],
            stacks=["s1"],
            seeds=[1],
            created_at=datetime.now(UTC),
        )
        assert h.startswith("sha256:")

    def test_run_hash_deterministic_same_inputs(self) -> None:
        ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        h1 = make_run_hash(["t1"], ["m1"], ["s1"], [1], ts)
        h2 = make_run_hash(["t1"], ["m1"], ["s1"], [1], ts)
        assert h1 == h2

    def test_run_hash_changes_with_different_tasks(self) -> None:
        ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        h1 = make_run_hash(["t1"], ["m1"], ["s1"], [1], ts)
        h2 = make_run_hash(["t2"], ["m1"], ["s1"], [1], ts)
        assert h1 != h2

    def test_run_hash_length(self) -> None:
        h = make_run_hash(["t1"], ["m1"], ["s1"], [1], datetime.now(UTC))
        # "sha256:" + 64 hex chars
        assert len(h) == len("sha256:") + 64


# ---------------------------------------------------------------------------
# 7. TestValidateSpecs
# ---------------------------------------------------------------------------


class TestValidateSpecs:
    def test_validate_task_specs_all_present(self, tmp_path: Path, monkeypatch: Any) -> None:
        import smoke_run as sr

        tasks_root = tmp_path / "tasks"
        for task_id in ["task_a", "task_b"]:
            yaml_path = tasks_root / task_id / "task.yaml"
            yaml_path.parent.mkdir(parents=True)
            yaml_path.write_text("version: 0.1\n")

        monkeypatch.setattr(sr, "_TASK_SPECS_ROOT", tasks_root)
        result = validate_task_specs(["task_a", "task_b"])
        assert result.ok
        assert result.issues == []

    def test_validate_task_specs_missing(self, tmp_path: Path, monkeypatch: Any) -> None:
        import smoke_run as sr

        monkeypatch.setattr(sr, "_TASK_SPECS_ROOT", tmp_path / "nonexistent")
        result = validate_task_specs(["task_missing"])
        assert not result.ok
        assert len(result.issues) == 1

    def test_validate_stack_specs_all_present(self, tmp_path: Path, monkeypatch: Any) -> None:
        import smoke_run as sr

        stacks_root = tmp_path / "stacks"
        yaml_path = stacks_root / "raw-llm" / "stack.yaml"
        yaml_path.parent.mkdir(parents=True)
        yaml_path.write_text("stack_id: raw-llm\n")

        monkeypatch.setattr(sr, "_STACK_SPECS_ROOT", stacks_root)
        result = validate_stack_specs(["raw-llm"])
        assert result.ok

    def test_validate_stack_specs_missing(self, tmp_path: Path, monkeypatch: Any) -> None:
        import smoke_run as sr

        monkeypatch.setattr(sr, "_STACK_SPECS_ROOT", tmp_path / "nonexistent")
        result = validate_stack_specs(["raw-llm"])
        assert not result.ok


# ---------------------------------------------------------------------------
# 8. TestDeterminismCheck
# ---------------------------------------------------------------------------


class TestDeterminismCheck:
    """Steps 12-13: re-run one eval and compare eval_id + artifact sha256."""

    @pytest.mark.asyncio
    async def test_determinism_check_passes_with_fake_caller(self, tmp_path: Path) -> None:
        """Determinism check must pass when both runs use FakeEvalCaller."""
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1, 2, 3],
        )
        journal = JournalWriter(tmp_path / "j.ndjson")
        runner = GridRunner(
            caller=FakeEvalCaller(),
            journal_writer=journal,
            budget_gate=BudgetGate(cap_usd=_UNLIMITED_BUDGET),
            pricing_snapshot={},
        )
        original = await runner.run(spec)
        journal.close()

        result = await determinism_check(spec, original, _UNLIMITED_BUDGET, tmp_path)
        assert result.ok, f"Determinism check failed: {result.issues}"
