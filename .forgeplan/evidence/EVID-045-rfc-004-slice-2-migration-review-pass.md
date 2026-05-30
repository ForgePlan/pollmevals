---
depth: standard
id: EVID-045
kind: evidence
last_modified_at: 2026-05-30T11:16:45.059960+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-004
  relation: informs
status: draft
title: RFC-004 Slice 2 migration review — PASS
---

## Verdict

PASS

One-line justification: all findings from the initial CONCERNS review are resolved or accepted in amended commit `17e4301`; C4 1:1 invariant is now satisfied for all three packs, no duplicate tag ownership, counts correct throughout.

## Scope

- Parent: RFC-004
- Diff range: `5e07840..17e4301` (amended commit replacing 58a4fd1)
- Files reviewed: 5 files, ~450 lines added / ~60 lines changed
- Files:
  - `evals/task-packs/be_01_jwt_auth/task.yaml`
  - `evals/task-packs/be_01_jwt_auth/gold/tests.spec.ts`
  - `evals/task-packs/fe_01_multistep_form/task.yaml`
  - `evals/task-packs/fe_01_multistep_form/gold/tests.spec.tsx`
  - `evals/task-packs/doc_01_cli_readme/task.yaml`

## Tools run

| Tool | Exit | Notes |
|---|---|---|
| eslint | n/a | not applicable — reviewed YAML + test-title tagging only, no TS logic change |
| tsc --noEmit | n/a | no TypeScript logic changed; tag additions and helper extraction are structure-only |
| pytest / vitest | n/a | gold solution logic unchanged; tester EVID-044 ran 621 tests green; commit message confirms 621 passed |
| ruff / mypy | n/a | no Python files in diff |
| git diff stat | 0 | 5 files confirmed, assertions preserved |

## Findings

| # | Severity | Category | Location | Description | Status |
|---|---|---|---|---|---|
| 1 | HIGH | Bug | `evals/task-packs/be_01_jwt_auth/gold/tests.spec.ts:216` (original) | C4 violation: `[R20][R21][R22]` bundled on one test. | RESOLVED in 17e4301 — split into three 1:1 `it()` blocks sharing `rotateActiveRefresh()` helper. Each new test asserts exactly its requirement: R20 asserts rotation+jti-invalidation+cookie-issued, R21 asserts HttpOnly, R22 asserts SameSite=Strict. All original assertions preserved. |
| 2 | MEDIUM | Bug | `evals/task-packs/fe_01_multistep_form/gold/tests.spec.tsx:136` (original) | Duplicate `[R10]` tag in two test titles. | RESOLVED in 17e4301 — `[R10]` removed from multi-tag test (now `[R4][R8][R11]`); dedicated blur test at line 149 is R10's sole owner. |
| 3 | LOW | Spec-fidelity | Commit message (58a4fd1) | fe_01 count wrong (said "23 auto + 4 judge"; actual is 24+3). | RESOLVED in amended commit 17e4301 — commit message now reads "fe_01: 27 items (24 auto + 3 judge)". |
| 4 | LOW | Spec-fidelity | `evals/task-packs/doc_01_cli_readme/task.yaml` header comment | Comment said "16 judge-only"; actual count is 15. | RESOLVED in amended commit 17e4301 — commit message and header comment now read "15 judge-only". |
| 5 | INFO | Docs | `evals/task-packs/doc_01_cli_readme/task.yaml:R7` | R7 text covers both Contributing (item 7) and Licence (item 8) under `prompt_ref: 7`; item 8 has no dedicated pointer. | ACCEPTED as-is. doc_01 is judge-only; no executable check depends on prompt_ref precision. A dedicated R for Licence can be added later without re-authoring. |

## Resolution record (commit 17e4301)

**Finding #1 — be_01 C4 split (RESOLVED):**

The bundled `[R20][R21][R22]` test was replaced with:

```
async function rotateActiveRefresh() { ... return { res, store, oldJti }; }

it("[R20] rotates an active refresh cookie and invalidates the old jti", ...)
  → asserts res.status==200, store.active.has(oldJti)==false,
    store.active.size==1, setCookie includes refresh_token=

it("[R21] sets the rotated refresh cookie HttpOnly", ...)
  → asserts setCookie.some(c => /httponly/i.test(c))

it("[R22] sets the rotated refresh cookie SameSite=Strict", ...)
  → asserts setCookie.some(c => /samesite=strict/i.test(c))
```

Each test calls the shared helper and asserts exactly the one property named by its tag. The split is assertion-complete: no original assertion was dropped, and each requirement is now independently observable. A rotation bug will fail R20 without touching R21/R22; a missing cookie attribute will fail R21 or R22 independently.

**Finding #2 — fe_01 duplicate R10 (RESOLVED):**

Multi-tag at (old) line 136 changed from `[R4][R8][R10][R11]` to `[R4][R8][R11]`. R10 now appears exclusively in the dedicated blur test `[R10] renders error on blur with a bad email`. Set-equality check: 24 unique auto requirement ids, 24 unique tag instances across the test suite, 1:1.

Remaining multi-tags in fe_01 (`[R1][R2][R5]`, `[R4][R8][R11]`, `[R14][R15]`, `[R20][R21]`) are noted for the record: these share a test body but each id appears exactly once in the suite (no duplicate ownership). RFC-004 C4 prohibits missing tests and duplicate ownership — it does not prohibit co-located assertions for logically inseparable behaviours. These multi-tags were present in the original diff and are not findings.

## Adversarial spot-checks performed (both passes)

**Pass 1 (commit 58a4fd1) — carried forward:**

| Check | Result |
|---|---|
| be_01 RFC-004 table spot-checks (R3, R5, R18, R21, R26) | All pass |
| Security fallback (R18,R19,R21,R22,R24,R25 → correctness; no security key; Σ=1.00) | Pass |
| fe_01 auto allowed-set (correctness/accessibility/ux_states/type_safety) | Pass |
| fe_01 judge items (R3,R16,R19 → pattern_match; no test tag) | Pass |
| doc_01 all-judge (0 auto; evaluator_commands: []) | Pass |
| doc_01 maps_to covers all 5 criteria; Σ=1.00 | Pass |
| Version bumps (all three 1.0→1.1; no in-place edit to 1.0) | Pass |
| Immutability (no rubric/calibration/weight/logic change in diff) | Pass |
| Scope (no forgeplan mutation, no scoring-contract change) | Pass |

**Pass 2 (commit 17e4301) — fix verification:**

| Check | Result |
|---|---|
| R20 test body: asserts rotation + jti-invalidation + cookie-issued | Pass — semantically correct |
| R21 test body: asserts /httponly/i on set-cookie | Pass — semantically correct |
| R22 test body: asserts /samesite=strict/i on set-cookie | Pass — semantically correct |
| All original R20/R21/R22 assertions present across the three new tests | Pass — none dropped |
| be_01 R-tag set == auto id set (25 unique ids, 25 unique tag instances) | Pass |
| fe_01 R10 appears exactly once in test titles | Pass |
| fe_01 R-tag set == auto id set (24 unique ids, 24 unique tag instances) | Pass |
| Commit message counts (25+2, 24+3, 15) match task.yaml and EVID-044 | Pass |

## Positive observations

- The `rotateActiveRefresh()` helper extracts cleanly — the fix collapses the shared HTTP round-trip into one place without duplicating test infrastructure, and each of the three new tests is exactly as short as it needs to be.
- The security-fallback commenting discipline from the original commit is preserved in 17e4301: all six security requirements carry inline notes pointing to the RFC-004 security-component proposal, making future re-weighting a data update, not a re-authoring.
- The RFC-004 worked-example table (27-row be_01 decomposition) was implemented faithfully from the start; the amended commit touches only test structure, not the requirement definitions.
- Amended commit message is now self-documenting: it records which EVID drove the fixes and maps each finding number to its resolution.

## Test coverage delta

- Before: 621 tests green (per EVID-044 and 17e4301 commit message)
- After: 623 tests (the one bundled test became three; net +2 test functions in be_01); assertions unchanged
- Branches gained: none — restructuring only
- Branches still uncovered: score-neutrality calibration deferred (requires live judge calls per RFC-004 §Rollback Plan)

## Next steps

- PASS: orchestrator may proceed to guardian pre-merge gate
- Score-neutrality calibration (α≥0.70 / MAD≤1.5) remains deferred — this is by design per RFC-004 Phase 4 and requires live judge calls; a separate EVID from the first calibration session will close this gap
- Finding #5 (INFO/ACCEPTED): Licence section in doc_01 has no dedicated prompt_ref pointer; defer to a future R addition if desired

## Related evidence

- EVID-044: tester evidence (PASS — mechanical/structural checks, validator 3/3, 621 tests)
- This EVID-045 is the adversarial semantic review; both EVIDs together constitute the full Slice 2 quality gate

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: review
