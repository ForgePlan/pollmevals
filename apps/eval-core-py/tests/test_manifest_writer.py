"""Tests for ManifestWriter — state machine, schema drift, atomicity, immutability.

Covers:
  1. TestStateMachine          — all allowed/disallowed status transitions
  2. TestSchemaValidation      — valid write passes; tampered payload raises
  3. TestSchemaDriftFixes      — the 3 known Pydantic v2 ↔ on-disk schema drifts
  4. TestAtomicWrite           — .tmp cleanup on failure; no leftover on success
  5. TestImmutability          — chmod 0o444 on terminal; second write raises
  6. TestReadRoundTrip         — write then read produces equivalent Manifest
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

import jsonschema
import pytest

from src.contracts import (
    METHODOLOGY_VERSION_V0_1_0,
    SCHEMA_VERSION_V1_0_0,
    ArtifactRef,
    CountsByStatus,
    ErrorClass,
    EvalArtifactRefs,
    EvalRow,
    EvalStats,
    EvalStatus,
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
from src.orchestrator.manifest_writer import (
    InvalidTransitionError,
    ManifestPath,
    ManifestWriter,
    SchemaValidationError,
    _coerce_decimal_strings_to_numbers,
    _to_disk_format,
)

# ---------------------------------------------------------------------------
# Shared constants (mirrors test_contracts.py for isolation)
# ---------------------------------------------------------------------------

_SHA256_A = "a" * 64
_SHA256_B = "b" * 64
_SHA256_C = "c" * 64
_EVAL_ID = "a" * 16
_CREATED_AT = datetime(2026, 5, 23, 0, 0, 0, tzinfo=UTC)
_SNAPSHOT_AT = datetime(2026, 5, 23, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helper factories (duplicated for test isolation — no cross-module dep)
# ---------------------------------------------------------------------------


def _pricing() -> PricingSnapshot:
    return PricingSnapshot(
        input_per_mtoken_usd=Decimal("3.000"),
        output_per_mtoken_usd=Decimal("15.000"),
        snapshot_at=_SNAPSHOT_AT,
    )


def _artifact_ref(sha: str = _SHA256_A) -> ArtifactRef:
    return ArtifactRef(
        sha256=sha,
        size_bytes=128,
        uri=f"file://artifacts/runs/sha256:{_SHA256_A}/evals/{_EVAL_ID}/raw_output-{sha}.txt",
        mime_type="text/plain",
    )


def _eval_artifact_refs(
    *,
    include_optional: bool = False,
    stdout: ArtifactRef | None = None,
    stderr: ArtifactRef | None = None,
    trace_json: ArtifactRef | None = None,
) -> EvalArtifactRefs:
    optional_kwargs: dict[str, Any] = {}
    if include_optional:
        ref_c = ArtifactRef(
            sha256=_SHA256_C,
            size_bytes=32,
            uri=f"file://artifacts/runs/sha256:{_SHA256_A}/evals/{_EVAL_ID}/stdout-{_SHA256_C}.txt",
            mime_type="text/plain",
        )
        optional_kwargs = {"stdout": ref_c, "stderr": ref_c, "trace_json": ref_c}
    elif stdout is not None or stderr is not None or trace_json is not None:
        optional_kwargs = {}
        if stdout is not None:
            optional_kwargs["stdout"] = stdout
        if stderr is not None:
            optional_kwargs["stderr"] = stderr
        if trace_json is not None:
            optional_kwargs["trace_json"] = trace_json

    return EvalArtifactRefs(
        raw_output=_artifact_ref(_SHA256_A),
        normalized_output=_artifact_ref(_SHA256_B),
        evaluator_json=ArtifactRef(
            sha256=_SHA256_B,
            size_bytes=64,
            uri=f"file://artifacts/runs/sha256:{_SHA256_A}/evals/{_EVAL_ID}/evaluator-{_SHA256_B}.json",
            mime_type="application/json",
        ),
        **optional_kwargs,
    )


def _eval_stats(cost_usd: Decimal = Decimal("0.001")) -> EvalStats:
    return EvalStats(
        input_tokens=512,
        output_tokens=256,
        wall_clock_ms=3000,
        cost_usd=cost_usd,
    )


def _eval_row(
    *,
    status: EvalStatus = EvalStatus.SCORED,
    error_class: ErrorClass | None = None,
    started_at: datetime | None = _CREATED_AT,
    completed_at: datetime | None = _SNAPSHOT_AT,
    include_optional_refs: bool = False,
    cost_usd: Decimal = Decimal("0.001"),
) -> EvalRow:
    return EvalRow(
        eval_id=_EVAL_ID,
        model_id="claude-sonnet-4-6",
        stack_id="raw-llm",
        task_id="be_01_jwt_auth",
        seed=42,
        status=status,
        error_class=error_class,
        artifact_refs=_eval_artifact_refs(include_optional=include_optional_refs),
        stats=_eval_stats(cost_usd=cost_usd),
        started_at=started_at,
        completed_at=completed_at,
    )


def _aggregates(
    scored: int = 1, failed: int = 0, cost: Decimal = Decimal("0.001")
) -> RunAggregates:
    return RunAggregates(
        counts_by_status=CountsByStatus(scored=scored, failed=failed, skipped=0),
        total_cost_usd=cost,
        total_wall_clock_ms=3000,
    )


def make_manifest(**overrides: Any) -> Manifest:
    """Build a valid Manifest with sensible defaults. Pass overrides for edge cases."""
    defaults: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION_V1_0_0,
        "run_hash": f"sha256:{_SHA256_A}",
        "run_type": RunType.SMOKE,
        "methodology_version": METHODOLOGY_VERSION_V0_1_0,
        "created_at": _CREATED_AT,
        "published_at": None,
        "region": Region.EU_CENTRAL,
        "stack_pins": [
            StackPin(stack_id="raw-llm", stack_version="0.1.0", stack_yaml_sha256=_SHA256_A)
        ],
        "model_pins": [
            ModelPin(
                model_id="claude-sonnet-4-6",
                provider_id="anthropic",
                provider_route_id="openrouter/anthropic/claude-sonnet-4-6",
                pricing_snapshot=_pricing(),
            )
        ],
        "task_pins": [
            TaskPin(task_id="be_01_jwt_auth", task_version="1.0.0", task_pack_sha256=_SHA256_B)
        ],
        "seed_set": [42, 43, 44],
        "evals": [_eval_row()],
        "aggregates": _aggregates(),
        "status": RunStatus.CREATED,
        "inspect_ai_version": "0.3.46",
        "orchestrator_version": "v0.0.1",
    }
    return Manifest(**{**defaults, **overrides})


@pytest.fixture
def mp(tmp_path: Path) -> ManifestPath:
    """ManifestPath rooted in a pytest tmp_path."""
    return ManifestPath(run_hash=f"sha256:{_SHA256_A}", root=tmp_path)


@pytest.fixture
def writer(mp: ManifestPath) -> ManifestWriter:
    return ManifestWriter(mp)


# ---------------------------------------------------------------------------
# 1. TestStateMachine
# ---------------------------------------------------------------------------


class TestStateMachine:
    """State machine transitions: allowed edges pass, all others raise."""

    @pytest.mark.parametrize(
        "from_status,to_status,should_pass",
        [
            # --- Allowed transitions (the happy path) ---
            (RunStatus.CREATED, RunStatus.EXECUTING, True),
            (RunStatus.EXECUTING, RunStatus.EVALUATING, True),
            (RunStatus.EVALUATING, RunStatus.AGGREGATING, True),
            (RunStatus.AGGREGATING, RunStatus.PUBLISHED, True),
            (RunStatus.AGGREGATING, RunStatus.DEGRADED, True),
            # --- Skipping states ---
            (RunStatus.CREATED, RunStatus.PUBLISHED, False),
            (RunStatus.CREATED, RunStatus.EVALUATING, False),
            (RunStatus.CREATED, RunStatus.AGGREGATING, False),
            (RunStatus.CREATED, RunStatus.DEGRADED, False),
            (RunStatus.EXECUTING, RunStatus.AGGREGATING, False),
            (RunStatus.EXECUTING, RunStatus.PUBLISHED, False),
            (RunStatus.EXECUTING, RunStatus.DEGRADED, False),
            (RunStatus.EVALUATING, RunStatus.PUBLISHED, False),
            (RunStatus.EVALUATING, RunStatus.DEGRADED, False),
            # --- Terminal: no outgoing edges ---
            (RunStatus.PUBLISHED, RunStatus.CREATED, False),
            (RunStatus.PUBLISHED, RunStatus.EXECUTING, False),
            (RunStatus.PUBLISHED, RunStatus.EVALUATING, False),
            (RunStatus.PUBLISHED, RunStatus.AGGREGATING, False),
            (RunStatus.PUBLISHED, RunStatus.DEGRADED, False),
            (RunStatus.DEGRADED, RunStatus.CREATED, False),
            (RunStatus.DEGRADED, RunStatus.EXECUTING, False),
            (RunStatus.DEGRADED, RunStatus.PUBLISHED, False),
        ],
    )
    def test_transition(
        self,
        tmp_path: Path,
        from_status: RunStatus,
        to_status: RunStatus,
        should_pass: bool,
    ) -> None:
        """Write a manifest at from_status, then attempt transition to to_status."""
        mp = ManifestPath(run_hash=f"sha256:{_SHA256_A}", root=tmp_path)
        w = ManifestWriter(mp)

        # Write the "from" manifest with allow_terminal_overwrite to bypass
        # any existing terminal guard for parametrized test isolation.
        from_manifest = make_manifest(status=from_status)
        # For terminal from_statuses we need to bootstrap the file without
        # going through the normal state machine (test isolation).
        # Write raw JSON to bypass the writer's own guard.
        mp.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _to_disk_format(from_manifest)
        mp.manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        # Restore write permission if a previous iteration made it 0o444
        mp.manifest_path.chmod(0o644)

        to_manifest = make_manifest(status=to_status)

        if should_pass:
            w.write(to_manifest)
            # Verify the on-disk status matches
            assert w.current_status() == to_status
        else:
            with pytest.raises(InvalidTransitionError):
                w.write(to_manifest)

    def test_no_existing_file_accepts_any_initial_status(self, writer: ManifestWriter) -> None:
        """When no manifest.json exists, any status can be written (first write)."""
        writer.write(make_manifest(status=RunStatus.CREATED))
        assert writer.current_status() == RunStatus.CREATED

    def test_self_transition_disallowed(self, tmp_path: Path) -> None:
        """No self-loops: writing the same status twice raises InvalidTransitionError."""
        mp = ManifestPath(run_hash=f"sha256:{_SHA256_A}", root=tmp_path)
        w = ManifestWriter(mp)
        first = make_manifest(status=RunStatus.CREATED)
        w.write(first)
        second = make_manifest(status=RunStatus.CREATED)
        with pytest.raises(InvalidTransitionError):
            w.write(second)

    def test_full_happy_path_chain(self, writer: ManifestWriter) -> None:
        """All four allowed transitions in sequence succeed end-to-end."""
        chain = [
            RunStatus.CREATED,
            RunStatus.EXECUTING,
            RunStatus.EVALUATING,
            RunStatus.AGGREGATING,
            RunStatus.PUBLISHED,
        ]
        for status in chain:
            writer.write(make_manifest(status=status))
            assert writer.current_status() == status

    def test_aggregating_to_degraded(self, writer: ManifestWriter) -> None:
        """Alternative terminal path: aggregating → degraded."""
        pre_terminal = [
            RunStatus.CREATED,
            RunStatus.EXECUTING,
            RunStatus.EVALUATING,
            RunStatus.AGGREGATING,
        ]
        for status in pre_terminal:
            writer.write(make_manifest(status=status))
        writer.write(make_manifest(status=RunStatus.DEGRADED))
        assert writer.current_status() == RunStatus.DEGRADED


# ---------------------------------------------------------------------------
# 2. TestSchemaValidation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """JSON Schema validation gate fires before file rename."""

    def test_valid_manifest_writes_without_error(self, writer: ManifestWriter) -> None:
        writer.write(make_manifest(status=RunStatus.CREATED))
        assert writer.current_status() == RunStatus.CREATED

    def test_tampered_run_hash_raises_schema_error(self, writer: ManifestWriter) -> None:
        """run_hash without sha256: prefix fails pattern constraint."""
        # Build a valid manifest, then tamper with its serialised form to
        # inject an invalid run_hash — we do this by intercepting _atomic_write.
        manifest = make_manifest(status=RunStatus.CREATED)
        payload = _to_disk_format(manifest)
        # Corrupt the run_hash
        payload["run_hash"] = "deadbeef"
        with pytest.raises(SchemaValidationError, match="run_hash"):
            from src.orchestrator import manifest_writer as mw

            mw._validate_against_schema(payload, writer._mp.manifest_path)

    def test_inspect_ai_version_none_on_non_published_is_allowed(
        self, writer: ManifestWriter
    ) -> None:
        """inspect_ai_version=None is permitted for pre-published manifests."""
        manifest = make_manifest(status=RunStatus.CREATED, inspect_ai_version=None)
        # Should not raise
        writer.write(manifest)

    def test_inspect_ai_version_none_on_published_documents_gap(
        self, writer: ManifestWriter
    ) -> None:
        """SPEC-001 requires inspect_ai_version for published runs.

        NOTE: The current on-disk schema does NOT enforce inspect_ai_version
        as required — it is optional in the schema. The SPEC-001 requirement
        ("Cannot publish without inspect_ai_version") is currently enforced
        only by convention, not by the schema.

        This test documents the gap: publishing without inspect_ai_version
        currently PASSES schema validation. When the schema is updated to
        require inspect_ai_version for published manifests, this test should
        be inverted to expect SchemaValidationError.
        """
        # Walk through the full state chain to reach published
        pre_terminal = [
            RunStatus.CREATED,
            RunStatus.EXECUTING,
            RunStatus.EVALUATING,
            RunStatus.AGGREGATING,
        ]
        for status in pre_terminal:
            writer.write(make_manifest(status=status, inspect_ai_version=None))
        # Currently passes — documents the schema gap
        writer.write(make_manifest(status=RunStatus.PUBLISHED, inspect_ai_version=None))
        # TODO: when schema adds required inspect_ai_version for published,
        #       update this test to: pytest.raises(SchemaValidationError)

    def test_schema_error_carries_field_path_context(self, writer: ManifestWriter) -> None:
        """SchemaValidationError message contains the field path and manifest path."""
        manifest = make_manifest(status=RunStatus.CREATED)
        payload = _to_disk_format(manifest)
        payload["run_hash"] = "invalid_no_prefix"
        with pytest.raises(SchemaValidationError) as exc_info:
            from src.orchestrator import manifest_writer as mw

            mw._validate_against_schema(payload, writer._mp.manifest_path)
        assert "run_hash" in str(exc_info.value)

    def test_schema_error_wraps_jsonschema_cause(self, writer: ManifestWriter) -> None:
        """SchemaValidationError.cause is the original jsonschema.ValidationError."""
        manifest = make_manifest(status=RunStatus.CREATED)
        payload = _to_disk_format(manifest)
        payload["run_hash"] = "bad"
        with pytest.raises(SchemaValidationError) as exc_info:
            from src.orchestrator import manifest_writer as mw

            mw._validate_against_schema(payload, writer._mp.manifest_path)
        assert isinstance(exc_info.value.cause, jsonschema.ValidationError)


# ---------------------------------------------------------------------------
# 3. TestSchemaDriftFixes
# ---------------------------------------------------------------------------


class TestSchemaDriftFixes:
    """Verify the 3 schema drift fixes applied by _to_disk_format."""

    def test_drift1_decimal_cost_usd_serialised_as_number_not_string(
        self, writer: ManifestWriter
    ) -> None:
        """Drift #1: cost_usd=Decimal('0.005') must be a JSON number on disk, not a string."""
        manifest = make_manifest(
            evals=[_eval_row(cost_usd=Decimal("0.005"))],
            aggregates=_aggregates(cost=Decimal("0.005")),
            status=RunStatus.CREATED,
        )
        writer.write(manifest)
        raw = json.loads(writer._mp.manifest_path.read_text())
        # cost_usd inside evals[0].stats must be a float, not a string
        cost_value = raw["evals"][0]["stats"]["cost_usd"]
        assert isinstance(cost_value, float), (
            f"Expected float on disk, got {type(cost_value).__name__!r}: {cost_value!r}. "
            "Drift fix #1 failed — Pydantic Decimal is no longer serialised as string "
            "or the coercion logic broke."
        )
        assert abs(cost_value - 0.005) < 1e-9

    def test_drift1_total_cost_usd_serialised_as_number(self, writer: ManifestWriter) -> None:
        """Drift #1: total_cost_usd in aggregates must be a float on disk."""
        manifest = make_manifest(
            aggregates=_aggregates(cost=Decimal("0.123")),
            status=RunStatus.CREATED,
        )
        writer.write(manifest)
        raw = json.loads(writer._mp.manifest_path.read_text())
        total = raw["aggregates"]["total_cost_usd"]
        assert isinstance(total, float)
        assert abs(total - 0.123) < 1e-9

    def test_drift1_pricing_snapshot_fields_serialised_as_numbers(
        self, writer: ManifestWriter
    ) -> None:
        """Drift #1: input/output_per_mtoken_usd must be floats on disk."""
        writer.write(make_manifest(status=RunStatus.CREATED))
        raw = json.loads(writer._mp.manifest_path.read_text())
        pricing = raw["model_pins"][0]["pricing_snapshot"]
        assert isinstance(pricing["input_per_mtoken_usd"], float)
        assert isinstance(pricing["output_per_mtoken_usd"], float)

    def test_drift2_optional_artifact_refs_absent_when_none(self, writer: ManifestWriter) -> None:
        """Drift #2: stdout/stderr/trace_json keys absent from JSON when ArtifactRef is None."""
        # Build eval row with no optional artifact refs (stdout/stderr/trace_json all None)
        manifest = make_manifest(
            evals=[_eval_row(include_optional_refs=False)],
            status=RunStatus.CREATED,
        )
        writer.write(manifest)
        raw = json.loads(writer._mp.manifest_path.read_text())
        artifact_refs = raw["evals"][0]["artifact_refs"]
        # Keys must be absent, not null
        assert "stdout" not in artifact_refs, "stdout should be absent (not null) when None"
        assert "stderr" not in artifact_refs, "stderr should be absent (not null) when None"
        assert "trace_json" not in artifact_refs, "trace_json should be absent (not null) when None"

    def test_drift2_optional_artifact_refs_present_when_populated(
        self, writer: ManifestWriter
    ) -> None:
        """Drift #2: stdout/stderr/trace_json present when ArtifactRef is populated."""
        manifest = make_manifest(
            evals=[_eval_row(include_optional_refs=True)],
            status=RunStatus.CREATED,
        )
        writer.write(manifest)
        raw = json.loads(writer._mp.manifest_path.read_text())
        artifact_refs = raw["evals"][0]["artifact_refs"]
        assert "stdout" in artifact_refs
        assert "stderr" in artifact_refs
        assert "trace_json" in artifact_refs

    def test_drift3_completed_at_none_absent_from_json(self, writer: ManifestWriter) -> None:
        """Drift #3: completed_at=None must be absent from JSON (not 'null')."""
        manifest = make_manifest(
            evals=[_eval_row(completed_at=None)],
            status=RunStatus.CREATED,
        )
        writer.write(manifest)
        raw = json.loads(writer._mp.manifest_path.read_text())
        eval_raw = raw["evals"][0]
        assert "completed_at" not in eval_raw, (
            "completed_at=None must produce absent key, not null value."
        )

    def test_drift3_started_at_none_absent_from_json(self, writer: ManifestWriter) -> None:
        """Drift #3: started_at=None is dropped from JSON.

        Note: in production, every EvalRow should have started_at populated.
        started_at=None is only valid during pre-execution states. The schema
        does not require started_at, so absence is acceptable at the schema
        level even if it indicates a real data quality issue.
        """
        manifest = make_manifest(
            evals=[_eval_row(started_at=None, completed_at=None)],
            status=RunStatus.CREATED,
        )
        writer.write(manifest)
        raw = json.loads(writer._mp.manifest_path.read_text())
        eval_raw = raw["evals"][0]
        assert "started_at" not in eval_raw

    def test_drift3_published_at_none_absent_from_json(self, writer: ManifestWriter) -> None:
        """Drift #3: published_at=None must be absent from the root JSON object."""
        manifest = make_manifest(status=RunStatus.CREATED, published_at=None)
        writer.write(manifest)
        raw = json.loads(writer._mp.manifest_path.read_text())
        assert "published_at" not in raw

    def test_coerce_decimal_strings_recursive(self) -> None:
        """Unit test for _coerce_decimal_strings_to_numbers traversal."""
        payload: dict[str, Any] = {
            "evals": [
                {
                    "stats": {"cost_usd": "0.001", "wall_clock_ms": 3000},
                    "model_id": "abc123",
                }
            ],
            "aggregates": {"total_cost_usd": "0.005"},
            "model_pins": [
                {
                    "pricing_snapshot": {
                        "input_per_mtoken_usd": "3.0",
                        "output_per_mtoken_usd": "15.0",
                    }
                }
            ],
        }
        coerced = _coerce_decimal_strings_to_numbers(payload)
        assert isinstance(coerced, dict)
        assert isinstance(coerced["evals"][0]["stats"]["cost_usd"], float)
        assert isinstance(coerced["aggregates"]["total_cost_usd"], float)
        pricing = coerced["model_pins"][0]["pricing_snapshot"]
        assert isinstance(pricing["input_per_mtoken_usd"], float)
        # Non-Decimal fields must not be touched
        assert coerced["evals"][0]["stats"]["wall_clock_ms"] == 3000
        assert coerced["evals"][0]["model_id"] == "abc123"

    def test_coerce_does_not_convert_non_decimal_string_fields(self) -> None:
        """Non-Decimal string fields must pass through unmodified."""
        payload: dict[str, Any] = {
            "run_hash": "sha256:" + "a" * 64,
            "eval_id": "a" * 16,
            "model_id": "claude-sonnet-4-6",
        }
        result = _coerce_decimal_strings_to_numbers(payload)
        # All values must be unchanged
        assert result["run_hash"] == payload["run_hash"]
        assert result["eval_id"] == payload["eval_id"]
        assert result["model_id"] == payload["model_id"]


# ---------------------------------------------------------------------------
# 4. TestAtomicWrite
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    """Verify .tmp staging file semantics and cleanup on failure."""

    def test_write_succeeds_file_exists(self, writer: ManifestWriter) -> None:
        writer.write(make_manifest(status=RunStatus.CREATED))
        assert writer._mp.manifest_path.exists()

    def test_tmp_file_absent_after_successful_write(self, writer: ManifestWriter) -> None:
        writer.write(make_manifest(status=RunStatus.CREATED))
        assert not writer._mp.tmp_path.exists(), ".tmp must be cleaned up after successful rename"

    def test_tmp_file_absent_after_schema_validation_failure(self, writer: ManifestWriter) -> None:
        """On schema validation error (before _atomic_write), no .tmp should be left."""
        # Schema validation fires before atomic_write; .tmp is never created.
        manifest = make_manifest(status=RunStatus.CREATED)
        # Patch _validate_against_schema to raise SchemaValidationError
        from src.orchestrator import manifest_writer as mw

        def _boom(payload: dict[str, Any], path: Path) -> None:
            raise SchemaValidationError(
                "injected failure",
                jsonschema.ValidationError("injected"),
            )

        with (
            patch.object(mw, "_validate_against_schema", _boom),
            pytest.raises(SchemaValidationError),
        ):
            writer.write(manifest)

        assert not writer._mp.tmp_path.exists()
        assert not writer._mp.manifest_path.exists()

    def test_manifest_unchanged_when_write_raises(self, writer: ManifestWriter) -> None:
        """First write succeeds. Second (failed) write must not corrupt the first."""
        writer.write(make_manifest(status=RunStatus.CREATED))
        assert writer.current_status() == RunStatus.CREATED

        # Force the second write to fail at the OS level after schema validation.
        from src.orchestrator import manifest_writer as mw

        def _fail_rename(path: Path, tmp_path: Path, payload: dict[str, Any]) -> None:
            raise OSError("simulated disk failure")

        with (
            patch.object(mw, "_atomic_write", _fail_rename),
            pytest.raises(OSError, match="simulated disk failure"),
        ):
            writer.write(make_manifest(status=RunStatus.EXECUTING))

        # Original file must still report the original status
        assert writer.current_status() == RunStatus.CREATED

    def test_parent_directory_created_automatically(self, tmp_path: Path) -> None:
        """ManifestWriter creates intermediate directories as needed."""
        mp = ManifestPath(
            run_hash=f"sha256:{_SHA256_B}",
            root=tmp_path / "deeply" / "nested",
        )
        w = ManifestWriter(mp)
        w.write(make_manifest(status=RunStatus.CREATED))
        assert mp.manifest_path.exists()


# ---------------------------------------------------------------------------
# 5. TestImmutability
# ---------------------------------------------------------------------------


class TestImmutability:
    """chmod 0o444 on terminal statuses; second write raises; bypass documented."""

    def _write_to_terminal(self, writer: ManifestWriter, terminal: RunStatus) -> None:
        """Helper: drive writer from CREATED through all intermediate states to terminal."""
        path_chain = [
            RunStatus.CREATED,
            RunStatus.EXECUTING,
            RunStatus.EVALUATING,
            RunStatus.AGGREGATING,
            terminal,
        ]
        for status in path_chain:
            writer.write(make_manifest(status=status))

    def test_published_manifest_file_mode_is_0o444(self, writer: ManifestWriter) -> None:
        """AC-2: Published manifest file is set to read-only mode 0o444."""
        self._write_to_terminal(writer, RunStatus.PUBLISHED)
        mode = writer._mp.manifest_path.stat().st_mode & 0o777
        assert mode == 0o444, f"Expected 0o444, got {oct(mode)}"

    def test_degraded_manifest_file_mode_is_0o444(self, writer: ManifestWriter) -> None:
        """Degraded manifest file is also set to read-only mode 0o444."""
        self._write_to_terminal(writer, RunStatus.DEGRADED)
        mode = writer._mp.manifest_path.stat().st_mode & 0o777
        assert mode == 0o444, f"Expected 0o444, got {oct(mode)}"

    def test_is_published_true_after_publish(self, writer: ManifestWriter) -> None:
        self._write_to_terminal(writer, RunStatus.PUBLISHED)
        assert writer.is_published() is True

    def test_is_published_true_after_degraded(self, writer: ManifestWriter) -> None:
        """is_published() returns True for degraded too (both are terminal)."""
        self._write_to_terminal(writer, RunStatus.DEGRADED)
        assert writer.is_published() is True

    def test_is_published_false_before_terminal(self, writer: ManifestWriter) -> None:
        writer.write(make_manifest(status=RunStatus.CREATED))
        assert writer.is_published() is False

    def test_second_write_to_published_raises_without_bypass(self, writer: ManifestWriter) -> None:
        """AC-2: Writing again to a published manifest raises InvalidTransitionError."""
        self._write_to_terminal(writer, RunStatus.PUBLISHED)
        # Restore write permission so the writer can attempt the write
        writer._mp.manifest_path.chmod(0o644)
        with pytest.raises(InvalidTransitionError, match="terminal"):
            writer.write(make_manifest(status=RunStatus.PUBLISHED))

    def test_second_write_to_degraded_raises_without_bypass(self, writer: ManifestWriter) -> None:
        self._write_to_terminal(writer, RunStatus.DEGRADED)
        writer._mp.manifest_path.chmod(0o644)
        with pytest.raises(InvalidTransitionError, match="terminal"):
            writer.write(make_manifest(status=RunStatus.DEGRADED))

    def test_allow_terminal_overwrite_bypasses_immutability_guard(
        self, writer: ManifestWriter
    ) -> None:
        """allow_terminal_overwrite=True bypasses the terminal guard.

        Use only for migrations and test scenarios — NOT production writes.
        Even with the bypass, the file mode is re-applied to 0o444.
        """
        self._write_to_terminal(writer, RunStatus.PUBLISHED)
        # Restore write permission to simulate an admin reset
        writer._mp.manifest_path.chmod(0o644)

        # Build a new published manifest (e.g. corrected orchestrator_version)
        corrected = make_manifest(
            status=RunStatus.PUBLISHED,
            orchestrator_version="v0.0.2-corrected",
        )
        # Should not raise
        writer.write(corrected, allow_terminal_overwrite=True)

        # File is again immutable
        mode = writer._mp.manifest_path.stat().st_mode & 0o777
        assert mode == 0o444

        # Content reflects the correction
        reloaded = writer.read()
        assert reloaded is not None
        assert reloaded.orchestrator_version == "v0.0.2-corrected"


# ---------------------------------------------------------------------------
# 6. TestReadRoundTrip
# ---------------------------------------------------------------------------


class TestReadRoundTrip:
    """Write a Manifest, read it back, assert equivalence."""

    def test_basic_round_trip(self, writer: ManifestWriter) -> None:
        original = make_manifest(status=RunStatus.CREATED)
        writer.write(original)
        restored = writer.read()
        assert restored is not None
        assert restored.run_hash == original.run_hash
        assert restored.status == original.status
        assert restored.methodology_version == original.methodology_version
        assert restored.run_type == original.run_type
        assert restored.region == original.region

    def test_decimal_fields_round_trip_with_acceptable_precision(
        self, writer: ManifestWriter
    ) -> None:
        """Decimal values survive disk round-trip within acceptable tolerance.

        Precision loss: Decimal("0.005") → float 0.005 on disk → Decimal via Pydantic.
        Acceptable per ADR-0002: the manifest is the snapshot for reporting, not
        the accumulation buffer.
        """
        manifest = make_manifest(
            evals=[_eval_row(cost_usd=Decimal("0.005"))],
            aggregates=_aggregates(cost=Decimal("0.005")),
            status=RunStatus.CREATED,
        )
        writer.write(manifest)
        restored = writer.read()
        assert restored is not None
        tolerance = Decimal("0.0001")
        assert (
            abs(manifest.aggregates.total_cost_usd - restored.aggregates.total_cost_usd) < tolerance
        )
        assert abs(manifest.evals[0].stats.cost_usd - restored.evals[0].stats.cost_usd) < tolerance

    def test_optional_fields_restore_as_none(self, writer: ManifestWriter) -> None:
        """Optional fields absent from JSON restore to None in Pydantic."""
        manifest = make_manifest(
            status=RunStatus.CREATED,
            published_at=None,
            inspect_eval_log_sha256=None,
            evals=[_eval_row(started_at=None, completed_at=None)],
        )
        writer.write(manifest)
        restored = writer.read()
        assert restored is not None
        assert restored.published_at is None
        assert restored.inspect_eval_log_sha256 is None
        assert restored.evals[0].started_at is None
        assert restored.evals[0].completed_at is None

    def test_read_returns_none_when_no_file(self, writer: ManifestWriter) -> None:
        assert writer.read() is None

    def test_current_status_returns_none_when_no_file(self, writer: ManifestWriter) -> None:
        assert writer.current_status() is None

    def test_status_chain_round_trips(self, writer: ManifestWriter) -> None:
        """Each status in the chain is correctly persisted and read back."""
        pre_terminal = [
            RunStatus.CREATED,
            RunStatus.EXECUTING,
            RunStatus.EVALUATING,
            RunStatus.AGGREGATING,
        ]
        for status in pre_terminal:
            writer.write(make_manifest(status=status))
            assert writer.current_status() == status
            restored = writer.read()
            assert restored is not None
            assert restored.status == status

    def test_stack_pins_round_trip(self, writer: ManifestWriter) -> None:
        manifest = make_manifest(status=RunStatus.CREATED)
        writer.write(manifest)
        restored = writer.read()
        assert restored is not None
        assert len(restored.stack_pins) == len(manifest.stack_pins)
        assert restored.stack_pins[0].stack_id == manifest.stack_pins[0].stack_id

    def test_pricing_snapshot_round_trips(self, writer: ManifestWriter) -> None:
        manifest = make_manifest(status=RunStatus.CREATED)
        writer.write(manifest)
        restored = writer.read()
        assert restored is not None
        orig_pricing = manifest.model_pins[0].pricing_snapshot
        rest_pricing = restored.model_pins[0].pricing_snapshot
        tolerance = Decimal("0.0001")
        assert (
            abs(orig_pricing.input_per_mtoken_usd - rest_pricing.input_per_mtoken_usd) < tolerance
        )
        assert (
            abs(orig_pricing.output_per_mtoken_usd - rest_pricing.output_per_mtoken_usd) < tolerance
        )
