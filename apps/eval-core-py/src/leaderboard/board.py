"""Emit the rich harness x model Board (apps/site/src/lib/board.ts shape) from runs.

RFC-006 Phase 4c. Turns scored ``EvalRow``s into the JSON the public site
renders, replacing the illustrative preview (``board.illustrative.json``) with
real ``(model x harness x task)`` numbers.

Mirrors the TypeScript ``Board`` contract field-for-field. Harness metadata
(level, family, layers) is derived from ``stacks/<id>/stack.yaml``; model
metadata (name, tier) from a small registry; cell score/cost/latency from the
EvalRows (judge-aggregate median when a deterministic score isn't set).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from src.contracts import EvalRow, EvalStatus

# ---------------------------------------------------------------------------
# Harness / model metadata (the Board needs display fields the run doesn't carry)
# ---------------------------------------------------------------------------

# Scaffolding family per stack (matches board.ts Harness.family). Default
# "agnostic" for unknown CLI harnesses.
_STACK_FAMILY: dict[str, str] = {
    "raw-llm": "baseline",
    "aider": "agnostic",
    "codex": "agnostic",
    "opencode": "agnostic",
    "goose": "agnostic",
    "openhands": "agnostic",
    "hermes": "agnostic",
    "cline": "vendor",
    "claude-code-basic": "vendor",
    "pi": "vendor",
    "forgeplan-framework": "framework",
}

# Ordered L-keys → numeric level. The harness level is the highest true layer.
_LAYER_ORDER: list[str] = [
    "L0_bare_llm",
    "L1_system_prompt",
    "L2_tools",
    "L3_skills",
    "L4_file_memory",
    "L5_vector_memory",
    "L6_subagents",
    "L7_validator",
    "L8_framework",
]

# Model display name + cost tier, keyed by the proxy alias / model_id segment.
_MODEL_REGISTRY: dict[str, tuple[str, str]] = {
    "qwen-3-14b": ("Qwen 3 14B", "cheap"),
    "qwen-3-32b": ("Qwen 3 32B", "cheap"),
    "llama-3-3-70b": ("Llama 3.3 70B", "cheap"),
    "gemini-3-flash": ("Gemini 3 Flash", "mid"),
    "gpt-5-mini": ("GPT-5 mini", "mid"),
    "deepseek-v3-5": ("DeepSeek V3.5", "mid"),
    "claude-sonnet-4-6": ("Claude Sonnet 4.6", "frontier"),
    "gpt-5": ("GPT-5", "frontier"),
    "claude-opus-4-7": ("Claude Opus 4.7", "frontier"),
    "gemini-2-5-pro": ("Gemini 2.5 Pro", "frontier"),
}


def _alias(model_id: str) -> str:
    """provider-route → short alias (matches default_model_alias)."""
    return model_id.rsplit("/", 1)[-1]


# ---------------------------------------------------------------------------
# Board contract (mirrors apps/site/src/lib/board.ts)
# ---------------------------------------------------------------------------


class Harness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stack_id: str
    name: str
    level: int
    layers: list[str]
    family: str


class ModelRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str
    name: str
    tier: str


class TaskScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float | None
    cost_usd: float
    pass_hat_k: float | None = None


class Cell(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str
    stack_id: str
    mean_score: float | None
    mean_cost_usd: float
    mean_latency_ms: int
    pass_hat_k: float | None = None
    quality_per_dollar: float | None
    per_task: dict[str, TaskScore]
    on_frontier: bool = False


class Board(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_hash: str
    run_type: str
    methodology_version: str
    region: str
    scored: bool
    illustrative: bool
    solved_threshold: float
    harnesses: list[Harness]
    models: list[ModelRef]
    tasks: list[str]
    cells: list[Cell]


# ---------------------------------------------------------------------------
# Derivations
# ---------------------------------------------------------------------------


def _harness_from_yaml(stack_id: str, stacks_root: Path) -> Harness:
    """Build Harness display metadata from stacks/<id>/stack.yaml."""
    data = yaml.safe_load((stacks_root / stack_id / "stack.yaml").read_text(encoding="utf-8"))
    layers_map = data.get("layers", {}) if isinstance(data, dict) else {}
    true_layers = [k for k in _LAYER_ORDER if isinstance(layers_map, dict) and layers_map.get(k)]
    level = max((_LAYER_ORDER.index(k) for k in true_layers), default=0)
    return Harness(
        stack_id=stack_id,
        name=str(data.get("name", stack_id)) if isinstance(data, dict) else stack_id,
        level=level,
        layers=true_layers,
        family=_STACK_FAMILY.get(stack_id, "agnostic"),
    )


def _model_ref(model_id: str) -> ModelRef:
    name, tier = _MODEL_REGISTRY.get(_alias(model_id), (_alias(model_id), "mid"))
    return ModelRef(model_id=model_id, name=name, tier=tier)


def _row_score(row: EvalRow) -> float | None:
    """Single 0-10 score for an EvalRow: final_score, else judge-aggregate mean."""
    if row.final_score is not None:
        return round(float(row.final_score), 2)
    agg = row.judge_aggregate
    if agg is not None and agg.median_per_criterion:
        return round(statistics.mean(agg.median_per_criterion.values()), 2)
    return None


# ---------------------------------------------------------------------------
# Emitter
# ---------------------------------------------------------------------------


def build_board(
    eval_rows: list[EvalRow],
    *,
    stacks_root: Path,
    run_hash: str,
    run_type: str = "weekly",
    methodology_version: str = "v0.1.0",
    region: str = "eu-central",
    solved_threshold: float = 6.0,
    illustrative: bool = False,
) -> Board:
    """Aggregate scored EvalRows into the public Board.

    One cell per (model_id, stack_id). per_task holds each task's score/cost;
    mean_* average across the cell's tasks. quality_per_dollar = mean_score /
    mean_cost. ``on_frontier`` is left False (the site computes it client-side).
    FAILED rows contribute cost (transparency) but a null score.
    """
    # group rows by (model_id, stack_id) then task_id
    by_cell: dict[tuple[str, str], dict[str, list[EvalRow]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in eval_rows:
        by_cell[(r.model_id, r.stack_id)][r.task_id].append(r)

    model_ids = sorted({m for m, _ in by_cell})
    stack_ids = sorted({s for _, s in by_cell})
    task_ids = sorted({r.task_id for r in eval_rows})

    cells: list[Cell] = []
    any_scored = False
    for (model_id, stack_id), tasks in sorted(by_cell.items()):
        per_task: dict[str, TaskScore] = {}
        for task_id, rows in tasks.items():
            scores = [s for r in rows if (s := _row_score(r)) is not None]
            costs = [float(r.stats.cost_usd) for r in rows]
            per_task[task_id] = TaskScore(
                score=round(statistics.median(scores), 2) if scores else None,
                cost_usd=round(statistics.mean(costs), 6) if costs else 0.0,
            )
        cell_scores = [t.score for t in per_task.values() if t.score is not None]
        cell_costs = [t.cost_usd for t in per_task.values()]
        all_rows = [r for rows in tasks.values() for r in rows]
        latencies = [r.stats.wall_clock_ms for r in all_rows]
        mean_score = round(statistics.mean(cell_scores), 2) if cell_scores else None
        mean_cost = round(statistics.mean(cell_costs), 6) if cell_costs else 0.0
        if mean_score is not None:
            any_scored = True
        cells.append(
            Cell(
                model_id=model_id,
                stack_id=stack_id,
                mean_score=mean_score,
                mean_cost_usd=mean_cost,
                mean_latency_ms=int(statistics.mean(latencies)) if latencies else 0,
                quality_per_dollar=(
                    round(mean_score / mean_cost, 2)
                    if mean_score is not None and mean_cost > 0
                    else None
                ),
                per_task=per_task,
            )
        )

    return Board(
        run_hash=run_hash,
        run_type=run_type,
        methodology_version=methodology_version,
        region=region,
        scored=any_scored,
        illustrative=illustrative,
        solved_threshold=solved_threshold,
        harnesses=[_harness_from_yaml(s, stacks_root) for s in stack_ids],
        models=[_model_ref(m) for m in model_ids],
        tasks=task_ids,
        cells=cells,
    )


def _statuses_present(eval_rows: list[EvalRow]) -> set[EvalStatus]:
    """Helper for callers/tests: which EvalStatus values are in the set."""
    return {r.status for r in eval_rows}
