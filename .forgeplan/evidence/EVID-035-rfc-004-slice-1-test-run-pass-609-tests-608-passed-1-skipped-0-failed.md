---
depth: standard
id: EVID-035
kind: evidence
last_modified_at: 2026-05-29T13:56:43.544569+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-004
  relation: informs
status: active
title: 'RFC-004 Slice 1 test run — PASS (609 tests: 608 passed, 1 skipped, 0 failed)'
---

## Verdict

**PASS**

608/609 tests passed, 0 failed, 1 skipped (pre-existing intentional deferral). Validator additivity: 3/3 task specs valid. TS contracts: clean typecheck. All 48 new Slice 1 tests (test_component_score.py + test_task_contracts.py) passed. Coverage gap noted: the 5 MUST validator rules in validate-task-specs.py lack dedicated unit tests (tested only end-to-end via the script invocation).

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: test

## Runner detected

- Ecosystem: python + node
- Runner: pytest (Python), tsc --noEmit (TypeScript)
- Output format: text (pytest) / compiler output (tsc)
- Config source: apps/eval-core-py/pyproject.toml (pytest), packages/contracts/tsconfig.json (tsc)

## Command run

```bash
# Command 1 — task spec validator (additivity check)
uv run -- python infra/scripts/validate-task-specs.py
# Exit code: 0

# Command 2 — full Python test suite
uv run -- pytest apps/eval-core-py/tests/ -q
# Exit code: 0

# Command 2b — targeted verbose run on new test files
uv run -- pytest apps/eval-core-py/tests/test_component_score.py apps/eval-core-py/tests/test_task_contracts.py -v
# Exit code: 0

# Command 3 — TypeScript contracts typecheck
npx --yes tsc --noEmit -p packages/contracts/tsconfig.json
# Exit code: 0
```

Exit code: `0` (all three commands)

## Summary

| Metric | Value |
|---|---|
| Passed | 608 |
| Failed | 0 |
| Skipped | 1 |
| Flaky (passed on retry) | 0 |
| Total | 609 |
| Duration | 7.36 seconds (Python suite) |

### New Slice 1 test files — detailed breakdown

| File | Tests | Result |
|---|---|---|
| test_component_score.py | 20 | 20 passed |
| test_task_contracts.py | 28 | 28 passed |
| **Slice 1 total** | **48** | **48 passed** |

### test_component_score.py coverage of component_score math

| Scenario class | Tests | Status |
|---|---|---|
| TestComponentScoreHappyPath (half/all-pass/all-fail/single/fractional) | 6 | PASS |
| TestComponentScoreNoAutoReqs (empty/judge-only/different-component → None) | 3 | PASS |
| TestComponentScoreIsolation (other-component results ignored, judge excluded) | 3 | PASS |
| TestComponentScoreMissingResult (missing auto req counts as fail) | 2 | PASS |
| TestComponentScoreReturnType (float not int, None for zero auto) | 2 | PASS |
| test_score_in_valid_range parametrized [0-1, 1-1, 3-7, 10-10] | 4 | PASS |

### test_task_contracts.py coverage of Pydantic models + JSON Schema

| Scenario class | Tests | Status |
|---|---|---|
| TestTaskRequirement (happy path auto+judge, id pattern, empty text, check_type, prompt_ref, extra field, frozen, multidigit id) | 12 | PASS |
| TestRequirementResult (happy path auto/judge, invalid check_type, extra field, frozen, JSON roundtrip auto+judge/null) | 8 | PASS |
| TestTaskSchemaRoundTrip (task without/with requirements validates; invalid id/missing field/extra field/check_type/prompt_ref-zero/empty-text fails) | 8 | PASS |

## AC coverage delta

Parent: RFC-004

| AC Item | Status | Notes |
|---|---|---|
| Additivity: 3 existing packs validate unchanged | PASS | 3/3 task specs valid, EXIT=0 |
| component_score math: happy path | PASS | test_all_pass_returns_10, test_all_fail_returns_0, test_half_pass_returns_5 |
| component_score math: zero auto reqs | PASS | TestComponentScoreNoAutoReqs — 3 tests covering empty/judge-only/different-component |
| component_score math: all-fail | PASS | test_all_fail_returns_0 |
| component_score math: all-pass | PASS | test_all_pass_returns_10 |
| TS contracts typecheck clean | PASS | tsc --noEmit EXIT=0 |
| Pydantic models round-trip | PASS | TestTaskSchemaRoundTrip — 8 tests |
| MUST validator rule 1 (unique ids) — dedicated unit test | GAP | No unit test calls validate_one with a duplicate-id payload. The 5 MUST rules in validate-task-specs.py (unique-id, maps_to allowed-set, auto→deterministic, prompt_ref-resolvable, Σ weights=1.0) are exercised only end-to-end via the script invocation on the 3 real packs, which are all valid — so malformed rejection is NOT unit-tested. |
| MUST validator rule 2 (maps_to allowed set) | GAP | Same — no unit test with invalid maps_to value |
| MUST validator rule 3 (auto→deterministic only) | GAP | Same — no unit test with auto→judge-criterion |
| MUST validator rule 4 (prompt_ref resolvable) | GAP | Same — no unit test with out-of-range prompt_ref |
| MUST validator rule 5 (Σ weights = 1.0) | GAP | Same — no unit test with Σ ≠ 1.0 |

AC target: no explicit coverage % stated in RFC-004. AC silent on coverage threshold.
Actual coverage: pytest-cov not installed (ModuleNotFoundError: No module named 'pytest_cov'). Coverage %: n/a — instrumentation unavailable.
Delta: n/a

## Failing tests

None — 0 failures.

## Skipped tests

| File:line | Test name | Reason |
|---|---|---|
| apps/eval-core-py/tests/test_contracts.py:1053 | TestAcceptanceCriteria::test_ac6_deferred | Pre-existing intentional deferral: "AC-6 (journal crash recovery) is deferred to Wave 3 journal tests per SPEC-001." Not related to Slice 1. |

## Slow tests (top 5)

| Test | Duration |
|---|---|
| test_smoke_runner.py::TestBudgetAbort::test_build_aggregates_reflects_budget_breach | 1590ms |
| test_judge_panel.py::TestJudgePanelAggregateSliceC::test_bootstrap_ci_deterministic | 160ms |
| test_judge_panel.py::TestJudgePanelAggregateSliceC::test_perfect_agreement_alpha_one | 100ms |
| test_integration.py::TestSchemaRoundTripThroughFullPipeline::test_manifest_json_validates_against_schema | 90ms |
| test_integration.py::TestFullSmokeRunHappyPath::test_manifest_schema_valid | 80ms |

None of the top-5 slow tests are from Slice 1 files. The 48 new Slice 1 tests completed in 0.15s.

## Flaky candidates

None observed. No retry runs performed (no --reruns flag, pytest-rerunfailures not installed). Single run was deterministic.

## Audit trail

- Commit tested: afb0f4c (DETACHED HEAD — feat(contracts): RFC-004 Slice 1 — requirements[] schema + validator + component_score)
- Branch: feat/rfc-004-requirements-schema (checked out as detached HEAD)
- Agent: claude-code/sonnet-4-6/tester-task-rfc004-slice1
- Runner versions: pytest 9.0.3, Python 3.12.7, uv 0.6.10, node 22.18.0
- Coverage tooling: pytest-cov NOT available (not in venv); coverage % not measured

## Next steps

- **PASS: hand back to guardian for activation gate** — all functional tests pass, 0 regressions, all 48 Slice 1 tests green.
- **CONCERNS (non-blocking):** The 5 MUST validator rules in `infra/scripts/validate-task-specs.py` have no dedicated unit tests calling `validate_one` with bad inputs (duplicate ids, invalid maps_to, auto→judge-criterion, unresolvable prompt_ref, Σ≠1.0). These rules are implemented in the validator (code confirmed) but not covered by the pytest suite. Recommend coder add validator unit tests before Slice 2 (Phase 2 gate per RFC-004 § Implementation Phases). This is a SHOULD, not a BLOCKER for activation — the end-to-end additivity check confirms the existing packs pass the rules.
- **CONCERNS (non-blocking):** pytest-cov is absent from the venv. Add `pytest-cov` to dev dependencies to enable coverage reporting on future runs.


