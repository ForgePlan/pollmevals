"""Aggregate a Run manifest into a publishable leaderboard (one row per modelxstack).

Grouping: evals are bucketed by (model_id, stack_id). Cost / latency / token
aggregates come from `EvalStats` and are always present. Quality aggregates
(score + reliability) are computed from `EvalRow.final_score` and are `None`
when the run is unscored (e.g. a smoke run executed before the evaluators were
wired) — never invented.

Reliability uses the pass@k / pass^k machinery (src.scoring.pass_k): within a
(model, stack) entry, each task forms one "cell" = the per-seed solved-booleans,
and the entry's pass@k / pass^k / flaky are computed across those task cells.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import median

from pydantic import BaseModel, Field

from src.contracts import EvalRow, EvalStatus, Manifest
from src.scoring import flaky_fraction, pass_at_k, pass_hat_k

# A candidate "solves" a task at/above this final_score (0-10) by default.
# Reported alongside the leaderboard so the threshold is never hidden.
_DEFAULT_SOLVED_THRESHOLD = 6.0


class LeaderboardEntry(BaseModel):
    """One publishable row: a (model, stack) pair aggregated over tasks x seeds."""

    model_config = {"frozen": True}

    model_id: str
    stack_id: str

    # ── Coverage / status (always present) ──────────────────────────────────
    n_evals: int = Field(ge=0)
    n_scored: int = Field(ge=0)  # status == SCORED
    n_failed: int = Field(ge=0)
    n_tasks: int = Field(ge=0)  # distinct task_ids attempted
    n_seeds: int = Field(ge=0)  # distinct seeds attempted

    # ── Cost / efficiency (always present — the honest v0.1 signal) ─────────
    total_cost_usd: Decimal = Field(ge=Decimal(0))
    mean_cost_usd: Decimal = Field(ge=Decimal(0))
    total_tokens_in: int = Field(ge=0)
    total_tokens_out: int = Field(ge=0)
    mean_latency_ms: float = Field(ge=0)
    p50_latency_ms: float = Field(ge=0)

    # ── Quality / reliability (None until the run carries real scores) ──────
    mean_score: float | None = None  # mean final_score over scored evals
    pass_at_1: float | None = None  # fraction of scored evals that solved
    pass_at_k: float | None = None  # capability ceiling over task cells
    pass_hat_k: float | None = None  # reliability (solved every seed)
    flaky: float | None = None  # pass@k - pass^k


class Leaderboard(BaseModel):
    """The full publishable document for one Run."""

    model_config = {"frozen": True}

    run_hash: str
    run_type: str
    methodology_version: str
    region: str
    scored: bool  # True iff at least one eval carries a real final_score
    solved_threshold: float  # the pass@1/pass^k "solved" cutoff used
    n_models: int = Field(ge=0)
    n_stacks: int = Field(ge=0)
    n_tasks: int = Field(ge=0)
    entries: list[LeaderboardEntry]


def _entry_for_group(
    model_id: str,
    stack_id: str,
    rows: list[EvalRow],
    threshold: float,
) -> LeaderboardEntry:
    n_evals = len(rows)
    n_scored = sum(1 for r in rows if r.status == EvalStatus.SCORED)
    n_failed = sum(1 for r in rows if r.status == EvalStatus.FAILED)
    tasks = {r.task_id for r in rows}
    seeds = {r.seed for r in rows}

    total_cost = sum((r.stats.cost_usd for r in rows), Decimal(0))
    mean_cost = (total_cost / n_evals) if n_evals else Decimal(0)
    tokens_in = sum(r.stats.input_tokens for r in rows)
    tokens_out = sum(r.stats.output_tokens for r in rows)
    latencies = [float(r.stats.wall_clock_ms) for r in rows]
    mean_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
    p50_latency = float(median(latencies)) if latencies else 0.0

    # ── Quality: only when real scores exist ────────────────────────────────
    scored_vals = [r.final_score for r in rows if r.final_score is not None]
    mean_score: float | None = None
    pass1: float | None = None
    pak: float | None = None
    phk: float | None = None
    flaky: float | None = None
    if scored_vals:
        mean_score = sum(scored_vals) / len(scored_vals)
        solved_flags = [s >= threshold for s in scored_vals]
        pass1 = sum(1 for f in solved_flags if f) / len(solved_flags)
        # Reliability: one cell per task = its per-seed solved-booleans.
        cells: list[list[bool]] = []
        by_task: dict[str, list[bool]] = defaultdict(list)
        for r in rows:
            if r.final_score is not None:
                by_task[r.task_id].append(r.final_score >= threshold)
        cells = [v for v in by_task.values() if v]
        if cells:
            pak = pass_at_k(cells)
            phk = pass_hat_k(cells)
            flaky = flaky_fraction(cells)

    return LeaderboardEntry(
        model_id=model_id,
        stack_id=stack_id,
        n_evals=n_evals,
        n_scored=n_scored,
        n_failed=n_failed,
        n_tasks=len(tasks),
        n_seeds=len(seeds),
        total_cost_usd=total_cost,
        mean_cost_usd=mean_cost,
        total_tokens_in=tokens_in,
        total_tokens_out=tokens_out,
        mean_latency_ms=mean_latency,
        p50_latency_ms=p50_latency,
        mean_score=mean_score,
        pass_at_1=pass1,
        pass_at_k=pak,
        pass_hat_k=phk,
        flaky=flaky,
    )


def build_leaderboard(
    manifest: Manifest,
    *,
    solved_threshold: float = _DEFAULT_SOLVED_THRESHOLD,
) -> Leaderboard:
    """Aggregate a Run manifest into a publishable Leaderboard.

    Args:
        manifest: a loaded, immutable Run manifest.
        solved_threshold: final_score (0-10) at/above which an eval counts as
            "solved" for pass@1 / pass@k / pass^k. Recorded on the output so the
            cutoff is transparent.

    Returns:
        A Leaderboard with one entry per (model, stack), sorted by mean_score
        descending (scored runs) then by mean_cost ascending (cheaper first) —
        a stable, deterministic order. Quality fields are None on unscored runs.
    """
    groups: dict[tuple[str, str], list[EvalRow]] = defaultdict(list)
    for row in manifest.evals:
        groups[(row.model_id, row.stack_id)].append(row)

    entries = [
        _entry_for_group(model_id, stack_id, rows, solved_threshold)
        for (model_id, stack_id), rows in groups.items()
    ]
    # Deterministic order: best score first (None sorts last), then cheapest,
    # then model_id for a total tie-break.
    entries.sort(
        key=lambda e: (
            -(e.mean_score if e.mean_score is not None else -1.0),
            e.mean_cost_usd,
            e.model_id,
        )
    )

    scored = any(e.mean_score is not None for e in entries)
    return Leaderboard(
        run_hash=manifest.run_hash,
        run_type=str(manifest.run_type.value),
        methodology_version=manifest.methodology_version,
        region=str(manifest.region.value),
        scored=scored,
        solved_threshold=solved_threshold,
        n_models=len({e.model_id for e in entries}),
        n_stacks=len({e.stack_id for e in entries}),
        n_tasks=len({r.task_id for r in manifest.evals}),
        entries=entries,
    )
