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
from src.leaderboard.board import build_board  # noqa: E402
from src.orchestrator.cost import BudgetGate, PricingTuple, compute_cost  # noqa: E402
from src.orchestrator.eval_caller import EvalResult, InspectEvalCaller  # noqa: E402
from src.orchestrator.grid_runner import GridRunner, GridSpec  # noqa: E402
from src.orchestrator.journal import JournalWriter  # noqa: E402
from src.orchestrator.judge_panel import JudgePanel  # noqa: E402
from src.orchestrator.stack_caller import (  # noqa: E402
    StackExecutorCaller,
    make_be01_snapshot_provider,
    make_task_prompt_provider,
)
from src.orchestrator.stack_executor import (  # noqa: E402
    SANDBOX_PROXY_BASE_URL,
    DockerHarnessLauncher,
    StackExecutor,
)

_CANDIDATE = "qwen-3-14b"  # proxy alias; InspectEvalCaller POSTs this as `model`
_TASK = "be_01_jwt_auth"
_JUDGES = ["claude-sonnet-4-6-judge", "gpt-5-mini-judge", "gemini-3-flash"]
_RUN_HASH = "sha256:" + "realboard".ljust(58, "0")[:58]
_QWEN_PRICING = PricingTuple(
    model_id=_CANDIDATE,
    input_per_mtoken_usd=Decimal("0.07"),
    output_per_mtoken_usd=Decimal("0.24"),
    snapshot_at=datetime(2026, 6, 2, tzinfo=UTC),
)


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
    args = ap.parse_args()

    os.chdir(REPO)
    _load_env(REPO)
    key = os.environ.get("LITELLM_MASTER_KEY", "")
    if not key:
        print("ERROR: LITELLM_MASTER_KEY not set (.env)", file=sys.stderr)
        return 2
    if not args.confirm_spend:
        print("DRY: pass --confirm-spend to run the real 2-cell grid (~$0.25).")
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
    )
    # aider: harness → patch via the sandbox bastion.
    stack_caller = StackExecutorCaller(
        executor=StackExecutor(
            launcher=DockerHarnessLauncher(),
            proxy_base_url=SANDBOX_PROXY_BASE_URL,
            api_key=key,
            pricing_snapshot={_CANDIDATE: _QWEN_PRICING},
        ),
        stacks_root=stacks_root,
        snapshot_provider=make_be01_snapshot_provider(REPO),
        prompt_provider=prompt_provider,
        log_dir=log_dir,
        run_hash=_RUN_HASH,
    )

    def caller_for(stack_id: str) -> object:
        return stack_caller if stack_id != "raw-llm" else inspect_caller

    panel = JudgePanel(judge_models=_JUDGES, candidate_model_id=_CANDIDATE, rubric_version="1.0")
    runner = GridRunner(
        caller=inspect_caller,
        caller_for_stack=caller_for,  # type: ignore[arg-type]
        journal_writer=JournalWriter(log_dir / "journal.ndjson"),
        budget_gate=BudgetGate(cap_usd=Decimal("5")),
        pricing_snapshot={_CANDIDATE: _QWEN_PRICING},
        judge_panel=panel,
        # FOLLOW-UP: JudgePanel uses inspect_ai eval_async, which forbids
        # concurrent calls — running evals in parallel crashes the judge step.
        # Serialize for now; the real fix is an asyncio.Lock in JudgePanel.score.
        max_concurrent=1,
    )
    spec = GridSpec(
        run_hash=_RUN_HASH,
        models=[_CANDIDATE],
        tasks=[_TASK],
        stacks=["raw-llm", "aider"],
        seeds=[1, 2, 3],
    )

    print("Running real grid: raw-llm + aider x qwen-3-14b x be_01 (3 seeds) ...")
    result = await runner.run(spec)
    rows = _rows_from_result(result, {_CANDIDATE: _QWEN_PRICING})

    print(f"\n=== {len(rows)} eval rows, total cost ${result.total_cost_usd} ===")
    for r in rows:
        score = r.judge_aggregate.median_per_criterion if r.judge_aggregate else None
        print(f"  {r.stack_id:<8} x {r.model_id:<12} status={r.status} score={score}")

    board = build_board(rows, stacks_root=stacks_root, run_hash=_RUN_HASH, run_type="smoke")
    out = REPO / "apps" / "site" / "public" / "board.json"
    out.write_text(board.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out}")
    print(f"  cells: {len(board.cells)}  scored: {board.scored}")
    for c in board.cells:
        print(
            f"    {c.stack_id:<8} x {c.model_id}: score={c.mean_score} "
            f"cost=${c.mean_cost_usd} q/$={c.quality_per_dollar}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
