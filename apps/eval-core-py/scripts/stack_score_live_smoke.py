#!/usr/bin/env python
"""Live: aider x qwen-3-14b x be_01 -> patch -> JUDGE PANEL -> FIRST scored number.

RFC-006 Phase 4. Chains Half A (StackExecutor) + the Half A->B bridge
(stack_scoring) + the operational judge panel (#28). Judges are used (not the
be_01 deterministic evaluators, which invert — EVID-027); judged-subjective
scoring is also POLLMEVALS' edge.

Cost: ~$0.0006 (aider on qwen) + ~$0.05 (3 judges). Gated by --confirm-spend.

Prereqs: make stack-up && make sandbox-net-up && make harness-image-aider.
Run:
  uv run --project apps/eval-core-py python \
      apps/eval-core-py/scripts/stack_score_live_smoke.py --confirm-spend
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import statistics
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "apps" / "eval-core-py"))

from src.orchestrator.cost import PricingTuple  # noqa: E402
from src.orchestrator.judge_panel import JudgePanel  # noqa: E402
from src.orchestrator.stack_executor import (  # noqa: E402
    DockerHarnessLauncher,
    ExecStatus,
    StackAdapter,
    StackExecRequest,
    StackExecutor,
)
from src.orchestrator.stack_scoring import (  # noqa: E402
    cost_with_judges,
    exec_result_to_eval_result,
)

_CANDIDATE = "openrouter/qwen/qwen-3-14b"
_TASK = "be_01_jwt_auth"
_JUDGES = ["claude-sonnet-4-6-judge", "gpt-5-mini-judge", "gemini-3-flash"]
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


def _seed_candidate_snapshot(dst: Path, pack: Path) -> None:
    """be_01 CANDIDATE workspace: pinned deps only — NO gold, NO tests."""
    for f in ("package.json", "tsconfig.json"):
        shutil.copy(pack / "gold" / f, dst / f)
    (dst / "solution.ts").write_text(
        "// Implement the Express JWT auth middleware here (see the task prompt).\n",
        encoding="utf-8",
    )


async def _main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-spend", action="store_true", help="real $ (aider + judges)")
    args = ap.parse_args()

    # JudgePanel resolves rubric.yaml relative to cwd; anchor at the repo root.
    os.chdir(REPO)
    _load_env(REPO)
    master_key = os.environ.get("LITELLM_MASTER_KEY", "")
    if not master_key:
        print("ERROR: LITELLM_MASTER_KEY not set (.env)", file=sys.stderr)
        return 2
    if not args.confirm_spend:
        print("DRY: pass --confirm-spend to run aider + 3 judges for real (~$0.05).")
        return 0

    pack = REPO / "evals" / "task-packs" / _TASK
    prompt = str(yaml.safe_load((pack / "task.yaml").read_text())["prompt_template"])
    adapter = StackAdapter.from_yaml_path(REPO / "stacks" / "aider" / "stack.yaml")

    snapshot = Path(tempfile.mkdtemp(prefix="pollmevals-score-"))
    _seed_candidate_snapshot(snapshot, pack)
    artifacts = snapshot / "artifacts"

    # --- Half A: harness -> patch ---
    print(f"[1/3] Half A: aider x qwen x {_TASK} ...")
    executor = StackExecutor(
        launcher=DockerHarnessLauncher(),
        api_key=master_key,
        pricing_snapshot={_CANDIDATE: _QWEN_PRICING},
    )
    request = StackExecRequest(
        eval_id="score-aider-qwen-be01",
        model_id=_CANDIDATE,
        model_alias="qwen-3-14b",
        stack=adapter,
        task_id=_TASK,
        task_prompt=prompt,
        repo_snapshot_dir=snapshot,
        seed=1,
        timeout_s=600,
    )
    exec_result = await executor.execute(request)
    print(
        f"      status={exec_result.status} cost=${exec_result.cost_usd} "
        f"wall={exec_result.wall_ms}ms"
    )
    if exec_result.status is not ExecStatus.OK:
        print(f"      executor did not produce a patch: {exec_result.error_detail}")
        return 1

    # --- Bridge: Half A -> Half B ---
    print("[2/3] bridge: StackExecResult -> EvalResult (write submission artifact)")
    eval_result = exec_result_to_eval_result(exec_result, log_dir=artifacts)

    # --- Half B: judge panel (inversion-free) ---
    print(f"[3/3] Half B: {len(_JUDGES)} judges score the patch via the be_01 rubric ...")
    panel = JudgePanel(
        judge_models=_JUDGES,
        candidate_model_id=_CANDIDATE,
        rubric_version="1.0",
    )
    judgments = await panel.score(eval_result, _TASK)
    agg = panel.aggregate(judgments)

    judge_cost = sum((j.cost_usd for j in judgments), Decimal("0"))
    total = cost_with_judges(exec_result.cost_usd, judge_cost)

    print("\n=== FIRST SCORED (model x harness x task) NUMBER ===")
    print(f"stack:        aider x qwen-3-14b   task: {_TASK}")
    for j in judgments:
        print(f"  judge {j.judge_model_id:<24} total={j.total_score:5.2f} cost=${j.cost_usd}")
    panel_median = statistics.median([j.total_score for j in judgments]) if judgments else 0.0
    print(f"panel median: {panel_median:.2f} / 10   (per-criterion: {agg.median_per_criterion})")
    print(
        f"alpha:        point={agg.alpha_point} ci_lower={agg.alpha_ci_lower} "
        f"status={agg.judge_status}"
    )
    print(f"cost:         harness=${exec_result.cost_usd} + judges=${judge_cost} = ${total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
