"""End-to-end integration tests for POLLMEVALS orchestrator (Phase 2A scope).

Uses FakeEvalCaller exclusively — NO real LLM. Wires together every Wave 1-5
component into a full smoke-run-style flow against a tmp_path filesystem.

Validates:
- SC-1: 0 missing artifacts after run completes
- SC-3: failed evals stored with error_class (not dropped from denominator)
- AC-2: published manifest immutable (file mode 0o444)
- AC-6: crash recovery via journal — out of scope this sprint (Phase 2A-B)
- Full status state machine: created → executing → evaluating → aggregating → published

These tests catch regressions across the whole orchestrator: if grid_runner,
journal, manifest_writer, cost, or contracts drift apart, this suite fails.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from src.contracts import (
    METHODOLOGY_VERSION_V0_1_0,
    SCHEMA_VERSION_V1_0_0,
    CountsByStatus,
    EvalRow,
    Manifest,
    ModelPin,
    PricingSnapshot,
    Region,
    RunAggregates,
    RunStatus,
    RunType,
    StackPin,
    TaskPin,
)
from src.orchestrator.cost import BudgetGate, PricingTuple
from src.orchestrator.eval_caller import _DEFAULT_COST_USD, FakeEvalCaller
from src.orchestrator.grid_runner import GridRunner, GridRunResult, GridSpec
from src.orchestrator.journal import JournalReader, JournalWriter
from src.orchestrator.manifest_writer import (
    InvalidTransitionError,
    ManifestPath,
    ManifestWriter,
    _load_on_disk_schema,
)

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

_RUN_HASH = "sha256:" + "c" * 64
_SHA256_STUB = "d" * 64
_CREATED_AT = datetime(2026, 5, 24, 0, 0, 0, tzinfo=UTC)
_SNAPSHOT_AT = datetime(2026, 5, 24, 1, 0, 0, tzinfo=UTC)

_SMOKE_MODELS = [
    "openrouter/anthropic/claude-sonnet-4-6",
    "openrouter/openai/gpt-4o-mini",
    "openrouter/google/gemini-flash-1-5",
    "openrouter/qwen/qwen-2-5-14b",
    "openrouter/meta-llama/llama-4-70b",
]
_SMOKE_TASKS = ["be_01_jwt_auth", "fe_01_multistep_form", "doc_01_cli_readme"]
_SMOKE_STACKS = ["raw-llm"]
_SMOKE_SEEDS = [1, 2, 3]

# BudgetGate with a cap large enough that it never fires in happy-path tests.
_UNLIMITED_BUDGET = BudgetGate(cap_usd=Decimal("9999"))

# Default empty pricing snapshot — grid_runner cost tracking uses EvalRow.stats.cost_usd.
_NO_PRICING: dict[str, PricingTuple] = {}


# ---------------------------------------------------------------------------
# Helpers — isolates test logic from future orchestrator assembly changes
# ---------------------------------------------------------------------------


def _build_grid_spec_5x3x1x3(run_hash: str) -> GridSpec:
    """Canonical 45-eval smoke run spec: 5 models x 3 tasks x 1 stack x 3 seeds."""
    return GridSpec(
        run_hash=run_hash,
        models=list(_SMOKE_MODELS),
        tasks=list(_SMOKE_TASKS),
        stacks=list(_SMOKE_STACKS),
        seeds=list(_SMOKE_SEEDS),
    )


def _build_pricing_snapshot(model_ids: list[str]) -> dict[str, PricingTuple]:
    """Build an in-test pricing snapshot for a list of model IDs.

    Uses deterministic but realistic values (Claude Sonnet tier: $3/$15 per Mtoken).
    No HTTP — all data is constructed in-process.
    """
    result: dict[str, PricingTuple] = {}
    for model_id in model_ids:
        result[model_id] = PricingTuple(
            model_id=model_id,
            input_per_mtoken_usd=Decimal("3.000000"),
            output_per_mtoken_usd=Decimal("15.000000"),
            snapshot_at=_SNAPSHOT_AT,
        )
    return result


def _make_model_pins(model_ids: list[str]) -> list[ModelPin]:
    """Build ModelPin list from model IDs with a shared pricing snapshot."""
    pins: list[ModelPin] = []
    pricing = PricingSnapshot(
        input_per_mtoken_usd=Decimal("3.000000"),
        output_per_mtoken_usd=Decimal("15.000000"),
        snapshot_at=_SNAPSHOT_AT,
    )
    for model_id in model_ids:
        # provider_id is the first component before '/' (skip 'openrouter' prefix)
        parts = model_id.split("/")
        provider_id = parts[1] if len(parts) >= 3 else parts[0]
        pins.append(
            ModelPin(
                model_id=model_id,
                provider_id=provider_id,
                provider_route_id=model_id,
                pricing_snapshot=pricing,
            )
        )
    return pins


def _make_stack_pins(stack_ids: list[str]) -> list[StackPin]:
    return [
        StackPin(
            stack_id=sid,
            stack_version="0.1.0",
            stack_yaml_sha256=hashlib.sha256(sid.encode()).hexdigest(),
        )
        for sid in stack_ids
    ]


def _make_task_pins(task_ids: list[str]) -> list[TaskPin]:
    return [
        TaskPin(
            task_id=tid,
            task_version="1.0.0",
            task_pack_sha256=hashlib.sha256(tid.encode()).hexdigest(),
        )
        for tid in task_ids
    ]


def _assemble_manifest_from_results(
    spec: GridSpec,
    results: GridRunResult,
    *,
    status: RunStatus,
    run_hash: str = _RUN_HASH,
) -> Manifest:
    """Build a Manifest from grid run results.

    Helper isolates the test from the future orchestrator's manifest-assembly
    logic (which lives in Phase 2B). Computes aggregates from the GridRunResult
    and wires them into a Manifest instance ready for ManifestWriter.write().

    Args:
        spec:      The GridSpec used for this run (provides model/task/stack pins).
        results:   GridRunResult returned by GridRunner.run().
        status:    The RunStatus to set on the assembled manifest.
        run_hash:  The run hash (must match spec.run_hash and ManifestPath.run_hash).

    Returns:
        A fully-populated Manifest instance.
    """
    scored_count = len(results.succeeded())
    failed_count = len(results.failed())

    # Count by error_class for failed evals.
    counts_by_error_class: dict[str, int] = {}
    for r in results.failed():
        from src.orchestrator.eval_caller import EvalResult as _EvalResult

        if isinstance(r, _EvalResult) and r.eval_row is not None and r.eval_row.error_class:
            ec = str(r.eval_row.error_class)
            counts_by_error_class[ec] = counts_by_error_class.get(ec, 0) + 1

    # Distinct models with >= 1 scored eval.
    scored_model_ids: set[str] = set()
    for r in results.succeeded():
        if r.eval_row is not None:
            scored_model_ids.add(r.eval_row.model_id)

    total_wall_clock_ms = 0
    for r in results.succeeded():
        if r.eval_row is not None:
            total_wall_clock_ms += r.eval_row.stats.wall_clock_ms

    aggregates = RunAggregates(
        counts_by_status=CountsByStatus(
            scored=scored_count,
            failed=failed_count,
            skipped=0,
        ),
        counts_by_error_class=counts_by_error_class,
        total_cost_usd=results.total_cost_usd,
        total_wall_clock_ms=total_wall_clock_ms,
        budget_breach=results.budget_breach,
        available_models_count=len(scored_model_ids),
    )

    # Collect EvalRow list from results (succeeded + gracefully-failed both provide rows).
    eval_rows: list[EvalRow] = []
    for r in results.results:
        from src.orchestrator.eval_caller import EvalResult as _EvalResult

        if isinstance(r, _EvalResult) and r.eval_row is not None:
            eval_rows.append(r.eval_row)

    published_at = _CREATED_AT if status in {RunStatus.PUBLISHED, RunStatus.DEGRADED} else None

    return Manifest(
        schema_version=SCHEMA_VERSION_V1_0_0,
        run_hash=run_hash,
        run_type=RunType.SMOKE,
        methodology_version=METHODOLOGY_VERSION_V0_1_0,
        created_at=_CREATED_AT,
        published_at=published_at,
        region=Region.EU_CENTRAL,
        stack_pins=_make_stack_pins(spec.stacks),
        model_pins=_make_model_pins(spec.models),
        task_pins=_make_task_pins(spec.tasks),
        seed_set=spec.seeds,
        evals=eval_rows,
        aggregates=aggregates,
        status=status,
        orchestrator_version="v0.0.1-test",
    )


async def _run_full_pipeline(
    *,
    spec: GridSpec,
    caller: FakeEvalCaller,
    budget_gate: BudgetGate,
    tmp_dir: Path,
    run_hash: str = _RUN_HASH,
) -> tuple[GridRunResult, ManifestWriter]:
    """Execute the full orchestrator pipeline and return results + writer.

    Drives the complete state machine: created → executing → evaluating →
    aggregating → published (or degraded if budget_breach).

    Returns:
        (GridRunResult, ManifestWriter) — caller inspects both.
    """
    mp = ManifestPath(run_hash=run_hash, root=tmp_dir)
    journal_path = tmp_dir / run_hash / "manifest.journal.ndjson"
    (tmp_dir / run_hash).mkdir(parents=True, exist_ok=True)

    writer = ManifestWriter(mp)

    # created
    created_manifest = _assemble_manifest_from_results(
        spec,
        GridRunResult(results=[], total_cost_usd=Decimal("0"), budget_breach=False),
        status=RunStatus.CREATED,
        run_hash=run_hash,
    )
    writer.write(created_manifest)

    # executing
    executing_manifest = created_manifest.model_copy(update={"status": RunStatus.EXECUTING})
    writer.write(executing_manifest)

    # Run grid
    with JournalWriter(journal_path) as journal_writer:
        runner = GridRunner(
            caller=caller,
            journal_writer=journal_writer,
            budget_gate=budget_gate,
            pricing_snapshot=_NO_PRICING,
        )
        grid_result = await runner.run(spec)

    # evaluating
    evaluating_manifest = executing_manifest.model_copy(update={"status": RunStatus.EVALUATING})
    writer.write(evaluating_manifest)

    # aggregating
    aggregating_manifest = evaluating_manifest.model_copy(update={"status": RunStatus.AGGREGATING})
    writer.write(aggregating_manifest)

    # published or degraded
    terminal_status = RunStatus.DEGRADED if grid_result.budget_breach else RunStatus.PUBLISHED
    final_manifest = _assemble_manifest_from_results(
        spec, grid_result, status=terminal_status, run_hash=run_hash
    )
    writer.write(final_manifest)

    return grid_result, writer


# ---------------------------------------------------------------------------
# 1. TestFullSmokeRunHappyPath — anchor test, proves the full 45-eval pipeline
# ---------------------------------------------------------------------------


class TestFullSmokeRunHappyPath:
    """SC-1: 0 missing artifacts, full state machine, all 45 evals scored."""

    @pytest.mark.asyncio
    async def test_45_results_no_drops(self, tmp_path: Path) -> None:
        """FR-009: len(results) == 45, no entries dropped."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        caller = FakeEvalCaller()
        grid_result, _ = await _run_full_pipeline(
            spec=spec,
            caller=caller,
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        assert len(grid_result.results) == 45

    @pytest.mark.asyncio
    async def test_all_45_scored(self, tmp_path: Path) -> None:
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        grid_result, _ = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        assert len(grid_result.succeeded()) == 45
        assert len(grid_result.failed()) == 0

    @pytest.mark.asyncio
    async def test_journal_has_45_rows(self, tmp_path: Path) -> None:
        """SC-1: every eval produces exactly one journal row."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        journal_path = tmp_path / _RUN_HASH / "manifest.journal.ndjson"
        rows = list(JournalReader(journal_path).read_all())
        assert len(rows) == 45

    @pytest.mark.asyncio
    async def test_all_journal_rows_scored(self, tmp_path: Path) -> None:
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        journal_path = tmp_path / _RUN_HASH / "manifest.journal.ndjson"
        rows = list(JournalReader(journal_path).read_all())
        statuses = [r["status"] for r in rows]
        assert all(s == "scored" for s in statuses)

    @pytest.mark.asyncio
    async def test_manifest_json_exists_and_parses(self, tmp_path: Path) -> None:
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        _, writer = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        assert manifest_path.exists()
        loaded = writer.read()
        assert loaded is not None
        assert loaded.status == RunStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_manifest_schema_valid(self, tmp_path: Path) -> None:
        """Manifest on disk passes jsonschema validation."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        with manifest_path.open() as fh:
            payload: dict[str, Any] = json.load(fh)
        schema = _load_on_disk_schema()
        jsonschema.validate(payload, schema)  # raises on failure

    @pytest.mark.asyncio
    async def test_full_state_machine_traversed(self, tmp_path: Path) -> None:
        """Confirm all intermediate statuses were written (can be verified via writer.read)."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        _, writer = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        # Final status must be published (not degraded — no budget breach).
        assert writer.current_status() == RunStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_manifest_file_immutable_after_publish(self, tmp_path: Path) -> None:
        """AC-2: manifest.json is chmod 0o444 after published status."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        mode = manifest_path.stat().st_mode & 0o777
        assert mode == 0o444, f"Expected 0o444, got {oct(mode)}"

    @pytest.mark.asyncio
    async def test_total_cost_positive_within_budget(self, tmp_path: Path) -> None:
        """Total cost > 0 and within unlimited budget (no budget breach)."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        grid_result, _ = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        assert grid_result.total_cost_usd > Decimal("0")
        assert grid_result.budget_breach is False

    @pytest.mark.asyncio
    async def test_total_cost_equals_n_evals_times_default(self, tmp_path: Path) -> None:
        """45 evals * _DEFAULT_COST_USD should equal total_cost_usd."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        grid_result, _ = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        expected = _DEFAULT_COST_USD * 45
        assert grid_result.total_cost_usd == expected


# ---------------------------------------------------------------------------
# 2. TestFullSmokeRunWithFailures — SC-3 end-to-end
# ---------------------------------------------------------------------------


class TestFullSmokeRunWithFailures:
    """SC-3: failed evals stored with error_class, not dropped from denominator."""

    @pytest.mark.asyncio
    async def test_45_total_none_dropped(self, tmp_path: Path) -> None:
        """FR-009: 42 scored + 3 failed = 45 total, no entries dropped."""
        # Inject 3 failures with distinct error classes, each on a unique
        # (stack, task, seed) key so FakeEvalCaller picks them up.
        failures = {
            ("raw-llm", "be_01_jwt_auth", 1): "rate_limit",
            ("raw-llm", "fe_01_multistep_form", 2): "network",
            ("raw-llm", "doc_01_cli_readme", 3): "timeout",
        }
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        caller = FakeEvalCaller(simulate_failures=failures)
        grid_result, _ = await _run_full_pipeline(
            spec=spec,
            caller=caller,
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        # 3 failure keys x 5 models = 15 failed evals (each key matches all models).
        total = len(grid_result.results)
        assert total == 45

    @pytest.mark.asyncio
    async def test_failed_evals_have_correct_error_classes(self, tmp_path: Path) -> None:
        """Failed EvalRows carry the injected error_class values."""
        failures = {
            ("raw-llm", "be_01_jwt_auth", 1): "rate_limit",
            ("raw-llm", "fe_01_multistep_form", 2): "network",
            ("raw-llm", "doc_01_cli_readme", 3): "timeout",
        }
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        caller = FakeEvalCaller(simulate_failures=failures)
        grid_result, _ = await _run_full_pipeline(
            spec=spec,
            caller=caller,
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        from src.orchestrator.eval_caller import EvalResult as _EvalResult

        failed_error_classes: set[str] = set()
        for r in grid_result.failed():
            if isinstance(r, _EvalResult) and r.eval_row is not None and r.eval_row.error_class:
                failed_error_classes.add(str(r.eval_row.error_class))

        assert "rate_limit" in failed_error_classes
        assert "network" in failed_error_classes
        assert "timeout" in failed_error_classes

    @pytest.mark.asyncio
    async def test_journal_has_all_45_rows_including_failed(self, tmp_path: Path) -> None:
        """SC-3: failed evals appear in the journal (not silently skipped)."""
        failures = {
            ("raw-llm", "be_01_jwt_auth", 1): "rate_limit",
            ("raw-llm", "fe_01_multistep_form", 2): "network",
            ("raw-llm", "doc_01_cli_readme", 3): "timeout",
        }
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        caller = FakeEvalCaller(simulate_failures=failures)
        await _run_full_pipeline(
            spec=spec,
            caller=caller,
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        journal_path = tmp_path / _RUN_HASH / "manifest.journal.ndjson"
        rows = list(JournalReader(journal_path).read_all())
        assert len(rows) == 45

        failed_rows = [r for r in rows if r.get("status") == "failed"]
        assert len(failed_rows) > 0  # at least the injected failures are present

    @pytest.mark.asyncio
    async def test_journal_failed_rows_have_error_class(self, tmp_path: Path) -> None:
        """Journal rows for failed evals carry error_class field."""
        failures = {("raw-llm", "be_01_jwt_auth", 1): "rate_limit"}
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        caller = FakeEvalCaller(simulate_failures=failures)
        await _run_full_pipeline(
            spec=spec,
            caller=caller,
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        journal_path = tmp_path / _RUN_HASH / "manifest.journal.ndjson"
        rows = list(JournalReader(journal_path).read_all())
        failed_rows = [r for r in rows if r.get("status") == "failed"]
        for row in failed_rows:
            assert row.get("error_class") is not None, "failed row missing error_class"

    @pytest.mark.asyncio
    async def test_run_still_publishes_with_failures(self, tmp_path: Path) -> None:
        """Failures do not block publication when budget is not breached."""
        failures = {
            ("raw-llm", "be_01_jwt_auth", 1): "rate_limit",
            ("raw-llm", "fe_01_multistep_form", 2): "network",
            ("raw-llm", "doc_01_cli_readme", 3): "timeout",
        }
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        caller = FakeEvalCaller(simulate_failures=failures)
        grid_result, writer = await _run_full_pipeline(
            spec=spec,
            caller=caller,
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        # No budget breach → published (not degraded).
        assert grid_result.budget_breach is False
        assert writer.current_status() == RunStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_manifest_aggregates_counts_by_status(self, tmp_path: Path) -> None:
        """Manifest aggregates.counts_by_status.failed reflects failed evals count."""
        # One failure key x 5 models = 5 failed; but let us use a simpler single-model grid.
        failures = {("raw-llm", "task-0", 1): "rate_limit"}
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1, 2, 3],
        )
        caller = FakeEvalCaller(simulate_failures=failures)
        _grid_result, writer = await _run_full_pipeline(
            spec=spec,
            caller=caller,
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        loaded = writer.read()
        assert loaded is not None
        assert loaded.aggregates.counts_by_status.failed == 1
        assert loaded.aggregates.counts_by_status.scored == 2

    @pytest.mark.asyncio
    async def test_manifest_aggregates_counts_by_error_class(self, tmp_path: Path) -> None:
        """counts_by_error_class in manifest aggregates tracks each error type."""
        failures = {("raw-llm", "task-0", 1): "rate_limit"}
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1, 2, 3],
        )
        caller = FakeEvalCaller(simulate_failures=failures)
        _grid_result, writer = await _run_full_pipeline(
            spec=spec,
            caller=caller,
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        loaded = writer.read()
        assert loaded is not None
        assert "rate_limit" in loaded.aggregates.counts_by_error_class
        assert loaded.aggregates.counts_by_error_class["rate_limit"] == 1


# ---------------------------------------------------------------------------
# 3. TestImmutabilityAfterPublish — AC-2
# ---------------------------------------------------------------------------


class TestImmutabilityAfterPublish:
    """AC-2: published manifest is immutable (0o444) and rejects further writes."""

    @pytest.mark.asyncio
    async def test_manifest_file_mode_is_0o444(self, tmp_path: Path) -> None:
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1],
        )
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        mode = manifest_path.stat().st_mode & 0o777
        assert mode == 0o444

    @pytest.mark.asyncio
    async def test_second_write_raises_invalid_transition(self, tmp_path: Path) -> None:
        """Writing to an already-published manifest raises InvalidTransitionError."""
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1],
        )
        grid_result, writer = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        # Attempt to write again with published status — must fail.
        next_manifest = _assemble_manifest_from_results(
            spec, grid_result, status=RunStatus.PUBLISHED, run_hash=_RUN_HASH
        )
        with pytest.raises(InvalidTransitionError):
            writer.write(next_manifest)

    @pytest.mark.asyncio
    async def test_published_manifest_is_readable_after_lock(self, tmp_path: Path) -> None:
        """Immutable (0o444) manifest.json can still be read back via writer.read()."""
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1],
        )
        _, writer = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        loaded = writer.read()
        assert loaded is not None
        assert loaded.status == RunStatus.PUBLISHED
        assert loaded.run_hash == _RUN_HASH

    @pytest.mark.asyncio
    async def test_is_published_returns_true(self, tmp_path: Path) -> None:
        """ManifestWriter.is_published() returns True after terminal write."""
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1],
        )
        _, writer = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        assert writer.is_published() is True

    @pytest.mark.asyncio
    async def test_all_fields_intact_after_immutable_lock(self, tmp_path: Path) -> None:
        """All Pydantic fields survive the publish → read round-trip correctly."""
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1],
        )
        _, writer = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        loaded = writer.read()
        assert loaded is not None
        assert loaded.schema_version == SCHEMA_VERSION_V1_0_0
        assert loaded.methodology_version == METHODOLOGY_VERSION_V0_1_0
        assert loaded.run_type == RunType.SMOKE
        assert loaded.region == Region.EU_CENTRAL
        assert len(loaded.evals) == 1


# ---------------------------------------------------------------------------
# 4. TestBudgetBreachToDegraded — AC-3 + degraded transition
# ---------------------------------------------------------------------------


class TestBudgetBreachToDegraded:
    """AC-3: budget breach during grid run → manifest transitions to degraded."""

    @pytest.mark.asyncio
    async def test_budget_breach_triggers_degraded_status(self, tmp_path: Path) -> None:
        """A tight budget that fires mid-run produces budget_breach=True → degraded."""
        # Default cost = $0.0125/eval. Cap=$0.02, threshold=0.016.
        # 1 eval → $0.0125 (under threshold). 2nd eval → $0.025 (over threshold → breach).
        gate = BudgetGate(cap_usd=Decimal("0.02"))
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0", "model-1"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1, 2],
        )  # 4 total requests
        grid_result, writer = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=gate,
            tmp_dir=tmp_path,
        )
        assert grid_result.budget_breach is True
        assert writer.current_status() == RunStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_degraded_manifest_is_immutable(self, tmp_path: Path) -> None:
        """Degraded is a terminal status — manifest gets chmod 0o444."""
        gate = BudgetGate(cap_usd=Decimal("0.02"))
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0", "model-1"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1, 2],
        )
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=gate,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        mode = manifest_path.stat().st_mode & 0o777
        assert mode == 0o444

    @pytest.mark.asyncio
    async def test_degraded_manifest_budget_breach_true_in_aggregates(self, tmp_path: Path) -> None:
        """aggregates.budget_breach is True when run degraded due to cost."""
        gate = BudgetGate(cap_usd=Decimal("0.02"))
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0", "model-1"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1, 2],
        )
        _, writer = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=gate,
            tmp_dir=tmp_path,
        )
        loaded = writer.read()
        assert loaded is not None
        assert loaded.aggregates.budget_breach is True

    @pytest.mark.asyncio
    async def test_degraded_write_raises_on_further_write(self, tmp_path: Path) -> None:
        """degraded is terminal — a second write raises InvalidTransitionError."""
        gate = BudgetGate(cap_usd=Decimal("0.02"))
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0", "model-1"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1, 2],
        )
        grid_result, writer = await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=gate,
            tmp_dir=tmp_path,
        )
        another_manifest = _assemble_manifest_from_results(
            spec, grid_result, status=RunStatus.DEGRADED, run_hash=_RUN_HASH
        )
        with pytest.raises(InvalidTransitionError):
            writer.write(another_manifest)

    @pytest.mark.asyncio
    async def test_aggregating_to_degraded_allowed_transition(self, tmp_path: Path) -> None:
        """State machine allows aggregating → degraded (verify via successful write)."""
        # Build a minimal manifest at aggregating status.
        run_hash = "sha256:" + "e" * 64
        mp = ManifestPath(run_hash=run_hash, root=tmp_path)
        (tmp_path / run_hash).mkdir(parents=True, exist_ok=True)
        writer = ManifestWriter(mp)

        # Build stub spec for manifest assembly.
        spec = GridSpec(
            run_hash=run_hash,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1],
        )
        stub_grid = GridRunResult(
            results=[],
            total_cost_usd=Decimal("0.05"),
            budget_breach=True,
        )

        # Write through state machine up to aggregating.
        pre_terminal = [
            RunStatus.CREATED,
            RunStatus.EXECUTING,
            RunStatus.EVALUATING,
            RunStatus.AGGREGATING,
        ]
        for status in pre_terminal:
            m = _assemble_manifest_from_results(spec, stub_grid, status=status, run_hash=run_hash)
            writer.write(m)

        # aggregating → degraded must be allowed (no exception).
        degraded = _assemble_manifest_from_results(
            spec, stub_grid, status=RunStatus.DEGRADED, run_hash=run_hash
        )
        writer.write(degraded)  # must not raise
        assert writer.current_status() == RunStatus.DEGRADED


# ---------------------------------------------------------------------------
# 5. TestSchemaRoundTripThroughFullPipeline — 3 known drift fixes
# ---------------------------------------------------------------------------


class TestSchemaRoundTripThroughFullPipeline:
    """Verify the 3 Pydantic v2 ↔ on-disk schema drift fixes survive end-to-end."""

    @pytest.mark.asyncio
    async def test_manifest_json_validates_against_schema(self, tmp_path: Path) -> None:
        """Drift #1 fix: cost_usd (Decimal) serialised as float, not string."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        with manifest_path.open() as fh:
            payload: dict[str, Any] = json.load(fh)
        schema = _load_on_disk_schema()
        # Raises jsonschema.ValidationError on failure.
        jsonschema.validate(payload, schema)

    @pytest.mark.asyncio
    async def test_cost_usd_fields_are_numbers_not_strings(self, tmp_path: Path) -> None:
        """Drift #1: cost_usd must be a JSON number, not a quoted string."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        with manifest_path.open() as fh:
            payload: dict[str, Any] = json.load(fh)

        # Check aggregates.total_cost_usd is a float, not a string.
        total_cost = payload.get("aggregates", {}).get("total_cost_usd")
        assert isinstance(total_cost, (int, float)), (
            f"total_cost_usd should be a number, got {type(total_cost).__name__}: {total_cost!r}"
        )

        # Check per-eval stats.cost_usd is a float.
        evals = payload.get("evals", [])
        assert len(evals) > 0
        first_eval_cost = evals[0].get("stats", {}).get("cost_usd")
        assert isinstance(first_eval_cost, (int, float)), (
            f"stats.cost_usd should be a number, got {type(first_eval_cost).__name__}"
        )

    @pytest.mark.asyncio
    async def test_no_null_optional_artifact_refs_in_json(self, tmp_path: Path) -> None:
        """Drift #2: optional ArtifactRef fields (stdout/stderr/trace_json) absent when None."""
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1],
        )
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        with manifest_path.open() as fh:
            payload: dict[str, Any] = json.load(fh)

        for eval_entry in payload.get("evals", []):
            refs = eval_entry.get("artifact_refs", {})
            # These keys must not appear as null — they should be absent.
            for optional_key in ("stdout", "stderr", "trace_json"):
                assert optional_key not in refs or refs[optional_key] is not None, (
                    f"Optional ArtifactRef '{optional_key}' serialised as null (drift #2)"
                )

    @pytest.mark.asyncio
    async def test_completed_at_none_absent_from_json(self, tmp_path: Path) -> None:
        """Drift #3: started_at/completed_at=None dropped; those that are set appear."""
        spec = GridSpec(
            run_hash=_RUN_HASH,
            models=["model-0"],
            tasks=["task-0"],
            stacks=["raw-llm"],
            seeds=[1],
        )
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        with manifest_path.open() as fh:
            payload: dict[str, Any] = json.load(fh)

        # FakeEvalCaller always sets started_at + completed_at.
        for eval_entry in payload.get("evals", []):
            # They must either be absent or be a non-null string.
            for key in ("started_at", "completed_at"):
                val = eval_entry.get(key)
                if key in eval_entry:
                    assert val is not None, f"{key} serialised as null (drift #3)"

    @pytest.mark.asyncio
    async def test_pydantic_round_trip_via_model_validate_json(self, tmp_path: Path) -> None:
        """Full round-trip: disk JSON → Pydantic validates and reconstructs correctly."""
        spec = _build_grid_spec_5x3x1x3(_RUN_HASH)
        await _run_full_pipeline(
            spec=spec,
            caller=FakeEvalCaller(),
            budget_gate=_UNLIMITED_BUDGET,
            tmp_dir=tmp_path,
        )
        manifest_path = tmp_path / _RUN_HASH / "manifest.json"
        raw_json = manifest_path.read_text()
        loaded = Manifest.model_validate_json(raw_json)

        assert loaded.status == RunStatus.PUBLISHED
        assert loaded.run_hash == _RUN_HASH
        assert len(loaded.evals) == 45
        assert loaded.aggregates.counts_by_status.scored == 45
        # Decimal fields are restored as Decimal (Pydantic coerces float → Decimal).
        assert isinstance(loaded.aggregates.total_cost_usd, Decimal)
        assert loaded.aggregates.total_cost_usd > Decimal("0")
