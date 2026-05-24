"""Shared pytest fixtures for eval-core-py tests.

All fixtures are deterministic — no LLM calls, no network calls.
LLM mocking is deferred to Wave 4 (EvalCaller stub injection).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Primitive fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_methodology_version() -> str:
    """Pinned methodology version string used across all smoke-run tests."""
    return "v0.1.0"


@pytest.fixture
def fake_seed() -> int:
    """Canonical seed value for deterministic test scenarios."""
    return 42


@pytest.fixture
def tmp_run_dir(tmp_path: Path) -> Path:
    """Temporary directory that mirrors the artifacts/runs/{run_hash}/ layout.

    Structure created:
        <tmp>/runs/sha256:aabbcc.../
            evals/
            manifest.journal.ndjson  (empty, ready for appends)
    """
    run_hash = "sha256:" + "a" * 64
    run_dir = tmp_path / "runs" / run_hash
    (run_dir / "evals").mkdir(parents=True)
    (run_dir / "manifest.journal.ndjson").touch()
    return run_dir


# ---------------------------------------------------------------------------
# EvalRow factory fixture
# ---------------------------------------------------------------------------


def _make_artifact_ref(content: str, mime_type: str, base_uri: str) -> dict[str, Any]:
    """Build a canned ArtifactRef dict for a given content string."""
    digest = hashlib.sha256(content.encode()).hexdigest()
    size = len(content.encode())
    return {
        "sha256": digest,
        "size_bytes": size,
        "uri": f"{base_uri}-{digest}.txt",
        "mime_type": mime_type,
    }


@pytest.fixture
def fake_eval_result() -> Any:
    """Factory fixture returning a callable that produces a canned EvalRow dict.

    Usage::

        def test_something(fake_eval_result):
            row = fake_eval_result()                        # defaults
            row_failed = fake_eval_result(status="failed", error_class="timeout")

    The returned dict conforms to the SPEC-001 EvalRow schema.
    Required fields populated: eval_id, model_id, stack_id, task_id, seed,
    status, artifact_refs, stats.
    """

    def _factory(
        *,
        model_id: str = "claude-sonnet-4-6",
        stack_id: str = "raw-llm",
        task_id: str = "be_01_jwt_auth",
        seed: int = 42,
        status: str = "scored",
        error_class: str | None = None,
        input_tokens: int = 512,
        output_tokens: int = 256,
        wall_clock_ms: int = 3000,
        cost_usd: float | None = 0.001,
        final_score: float | None = None,
    ) -> dict[str, Any]:
        # eval_id: sha256(run_hash + model + stack + task + seed)[:16]
        id_material = f"sha256:{'a' * 64}:{model_id}:{stack_id}:{task_id}:{seed}"
        eval_id = hashlib.sha256(id_material.encode()).hexdigest()[:16]

        base_uri_prefix = f"file://artifacts/runs/sha256:{'a' * 64}/evals/{eval_id}"

        raw_text = "def generate_token(user_id: int) -> str: ..."
        norm_text = raw_text.strip()
        evaluator_json = (
            '{"test_pass_rate": 1.0, "lint_errors": 0, "complexity": 3, "coverage": 0.92}'
        )

        artifact_refs: dict[str, Any] = {
            "raw_output": _make_artifact_ref(
                raw_text, "text/plain", f"{base_uri_prefix}/raw_output"
            ),
            "normalized_output": _make_artifact_ref(
                norm_text, "text/plain", f"{base_uri_prefix}/normalized_output"
            ),
            "evaluator_json": _make_artifact_ref(
                evaluator_json,
                "application/json",
                f"{base_uri_prefix}/evaluator_json",
            ),
        }

        automatic_metrics: dict[str, Any] | None = None
        if status == "scored":
            automatic_metrics = {
                "test_pass_rate": 1.0,
                "lint_errors": 0,
                "complexity": 3,
                "coverage": 0.92,
            }

        return {
            "eval_id": eval_id,
            "model_id": model_id,
            "stack_id": stack_id,
            "task_id": task_id,
            "seed": seed,
            "status": status,
            "error_class": error_class,
            "artifact_refs": artifact_refs,
            "automatic_metrics": automatic_metrics,
            "final_score": final_score,
            "stats": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "wall_clock_ms": wall_clock_ms,
                "cost_usd": cost_usd,
            },
        }

    return _factory
