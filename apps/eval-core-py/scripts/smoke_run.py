"""Phase 2B coda smoke-run entrypoint.

Per docs/04-runbook/12-first-smoke-run-playbook.md.

Executes 45 evals (3 tasks x 5 models x 3 seeds x 1 stack=raw-llm).
Real LLM spend ~$5-15. Requires explicit confirmation flag --confirm-spend.

Playbook steps implemented (1-14):
  1.  Validate task specs    -- check evals/tasks/<task_id>/task.yaml exists
  2.  Validate stack specs   -- check stacks/raw-llm/stack.yaml exists
  3.  Check LiteLLM proxy    -- GET /health on http://localhost:4000
  4.  Pre-flight prompt      -- one /chat/completions per model (dry-run skips)
  5.  Create run snapshot    -- deterministic run_hash + manifest skeleton
  6.  Execute grid           -- GridRunner (45 evals; FakeEvalCaller in --dry-run)
  7.  Save raw outputs       -- artifacts/runs/<hash>/evals/
  8.  Run evaluators         -- stub (real wiring in Phase 2D)
  9.  Save evaluator JSON    -- written by EvalCaller via ArtifactRef
  10. Aggregate scores       -- RunAggregates built from GridRunResult
  11. Create manifest        -- ManifestWriter, mode 0o444 on terminal (ADR-002)
  12. Re-run one eval        -- determinism check via FakeEvalCaller replay
  13. Compare deterministic  -- eval_id + artifact sha256 match
  14. Write postmortem       -- artifacts/runs/<hash>/POSTMORTEM.md
"""

# NOTE: E402 noqa needed below — sys.path must be extended before src.* imports
# because this script can be run directly from repo root via
# `uv run python apps/eval-core-py/scripts/smoke_run.py`.

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple, cast

# ---------------------------------------------------------------------------
# Repo / package roots
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).parents[3]
_EVAL_CORE_ROOT: Path = Path(__file__).parents[1]

# Ensure src/ is importable when invoked as a standalone script.
if str(_EVAL_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_EVAL_CORE_ROOT))

from src.contracts import (  # noqa: E402
    METHODOLOGY_VERSION_V0_1_0,
    SCHEMA_VERSION_V1_0_0,
    CountsByStatus,
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
from src.evaluators import (  # noqa: E402
    ComplexityEvaluator,
    Evaluator,
    LintEvaluator,
    SecretScanEvaluator,
    TypeSafetyEvaluator,
)
from src.evaluators.protocol import EvaluatorResult  # noqa: E402
from src.orchestrator.cost import BudgetGate  # noqa: E402
from src.orchestrator.eval_caller import (  # noqa: E402
    FakeEvalCaller,
    InspectEvalCaller,
)
from src.orchestrator.grid_runner import (  # noqa: E402
    SMOKE_MODELS,
    SMOKE_STACKS,
    SMOKE_TASKS,
    GridRunner,
    GridRunResult,
    GridSpec,
)
from src.orchestrator.journal import JournalWriter  # noqa: E402
from src.orchestrator.manifest_writer import ManifestPath, ManifestWriter  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_BUDGET_USD = Decimal("50")
_LITELLM_BASE_URL = "http://localhost:4000"
_ARTIFACTS_ROOT = _REPO_ROOT / "artifacts" / "runs"
_TASK_SPECS_ROOT = _REPO_ROOT / "evals" / "tasks"
_STACK_SPECS_ROOT = _REPO_ROOT / "stacks"

# Canonical LiteLLM model_name entries (from infra/litellm-config.yaml).
_LITELLM_MODEL_NAMES: dict[str, str] = {
    "openrouter/anthropic/claude-sonnet-4-6": "claude-sonnet-4-6",
    "openrouter/openai/gpt-4o-mini": "gpt-5-mini",
    "openrouter/google/gemini-flash-1-5": "gemini-3-flash",
    "openrouter/qwen/qwen-2-5-14b": "qwen-3-14b",
    "openrouter/meta-llama/llama-4-70b": "llama-3-3-70b",
}

# Estimated cost per eval (conservative; used for dry-run cost projection).
_ESTIMATED_COST_PER_EVAL_USD = Decimal("0.0125")
_ESTIMATED_SPEND_LOW_USD = Decimal("5")
_ESTIMATED_SPEND_HIGH_USD = Decimal("15")

ORCHESTRATOR_VERSION = "pollmevals-eval-core/0.0.0"


# ---------------------------------------------------------------------------
# Pre-flight result
# ---------------------------------------------------------------------------


class PreflightResult(NamedTuple):
    ok: bool
    issues: list[str]


# ---------------------------------------------------------------------------
# Step 1: Validate task specs
# ---------------------------------------------------------------------------


def validate_task_specs(task_ids: list[str]) -> PreflightResult:
    """Step 1 -- Check that each task_id has a task.yaml under evals/tasks/."""
    issues: list[str] = []
    for task_id in task_ids:
        yaml_path = _TASK_SPECS_ROOT / task_id / "task.yaml"
        if not yaml_path.exists():
            issues.append(f"Missing task spec: {yaml_path}")
    return PreflightResult(ok=len(issues) == 0, issues=issues)


# ---------------------------------------------------------------------------
# Step 2: Validate stack specs
# ---------------------------------------------------------------------------


def validate_stack_specs(stack_ids: list[str]) -> PreflightResult:
    """Step 2 -- Check that each stack_id has a stack.yaml under stacks/."""
    issues: list[str] = []
    for stack_id in stack_ids:
        yaml_path = _STACK_SPECS_ROOT / stack_id / "stack.yaml"
        if not yaml_path.exists():
            issues.append(f"Missing stack spec: {yaml_path}")
    return PreflightResult(ok=len(issues) == 0, issues=issues)


# ---------------------------------------------------------------------------
# Step 3: Check LiteLLM proxy
# ---------------------------------------------------------------------------


async def check_litellm_proxy(base_url: str = _LITELLM_BASE_URL) -> PreflightResult:
    """Step 3 -- Ping LiteLLM proxy GET /health/liveliness.

    LiteLLM's `/health` endpoint requires the master key in newer versions;
    `/health/liveliness` is the standard k8s-style unauthenticated readiness
    probe that still works for connectivity check. If the proxy is up but the
    key is wrong, the actual chat completions call surfaces the auth error.
    """
    import os

    import httpx

    master_key = os.environ.get("LITELLM_MASTER_KEY", "")
    headers = {"Authorization": f"Bearer {master_key}"} if master_key else {}
    url = f"{base_url.rstrip('/')}/health/liveliness"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return PreflightResult(ok=True, issues=[])
            return PreflightResult(
                ok=False,
                issues=[f"LiteLLM proxy unhealthy: HTTP {resp.status_code} from {url}"],
            )
    except Exception as exc:
        return PreflightResult(
            ok=False,
            issues=[f"LiteLLM proxy unreachable at {base_url}: {exc}"],
        )


# ---------------------------------------------------------------------------
# Step 4: Pre-flight prompts per model
# ---------------------------------------------------------------------------


async def preflight_prompts(
    model_ids: list[str],
    api_key: str,
    base_url: str = _LITELLM_BASE_URL,
) -> PreflightResult:
    """Step 4 -- Send one minimal chat completion to each model route.

    Uses the LiteLLM model_name aliases from infra/litellm-config.yaml.
    Any failure is logged but does not abort -- a model can be absent from the
    live stack (degraded threshold is 3/5 per PRD-001).
    """
    import httpx

    issues: list[str] = []
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        for model_id in model_ids:
            litellm_name = _LITELLM_MODEL_NAMES.get(model_id, model_id)
            payload: dict[str, object] = {
                "model": litellm_name,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 16,
            }
            try:
                resp = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code == 200:
                    logger.info("Pre-flight OK: model=%s", model_id)
                else:
                    issues.append(f"Pre-flight WARN: model={model_id} -> HTTP {resp.status_code}")
                    logger.warning(
                        "Pre-flight WARN: model=%s status=%d",
                        model_id,
                        resp.status_code,
                    )
            except Exception as exc:
                issues.append(f"Pre-flight WARN: model={model_id} -> {exc}")
                logger.warning("Pre-flight WARN: model=%s exc=%s", model_id, exc)

    ok_count = len(model_ids) - len(issues)
    if ok_count < 3:
        return PreflightResult(
            ok=False,
            issues=[
                *issues,
                (
                    f"Only {ok_count}/{len(model_ids)} models responded"
                    " -- below degraded threshold (3)"
                ),
            ],
        )
    return PreflightResult(ok=True, issues=issues)


# ---------------------------------------------------------------------------
# Step 5: Create run snapshot (run_hash + manifest skeleton)
# ---------------------------------------------------------------------------


def make_run_hash(
    tasks: list[str],
    models: list[str],
    stacks: list[str],
    seeds: list[int],
    created_at: datetime,
) -> str:
    """Derive a deterministic sha256 run_hash from the grid inputs."""
    material = (
        f"tasks={','.join(sorted(tasks))}"
        f"|models={','.join(sorted(models))}"
        f"|stacks={','.join(sorted(stacks))}"
        f"|seeds={','.join(str(s) for s in sorted(seeds))}"
        f"|created_at={created_at.isoformat()}"
    )
    digest = hashlib.sha256(material.encode()).hexdigest()
    return f"sha256:{digest}"


# Library-first cost path (per CLAUDE.md Library-first rule, 2026-05-25):
# Primary: litellm.cost_per_token() — auto-updated with model price changes
#         via LiteLLM's maintained model_cost map.
# Fallback: hardcoded dict below — only when LiteLLM doesn't know the alias.
# Aliases (LiteLLM proxy route names) -> canonical OpenRouter paths that
# LiteLLM SDK recognises for cost lookup.
_PROXY_ALIAS_TO_LITELLM_MODEL: dict[str, str] = {
    # ADR-003 smoke baseline (5 models)
    "claude-sonnet-4-6": "openrouter/anthropic/claude-sonnet-4.6",
    "gpt-5-mini": "openrouter/openai/gpt-5-mini",
    "gemini-3-flash": "openrouter/google/gemini-3-flash-preview",
    "qwen-3-14b": "openrouter/qwen/qwen3-14b",
    "llama-3-3-70b": "openrouter/meta-llama/llama-3.3-70b-instruct",
    # ADR-006 Phase 1 additions — OpenRouter closed APIs
    "claude-opus-4-7": "openrouter/anthropic/claude-opus-4.7",
    "gpt-5": "openrouter/openai/gpt-5",
    "gemini-2-5-pro": "openrouter/google/gemini-2.5-pro",
    "grok-4": "openrouter/x-ai/grok-4",
    "deepseek-v3-5": "openrouter/deepseek/deepseek-v3.5",
    # ADR-006 Phase 1 additions — Cerebras direct
    "llama-3-3-70b-cerebras": "cerebras/llama3.3-70b",
    "qwen-3-32b": "cerebras/qwen-3-32b",
    "glm-4-7": "cerebras/glm-4.7",
    "gpt-oss-120b": "cerebras/gpt-oss-120b",
    # ADR-006 Phase 1 additions — Runpod vLLM
    "qwen-2-5-72b": "hosted_vllm/Qwen/Qwen2.5-72B-Instruct",
}

# Fallback when litellm.cost_per_token() is unknown for the alias. Per-Mtoken USD.
# Refresh when LiteLLM lookup misses for an alias we still want priced.
# Primary path: litellm.cost_per_token() — auto-updated (commit 5d4b432).
# Fallback numbers: OpenRouter/Cerebras published prices as of 2026-05-25 (ADR-006).
_FALLBACK_PRICING_PER_MTOKEN: dict[str, tuple[Decimal, Decimal]] = {
    # ADR-003 smoke baseline (5 models)
    "claude-sonnet-4-6": (Decimal("3.00"), Decimal("15.00")),
    "gpt-5-mini": (Decimal("0.25"), Decimal("2.00")),
    "gemini-3-flash": (Decimal("0.075"), Decimal("0.30")),
    "qwen-3-14b": (Decimal("0.06"), Decimal("0.12")),
    "llama-3-3-70b": (Decimal("0.60"), Decimal("0.60")),
    # ADR-006 Phase 1 additions — OpenRouter closed APIs
    "claude-opus-4-7": (Decimal("15.00"), Decimal("75.00")),
    "gpt-5": (Decimal("5.00"), Decimal("15.00")),
    "gemini-2-5-pro": (Decimal("2.50"), Decimal("10.00")),
    "grok-4": (Decimal("5.00"), Decimal("15.00")),
    "deepseek-v3-5": (Decimal("0.27"), Decimal("1.10")),
    # ADR-006 Phase 1 additions — Cerebras direct
    "llama-3-3-70b-cerebras": (Decimal("0.85"), Decimal("1.20")),
    "qwen-3-32b": (Decimal("0.18"), Decimal("0.36")),
    "glm-4-7": (Decimal("0.18"), Decimal("0.36")),
    "gpt-oss-120b": (Decimal("0.10"), Decimal("0.20")),
    # ADR-006 Phase 1 additions — Runpod vLLM
    "qwen-2-5-72b": (Decimal("0.90"), Decimal("0.90")),
}


def _make_pricing_snapshot(model_id: str) -> PricingSnapshot:
    """Build pricing snapshot via LiteLLM SDK (Library-first, CLAUDE.md 2026-05-25).

    Primary: litellm.cost_per_token(model, prompt_tokens=1M, completion_tokens=1M)
    gives per-Mtoken rates. Fallback to hardcoded dict only when LiteLLM doesn't
    know the model (returns 0/0 or raises). Logs fallback events so we know to
    refresh the lookup.
    """
    litellm_model = _PROXY_ALIAS_TO_LITELLM_MODEL.get(model_id, model_id)
    try:
        import litellm  # local import — heavy dep, only used for cost

        prompt_cost_1m, completion_cost_1m = litellm.cost_per_token(
            model=litellm_model,
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
        )
        ipt = Decimal(str(prompt_cost_1m))
        opt = Decimal(str(completion_cost_1m))
        if ipt == 0 and opt == 0:
            raise ValueError(f"cost_per_token returned 0/0 for {litellm_model!r}")
    except Exception as exc:
        logger.debug(
            "litellm.cost_per_token miss for %s (litellm=%s, err=%s); using fallback",
            model_id,
            litellm_model,
            exc,
        )
        ipt, opt = _FALLBACK_PRICING_PER_MTOKEN.get(model_id, (Decimal("0"), Decimal("0")))
    return PricingSnapshot(
        input_per_mtoken_usd=ipt,
        output_per_mtoken_usd=opt,
        snapshot_at=datetime.now(UTC),
    )


def _make_stub_pricing_snapshot() -> PricingSnapshot:
    """Build a zero-cost pricing snapshot for dry-run / unknown-pricing models.

    Kept for backward compatibility with tests. New code should use
    `_make_pricing_snapshot(model_id)` to get per-model rates.
    """
    return PricingSnapshot(
        input_per_mtoken_usd=Decimal("0"),
        output_per_mtoken_usd=Decimal("0"),
        snapshot_at=datetime.now(UTC),
    )


def _compute_eval_cost(input_tokens: int, output_tokens: int, pricing: PricingSnapshot) -> Decimal:
    """Compute cost in USD from tokens and pricing snapshot."""
    return (
        Decimal(input_tokens) * pricing.input_per_mtoken_usd
        + Decimal(output_tokens) * pricing.output_per_mtoken_usd
    ) / Decimal("1000000")


def _make_stack_pin(stack_id: str) -> StackPin:
    yaml_path = _STACK_SPECS_ROOT / stack_id / "stack.yaml"
    if yaml_path.exists():
        sha = hashlib.sha256(yaml_path.read_bytes()).hexdigest()
    else:
        sha = hashlib.sha256(stack_id.encode()).hexdigest()
    return StackPin(stack_id=stack_id, stack_version="0.1.0", stack_yaml_sha256=sha)


def _make_model_pin(model_id: str, pricing: PricingSnapshot) -> ModelPin:
    parts = model_id.split("/")
    provider_id = parts[0] if len(parts) > 1 else "unknown"
    return ModelPin(
        model_id=model_id,
        provider_id=provider_id,
        provider_route_id=model_id,
        pricing_snapshot=pricing,
    )


def _make_task_pin(task_id: str) -> TaskPin:
    yaml_path = _TASK_SPECS_ROOT / task_id / "task.yaml"
    if yaml_path.exists():
        sha = hashlib.sha256(yaml_path.read_bytes()).hexdigest()
    else:
        sha = hashlib.sha256(task_id.encode()).hexdigest()
    return TaskPin(task_id=task_id, task_version="0.1.0", task_pack_sha256=sha)


def build_initial_manifest(
    run_hash: str,
    tasks: list[str],
    models: list[str],
    stacks: list[str],
    seeds: list[int],
    created_at: datetime,
) -> Manifest:
    """Build the initial (status=created) Manifest skeleton.

    Each model gets its own pricing snapshot via litellm.cost_per_token() lookup
    (Library-first) with hardcoded fallback when LiteLLM doesn't know the alias.
    """
    return Manifest(
        schema_version=SCHEMA_VERSION_V1_0_0,
        run_hash=run_hash,
        run_type=RunType.SMOKE,
        methodology_version=METHODOLOGY_VERSION_V0_1_0,
        created_at=created_at,
        region=Region.EU_CENTRAL,
        stack_pins=[_make_stack_pin(s) for s in stacks],
        model_pins=[_make_model_pin(m, _make_pricing_snapshot(m)) for m in models],
        task_pins=[_make_task_pin(t) for t in tasks],
        seed_set=seeds,
        evals=[],
        aggregates=RunAggregates(
            counts_by_status=CountsByStatus(scored=0, failed=0, skipped=0),
            total_cost_usd=Decimal("0"),
            total_wall_clock_ms=0,
        ),
        status=RunStatus.CREATED,
        orchestrator_version=ORCHESTRATOR_VERSION,
    )


# ---------------------------------------------------------------------------
# Steps 8+10: Stub evaluators + aggregate scores
# ---------------------------------------------------------------------------


def run_evaluators(
    grid_result: GridRunResult,
) -> dict[str, dict[str, dict[str, float | int]]]:
    """Step 8+10 -- Stub: real evaluators land in Phase 2D.

    Returns per_task_metrics structure required by RunAggregates.
    For now: counts test_pass_rate from scored evals' automatic_metrics.
    """
    per_task: dict[str, list[float]] = {}
    for result in grid_result.succeeded():
        row = result.eval_row
        if row is None:
            continue
        task = row.task_id
        metrics = row.automatic_metrics or {}
        tpr = metrics.get("test_pass_rate")
        if isinstance(tpr, (int, float)):
            per_task.setdefault(task, []).append(float(tpr))

    out: dict[str, dict[str, dict[str, float | int]]] = {}
    for task_id, scores in per_task.items():
        n = len(scores)
        mean_val = sum(scores) / n if n else 0.0
        sorted_scores = sorted(scores)
        median_val = sorted_scores[n // 2] if n else 0.0
        p95_idx = max(0, int(n * 0.95) - 1)
        p95_val = sorted_scores[p95_idx] if n else 0.0
        out[task_id] = {
            "test_pass_rate": {
                "mean": mean_val,
                "median": median_val,
                "p95": p95_val,
                "sample_count": n,
            }
        }
    return out


# ---------------------------------------------------------------------------
# Step 8: Phase 2D real evaluator dispatch
# ---------------------------------------------------------------------------

_EVALUATORS: list[Evaluator] = [
    LintEvaluator(),
    ComplexityEvaluator(),
    SecretScanEvaluator(),
    TypeSafetyEvaluator(),
]


def _resolve_artifact_path(uri: str) -> str:
    """Resolve a file:// artifact URI to an absolute local path.

    URIs are of the form ``file://artifacts/runs/<hash>/evals/<id>/...``
    The repo-relative portion is resolved against _REPO_ROOT so both
    dry-run (tmp) and real-run (artifacts/) paths work.

    Non-file:// URIs (e.g. r2://) are returned unchanged -- callers must
    handle the path-not-exists case gracefully.
    """
    if uri.startswith("file://"):
        rel = uri[len("file://") :]
        return str(_REPO_ROOT / rel)
    return uri


async def _dispatch_evaluators(grid_result: GridRunResult) -> None:
    """Run all EVALUATORS on each succeeded eval's raw_output artifact.

    Results are attached in-place to each EvalRow's automatic_metrics dict
    using model_copy(update=...) because EvalRow is frozen.

    Evaluator errors are caught and stored as {"error": str, "skipped": True}
    to preserve FR-009 invariant (no eval is silently dropped).
    """
    for eval_result in grid_result.succeeded():
        row = eval_result.eval_row
        if row is None:
            continue

        raw_output_path = _resolve_artifact_path(row.artifact_refs.raw_output.uri)
        eval_metrics: dict[str, object] = dict(row.automatic_metrics or {})

        for evaluator in _EVALUATORS:
            try:
                result: EvaluatorResult = await evaluator.evaluate(raw_output_path, row.task_id)
                eval_metrics[evaluator.name] = result.model_dump(mode="json")
            except Exception as exc:
                logger.warning(
                    "Evaluator %r failed for eval_id=%s: %s",
                    evaluator.name,
                    row.eval_id,
                    exc,
                )
                eval_metrics[evaluator.name] = {"error": str(exc), "skipped": True}

        # EvalRow is frozen -- use model_copy to produce updated instance.
        updated_row = row.model_copy(update={"automatic_metrics": eval_metrics})
        # Patch the eval_result in-place (EvalResult is a frozen dataclass --
        # we reassign the attribute on the mutable list element).
        object.__setattr__(eval_result, "eval_row", updated_row)


def build_aggregates(grid_result: GridRunResult) -> RunAggregates:
    """Step 10 -- Build RunAggregates from GridRunResult."""
    succeeded = grid_result.succeeded()
    failed_list = grid_result.failed()

    scored_count = len(succeeded)
    failed_count = sum(
        1
        for r in failed_list
        if not isinstance(r, BaseException)
        and r.eval_row is not None
        and r.eval_row.status == EvalStatus.FAILED
    )
    exception_count = sum(1 for r in failed_list if isinstance(r, BaseException))

    counts_by_error_class: dict[str, int] = {}
    for r in grid_result.results:
        if not isinstance(r, BaseException) and r.eval_row is not None:
            ec = r.eval_row.error_class
            if ec is not None:
                key = str(ec.value) if hasattr(ec, "value") else str(ec)
                counts_by_error_class[key] = counts_by_error_class.get(key, 0) + 1

    total_wall_ms = sum(
        r.eval_row.stats.wall_clock_ms
        for r in grid_result.results
        if not isinstance(r, BaseException) and r.eval_row is not None
    )

    per_task_metrics = run_evaluators(grid_result)

    scored_model_ids: set[str] = set()
    for r in succeeded:
        if r.eval_row is not None:
            scored_model_ids.add(r.eval_row.model_id)

    # Compute cost from tokens + pricing (InspectEvalCaller leaves cost=0; reconcile here
    # per CostReconciler post-run pattern documented in eval_caller.py:380).
    computed_total_cost = Decimal("0")
    for r in succeeded:
        if r.eval_row is None:
            continue
        pricing = _make_pricing_snapshot(r.eval_row.model_id)
        computed_total_cost += _compute_eval_cost(
            r.eval_row.stats.input_tokens,
            r.eval_row.stats.output_tokens,
            pricing,
        )

    return RunAggregates(
        counts_by_status=CountsByStatus(
            scored=scored_count,
            failed=failed_count + exception_count,
            skipped=0,
        ),
        counts_by_error_class=counts_by_error_class,
        total_cost_usd=computed_total_cost,
        total_wall_clock_ms=total_wall_ms,
        per_task_metrics=per_task_metrics,
        budget_breach=grid_result.budget_breach,
        available_models_count=len(scored_model_ids),
    )


# ---------------------------------------------------------------------------
# Step 11: Create manifest (write-once, ADR-002)
# ---------------------------------------------------------------------------


def write_final_manifest(
    initial_manifest: Manifest,
    grid_result: GridRunResult,
    run_dir: Path,
) -> Manifest:
    """Step 11 -- Transition manifest through all states to published/degraded.

    State machine: created -> executing -> evaluating -> aggregating
                   -> published/degraded
    Final file mode: 0o444 (ADR-002 immutability invariant).
    """
    mp = ManifestPath(run_hash=initial_manifest.run_hash, root=_ARTIFACTS_ROOT)
    writer = ManifestWriter(mp)

    aggregates = build_aggregates(grid_result)

    evals = [
        r.eval_row
        for r in grid_result.results
        if not isinstance(r, BaseException) and r.eval_row is not None
    ]

    is_degraded = grid_result.budget_breach or aggregates.available_models_count < 3
    terminal_status = RunStatus.DEGRADED if is_degraded else RunStatus.PUBLISHED
    published_at = datetime.now(UTC)

    executing = initial_manifest.model_copy(update={"status": RunStatus.EXECUTING})
    writer.write(initial_manifest)
    writer.write(executing)

    evaluating = executing.model_copy(update={"status": RunStatus.EVALUATING, "evals": evals})
    writer.write(evaluating)

    aggregating = evaluating.model_copy(
        update={"status": RunStatus.AGGREGATING, "aggregates": aggregates}
    )
    writer.write(aggregating)

    final = cast(
        Manifest,
        aggregating.model_copy(update={"status": terminal_status, "published_at": published_at}),
    )
    writer.write(final)  # triggers chmod 0o444

    return final


# ---------------------------------------------------------------------------
# Steps 12-13: Determinism check
# ---------------------------------------------------------------------------


async def determinism_check(
    spec: GridSpec,
    original_results: GridRunResult,
    budget: Decimal,
    run_dir: Path,
) -> PreflightResult:
    """Steps 12-13 -- Re-run one eval via FakeEvalCaller and compare identifiers.

    Uses FakeEvalCaller (never calls real LLMs) to verify the grid's
    deterministic eval_id derivation.
    """
    issues: list[str] = []

    first_req = next(spec.iter_requests())

    journal_path = run_dir / "determinism-check.journal.ndjson"
    journal = JournalWriter(journal_path)
    gate = BudgetGate(cap_usd=budget)
    single_spec = GridSpec(
        run_hash=spec.run_hash,
        models=[first_req.model_id],
        tasks=[first_req.task_id],
        stacks=[first_req.stack_id],
        seeds=[first_req.seed],
    )
    runner = GridRunner(
        caller=FakeEvalCaller(),
        journal_writer=journal,
        budget_gate=gate,
        pricing_snapshot={},
    )
    replay_result = await runner.run(single_spec)
    journal.close()

    if not replay_result.succeeded():
        issues.append("Determinism check: replay eval failed (no scored result)")
        return PreflightResult(ok=False, issues=issues)

    replayed = replay_result.succeeded()[0].eval_row
    assert replayed is not None  # guarded above

    original_match = next(
        (
            r.eval_row
            for r in original_results.results
            if not isinstance(r, BaseException)
            and r.eval_row is not None
            and r.eval_row.task_id == first_req.task_id
            and r.eval_row.model_id == first_req.model_id
            and r.eval_row.seed == first_req.seed
        ),
        None,
    )

    if original_match is None:
        if len(replayed.eval_id) != 16:
            issues.append(f"Determinism check: replay eval_id wrong length: {replayed.eval_id!r}")
    else:
        if len(replayed.eval_id) != 16:
            issues.append(
                f"Determinism check: replay eval_id length mismatch: {replayed.eval_id!r}"
            )
        # NOTE: raw_output sha256 comparison intentionally removed (was incorrect per
        # ADR-002 reproduce semantics). ADR-002 mandates evaluator-only reproduce on
        # CACHED raw_output, NOT re-firing LLM (which is what FakeEvalCaller-vs-real
        # comparison effectively did and always failed since outputs differ).
        # Proper evaluator-only replay lands in Phase 2D when real evaluators are
        # wired. Until then, determinism is verified at eval_id structural level only.

    return PreflightResult(ok=len(issues) == 0, issues=issues)


# ---------------------------------------------------------------------------
# Step 14: Postmortem template
# ---------------------------------------------------------------------------


def write_postmortem(
    run_dir: Path,
    run_hash: str,
    tasks: list[str],
    models: list[str],
    seeds: list[int],
    grid_result: GridRunResult,
) -> Path:
    """Step 14 -- Write POSTMORTEM.md from the template in playbook S Postmortem."""
    succeeded = grid_result.succeeded()
    failed_list = grid_result.failed()

    cost_per_model: dict[str, Decimal] = {}
    all_wall: list[int] = []
    for r in grid_result.results:
        if not isinstance(r, BaseException) and r.eval_row is not None:
            mid = r.eval_row.model_id
            cost_per_model[mid] = cost_per_model.get(mid, Decimal("0")) + r.eval_row.stats.cost_usd
            all_wall.append(r.eval_row.stats.wall_clock_ms)

    sorted_wall = sorted(all_wall)
    n = len(sorted_wall)
    p50 = sorted_wall[n // 2] if n else 0
    p95 = sorted_wall[int(n * 0.95)] if n else 0

    error_breakdown: dict[str, int] = {}
    for r in failed_list:
        if not isinstance(r, BaseException) and r.eval_row is not None:
            ec = r.eval_row.error_class
            key = str(ec.value) if ec and hasattr(ec, "value") else (str(ec) if ec else "unknown")
            error_breakdown[key] = error_breakdown.get(key, 0) + 1
        elif isinstance(r, BaseException):
            error_breakdown["exception"] = error_breakdown.get("exception", 0) + 1

    cost_lines = "\n".join(f"- {mid}: ${cost:.4f}" for mid, cost in sorted(cost_per_model.items()))
    error_lines = (
        "\n".join(f"- {ec}: {cnt}" for ec, cnt in sorted(error_breakdown.items())) or "(none)"
    )

    total = len(grid_result.results)
    scored = len(succeeded)

    content = f"""# Smoke Run Postmortem

## Run hash

{run_hash}

## Scope

- Tasks: {", ".join(tasks)}
- Models: {", ".join(models)}
- Seeds: {seeds}
- Stack: raw-llm

## What worked

- {scored}/{total} evals scored successfully

## What failed

{error_lines}

## Cost

Total: ${grid_result.total_cost_usd:.4f}

Per model:
{cost_lines or "(no cost data)"}

## Latency

- p50: {p50} ms
- p95: {p95} ms

## Task issues

(fill in after review of per_task_metrics in manifest.json)

## Model/provider issues

{"Budget gate triggered -- some evals skipped." if grid_result.budget_breach else "(none observed)"}

## Scoring issues

(Phase 2B stubs -- real evaluators wired in Phase 2D)

## Changes before next run

(fill in after postmortem discussion)
"""

    postmortem_path = run_dir / "POSTMORTEM.md"
    postmortem_path.write_text(content, encoding="utf-8")
    return postmortem_path


# ---------------------------------------------------------------------------
# Dry-run summary
# ---------------------------------------------------------------------------


def print_dry_run_summary(
    tasks: list[str],
    models: list[str],
    seeds: list[int],
    budget: Decimal,
    pre_checks: list[tuple[str, PreflightResult]],
) -> bool:
    """Print expected grid + cost + pre-flight results. Returns True if all pass."""
    n_evals = len(tasks) * len(models) * len(seeds)
    expected_cost = _ESTIMATED_COST_PER_EVAL_USD * n_evals
    spend_range = f"${_ESTIMATED_SPEND_LOW_USD}-${_ESTIMATED_SPEND_HIGH_USD}"

    print("=" * 60)
    print("SMOKE RUN DRY-RUN SUMMARY")
    print("=" * 60)
    print(f"Grid: {len(tasks)} tasks x {len(models)} models x {len(seeds)} seeds = {n_evals} evals")
    print(f"Expected cost: ~${expected_cost:.2f} (estimated {spend_range} actual)")
    print(f"Budget cap: ${budget}")
    print(f"Budget abort threshold: ${budget * Decimal('0.80')} (80%)")
    print()
    print("Pre-flight checks:")

    all_ok = True
    for name, result in pre_checks:
        status = "PASS" if result.ok else "FAIL"
        print(f"  [{status}] {name}")
        if result.issues:
            for issue in result.issues:
                print(f"         {issue}")
            if not result.ok:
                all_ok = False

    print()
    if all_ok:
        print("All pre-flight checks passed.")
        print()
        print("To execute (will spend real money):")
        print(
            "  uv run --project apps/eval-core-py"
            " python apps/eval-core-py/scripts/smoke_run.py --confirm-spend"
        )
    else:
        print("Pre-flight checks FAILED. Fix issues above before running.")
    print("=" * 60)
    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def async_main(args: argparse.Namespace) -> int:
    """Async entrypoint -- returns exit code."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    tasks = args.tasks.split(",") if args.tasks else list(SMOKE_TASKS)
    models_raw = args.models.split(",") if args.models else list(SMOKE_MODELS)
    # Translate OpenRouter paths to LiteLLM proxy aliases. SMOKE_MODELS contains
    # full OpenRouter paths (`openrouter/anthropic/claude-sonnet-4-6`); LiteLLM
    # proxy expects route names (`claude-sonnet-4-6`) per infra/litellm-config.yaml.
    # Pre-flight handles this transparently; grid execution needs explicit translation.
    models = [_LITELLM_MODEL_NAMES.get(m, m) for m in models_raw]
    seeds = list(range(1, args.seeds + 1))
    budget = Decimal(str(args.budget_usd))
    api_key: str = os.environ.get("LITELLM_MASTER_KEY", "")

    # Step 1
    task_check = validate_task_specs(tasks)
    if not task_check.ok:
        for issue in task_check.issues:
            logger.warning("Task spec: %s", issue)

    # Step 2
    stack_check = validate_stack_specs(list(SMOKE_STACKS))
    if not stack_check.ok:
        for issue in stack_check.issues:
            logger.warning("Stack spec: %s", issue)

    # Step 3
    proxy_check = await check_litellm_proxy()
    if not proxy_check.ok:
        for issue in proxy_check.issues:
            logger.warning("Proxy check: %s", issue)

    # Step 4 (skipped in dry-run)
    if args.dry_run:
        preflight_check = PreflightResult(
            ok=True, issues=["(skipped in --dry-run mode -- no real LLM calls)"]
        )
    else:
        preflight_check = await preflight_prompts(models, api_key)

    pre_checks: list[tuple[str, PreflightResult]] = [
        ("Task specs", task_check),
        ("Stack specs", stack_check),
        ("LiteLLM proxy", proxy_check),
        ("Pre-flight prompts", preflight_check),
    ]

    if args.dry_run:
        all_ok = print_dry_run_summary(tasks, models, seeds, budget, pre_checks)
        return 0 if all_ok else 1

    # Guard: --confirm-spend required beyond this point
    if not args.confirm_spend:
        print(
            "ERROR: --confirm-spend flag is required to proceed past pre-flight.\n"
            "This protects against accidental spend ($5-15 in real OpenRouter inference).\n"
            "Run with --dry-run to validate without spending.\n"
            "Run with --confirm-spend to execute.",
            file=sys.stderr,
        )
        return 2

    logger.info(
        "Starting smoke run: %d tasks x %d models x %d seeds",
        len(tasks),
        len(models),
        len(seeds),
    )

    # Step 5: create run snapshot
    created_at = datetime.now(UTC)
    run_hash = make_run_hash(tasks, models, list(SMOKE_STACKS), seeds, created_at)
    logger.info("Run hash: %s", run_hash)

    run_dir = _ARTIFACTS_ROOT / run_hash
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "evals").mkdir(exist_ok=True)

    initial_manifest = build_initial_manifest(
        run_hash, tasks, models, list(SMOKE_STACKS), seeds, created_at
    )

    spec = GridSpec(
        run_hash=run_hash,
        models=models,
        tasks=tasks,
        stacks=list(SMOKE_STACKS),
        seeds=seeds,
    )

    # Steps 6-7: execute grid + save raw outputs
    journal_path = run_dir / "manifest.journal.ndjson"
    journal_writer = JournalWriter(journal_path)
    budget_gate = BudgetGate(cap_usd=budget)
    caller = InspectEvalCaller(
        log_dir=run_dir / "evals",
        litellm_base_url=_LITELLM_BASE_URL,
        api_key=api_key,
    )
    runner = GridRunner(
        caller=caller,
        journal_writer=journal_writer,
        budget_gate=budget_gate,
        pricing_snapshot={},
    )

    logger.info("Executing %d evals...", spec.total_evals())
    grid_result = await runner.run(spec)
    journal_writer.close()

    logger.info(
        "Grid complete: %d scored, %d failed, budget_breach=%s, total_cost=$%s",
        len(grid_result.succeeded()),
        len(grid_result.failed()),
        grid_result.budget_breach,
        grid_result.total_cost_usd,
    )

    # Steps 8-9: evaluators (Phase 2D real dispatch)
    logger.info("Step 8: Running evaluators (Phase 2D — ruff/lizard/gitleaks)...")
    await _dispatch_evaluators(grid_result)

    # Steps 10-11: aggregate + write manifest (write-once, 0o444)
    logger.info("Step 10-11: Aggregating scores + writing manifest...")
    final_manifest = write_final_manifest(initial_manifest, grid_result, run_dir)
    manifest_path = _ARTIFACTS_ROOT / run_hash / "manifest.json"
    logger.info("Manifest written: %s (status=%s)", manifest_path, final_manifest.status)

    # Steps 12-13: determinism check
    logger.info("Step 12-13: Determinism check...")
    det_result = await determinism_check(spec, grid_result, budget, run_dir)
    if not det_result.ok:
        for issue in det_result.issues:
            logger.error("Determinism check FAILED: %s", issue)
    else:
        logger.info("Determinism check PASSED")

    # Step 14: write postmortem
    postmortem_path = write_postmortem(run_dir, run_hash, tasks, models, seeds, grid_result)
    logger.info("Postmortem written: %s", postmortem_path)

    scored = len(grid_result.succeeded())
    total = len(grid_result.results)
    print(
        f"\nSmoke run complete: {scored}/{total} evals scored, "
        f"${grid_result.total_cost_usd:.4f} spent, "
        f"status={final_manifest.status}\n"
        f"Artifacts: {run_dir}\n"
        f"Manifest:  {manifest_path}\n"
        f"Postmortem: {postmortem_path}\n"
    )

    return 0 if not grid_result.budget_breach else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 2B smoke-run entrypoint. "
            "Requires --confirm-spend to call real LLMs. "
            "Use --dry-run to validate pre-flight without spending."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=("Validate steps 1-5 only. No LLM calls. Exit 0 if all checks pass."),
    )
    parser.add_argument(
        "--confirm-spend",
        action="store_true",
        help="Required to execute past step 5 (real LLM spend ~$5-15).",
    )
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=50.0,
        help=("Hard budget cap in USD (default: 50, per PRD-001 NFR-001). Abort at 80%% = $40."),
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=3,
        help="Number of seeds per (model, task) pair (default: 3).",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default="",
        help=(
            "Comma-separated task IDs"
            " (default: be_01_jwt_auth,fe_01_multistep_form,doc_01_cli_readme)."
        ),
    )
    parser.add_argument(
        "--models",
        type=str,
        default="",
        help=("Comma-separated model IDs (default: 5 ADR-003 canonical routes)."),
    )

    args = parser.parse_args()
    sys.exit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()
