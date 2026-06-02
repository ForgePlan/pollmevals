#!/usr/bin/env python
"""Live smoke: aider x qwen-3-14b x be_01 -> a REAL patch via the bastion proxy.

RFC-006 Phase 3 first real run (Half A: harness -> patch). Proves the whole
candidate pipeline end-to-end with real money: StackExecutor -> the aider image
on the `pollmevals-sandbox` internal net -> the LiteLLM proxy (metered) -> a
captured git diff.

Cost: a fraction of a cent on qwen-3-14b. Spend is real, so it is gated behind
--confirm-spend (mirrors scripts/smoke_run.py).

Prerequisites:
  make stack-up          # proxy healthy
  make sandbox-net-up    # proxy attached to pollmevals-sandbox (decision A)
  make harness-image-aider

Run:
  uv run --project apps/eval-core-py python \
      apps/eval-core-py/scripts/stack_exec_live_smoke.py --confirm-spend
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "apps" / "eval-core-py"))

from src.orchestrator.cost import PricingTuple  # noqa: E402
from src.orchestrator.stack_executor import (  # noqa: E402
    SANDBOX_NETWORK,
    DockerHarnessLauncher,
    ExecStatus,
    HarnessRunPlan,
    NetworkPolicy,
    StackAdapter,
    StackExecRequest,
    StackExecutor,
)

# qwen-3-14b approximate OpenRouter pricing (per Mtoken). Informational for the
# smoke; the proxy is the metered source of truth for production reconciliation.
_QWEN_PRICING = PricingTuple(
    model_id="openrouter/qwen/qwen-3-14b",
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
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _seed_candidate_snapshot(dst: Path, pack: Path) -> None:
    """Seed a be_01 CANDIDATE workspace: pinned deps only — NO gold, NO tests."""
    gold = pack / "gold"
    for f in ("package.json", "tsconfig.json"):
        shutil.copy(gold / f, dst / f)
    (dst / "solution.ts").write_text(
        "// Implement the Express JWT auth middleware here (see the task prompt).\n",
        encoding="utf-8",
    )


async def _plumbing_check() -> int:
    """$0 end-to-end check of _run_sync: container on the bastion net writes to
    /workspace via a NO-MODEL command; the launcher must capture the diff."""
    snap = Path(tempfile.mkdtemp(prefix="pollmevals-plumb-"))
    (snap / "seed.txt").write_text("seed\n", encoding="utf-8")
    plan = HarnessRunPlan(
        image="pollmevals-harness-aider:0.1.0",
        command=["sh", "-c", "echo 'export const x = 1;' > /workspace/new.ts"],
        workdir="/workspace",
        mount_dir=snap,
        environment={},
        config_files={},
        timeout_s=60,
        network_policy=NetworkPolicy.PROXY_ONLY,
        proxy_host="pollmevals-litellm-proxy",
        proxy_port=4000,
        sandbox_network=SANDBOX_NETWORK,
    )
    outcome = await DockerHarnessLauncher().launch(plan)
    print(f"exit={outcome.exit_code} timed_out={outcome.timed_out} wall_ms={outcome.wall_ms}")
    print("--- captured patch ---\n" + outcome.patch)
    ok = "new.ts" in outcome.patch and outcome.exit_code == 0 and not outcome.timed_out
    print("PLUMBING OK ✅" if ok else "PLUMBING FAILED ❌")
    return 0 if ok else 1


async def _main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-spend", action="store_true", help="actually run (real $)")
    ap.add_argument("--plumbing", action="store_true", help="$0 no-model docker/patch check")
    ap.add_argument("--model-alias", default="qwen-3-14b")
    args = ap.parse_args()

    if args.plumbing:
        return await _plumbing_check()

    _load_env(REPO)
    master_key = os.environ.get("LITELLM_MASTER_KEY", "")
    if not master_key:
        print("ERROR: LITELLM_MASTER_KEY not set (.env)", file=sys.stderr)
        return 2

    if not args.confirm_spend:
        print("DRY: pass --confirm-spend to run aider x qwen x be_01 for real (~<$0.01).")
        return 0

    pack = REPO / "evals" / "task-packs" / "be_01_jwt_auth"
    prompt = str(yaml.safe_load((pack / "task.yaml").read_text())["prompt_template"])
    adapter = StackAdapter.from_yaml_path(REPO / "stacks" / "aider" / "stack.yaml")

    snapshot = Path(tempfile.mkdtemp(prefix="pollmevals-be01-"))
    _seed_candidate_snapshot(snapshot, pack)

    executor = StackExecutor(
        launcher=DockerHarnessLauncher(),
        api_key=master_key,
        pricing_snapshot={"openrouter/qwen/qwen-3-14b": _QWEN_PRICING},
    )
    request = StackExecRequest(
        eval_id="smoke-aider-qwen-be01",
        model_id="openrouter/qwen/qwen-3-14b",
        model_alias=args.model_alias,
        stack=adapter,
        task_id="be_01_jwt_auth",
        task_prompt=prompt,
        repo_snapshot_dir=snapshot,
        seed=1,
        timeout_s=600,
    )

    print(f"Running aider x {args.model_alias} x be_01 in {snapshot} ...")
    result = await executor.execute(request)

    print("\n=== RESULT ===")
    print(f"status:       {result.status}")
    print(f"error_detail: {result.error_detail}")
    print(f"tokens:       in={result.input_tokens} out={result.output_tokens}")
    print(f"cost_usd:     {result.cost_usd}")
    print(f"wall_ms:      {result.wall_ms}")
    if result.patch:
        out = snapshot / "captured.patch"
        out.write_text(result.patch, encoding="utf-8")
        nlines = result.patch.count("\n")
        print(f"patch:        {nlines} lines -> {out}")
        print("\n--- patch head (40 lines) ---")
        print("\n".join(result.patch.splitlines()[:40]))
    else:
        print("patch:        (none)")
        print("\n--- trace tail (30 lines) ---")
        print("\n".join(result.trace.splitlines()[-30:]))

    return 0 if result.status is ExecStatus.OK else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
