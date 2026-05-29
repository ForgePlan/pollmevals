"""fe_01 band-separation smoke test.

Runs CorrectnessEvaluator + CoverageEvaluator against each calibration band
(perfect / good / mediocre / poor / broken) for fe_01_multistep_form using the
live Docker sandbox (pollmevals-eval-ts:0.1.0).

Usage (from repo root):
    .venv/bin/python infra/scripts/verify-fe01-band-separation.py

Docker socket: defaults to the Docker Desktop macOS socket path. Override via
DOCKER_HOST env var if your daemon is elsewhere.

Requires:
    - pollmevals-eval-ts:0.1.0 Docker image built (see infra/docker/eval-ts/).
    - .venv populated: uv pip install pytest pytest-asyncio && uv pip install -e apps/eval-core-py
    - fe_01 gold/node_modules present: npm ci inside evals/task-packs/fe_01_multistep_form/gold/

Writes raw results to:
    artifacts/local/step3-eval-verify/fe_01/band_separation_results.json
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import shutil
import sys
import tempfile

# Wire the Docker Desktop macOS socket before any docker-py import.
# The docker-py SDK reads DOCKER_HOST; the CLI uses Docker contexts instead.
# On macOS with Docker Desktop the daemon socket is NOT at /var/run/docker.sock
# (that symlink doesn't exist) but at ~/.docker/run/docker.sock.
os.environ.setdefault(
    "DOCKER_HOST",
    f"unix://{pathlib.Path.home() / '.docker' / 'run' / 'docker.sock'}",
)

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps/eval-core-py/src"))

from evaluators.correctness_evaluator import CorrectnessEvaluator  # noqa: E402
from evaluators.coverage_evaluator import CoverageEvaluator  # noqa: E402

GOLD = REPO_ROOT / "evals/task-packs/fe_01_multistep_form/gold"
CALIBRATION = REPO_ROOT / "evals/task-packs/fe_01_multistep_form/calibration"
ARTIFACTS = REPO_ROOT / "artifacts/local/step3-eval-verify/fe_01"
TASK_ID = "fe_01_multistep_form"

# Source node_modules tree for the mounted workspace. Defaults to the gold
# pack's node_modules (host platform). Override with FE01_NODE_MODULES to point
# at a Linux-built tree when running on a non-Linux host: the sandbox image is
# linux/musl, so macOS-built native deps (rollup/esbuild) fail with
# MODULE_NOT_FOUND inside the container. Build a Linux tree with e.g.
#   docker run --rm -v "$PWD/build:/work" node:22.18-alpine \
#     sh -c "cd /work && npm install"  # against the pack's package.json+lock
NODE_MODULES_SRC = pathlib.Path(os.environ.get("FE01_NODE_MODULES", str(GOLD / "node_modules")))

BANDS = ["perfect", "good", "mediocre", "poor", "broken"]

# Primary gates from task spec comments:
#   perfect >= 0.85, broken <= 0.20
# Wider tolerance bands for intermediate levels (informational):
EXPECTED: dict[str, dict[str, float]] = {
    "perfect": {"min": 0.85, "max": 1.01},
    "good": {"min": 0.55, "max": 0.95},
    "mediocre": {"min": 0.25, "max": 0.75},
    "poor": {"min": 0.05, "max": 0.55},
    "broken": {"min": 0.00, "max": 0.20},
}


def _copy_node_modules_shared(tmp_root: pathlib.Path) -> pathlib.Path:
    """Copy gold node_modules once into a shared location inside tmp_root.

    Uses hardlinks (os.link via copy_function) + symlinks=True so that:
      - Regular files are hardlinked (same inode, no extra disk space on APFS).
      - Symlinks (e.g. node_modules/.bin/*) are recreated as symlinks with
        their original relative targets preserved.  Without symlinks=True,
        copytree dereferences symlinks into regular files — placing the
        vitest.mjs content at .bin/vitest causes Node ESM to resolve
        `import './dist/cli.js'` relative to .bin/ (wrong) instead of
        relative to vitest/ (correct), producing ERR_MODULE_NOT_FOUND.
    Falls back to a full file copy if os.link fails (e.g., cross-device).

    Returns the path to tmp_root/shared_node_modules.
    """
    shared = tmp_root / "shared_node_modules"
    if not shared.exists():
        try:
            shutil.copytree(
                NODE_MODULES_SRC,
                shared,
                symlinks=True,
                copy_function=os.link,
            )
        except OSError:
            # Cross-device or unsupported FS: fall back to regular copy.
            shutil.copytree(GOLD / "node_modules", shared, symlinks=True)
    return shared


def _build_submission_dir(
    band: str,
    tmp_root: pathlib.Path,
    shared_node_modules: pathlib.Path,
) -> pathlib.Path:
    """Create a workspace dir: gold test infra + calibration sample as solution.tsx.

    node_modules is placed as a REAL directory inside dst (not a symlink) so
    that Docker's bind-mount of dst as /workspace can resolve it.  A symlink
    to an absolute host path outside the mounted tree is dangling inside the
    container and causes npx --no vitest to attempt a network install
    (EAI_AGAIN, network_mode=none).

    We reuse the shared_node_modules tree (hardlinked from gold) to avoid
    copying 96 MB per band while keeping a self-contained directory per band.
    symlinks=True is mandatory to preserve .bin/* symlinks correctly.
    """
    dst = tmp_root / f"sub-{band}"
    dst.mkdir(parents=True)
    # Copy static test infrastructure from gold.
    for fname in ("package.json", "tsconfig.json", "tests.spec.tsx"):
        shutil.copy(GOLD / fname, dst / fname)
    # Place a real node_modules directory (hardlinked from shared) inside dst.
    # Docker bind-mounts dst as /workspace; a symlink to an outside path would
    # be dangling inside the container.
    try:
        shutil.copytree(
            shared_node_modules,
            dst / "node_modules",
            symlinks=True,
            copy_function=os.link,
        )
    except OSError:
        shutil.copytree(shared_node_modules, dst / "node_modules", symlinks=True)
    # Copy the calibration sample as solution.tsx (the name the tests import).
    sample = CALIBRATION / band / "sample-001.tsx"
    shutil.copy(sample, dst / "solution.tsx")
    return dst


async def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    correctness_ev = CorrectnessEvaluator()
    coverage_ev = CoverageEvaluator()

    results: dict[str, dict] = {}

    with tempfile.TemporaryDirectory(prefix="pollmevals-fe01-") as tmp_str:
        tmp_root = pathlib.Path(tmp_str)
        shared_nm = _copy_node_modules_shared(tmp_root)

        for band in BANDS:
            sub_dir = _build_submission_dir(band, tmp_root, shared_nm)
            print(f"\n{'=' * 60}\nBand: {band.upper()}\n{'=' * 60}")

            corr = await correctness_ev.evaluate(str(sub_dir), TASK_ID)
            cov = await coverage_ev.evaluate(str(sub_dir), TASK_ID)

            exp = EXPECTED[band]
            in_band = exp["min"] <= corr.score <= exp["max"]

            print(f"  correctness : score={corr.score:.4f}  skipped={corr.skipped}")
            if corr.skipped:
                print(f"    skip_reason: {corr.skip_reason}")
            print(f"  coverage    : score={cov.score:.4f}  skipped={cov.skipped}")
            if cov.skipped:
                print(f"    skip_reason: {cov.skip_reason}")
            print(
                f"  band check  : expected [{exp['min']:.2f}, {exp['max']:.2f}] → "
                f"{'PASS' if in_band else 'FAIL'}"
            )

            results[band] = {
                "correctness": {
                    "score": corr.score,
                    "skipped": corr.skipped,
                    "skip_reason": corr.skip_reason,
                    "findings_count": corr.findings_count,
                    "library_version": corr.library_version,
                },
                "coverage": {
                    "score": cov.score,
                    "skipped": cov.skipped,
                    "skip_reason": cov.skip_reason,
                    "findings_count": cov.findings_count,
                    "library_version": cov.library_version,
                },
                "expected_range": exp,
                "correctness_in_band": in_band,
            }

    out = ARTIFACTS / "band_separation_results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults written -> {out}")

    # Summary table
    print("\n" + "=" * 78)
    print("BAND SEPARATION SUMMARY (correctness)")
    print("=" * 78)
    print(f"{'Band':<12} {'Score':>8} {'Expected':>18} {'Pass?':>6}  {'Coverage':>10}")
    print("-" * 78)
    all_pass = True
    for band in BANDS:
        r = results[band]
        corr_score = r["correctness"]["score"]
        cov_score = r["coverage"]["score"]
        exp = r["expected_range"]
        in_band = r["correctness_in_band"]
        if not in_band:
            all_pass = False
        cov_display = "SKIP" if r["coverage"]["skipped"] else f"{cov_score:.4f}"
        print(
            f"{band:<12} {corr_score:>8.4f} "
            f"[{exp['min']:.2f}, {exp['max']:.2f}]{'':<4} "
            f"{'PASS' if in_band else 'FAIL':>6}  "
            f"{cov_display:>10}"
        )
    print("=" * 78)
    verdict = "GREEN" if all_pass else "RED"
    print(f"Verdict: {verdict}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
