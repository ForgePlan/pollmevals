"""Tests for orchestrator.eval_caller -- EvalCaller Protocol seam.

Covers:
 - Protocol structural conformance (runtime_checkable)
 - compute_eval_id determinism and output format
 - InspectEvalCaller stub behaviour (raises NotImplementedError, Phase 2B documented)
 - FakeEvalCaller success path (default + deterministic overrides)
 - FakeEvalCaller failure simulation path
"""

from __future__ import annotations

import pathlib
import re
from datetime import UTC

import pytest

from src.contracts import ErrorClass, EvalStatus
from src.orchestrator.eval_caller import (
    _FAKE_RUN_HASH,
    EvalCaller,
    EvalRequest,
    EvalResult,
    FakeEvalCaller,
    InspectEvalCaller,
    compute_eval_id,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EVAL_ID_RE = re.compile(r"^[a-f0-9]{16}$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def _make_request(
    *,
    stack_id: str = "raw-llm",
    task_id: str = "be_01_jwt_auth",
    seed: int = 42,
    model_id: str = "openrouter/anthropic/claude-sonnet-4-6",
) -> EvalRequest:
    eid = compute_eval_id(_FAKE_RUN_HASH, model_id, stack_id, task_id, seed)
    return EvalRequest(
        eval_id=eid,
        model_id=model_id,
        stack_id=stack_id,
        task_id=task_id,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# 1. Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_inspect_caller_is_eval_caller(self, tmp_path: pathlib.Path) -> None:
        caller = InspectEvalCaller(log_dir=tmp_path)
        assert isinstance(caller, EvalCaller)

    def test_fake_caller_is_eval_caller(self) -> None:
        caller = FakeEvalCaller()
        assert isinstance(caller, EvalCaller)

    def test_class_without_call_method_fails(self) -> None:
        class NoCaller:
            def run(self) -> None:
                pass

        assert not isinstance(NoCaller(), EvalCaller)

    def test_plain_object_fails(self) -> None:
        class NotACaller:
            pass

        assert not isinstance(NotACaller(), EvalCaller)


# ---------------------------------------------------------------------------
# 2. compute_eval_id
# ---------------------------------------------------------------------------


class TestComputeEvalId:
    def test_deterministic_same_inputs(self) -> None:
        args = ("sha256:" + "a" * 64, "model", "stack", "task", 1)
        assert compute_eval_id(*args) == compute_eval_id(*args)

    def test_different_seeds_produce_different_ids(self) -> None:
        id1 = compute_eval_id("sha256:" + "a" * 64, "model", "stack", "task", 1)
        id2 = compute_eval_id("sha256:" + "a" * 64, "model", "stack", "task", 2)
        assert id1 != id2

    def test_different_model_ids_produce_different_ids(self) -> None:
        id1 = compute_eval_id("sha256:" + "a" * 64, "model-a", "stack", "task", 1)
        id2 = compute_eval_id("sha256:" + "a" * 64, "model-b", "stack", "task", 1)
        assert id1 != id2

    def test_output_matches_eval_id_regex(self) -> None:
        eid = compute_eval_id("sha256:" + "b" * 64, "m", "s", "t", 0)
        assert _EVAL_ID_RE.match(eid), f"eval_id {eid!r} does not match ^[a-f0-9]{{16}}$"

    def test_different_run_hashes_produce_different_ids(self) -> None:
        id1 = compute_eval_id("sha256:" + "a" * 64, "m", "s", "t", 0)
        id2 = compute_eval_id("sha256:" + "b" * 64, "m", "s", "t", 0)
        assert id1 != id2

    def test_different_task_ids_produce_different_ids(self) -> None:
        id1 = compute_eval_id("sha256:" + "a" * 64, "m", "s", "task1", 0)
        id2 = compute_eval_id("sha256:" + "a" * 64, "m", "s", "task2", 0)
        assert id1 != id2


# ---------------------------------------------------------------------------
# 3. InspectEvalCaller stub
# ---------------------------------------------------------------------------


class TestInspectEvalCallerStub:
    @pytest.mark.asyncio
    async def test_raises_not_implemented(self, tmp_path: pathlib.Path) -> None:
        caller = InspectEvalCaller(log_dir=tmp_path)
        req = _make_request()
        with pytest.raises(NotImplementedError) as exc_info:
            await caller.call(req)
        msg = str(exc_info.value)
        assert "Phase 2B" in msg
        assert "OPENROUTER_API_KEY" in msg

    @pytest.mark.asyncio
    async def test_stub_message_mentions_fake_caller(self, tmp_path: pathlib.Path) -> None:
        caller = InspectEvalCaller(log_dir=tmp_path)
        req = _make_request()
        with pytest.raises(NotImplementedError) as exc_info:
            await caller.call(req)
        assert "FakeEvalCaller" in str(exc_info.value)

    def test_default_openrouter_base_url(self, tmp_path: pathlib.Path) -> None:
        caller = InspectEvalCaller(log_dir=tmp_path)
        assert caller._openrouter_base_url == "https://openrouter.ai/api/v1"

    def test_custom_openrouter_base_url(self, tmp_path: pathlib.Path) -> None:
        caller = InspectEvalCaller(
            log_dir=tmp_path,
            openrouter_base_url="http://localhost:4000/v1",
        )
        assert caller._openrouter_base_url == "http://localhost:4000/v1"


# ---------------------------------------------------------------------------
# 4. FakeEvalCaller -- success path
# ---------------------------------------------------------------------------


class TestFakeEvalCallerSuccess:
    @pytest.mark.asyncio
    async def test_default_returns_scored_status(self) -> None:
        caller = FakeEvalCaller()
        req = _make_request()
        result = await caller.call(req)
        assert isinstance(result, EvalResult)
        assert result.eval_row is not None
        assert result.eval_row.status == EvalStatus.SCORED

    @pytest.mark.asyncio
    async def test_eval_id_matches_compute_eval_id(self) -> None:
        caller = FakeEvalCaller()
        req = _make_request()
        result = await caller.call(req)
        assert result.eval_row is not None
        expected_id = compute_eval_id(
            _FAKE_RUN_HASH,
            req.model_id,
            req.stack_id,
            req.task_id,
            req.seed,
        )
        assert result.eval_row.eval_id == expected_id

    @pytest.mark.asyncio
    async def test_artifact_refs_have_valid_sha256(self) -> None:
        caller = FakeEvalCaller()
        req = _make_request()
        result = await caller.call(req)
        assert result.eval_row is not None
        refs = result.eval_row.artifact_refs
        for ref in [refs.raw_output, refs.normalized_output, refs.evaluator_json]:
            assert _SHA256_RE.match(ref.sha256), f"invalid sha256: {ref.sha256!r}"

    @pytest.mark.asyncio
    async def test_stats_populated_with_defaults(self) -> None:
        from decimal import Decimal

        caller = FakeEvalCaller()
        req = _make_request()
        result = await caller.call(req)
        assert result.eval_row is not None
        stats = result.eval_row.stats
        assert stats.input_tokens == 1000
        assert stats.output_tokens == 500
        assert stats.wall_clock_ms == 2000
        assert stats.cost_usd == Decimal("0.0125")

    @pytest.mark.asyncio
    async def test_no_exception_on_success(self) -> None:
        caller = FakeEvalCaller()
        req = _make_request()
        result = await caller.call(req)
        assert result.exception is None

    @pytest.mark.asyncio
    async def test_timestamps_are_timezone_aware(self) -> None:
        caller = FakeEvalCaller()
        req = _make_request()
        result = await caller.call(req)
        assert result.started_at.tzinfo is not None
        assert result.completed_at.tzinfo is not None
        assert result.started_at.tzinfo == UTC
        assert result.completed_at.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_default_automatic_metrics(self) -> None:
        caller = FakeEvalCaller()
        req = _make_request()
        result = await caller.call(req)
        assert result.eval_row is not None
        assert result.eval_row.automatic_metrics == {"test_pass_rate": 1.0}


# ---------------------------------------------------------------------------
# 5. FakeEvalCaller -- failure simulation
# ---------------------------------------------------------------------------


class TestFakeEvalCallerFailures:
    @pytest.mark.asyncio
    async def test_simulate_rate_limit(self) -> None:
        caller = FakeEvalCaller(simulate_failures={("raw-llm", "be_01_jwt_auth", 42): "rate_limit"})
        req = _make_request(stack_id="raw-llm", task_id="be_01_jwt_auth", seed=42)
        result = await caller.call(req)
        assert result.eval_row is not None
        assert result.eval_row.status == EvalStatus.FAILED
        assert result.eval_row.error_class == ErrorClass.RATE_LIMIT

    @pytest.mark.asyncio
    async def test_simulate_timeout(self) -> None:
        caller = FakeEvalCaller(simulate_failures={("raw-llm", "be_01_jwt_auth", 1): "timeout"})
        req = _make_request(stack_id="raw-llm", task_id="be_01_jwt_auth", seed=1)
        result = await caller.call(req)
        assert result.eval_row is not None
        assert result.eval_row.error_class == ErrorClass.TIMEOUT

    @pytest.mark.asyncio
    async def test_failed_row_still_valid_fr009(self) -> None:
        """Failed evals MUST be stored, not dropped (PRD-001 FR-009)."""
        caller = FakeEvalCaller(simulate_failures={("raw-llm", "be_01_jwt_auth", 42): "network"})
        req = _make_request()
        result = await caller.call(req)
        # Must have a valid EvalRow even on failure
        assert result.eval_row is not None
        # Must have error_class populated (model_validator on EvalRow enforces this)
        assert result.eval_row.error_class is not None
        # Must have artifact_refs (even failures produce refs per FR-009)
        assert result.eval_row.artifact_refs is not None

    @pytest.mark.asyncio
    async def test_failure_detail_identifies_fake_caller(self) -> None:
        caller = FakeEvalCaller(simulate_failures={("raw-llm", "be_01_jwt_auth", 42): "timeout"})
        req = _make_request()
        result = await caller.call(req)
        assert result.eval_row is not None
        assert result.eval_row.error_detail is not None
        assert "FakeEvalCaller" in result.eval_row.error_detail

    @pytest.mark.asyncio
    async def test_non_matching_key_still_succeeds(self) -> None:
        """A failure key for seed=1 must not affect seed=2."""
        caller = FakeEvalCaller(simulate_failures={("raw-llm", "be_01_jwt_auth", 1): "rate_limit"})
        req = _make_request(seed=2)
        result = await caller.call(req)
        assert result.eval_row is not None
        assert result.eval_row.status == EvalStatus.SCORED


# ---------------------------------------------------------------------------
# 6. FakeEvalCaller -- deterministic outputs
# ---------------------------------------------------------------------------


class TestFakeEvalCallerDeterministicOutputs:
    @pytest.mark.asyncio
    async def test_override_applies_to_matching_key(self) -> None:
        caller = FakeEvalCaller(
            deterministic_outputs={
                ("raw-llm", "be_01_jwt_auth", 42): {"automatic_metrics": {"test_pass_rate": 0.5}}
            }
        )
        req = _make_request(stack_id="raw-llm", task_id="be_01_jwt_auth", seed=42)
        result = await caller.call(req)
        assert result.eval_row is not None
        assert result.eval_row.automatic_metrics == {"test_pass_rate": 0.5}

    @pytest.mark.asyncio
    async def test_non_matching_key_uses_defaults(self) -> None:
        caller = FakeEvalCaller(
            deterministic_outputs={
                ("raw-llm", "be_01_jwt_auth", 42): {"automatic_metrics": {"test_pass_rate": 0.5}}
            }
        )
        # Different seed -- should get default metrics
        req = _make_request(stack_id="raw-llm", task_id="be_01_jwt_auth", seed=99)
        result = await caller.call(req)
        assert result.eval_row is not None
        assert result.eval_row.automatic_metrics == {"test_pass_rate": 1.0}

    @pytest.mark.asyncio
    async def test_determinism_same_request_twice(self) -> None:
        caller = FakeEvalCaller()
        req = _make_request()
        result1 = await caller.call(req)
        result2 = await caller.call(req)
        assert result1.eval_row is not None
        assert result2.eval_row is not None
        # eval_id and artifact sha256s must be identical
        assert result1.eval_row.eval_id == result2.eval_row.eval_id
        assert (
            result1.eval_row.artifact_refs.raw_output.sha256
            == result2.eval_row.artifact_refs.raw_output.sha256
        )

    @pytest.mark.asyncio
    async def test_different_seeds_produce_different_eval_ids(self) -> None:
        caller = FakeEvalCaller()
        req1 = _make_request(seed=1)
        req2 = _make_request(seed=2)
        result1 = await caller.call(req1)
        result2 = await caller.call(req2)
        assert result1.eval_row is not None
        assert result2.eval_row is not None
        assert result1.eval_row.eval_id != result2.eval_row.eval_id
