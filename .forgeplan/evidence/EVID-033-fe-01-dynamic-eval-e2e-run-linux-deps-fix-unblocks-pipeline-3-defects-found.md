---
depth: standard
id: EVID-033
kind: evidence
last_modified_at: 2026-05-29T09:42:26.933951+00:00
last_modified_by: claude-code/2.1.156
links:
- target: NOTE-008
  relation: informs
status: draft
title: fe_01 dynamic-eval e2e run — Linux-deps fix unblocks pipeline, 3 defects found
---

## Summary

Follow-up to EVID-031. After fixing task-pack `node_modules` Linux portability (build deps in `node:22.18-alpine` via `npm install`, point the verify harness at them via `FE01_NODE_MODULES`), the dynamic-eval pipeline **runs end-to-end for the first time** — `vitest` executes inside the sandbox and `CorrectnessEvaluator` emits real pass-rate scores (no longer 0.0/skipped). The e2e run then surfaced **3 distinct defects** that block valid band separation. These are exactly the failures e2e verification exists to catch; none were visible to the mocked unit tests.

## Structured Fields

```yaml
verdict: weakens
congruence_level: 3
evidence_type: measurement
falsifiable: true
sample_size: fe_01 — 5 bands × CorrectnessEvaluator + CoverageEvaluator, live Docker run
```

- **verdict: weakens** — the live measurement weakens the premise (held by NOTE-008 Step 4 + the prior handoff) that the 3 packs are calibration-ready via automatic evaluators. They are not, until the 3 defects below are resolved.
- **congruence_level: 3** — direct live measurement of the exact pipeline + pack in question.
- **evidence_type: measurement** — observed scores + container stderr, not theory.

## Win — Linux-deps fix unblocks the pipeline

Root cause of the prior block (EVID-031 layer 3): gold `node_modules` was macOS-native; the sandbox is linux/musl. Fix: build a Linux tree in `node:22.18-alpine` (same musl as the sandbox image) using `npm install` (NOT `npm ci` — `ci` fails on the macOS-generated lockfile's platform-specific optional deps), then point the harness at it via the new `FE01_NODE_MODULES` env override (committed in `infra/scripts/verify-fe01-band-separation.py`; `GOLD/node_modules` left untouched). Result: vitest runs; correctness scores are real numbers.

## The 3 defects (band separation RED — measured)

Live `CorrectnessEvaluator` scores (correctness = test pass rate; coverage all SKIP):

| Band | correctness | expected | result |
|---|---|---|---|
| perfect | 0.4348 | ≥ 0.85 | FAIL |
| good | 0.4348 | — | — |
| mediocre | 0.3043 | — | — |
| poor | 0.0870 | — | — |
| broken | **1.0000** | ≤ 0.20 | FAIL (inverted) |

**Defect 1 — CorrectnessEvaluator vacuous-pass (`total==0 → 1.0`).** `correctness_evaluator.py:180`: `pass_rate = 1.0 if total == 0 else passed/total`. The broken sample (`// broken/sample-001 — FATAL: missing closing brace — tsc rejects`) does not compile → vitest collects 0 tests → score 1.0 (best) instead of 0.0 (worst). This is why broken scored 1.0000. A load/compile failure must NOT score as vacuously correct for a code task.

**Defect 2 — CoverageEvaluator fails on read-only `/workspace`.** All coverage bands SKIP with `Serialized Error: {errno:-2, code:'ENOENT', syscall:'mkdir', path:'/workspace/coverage'}`. `runner.py` mounts `/workspace` `read_only` + `mode:ro` (frozen security — correct). `vitest --coverage` tries to write `/workspace/coverage`. Fix must route coverage output to a writable tmpfs (e.g. `--coverage.reportsDirectory=/tmp/coverage`), NOT loosen the read-only mount.

**Defect 3 — calibration sample ↔ gold-test export-surface mismatch.** Gold `tests.spec.tsx` imports 5 symbols: `MultiStepForm` + `fieldsForStep` / `hydrateDraft` / `isStepValid` / `validateField` (23 tests total). `gold/solution.tsx` exports all 5. But `calibration/perfect/sample-001.tsx` exports **only `MultiStepForm`** — the 4 helper functions are absent. Every test touching a helper fails on every sample → the perfect sample is structurally capped at ~10/23 = 0.4348. Automatic band separation is impossible as authored. This is a pack-design / methodology question, not a code bug.

## Why this matters (severity)

Defects 1+2 are CorrectnessEvaluator/CoverageEvaluator product bugs affecting ALL `fe_/ts_/fs_` packs. Defect 3 is a calibration-data/methodology question affecting fe_01 now and the be_01/doc_01 + PRD-006 Wave 1 authoring pattern (RFC-003). Together they mean: **no task pack can be honestly promoted to `calibration` via automatic evaluators until resolved.** The conceptual fork in Defect 3 (are calibration bands meant to band-separate under automatic eval at all, or are they judge-only?) needs the methodology owner — it may invalidate the handoff's "perfect ≥ 0.85 / broken ≤ 0.20" automatic-eval premise entirely.

## Follow-up (tracked)

- Defect 1 → sprint TaskList #7 (vacuous-pass).
- Defect 2 → #8 (coverage read-only).
- Defect 3 → #9 (sample/test surface mismatch — owner decision).
- Product-pipeline Linux-deps integration (auto-build per pack + cache, mount into network=none sandbox) — eval-pipeline follow-up beyond the verify harness.

## Provenance

- Live run: `FE01_NODE_MODULES=.../linux-deps-fe01/node_modules DOCKER_HOST=unix://$HOME/.docker/run/docker.sock .venv/bin/python infra/scripts/verify-fe01-band-separation.py`, exit 0, 2026-05-29.
- Results: `artifacts/local/step3-eval-verify/fe_01/band_separation_results.json` (gitignored).
- Export-surface mismatch confirmed by grep of gold tests imports vs sample exports.

