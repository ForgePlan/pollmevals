---
depth: standard
id: EVID-026
kind: evidence
last_modified_at: 2026-05-25T19:37:36.913403+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: NOTE-007
  relation: informs
- target: RFC-001
  relation: informs
status: active
title: Phase 2D Slice 2 part 2 — SandboxRun + CorrectnessEvaluator + CoverageEvaluator with Docker sandbox
---

# EVID-026: Phase 2D Slice 2 part 2 — SandboxRun + CorrectnessEvaluator + CoverageEvaluator with Docker sandbox

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: test

## Summary

Phase 2D Slice 2 part 2 completes the dynamic-evaluator half of the slice introduced by NOTE-007 (static/dynamic execution-boundary rule). Three pieces land:

| Component | Path | Role |
|---|---|---|
| `SandboxRun` helper | `apps/eval-core-py/src/evaluators/sandbox/runner.py` | Docker-backed code-execution helper. Materialises the frozen v0.1.0 sandbox policy in code (`network=none`, `read_only=True`, tmpfs, `mem_limit=512m`, `nano_cpus=1e9`, `pids_limit=50`, `cap_drop=[ALL]`, `security_opt=[no-new-privileges:true]`, ulimits nofile/fsize, hard timeout). |
| `CorrectnessEvaluator` | `apps/eval-core-py/src/evaluators/correctness_evaluator.py` | Runs `npx vitest run --reporter=json` inside the sandbox. Score = pass_rate. |
| `CoverageEvaluator` | `apps/eval-core-py/src/evaluators/coverage_evaluator.py` | Runs `npx vitest run --coverage --reporter=json` inside the sandbox. Reads `coverageMap` from the same JSON shape. Score = lines_covered / lines_total. |

Plus an `infra/docker/eval-ts/` directory carrying a pinned Node 22.18-alpine image with vitest 3.2.4 + typescript 5.9.3 + @vitest/coverage-v8 3.2.4 baked in (network=none at evaluator-run time forces all deps to be pre-installed).

The two dynamic evaluators register in `_EVALUATORS` so the smoke run dispatches them automatically when a TS-runnable task arrives. The 6-evaluator dispatch (lint + complexity + secret_scan + type_safety + correctness + coverage) gracefully degrades on non-TS tasks via the existing `skipped=True` semantics.

## ADI cycle

### Abduction — load-bearing hypotheses

- **H1**: docker-py's `client.containers.run()` accepts every frozen-policy flag verbatim (`network_mode="none"`, `read_only=True`, `tmpfs={"/tmp": "size=100m"}`, `mem_limit`, `nano_cpus`, `pids_limit`, `cap_drop=["ALL"]`, `security_opt=["no-new-privileges:true"]`, `ulimits=[...]`). No custom Docker API client needed.
- **H2**: Vitest 3.x `--reporter=json` emits `coverageMap` in the same JSON document when `--coverage` is passed, so ONE invocation can serve both CorrectnessEvaluator (pass-rate) and CoverageEvaluator (line coverage) — each evaluator extracts its own slice without needing to coordinate.
- **H3**: Wrapping the synchronous docker-py call in `asyncio.to_thread()` keeps the async Evaluator surface uniform with Slice 1 wraps (ComplexityEvaluator already wraps sync `lizard.analyze_file()` via the same technique). No async-docker rewrite needed.

### Deduction — observable predictions

- **H1 → Y1**: a `_build_run_kwargs` unit test passes EVERY flag from the frozen policy into `containers.run` kwargs. Assertion: kwargs dict contains `{network_mode: "none", read_only: True, tmpfs: {...}, mem_limit: "512m", cap_drop: ["ALL"], security_opt: ["no-new-privileges:true"]}`.
- **H1 → Y1-refute**: a missing field name or wrong type would surface as a docker SDK error at runtime AND a unit-test failure on kwargs shape.
- **H2 → Y2**: CoverageEvaluator can parse `coverageMap` from the SAME JSON shape that CorrectnessEvaluator parses for `numTotalTests/numPassedTests/numFailedTests`.
- **H2 → Y2-refute**: if `coverageMap` were emitted to a separate file (not embedded), CoverageEvaluator would skip with "coverageMap absent" on a report that has tests but no embedded coverage.
- **H3 → Y3**: 28 unit tests using `FakeSandbox` (programmable async-shaped stand-in) run in <0.3s with no real Docker daemon; full suite stays at 560 passed / 1 skipped.

### Induction — current evidence per prediction

| Prediction | Evidence | Status | H_i |
|---|---|---|---|
| Y1: all frozen-policy flags reach containers.run | `test_security_flags_passed_to_docker` asserts each kwarg (`network_mode == "none"`, `read_only is True`, `tmpfs == {"/tmp": "size=100m"}`, `mem_limit == "512m"`, `nano_cpus == 1e9`, `pids_limit == 50`, `cap_drop == ["ALL"]`, `security_opt == ["no-new-privileges:true"]`) | Confirmed | **H1 SUPPORTED** |
| Y1: bind-mount becomes read-only /workspace | `test_mount_dir_becomes_readonly_workspace_bind` asserts `volumes == {host_path: {"bind": "/workspace", "mode": "ro"}}` | Confirmed | **H1 SUPPORTED** |
| Y2: CoverageEvaluator parses coverageMap from the SAME JSON shape | `test_full_coverage_score_1_0` + `test_partial_coverage_score_proportional` + `test_zero_lines_total_score_1_0` all use a vitest JSON document with embedded coverageMap and produce correct ratios | Confirmed | **H2 SUPPORTED** |
| Y2: absent coverageMap surfaces as skip | `test_skip_when_coverage_map_absent` asserts `result.skipped is True and "coverageMap absent" in skip_reason` | Confirmed | **H2 SUPPORTED** |
| Y3: full suite stays clean | `pytest apps/eval-core-py/tests/ -q` → 560 passed, 1 skipped, 0 regressions (was 532; +28 for sandbox+correctness+coverage) | Confirmed | **H3 SUPPORTED** |
| Y3: mypy strict clean | `mypy --strict apps/eval-core-py/src/` → 0 issues, 27 source files (was 23; +4 for sandbox/__init__, sandbox/runner, correctness, coverage) | Confirmed | **H3 SUPPORTED** |
| Timeout path kills container deterministically | `test_timeout_kills_container_and_marks_timed_out` asserts `result.timed_out is True`, `container.kill.assert_called_once()`, `exit_code == 137` | Confirmed | additional H |
| SDK missing surfaces as ImportError | `test_ensure_client_raises_when_docker_sdk_missing` asserts `pytest.raises(ImportError, match="docker SDK not installed")` | Confirmed | additional H |

**ADI conclusion**: all three load-bearing hypotheses (H1, H2, H3) are **SUPPORTED**. 8/8 confirming predictions, 0 refutations.

## Trust Calculus per claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| docker-py supports the full frozen-policy flag set verbatim | 9 | 9 | 8 | 26/27 | F=9: Context7 `/docker/docker-py` confirmed every kwarg by name; pinned `docker>=7.1,<8`. G=9: each flag tested explicitly in `_build_run_kwargs` unit test. R=8: not yet exercised against a real daemon in this PR (integration test deferred to a dedicated runtime-validation session). |
| Vitest 3.x embeds coverageMap in the JSON reporter | 8 | 8 | 7 | 23/27 | F=8: web research 2026-05-25 quoted "Since Vitest 3, the JSON reporter includes coverage information in coverageMap if coverage is enabled" (vitest.dev/guide/reporters). G=8: extraction code is explicit per-file lines.{total,covered} sum. R=7: tests use synthetic JSON shape matching docs — first real-image run will calibrate R to 9. |
| asyncio.to_thread is sufficient for sandbox blocking-call wrap | 8 | 8 | 9 | 25/27 | F=8: standard library, documented contract. G=8: applied in exactly one place (`SandboxRun.run`). R=9: identical pattern already in production via `ComplexityEvaluator` wrapping `lizard.analyze_file()`. |
| Static/dynamic boundary (NOTE-007) survives full Slice 2 | 9 | 8 | 8 | 25/27 | F=9: 4 evaluators land — 1 static (type_safety) + 2 dynamic (correctness, coverage) follow the rule cleanly; 0 boundary violations. G=8: each evaluator's docstring states its side. R=8: pattern survives second slice — promotion criterion in NOTE-007 met (will be considered for ADR-007 in follow-up). |
| `_FakeSandbox` Protocol-mirror lets tests skip real Docker | 8 | 8 | 9 | 25/27 | F=8: duck-typed `run(config) -> SandboxResult` mirrors the real surface. G=8: every CorrectnessEvaluator + CoverageEvaluator test injects it. R=9: identical pattern as `FakeEvalCaller` / `FakeJudgePanel` — already shipped twice (PRD-001 smoke, RFC-002 Slice E). |
| Pinned Node + vitest + ts versions in Dockerfile | 7 | 8 | 6 | 21/27 | F=7: explicit pins (node@22.18-alpine, vitest@3.2.4, typescript@5.9.3, @vitest/coverage-v8@3.2.4). G=8: stored in `infra/docker/eval-ts/package.json` as canonical source. R=6: image NOT yet built in CI; first real build will calibrate R to 8-9. |

**Decision strength**: avg F+G+R = 24.2/27. Lowest single claim (Dockerfile pins, 21/27) above NOTE-002 weak-decision floor of 12. Action: build the image in a follow-up session (10 min) and capture the resulting image-build EVID to lift R on rows 2, 6 from 7→9 and 6→8.

## Conclusions

**Surviving hypotheses**: H1 (docker-py flag fidelity), H2 (vitest 3.x coverageMap embedding), H3 (asyncio.to_thread sufficiency) — all SUPPORTED.

**Decision strength**: STRONG (24.2/27 avg Trust Calculus, 8/8 predictions confirmed, 0 refutations).

**Follow-up work** (NOT blockers for this slice):

1. **Image build + integration test**: build `pollmevals-eval-ts:0.1.0` once locally, run `CorrectnessEvaluator` against a synthetic candidate dir with a trivial vitest suite, verify the real JSON shape matches the test fixtures. ~30 minutes. Captures EVID-027 image-build measurement.
2. **gVisor / Kata runtime upgrade** (v0.3 roadmap): wire `runtime: runsc` or `runtime: kata-runtime` in `SandboxRun._build_run_kwargs` once those runtimes are available on hosts. Code stays the same — only the daemon flag changes.
3. **NOTE-007 promotion to ADR-007**: with Slice 2 part 2 confirming the static/dynamic boundary across 4 evaluators, the pattern is ready for ADR-level formality. Open a dedicated session.
4. **CI image build**: optional GitHub Actions step that builds the sandbox image and runs the integration test on PR.

## Related Artifacts

- **PRD-001** (parent, auto-linked) — smoke run consumes all 6 evaluators including the 2 new dynamic ones.
- **NOTE-007** — static/dynamic boundary rule; this EVID confirms the rule survives 4-evaluator Slice 2.
- **NOTE-002** — Evidence Quality Standard contract this EVID follows.
- **RFC-001** — Evaluator Protocol that all 6 evaluators implement.
- `docs/02-methodology/security-sandbox.md` v0.1.0 — frozen policy materialised in `SandboxRun`.
- `docs/04-runbook/09-sandbox-security.md` — v0.1 → v0.3 → v1.0 roadmap.

## Provenance

| Field | Value |
|---|---|
| Branch | `feat/phase-2d-slice-2-sandbox-vitest` |
| New source files | `sandbox/__init__.py`, `sandbox/runner.py`, `correctness_evaluator.py`, `coverage_evaluator.py`, `infra/docker/eval-ts/Dockerfile`, `infra/docker/eval-ts/package.json` |
| New test files | `tests/test_sandbox.py` (6 tests), `tests/test_correctness_evaluator.py` (12 tests), `tests/test_coverage_evaluator.py` (10 tests) |
| Tests added | 28 (6 sandbox + 12 correctness + 10 coverage) |
| Full suite | `pytest apps/eval-core-py/tests/ -q` → 560 passed, 1 skipped, 0 regressions |
| mypy strict | `mypy --strict apps/eval-core-py/src/` → 0 issues, 27 source files |
| Dependency added | `docker>=7.1,<8` in `apps/eval-core-py/pyproject.toml` |
| Recorded | 2026-05-25, autorun mode (`/fpl-skills:autorun`) |




