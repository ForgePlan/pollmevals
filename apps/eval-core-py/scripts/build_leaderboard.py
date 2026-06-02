"""Emit a publishable leaderboard.json from a Run manifest.

Reads an immutable Run manifest, aggregates it (one row per modelxstack) via
src.leaderboard, and writes leaderboard.json next to the manifest (or to a path
you pass). This file is the data contract the public site (apps/site) consumes —
deterministic, UI-agnostic, and honest (cost/latency always; quality only when
the run carries real scores).

Usage:
    # newest run on disk -> its leaderboard.json
    uv run --project apps/eval-core-py python apps/eval-core-py/scripts/build_leaderboard.py

    # a specific manifest -> a specific output
    ... build_leaderboard.py --manifest artifacts/runs/<hash>/manifest.json --out /tmp/lb.json
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[3]
_APP = _REPO / "apps" / "eval-core-py"
sys.path.insert(0, str(_APP))

from src.contracts import Manifest  # noqa: E402
from src.leaderboard import build_leaderboard  # noqa: E402


def _pick_manifest_with_most_evals(paths: list[str]) -> str:
    def _n_evals(p: str) -> int:
        with open(p, encoding="utf-8") as fh:
            return len(json.load(fh).get("evals", []))

    return max(paths, key=_n_evals)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build leaderboard.json from a Run manifest.")
    parser.add_argument(
        "--manifest",
        type=str,
        default="",
        help="Path to manifest.json (default: the run with the most evals under artifacts/runs/).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="Output path (default: leaderboard.json next to the manifest).",
    )
    parser.add_argument(
        "--solved-threshold",
        type=float,
        default=6.0,
        help="final_score (0-10) at/above which an eval counts as solved (default: 6.0).",
    )
    args = parser.parse_args()

    manifest_path = args.manifest
    if not manifest_path:
        candidates = glob.glob(str(_REPO / "artifacts" / "runs" / "*" / "manifest.json"))
        if not candidates:
            print(
                "No manifests found under artifacts/runs/. Run a smoke run first.", file=sys.stderr
            )
            return 1
        manifest_path = _pick_manifest_with_most_evals(candidates)

    with open(manifest_path, encoding="utf-8") as fh:
        manifest = Manifest.model_validate(json.load(fh))

    leaderboard = build_leaderboard(manifest, solved_threshold=args.solved_threshold)

    out_path = args.out or str(pathlib.Path(manifest_path).parent / "leaderboard.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(leaderboard.model_dump_json(indent=2))

    q = "scored (quality + cost)" if leaderboard.scored else "unscored (cost/latency only)"
    print(
        f"Wrote {out_path}\n"
        f"  run={leaderboard.run_hash[:20]} type={leaderboard.run_type} {q}\n"
        f"  {leaderboard.n_models} models x {leaderboard.n_stacks} stacks x "
        f"{leaderboard.n_tasks} tasks -> {len(leaderboard.entries)} rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
