---
depth: standard
id: EVID-022
kind: evidence
last_modified_at: 2026-05-24T10:36:21.597483+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: EVID-021
  relation: supersedes
status: draft
title: Phase 2C OTel + InspectEvalCaller patch verified — commit 9e668db addresses EVID-021 CONCERNS
---

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: audit

## Verdict

PASS

One-line justification: All 4 EVID-021 CONCERNS findings are correctly patched, regression tests structurally prove Fix #1, mypy --strict reports 0 errors (was 4), pytest passes 358 tests (was 356), and no scope creep was introduced.

## Scope

- Parent: PRD-001
- Re-review of: EVID-021 (CONCERNS verdict on commit 0e494f6)
- Patch commit: `e26977e..9e668db`
- Reviewer agent: `claude-code/claude-sonnet-4-6/code-reviewer-task-evid-022`
- Files reviewed: 3 files, 68 lines added / 5 lines changed
- Files: `apps/eval-core-py/src/orchestrator/eval_caller.py`, `apps/eval-core-py/src/orchestrator/journal.py`, `apps/eval-core-py/tests/test_eval_caller.py`

## Tools run

| Tool | Exit | Notes |
|---|---|---|
| ruff check | 0 | clean — "All checks passed!" |
| mypy --strict | 0 | "no issues found in 7 source files" — was 4 errors before patch |
| pytest | 0 | 358 passed, 1 skipped (+2 new tests vs 356 before patch) |
| ruff format | n/a | not run — format-only check deferred; ruff check clean implies no import-order or style regressions |

## Findings

No new findings. All 4 EVID-021 CONCERNS verified as resolved. No scope creep, no regressions.

| # | Severity | Category | Location | Description | Status |
|---|---|---|---|---|---|
| EVID-021 #1 | HIGH | Bug | `eval_caller.py:274` | `except (TimeoutError, httpx.TimeoutException)` now catches both built-in and httpx timeout subclasses | FIXED |
| EVID-021 #2 | HIGH | Bug | `eval_caller.py:354-363` | `isinstance()` narrowing replaces broken `type: ignore[arg-type]`; mypy --strict 0 errors | FIXED |
| EVID-021 #3 | MEDIUM | Architecture | `journal.py:169-170, 180-181` | `span.record_exception(exc)` + `span.set_status(StatusCode.ERROR)` on both exception paths | FIXED |
| EVID-021 #7 | LOW | Test gap | `test_eval_caller.py:312-359` | Two new regression tests — `test_httpx_read_timeout_classified_as_timeout` and `test_httpx_connect_timeout_classified_as_timeout` — pass and assert `ErrorClass.TIMEOUT` | FIXED |

## Deferred item assessment

Finding #3 (journal span error recording) is fully in production code at `journal.py:169-170` and `journal.py:180-181`. A unit test using `InMemorySpanExporter` to verify the ERROR status is NOT present in this patch. Assessment: the `InMemorySpanExporter` infrastructure already exists in `test_telemetry.py` (lines 18 and 162), so adding a test does NOT require new infrastructure. This is a genuine test gap but not a blocker — the production code is correct, and the infrastructure to write the test exists. Filed as follow-up test gap for Phase 2D.

## ADI cycle

### Abduction — hypotheses (>=3)

H1: All 4 fixes correct, regression test for Finding #1 actually catches the bug — PASS verdict warranted.
H2: At least one fix is partial — production code correct but new test doesn't truly exercise the fixed path (e.g., mock doesn't raise real httpx exception).
H3: A regression was introduced by the isinstance narrowing in Fix #2 — token extraction returns 0 when it should return a value.

### Deduction — observable predictions

H1: mypy --strict 0 errors, pytest +2 new tests pass, the new tests mock `httpx.ReadTimeout`/`httpx.ConnectTimeout` as the actual side_effect, and assert `ErrorClass.TIMEOUT`.
H2: pytest passes but the new test mocks with `side_effect=TimeoutError(...)` (built-in) rather than `httpx.ReadTimeout(...)` — would pass even without Fix #1.
H3: pytest fails on token-extraction test(s), or existing usage-dict tests now return 0 where they returned real values.

### Induction — evidence per prediction

- mypy: exit 0, "no issues found in 7 source files" — H1 SUPPORTED, H3 NOT TRIGGERED
- pytest: 358 passed, 1 skipped — H3 REFUTED (no regressions), H1 SUPPORTED
- Fix #1 test structure: `side_effect=httpx.ReadTimeout("read timed out")` at `test_eval_caller.py:327` and `side_effect=httpx.ConnectTimeout("connect timed out")` at `test_eval_caller.py:352` — these are real httpx exception classes, not built-in TimeoutError. If Fix #1 were reverted, `httpx.ReadTimeout` would fall through to `except httpx.HTTPError` → `ErrorClass.NETWORK` → assertion `error_class == ErrorClass.TIMEOUT` would FAIL. H2 REFUTED.
- Fix #2 narrowing: `isinstance(_u, dict)` at `eval_caller.py:357`, then `isinstance(_pt, (int, float))` at `eval_caller.py:360` and `isinstance(_ct, (int, float))` at `eval_caller.py:362` — correct narrowing chain; no `type: ignore` comments remain. H1 SUPPORTED.
- Fix #3 span error recording: `span.record_exception(exc)` at `journal.py:169`, `span.set_status(StatusCode.ERROR, str(exc))` at `journal.py:170`, and the same pair at `journal.py:180-181` — both exception paths covered. H1 SUPPORTED.

## Trust Calculus per claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| Fix #1 catches httpx.TimeoutException | 9 | 9 | 9 | 27 | except clause explicitly names both; regression tests use real httpx types |
| Fix #2 mypy --strict clean | 9 | 9 | 9 | 27 | direct tool output: exit 0, "no issues found in 7 source files" |
| Fix #3 span error recording correct | 9 | 9 | 8 | 26 | code read confirmed both exception paths; no tool covers OTel status assertion |
| Fix #4 regression test is valid | 9 | 9 | 9 | 27 | side_effect is real httpx.ReadTimeout/ConnectTimeout; assertion on ErrorClass.TIMEOUT |

## Conclusions

- Surviving hypothesis: H1 — all 4 fixes correct, regression tests valid
- Decision strength: 96% (only gap: no InMemorySpanExporter test for Fix #3 — production code correct, test deferred)
- Follow-up needed: add `test_journal_span_records_error_on_corruption` using `InMemorySpanExporter` in `test_journal.py` — infrastructure already exists in `test_telemetry.py:162`, no new setup needed. Deferred to Phase 2D iteration.
- Phase 2D gate: READY

## Positive observations

- The isinstance narrowing in Fix #2 (`eval_caller.py:354-363`) is cleaner than the original — it handles the `usage=None` case, the `usage=non-dict` case, and the `prompt_tokens=None` case all explicitly, making the fallback-to-0 behaviour observable at a glance rather than implicit in `or {}`.
- Two regression tests were added (not one), covering both `ReadTimeout` and `ConnectTimeout` — thoroughness exceeds the minimum requested.
- Commit message format is exemplary: each finding number is cited, the test count delta is stated (358 was 356), and the Refs field uses slugs correctly per project convention.

## Test coverage delta

- Before: 356 passed, 1 skipped
- After: 358 passed, 1 skipped (+2 new regression tests)
- Branches gained: `httpx.ReadTimeout` classified as TIMEOUT; `httpx.ConnectTimeout` classified as TIMEOUT
- Branches still uncovered: `journal.append` span ERROR status via InMemorySpanExporter (Fix #3 production code correct, test deferred)

## Next steps

- PASS: orchestrator may proceed to Phase 2D activation gate
- Coder follow-up (not blocking): add `test_journal_span_records_error_on_corruption` in `test_journal.py` using existing `InMemorySpanExporter` infrastructure
- No further re-review needed before Phase 2D

## References

- Parent: PRD-001
- Re-reviews: EVID-021 (prior CONCERNS verdict on same scope)
- Commit reviewed: `9e668db`
- Commit range: `e26977e..9e668db`


