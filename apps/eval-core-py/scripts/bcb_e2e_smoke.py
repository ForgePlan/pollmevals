#!/usr/bin/env python
"""BCB e2e smoke — prove PythonCorrectnessEvaluator runs a real bcb-* pack.

Uses each pack's GOLD solution as the candidate (known-good → the gold suite
must pass → pass_rate ~1.0). Exercises the full path: assemble solution.py +
namespace-wired test + runner → mount read-only → run unittest in the
pollmevals-eval-py sandbox → parse → score.

Prereq: make eval-image-py  (+ Docker running). Run from anywhere:
  uv run --project apps/eval-core-py \\
      python apps/eval-core-py/scripts/bcb_e2e_smoke.py [bcb-0000 bcb-0006 ...]
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "apps" / "eval-core-py"))

from src.evaluators.python_correctness_evaluator import PythonCorrectnessEvaluator  # noqa: E402


def _ensure_docker_host() -> None:
    """macOS Docker Desktop puts the socket under ~/.docker/run — docker-py's
    from_env() won't find it unless DOCKER_HOST points there (same gotcha as
    DockerHarnessLauncher)."""
    if os.environ.get("DOCKER_HOST"):
        return
    for cand in (Path.home() / ".docker/run/docker.sock", Path("/var/run/docker.sock")):
        if cand.exists():
            os.environ["DOCKER_HOST"] = f"unix://{cand}"
            return


async def _run_one(packs_root: Path, pack: str) -> bool:
    gold_sol = packs_root / pack / "gold" / "solution.py"
    if not gold_sol.exists():
        print(f"  {pack}: SKIP — no gold/solution.py")
        return False
    cand = Path(tempfile.mkdtemp(prefix=f"bcb-cand-{pack}-"))
    try:
        shutil.copy(gold_sol, cand / "solution.py")
        ev = PythonCorrectnessEvaluator(packs_root=packs_root, timeout_s=120)
        r = await ev.evaluate(str(cand), pack)
    finally:
        shutil.rmtree(cand, ignore_errors=True)

    ok = (not r.skipped) and r.score >= 0.99
    tag = "PASS" if ok else ("SKIP" if r.skipped else "FAIL")
    print(f"  {pack}: {tag} score={r.score} findings={r.findings_count} ({r.library_version})")
    if r.skipped:
        print(f"      skip_reason: {r.skip_reason}")
    elif not ok:
        print(f"      {r.raw_output.splitlines()[1] if r.raw_output else ''}")
    return ok


async def _main() -> int:
    _ensure_docker_host()
    packs_root = REPO / "evals" / "task-packs"
    packs = sys.argv[1:] or ["bcb-0000"]
    print(f"BCB e2e smoke — {len(packs)} pack(s), gold solution vs gold tests:")
    results = [await _run_one(packs_root, p) for p in packs]
    passed = sum(results)
    print(f"\n{passed}/{len(packs)} packs scored gold solution at >=0.99 pass-rate")
    return 0 if passed == len(packs) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
