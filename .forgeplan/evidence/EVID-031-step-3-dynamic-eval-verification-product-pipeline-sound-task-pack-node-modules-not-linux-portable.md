---
depth: standard
id: EVID-031
kind: evidence
last_modified_at: 2026-05-28T23:46:51.668376+00:00
last_modified_by: claude-code/2.1.156
links:
- target: NOTE-008
  relation: informs
status: active
title: Step 3 dynamic-eval verification — product pipeline sound, task-pack node_modules not Linux-portable
---

## Summary

Verification of the dynamic-eval pipeline (Step 3 of the Wave 0+1 cleanup sprint, NOTE-008). Outcome: the **Docker image `pollmevals-eval-ts:0.1.0` builds clean (215 MB)** and the **CorrectnessEvaluator/CoverageEvaluator/SandboxRun product code is structurally sound** (deps-model B "submission-provides-everything"; command `npx --no vitest run` correct; 28/28 unit tests pass). However, **live band-separation numbers could NOT be obtained** — blocked by a real, separate infra gap: task-pack `node_modules` is not portable from the macOS authoring host to the Linux Alpine sandbox. This evidence **supports** NOTE-008's Fishbone analysis, which predicted exactly this "tools/infra" systemic-debt bone.

## Structured Fields

```yaml
verdict: supports
congruence_level: 3
evidence_type: measurement
falsifiable: true
sample_size: 1 Docker image build + 28 unit tests + 3 live band-sep run attempts (fe_01)
```

- **verdict: supports** — the measurement supports NOTE-008's premise that real tools/infra debt was deferred from Wave 0+1; the Fishbone "Dynamic eval verification deferred because Docker image deferred — circular dependency" bone is confirmed.
- **congruence_level: 3** — direct measurement of the same pipeline, in the same project context (POLLMEVALS dynamic evaluators), no analogy gap.
- **evidence_type: measurement** — Docker builds, unit-test counts, and live sandbox run errors are observed facts, not theory.

## What was verified (observed facts)

1. **Docker image** — `docker build -t pollmevals-eval-ts:0.1.0 infra/docker/eval-ts/` exits 0; image is 215 MB; bakes typescript 5.9.3 + vitest 3.2.4 + @vitest/coverage-v8 3.2.4 into `/home/node/app/node_modules`. (NOW-block item #1 — DONE.)
2. **Unit tests** — 28/28 PASS across `test_correctness_evaluator.py`, `test_coverage_evaluator.py`, `test_sandbox.py`. These mock the sandbox, so they exercise evaluator logic but NOT the live Docker path.
3. **Deps-delivery model = B (submission-provides-everything)** — the image bakes only the universal runner (vitest/ts); domain deps (react, @testing-library, jsdom, axe-core) live in the task pack's `node_modules`. The evaluator command `cd /workspace && npx --no vitest run --reporter=json` is correct for this model: vitest must resolve from the mounted `/workspace/node_modules`.
4. **Scope correction** — only `fe_*/ts_*/fs_*` prefixes route through CorrectnessEvaluator+CoverageEvaluator (`_TS_RUNNABLE_PREFIXES`). `be_01` uses its own task-pack Dockerfile; `doc_01` is judge-scored. So of the 3 calibration-ready packs, only `fe_01` is in scope for these two automatic evaluators.

## The blocker — task-pack node_modules not Linux-portable (band-sep BLOCKED)

Live band-separation on `fe_01` (perfect ≥ 0.85 / broken ≤ 0.20 expected) was attempted 3 times; all bands scored 0.0/skipped. Error progression, each a distinct layer:

1. `DockerException ... FileNotFoundError /var/run/docker.sock` → fixed: `DOCKER_HOST=unix:///Users/<user>/.docker/run/docker.sock` (docker-py SDK can't use the macOS Docker-Desktop context; the CLI can).
2. `EAI_AGAIN registry.npmjs.org` → root: verify-script symlinked `/workspace/node_modules` to a host path that is a dangling symlink inside the container → npx fell back to a network install → blocked by `--network=none`. Fixed in `infra/scripts/verify-fe01-band-separation.py` (real copytree + `symlinks=True` for `.bin`).
3. `MODULE_NOT_FOUND rollup/dist/native.js` → **STRUCTURAL, unfixed**: `fe_01/gold/node_modules` is installed on macOS (darwin-arm64); the sandbox is Linux x64 Alpine; native bindings (`@rollup/rollup-linux-x64-musl`, esbuild) are absent. An in-container `npm ci` to rebuild for Linux failed on the cross-platform `package-lock.json`.

Net: the **product pipeline is sound**, but no task pack with native deps can be evaluated until its `node_modules` is Linux-built at eval time.

## Severity & reframe

This is **NOT a product bug** in CorrectnessEvaluator/CoverageEvaluator/SandboxRun — those are correct. It is a **task-pack portability invariant** the harness implicitly requires (the Dockerfile says "self-contained: no network at evaluator-run time"): any `node_modules` mounted into `/workspace` must be Linux-compatible. Current packs ship macOS deps. This affects ALL packs with native deps and is an RFC-003 (authoring protocol) follow-up.

## Follow-up

Tracked as a dedicated infra task (sprint TaskList #6). Candidate resolutions, in preference order:
1. Build `node_modules` in-container immediately before the eval run (a pre-eval step in the workspace-assembly path) — keeps packs platform-agnostic.
2. Ship a Linux-built `node_modules` artifact per pack (larger repo / artifact store).
3. CI step that materializes Linux deps.

Until resolved: do NOT promote fe_01/be_01/doc_01 to lifecycle_state=calibration on the basis of automatic-evaluator band separation (it has not been demonstrated end-to-end).

## Reusable asset

`infra/scripts/verify-fe01-band-separation.py` — reproducible band-separation harness (sets DOCKER_HOST, assembles per-band workspaces, runs both evaluators, writes JSON + summary). Ready to re-run once Linux deps land — no further script changes expected.

## Provenance

- Docker build + image inspect: local, 2026-05-29.
- Unit tests: `uv pip install -e apps/eval-core-py` venv, 28/28.
- Live run errors: `artifacts/local/step3-eval-verify/fe_01/band_separation_results.json` (gitignored) + agent transcripts.
- Diagnosis converged across 3 sandbox-runner debugging iterations.


