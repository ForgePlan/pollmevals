#!/usr/bin/env python
"""Run a small REAL grid → emit the site's board.json (RFC-006 Phase 4c).

Validates the Phase-4b dispatch live AND produces real data: GridRunner routes
raw-llm → InspectEvalCaller (real task prompt) and aider → StackExecutorCaller,
the judge panel scores both, and the Board emitter writes
apps/site/public/board.json (illustrative: false).

Grid (default): raw-llm + aider x qwen-3-14b x be_01 = 2 cells. Cost ~$0.25
(judges dominate). Gated by --confirm-spend.

Prereqs: make stack-up && make sandbox-net-up && make harness-image-aider.
Run from anywhere (the script chdir's to the repo root):
  uv run --project apps/eval-core-py \\
      python apps/eval-core-py/scripts/build_real_board.py --confirm-spend
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "apps" / "eval-core-py"))

from src.contracts import EvalRow  # noqa: E402
from src.leaderboard.board import Board, build_board  # noqa: E402
from src.orchestrator.cost import BudgetGate, PricingTuple, compute_cost  # noqa: E402
from src.orchestrator.eval_caller import EvalResult, InspectEvalCaller  # noqa: E402
from src.orchestrator.grid_runner import GridRunner, GridSpec  # noqa: E402
from src.orchestrator.journal import JournalWriter  # noqa: E402
from src.orchestrator.judge_panel import JudgePanel  # noqa: E402
from src.orchestrator.stack_caller import (  # noqa: E402
    StackExecutorCaller,
    make_be01_snapshot_provider,
    make_task_prompt_provider,
    make_task_timeout_provider,
)
from src.orchestrator.stack_executor import (  # noqa: E402
    SANDBOX_PROXY_BASE_URL,
    DockerHarnessLauncher,
    StackExecutor,
)

# Candidate ladder — OPEN models only (cheap→strong). Judges are the closed
# frontier (claude/gpt/gemini), so open candidates never trigger self-judging.
# Non-cartesian grid: raw-llm runs on every candidate (a model-only baseline);
# aider only on models that actually follow its edit format. qwen (14b/32b)
# does; llama-70b and deepseek-v3.5 loop and time out (a real harness-compat
# signal, EVID prior) so they stay raw-llm-only here.
# Coding-model ladder by family, cheap→expensive (a broad capability sweep),
# topped by a frontier-open tier ("more powerful" candidates). raw-llm runs on
# all; aider only on the strong coders that follow its edit format.
_RAW_MODELS = [
    # Qwen
    "qwen-3-14b",
    "qwen3-coder-30b",
    "qwen-3-32b",
    "qwen3-235b",
    # DeepSeek
    "deepseek-v3-2",
    "deepseek-v3-5",
    "deepseek-v4-pro",
    # Mistral (coding)
    "codestral",
    "devstral",
    # Llama
    "llama-3-1-8b",
    "llama-3-3-70b",
    "llama-4-scout",
    # GLM
    "glm-4-32b",
    "glm-4-7",
    "glm-5",
    # frontier-open
    "kimi-k2-5",
    "grok-4",
]
_AIDER_MODELS = ["qwen-3-14b", "qwen3-coder-30b", "codestral", "devstral"]
# goose runs the SAME coder models as aider, so each (model) gives a directly
# comparable pair — isolating the harness variable (aider L4 vs goose L2 on
# identical models). Diverge this list later if goose handles models aider can't.
_GOOSE_MODELS = ["qwen-3-14b", "qwen3-coder-30b", "codestral", "devstral"]
# opencode (sst): model-agnostic, same coder models → directly comparable.
_OPENCODE_MODELS = ["qwen-3-14b", "qwen3-coder-30b", "codestral", "devstral"]
# Crush (charmbracelet): model-agnostic, same coder models for a clean comparison.
_CRUSH_MODELS = ["qwen-3-14b", "qwen3-coder-30b", "codestral", "devstral"]
# Cline: model-agnostic; same coder models (qwen-3-14b is too weak for its
# tool-use — a real compat data point; the stronger coders work).
_CLINE_MODELS = ["qwen-3-14b", "qwen3-coder-30b", "codestral", "devstral"]
# Per-stack candidate model lists for --add-stack (merge ONE harness column in).
_STACK_MODELS = {
    "aider": _AIDER_MODELS,
    "goose": _GOOSE_MODELS,
    "opencode": _OPENCODE_MODELS,
    "crush": _CRUSH_MODELS,
    "cline": _CLINE_MODELS,
}
_SEEDS = [1, 2]
_TASK = "be_01_jwt_auth"
_JUDGES = ["claude-sonnet-4-6-judge", "gpt-5-mini-judge", "gemini-3-flash"]
_RUN_HASH = "sha256:" + "realboard".ljust(58, "0")[:58]
_SNAP = datetime(2026, 6, 3, tzinfo=UTC)


# Approximate OpenRouter pricing (per Mtoken, in/out) — informational; the proxy
# meters the authoritative spend. Drives raw-llm cost + quality-per-$ on the board.
def _pt(mid: str, pin: str, pout: str) -> PricingTuple:
    return PricingTuple(mid, Decimal(pin), Decimal(pout), _SNAP)


_PRICING = {
    "qwen-3-14b": _pt("qwen-3-14b", "0.07", "0.24"),
    "qwen3-coder-30b": _pt("qwen3-coder-30b", "0.07", "0.27"),
    "qwen-3-32b": _pt("qwen-3-32b", "0.08", "0.28"),
    "qwen3-235b": _pt("qwen3-235b", "0.07", "0.10"),
    "deepseek-v3-2": _pt("deepseek-v3-2", "0.23", "0.34"),
    "deepseek-v3-5": _pt("deepseek-v3-5", "0.30", "0.90"),
    "deepseek-v4-pro": _pt("deepseek-v4-pro", "0.43", "0.87"),
    "codestral": _pt("codestral", "0.30", "0.90"),
    "devstral": _pt("devstral", "0.40", "2.00"),
    "llama-3-1-8b": _pt("llama-3-1-8b", "0.02", "0.05"),
    "llama-3-3-70b": _pt("llama-3-3-70b", "0.10", "0.32"),
    "llama-4-scout": _pt("llama-4-scout", "0.08", "0.30"),
    "glm-4-32b": _pt("glm-4-32b", "0.10", "0.10"),
    "glm-4-7": _pt("glm-4-7", "0.40", "1.75"),
    "glm-5": _pt("glm-5", "0.60", "2.08"),
    "kimi-k2-5": _pt("kimi-k2-5", "0.40", "1.90"),
    "grok-4": _pt("grok-4", "3.00", "15.00"),
}

# Reasoning-heavy candidates that exhausted a 4-8k budget on reasoning_tokens and
# returned empty content. Give them a large output budget (their model size) so
# reasoning + answer both fit. Non-reasoning models stay at the 4096 default.
_REASONING_HEAVY = {"glm-5", "kimi-k2-5", "qwen-3-32b", "glm-4-7"}
# A large output budget so reasoning_tokens + the answer both fit, without the
# 32k generations that make a full re-run take hours. If they still finish=length
# with empty content here, they're unscoreable as bare completion (a finding).
_REASONING_MAX_TOKENS = 16000


def _max_tokens_for(model_id: str) -> int:
    return _REASONING_MAX_TOKENS if model_id in _REASONING_HEAVY else 4096


def _load_env(repo: Path) -> None:
    envf = repo / ".env"
    if not envf.exists():
        return
    for line in envf.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _rows_from_result(result: object, pricing: dict[str, PricingTuple]) -> list[EvalRow]:
    """Collect EvalRows, reconciling any zero cost from token counts.

    InspectEvalCaller (raw-llm) leaves stats.cost_usd=0 for the post-run
    CostReconciler; compute it here so the Board's raw-llm cost + q/$ are real.
    """
    rows: list[EvalRow] = []
    for r in getattr(result, "results", []):
        if not (isinstance(r, EvalResult) and r.eval_row is not None):
            continue
        row = r.eval_row
        if row.stats.cost_usd == 0 and row.model_id in pricing:
            stats = row.stats.model_copy(
                update={"cost_usd": compute_cost(row.stats, pricing[row.model_id])}
            )
            row = row.model_copy(update={"stats": stats})
        rows.append(row)
    return rows


async def _main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-spend", action="store_true", help="real $ (~$0.25)")
    ap.add_argument(
        "--fill",
        default="",
        help="comma-separated models to re-run on raw-llm and MERGE into the "
        "existing board.json (fills previously-failed cells without re-running "
        "the rest). e.g. --fill grok-4",
    )
    ap.add_argument(
        "--add-stack",
        default="",
        help="run ONLY this stack's grid (on _STACK_MODELS[stack]) and MERGE its "
        "new harness column (cells + harness metadata) into the existing "
        "board.json, without re-spending on the other harnesses. e.g. "
        "--add-stack goose",
    )
    args = ap.parse_args()

    os.chdir(REPO)
    _load_env(REPO)
    key = os.environ.get("LITELLM_MASTER_KEY", "")
    if not key:
        print("ERROR: LITELLM_MASTER_KEY not set (.env)", file=sys.stderr)
        return 2
    if not args.confirm_spend:
        n = (len(_RAW_MODELS) + len(_AIDER_MODELS)) * len(_SEEDS)
        print(
            f"DRY: pass --confirm-spend to run {n} evals "
            f"(raw-llm x {_RAW_MODELS} + aider x {_AIDER_MODELS}, {len(_SEEDS)} seeds)."
        )
        return 0

    log_dir = Path(tempfile.mkdtemp(prefix="pollmevals-board-"))
    prompt_provider = make_task_prompt_provider(REPO)
    stacks_root = REPO / "stacks"

    # raw-llm: model completion with the REAL task prompt + a real solution budget.
    inspect_caller = InspectEvalCaller(
        log_dir=log_dir,
        litellm_base_url="http://localhost:4000",
        api_key=key,
        prompt_provider=prompt_provider,
        max_tokens=4096,
        # Reasoning-heavy models spend the whole budget on reasoning_tokens and
        # return empty content at 4-8k; give them their full output size so the
        # reasoning AND the answer fit. (Billed by actual usage, so the larger
        # cap costs nothing for models that stop early.)
        max_tokens_for=_max_tokens_for,
    )
    # aider: harness → patch via the sandbox bastion.
    stack_caller = StackExecutorCaller(
        executor=StackExecutor(
            launcher=DockerHarnessLauncher(),
            proxy_base_url=SANDBOX_PROXY_BASE_URL,
            api_key=key,
            pricing_snapshot=_PRICING,
        ),
        stacks_root=stacks_root,
        snapshot_provider=make_be01_snapshot_provider(REPO),
        prompt_provider=prompt_provider,
        log_dir=log_dir,
        run_hash=_RUN_HASH,
    )

    def caller_for(stack_id: str) -> object:
        return stack_caller if stack_id != "raw-llm" else inspect_caller

    # candidate_model_id only drives self-judging exclusion; all candidates are
    # open (non-judge-family), so any is safe here.
    panel = JudgePanel(
        judge_models=_JUDGES, candidate_model_id=_RAW_MODELS[0], rubric_version="1.0"
    )
    runner = GridRunner(
        caller=inspect_caller,
        caller_for_stack=caller_for,  # type: ignore[arg-type]
        journal_writer=JournalWriter(log_dir / "journal.ndjson"),
        budget_gate=BudgetGate(cap_usd=Decimal("5")),
        pricing_snapshot=_PRICING,
        judge_panel=panel,
        # JudgePanel now guards inspect_ai eval_async with a module-level
        # asyncio.Lock (_EVAL_ASYNC_LOCK), so concurrent evals are safe: the
        # judge step serializes on the lock while candidate calls overlap. 3-way
        # overlap cuts wall-clock ~3x; capped at 3 to bound parallel aider
        # containers (memory) during the aider spec.
        max_concurrent=3,
    )
    timeout_of = make_task_timeout_provider(REPO)
    # per-task wall-clock budget by difficulty (be_01 is medium -> 600s), so slow
    # model x harness pairs aren't cut off at the 300s default.
    task_timeout = {t: timeout_of(t) for t in [_TASK]}
    out = REPO / "apps" / "site" / "public" / "board.json"

    # --fill: re-run ONLY the named models on raw-llm and merge their cells into
    # the existing board.json (fills previously-failed cells, leaves the rest).
    if args.fill:
        fill_models = [m.strip() for m in args.fill.split(",") if m.strip()]
        print(f"FILL: raw-llm x {fill_models} → merge into {out.name} ...")
        result = await runner.run(
            GridSpec(
                run_hash=_RUN_HASH,
                models=fill_models,
                tasks=[_TASK],
                stacks=["raw-llm"],
                seeds=_SEEDS,
                task_timeout_s=task_timeout,
            )
        )
        rows = _rows_from_result(result, _PRICING)
        partial = build_board(rows, stacks_root=stacks_root, run_hash=_RUN_HASH, run_type="smoke")
        existing = Board.model_validate_json(out.read_text(encoding="utf-8"))
        new_by_key = {(c.model_id, c.stack_id): c for c in partial.cells}
        merged = [new_by_key.get((c.model_id, c.stack_id), c) for c in existing.cells]
        scored_now = sum(1 for c in merged if c.mean_score is not None)
        existing = existing.model_copy(update={"cells": merged, "scored": scored_now > 0})
        out.write_text(existing.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"  board now {scored_now}/{len(merged)} cells scored. filled:")
        for c in partial.cells:
            print(f"    {c.stack_id} x {c.model_id}: score={c.mean_score} cost=${c.mean_cost_usd}")
        return 0

    # --add-stack: run ONLY this harness's grid and merge its NEW column (cells +
    # harness metadata) into the existing board.json, without re-spending on the
    # other harnesses. Unlike --fill (replace cells in place), this also unions
    # the new harness into board.harnesses so the matrix renders the column.
    if args.add_stack:
        stack_id = args.add_stack
        models = _STACK_MODELS.get(stack_id, _AIDER_MODELS)
        print(f"ADD-STACK: {stack_id} x {models} → merge column into {out.name} ...")
        result = await runner.run(
            GridSpec(
                run_hash=_RUN_HASH,
                models=models,
                tasks=[_TASK],
                stacks=[stack_id],
                seeds=_SEEDS,
                task_timeout_s=task_timeout,
            )
        )
        rows = _rows_from_result(result, _PRICING)
        partial = build_board(rows, stacks_root=stacks_root, run_hash=_RUN_HASH, run_type="smoke")
        existing = Board.model_validate_json(out.read_text(encoding="utf-8"))
        # Replace-or-append cells by (model, stack); union harnesses + models.
        by_key = {(c.model_id, c.stack_id): c for c in existing.cells}
        for c in partial.cells:
            by_key[(c.model_id, c.stack_id)] = c
        h_by_id = {h.stack_id: h for h in existing.harnesses}
        for h in partial.harnesses:
            h_by_id[h.stack_id] = h
        m_by_id = {m.model_id: m for m in existing.models}
        for m in partial.models:
            m_by_id.setdefault(m.model_id, m)
        cells = list(by_key.values())
        scored_now = sum(1 for c in cells if c.mean_score is not None)
        merged_board = existing.model_copy(
            update={
                "cells": cells,
                "harnesses": list(h_by_id.values()),
                "models": list(m_by_id.values()),
                "scored": scored_now > 0,
            }
        )
        out.write_text(merged_board.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"  board now {scored_now}/{len(cells)} cells scored. new {stack_id} cells:")
        for c in partial.cells:
            print(f"    {c.stack_id} x {c.model_id}: score={c.mean_score} cost=${c.mean_cost_usd}")
        return 0

    # Two specs so the grid is non-cartesian: raw-llm on every candidate, aider
    # only on the models that follow its edit format. Same run_hash + runner so
    # rows merge into one board.
    specs = [
        GridSpec(
            run_hash=_RUN_HASH,
            models=_RAW_MODELS,
            tasks=[_TASK],
            stacks=["raw-llm"],
            seeds=_SEEDS,
            task_timeout_s=task_timeout,
        ),
        GridSpec(
            run_hash=_RUN_HASH,
            models=_AIDER_MODELS,
            tasks=[_TASK],
            stacks=["aider"],
            seeds=_SEEDS,
            task_timeout_s=task_timeout,
        ),
    ]

    n = (len(_RAW_MODELS) + len(_AIDER_MODELS)) * len(_SEEDS)
    print(
        f"Running grid: raw-llm x {_RAW_MODELS} + aider x {_AIDER_MODELS} "
        f"x {_TASK} ({len(_SEEDS)} seeds) = {n} evals ..."
    )
    rows = []
    total_cost = Decimal("0")
    out = REPO / "apps" / "site" / "public" / "board.json"

    def _emit() -> None:
        board = build_board(rows, stacks_root=stacks_root, run_hash=_RUN_HASH, run_type="smoke")
        out.write_text(board.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"  -> wrote {out}: {len(board.cells)} cells, scored={board.scored}")

    # Incremental: write the board after EACH spec so a hang/crash in the slow
    # aider spec still leaves the full raw-llm board on disk.
    for spec in specs:
        print(f"\n--- spec: {spec.stacks[0]} x {spec.models} ---", flush=True)
        result = await runner.run(spec)
        rows += _rows_from_result(result, _PRICING)
        total_cost += result.total_cost_usd
        _emit()

    print(f"\n=== {len(rows)} eval rows, total cost ${total_cost} ===")
    for r in rows:
        score = r.judge_aggregate.median_per_criterion if r.judge_aggregate else None
        print(f"  {r.stack_id:<8} x {r.model_id:<16} status={r.status} score={score}")

    board = build_board(rows, stacks_root=stacks_root, run_hash=_RUN_HASH, run_type="smoke")
    print(f"\nFinal board: {len(board.cells)} cells, scored={board.scored}")
    for c in board.cells:
        print(
            f"    {c.stack_id:<8} x {c.model_id:<16}: score={c.mean_score} "
            f"cost=${c.mean_cost_usd} q/$={c.quality_per_dollar}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
