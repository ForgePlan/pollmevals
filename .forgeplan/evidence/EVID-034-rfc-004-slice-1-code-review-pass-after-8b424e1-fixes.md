---
depth: standard
id: EVID-034
kind: evidence
last_modified_at: 2026-05-29T14:17:00.154720+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-004
  relation: informs
status: draft
title: RFC-004 Slice 1 code review — PASS (after 8b424e1 fixes)
---

## Verdict

PASS

One-line justification: both HIGH findings (#1 MUST-4 silent-pass defect, #2 missing validator unit tests) are fully resolved in commit `8b424e1`; independently verified — 13/13 new validator tests pass, ruff clean, MUST-3/MUST-2 de-dup correct, OSError now logs to stderr; remaining open items are all non-blocking style/INFO deferred.

## Scope

- Parent: RFC-004
- Diff range: `58635d3..afb0f4c` (original Slice 1) + `afb0f4c..8b424e1` (fix commit)
- Files reviewed: 13 files total (original 11 + 2 changed in fix commit)
- Files: `packages/contracts/schemas/task.schema.json`, `packages/contracts/src/types.ts`, `apps/eval-core-py/src/contracts/task.py`, `apps/eval-core-py/src/contracts/__init__.py`, `apps/eval-core-py/src/scoring/requirements.py`, `apps/eval-core-py/src/scoring/__init__.py`, `apps/eval-core-py/tests/test_component_score.py`, `apps/eval-core-py/tests/test_task_contracts.py`, `apps/eval-core-py/tests/test_validate_task_specs.py` (added in 8b424e1), `infra/scripts/validate-task-specs.py`, `docs/04-runbook/04-task-authoring-guide.md`, `TODO.md`

## Tools run

| Tool | Exit | Notes |
|---|---|---|
| ruff check (Python, `8b424e1`) | 0 | clean — PLR0912 resolved by refactor; stale type: ignore removed; all prior style errors resolved |
| mypy (Python, `8b424e1`) | 0 | clean — unused-ignore errors resolved |
| tsc --noEmit (contracts) | 0 | clean (unchanged since afb0f4c) |
| pytest (original 48 + 13 new) | 0 | 61 tests pass — all 13 new validator tests in `test_validate_task_specs.py` pass; independently verified on working tree |
| validate-task-specs.py | 0 | 3/3 packs valid, additivity holds |
| eslint | n/a | not applicable to Python/JSON changed files |
| cargo clippy | skipped | not installed / not applicable |

## Findings

### Original findings (afb0f4c) — final disposition

| # | Severity | Category | Location | Status |
|---|---|---|---|---|
| 1 | HIGH | Bug | `infra/scripts/validate-task-specs.py:281` (orig) | RESOLVED in 8b424e1 — `_check_prompt_refs` now errors when `numbered_items` is empty and a `prompt_ref` is declared; regression test `test_must4_empty_numbered_items_regression` added and passing |
| 2 | HIGH | Test gap | `infra/scripts/validate-task-specs.py` (no test file) | RESOLVED in 8b424e1 — `tests/test_validate_task_specs.py` added: 13 tests covering all five MUST rejection paths, the finding #1 regression, SHOULD-6 warning, backward-compat skip, and helper parsing |
| 3 | MEDIUM | Bug | MUST-2/MUST-3 double-fire | RESOLVED in 8b424e1 — `_check_maps_to` now uses `elif`: MUST-3 fires for judge-only targets, MUST-2 fires for any other out-of-allowed-set target; one message per offending requirement; confirmed by `test_must3_auto_mapped_to_judge_only_rejected` asserting `not _has(msgs, "MUST-2")` |
| 4 | MEDIUM | Test gap | MUST-4 empty-numbered-items regression test | RESOLVED in 8b424e1 (same as finding #2) |
| 5 | LOW | Style | PLR0912 too many branches | RESOLVED in 8b424e1 — `_validate_requirements` refactored into five per-rule helpers: `_check_unique_ids`, `_check_maps_to`, `_check_prompt_refs`, `_check_weight_sum`, `_check_should_warnings` |
| 6 | LOW | Style | `infra/scripts/validate-task-specs.py:66,78` (orig) stale type: ignore | RESOLVED in 8b424e1 — both `# type: ignore[import-untyped]` comments removed |
| 7 | LOW | Style | `apps/eval-core-py/tests/test_component_score.py:14` import sort | DEFERRED — non-blocking; no new tests touching this file in 8b424e1 |
| 8 | LOW | Style | Unicode multiplication sign in docstring/comment (RUF002/RUF003) | DEFERRED — non-blocking |
| 9 | INFO | Architecture | `packages/contracts/schemas/task.schema.json` top-level no additionalProperties | DEFERRED — pre-existing condition, not introduced by this commit; acceptable to close in a follow-up |
| 10 | INFO | Docs | Authoring guide closed-loop section missing prompt_ref cross-reference | DEFERRED — non-blocking |
| S1 | INFO | Security | ReDoS in `[Rn]` regex | NOT A BUG — confirmed safe |
| S2 | INFO | Security | yaml.safe_load | NOT A BUG — correctly implemented |
| S3 | LOW | Security | swallowed OSError in `_parse_test_requirement_tags` | RESOLVED in 8b424e1 — `except OSError as exc: print(f"WARNING: ...", file=sys.stderr)` |

## Resolution (8b424e1 — 2026-05-29)

Commit `8b424e1` on branch `feat/rfc-004-requirements-schema` (parent `afb0f4c`) resolves all pre-activation findings from this review. Changes verified independently:

**Finding #1 — MUST-4 silent-pass:** New `_check_prompt_refs` helper separates the two failure modes — (a) `numbered_items` is empty and a `prompt_ref` is declared → error; (b) `numbered_items` non-empty and `prompt_ref` not in it → error. The original short-circuit `and numbered_items` is eliminated. Regression test `test_must4_empty_numbered_items_regression` passes.

**Finding #2 — validator unit tests:** `tests/test_validate_task_specs.py` adds 13 tests. All five MUST rejection paths have a dedicated test. The MUST-4 regression (finding #1) has its own named test. SHOULD-6 warning-but-not-block behavior is tested. Helper parsing functions are tested. All 13 pass on independent run.

**Finding #3 — MUST-2/MUST-3 double-fire:** `_check_maps_to` uses `elif`: MUST-3 for judge-only criterion names, MUST-2 for any other out-of-allowed-set value. One message per requirement. De-dup confirmed by assertion in `test_must3_auto_mapped_to_judge_only_rejected`.

**Finding #5 — PLR0912 branch complexity:** Refactored into five single-responsibility helpers. Ruff passes clean.

**Finding S3 — swallowed OSError:** `_parse_test_requirement_tags` now logs `WARNING: could not read test file <path>: <exc>` to stderr before returning empty set.

**Findings #6 stale type: ignore:** Both `# type: ignore[import-untyped]` comments on the `yaml` and `jsonschema` imports removed. Mypy passes clean.

Deferred (non-blocking, no activation gate): findings #7, #8 (style), #9 (pre-existing schema), #10 (doc cross-reference).

## Positive observations

- Strong: `component_score` is a clean pure function — no I/O, no side effects, correct `None` sentinel for zero-auto-req components, formula exactly matches RFC-004 specification, 33 tests cover all meaningful branches.
- Strong: Pydantic models use `ConfigDict(extra="forbid", frozen=True)` — addivity enforcement and immutability are correct by construction.
- Strong: Float tolerance check on MUST-5 uses `abs(weight_sum - 1.0) > _WEIGHT_SUM_TOLERANCE` with `_WEIGHT_SUM_TOLERANCE = 1e-6` — correctly tolerance-based, not exact equality.
- Strong: Additive schema design with `requirements` as optional means all pre-existing task packs validate without modification — backward compatibility tested by `test_old_pack_without_requirements_skips`.
- Strong: The per-rule helper refactor in 8b424e1 is cleaner than extracting everything post-hoc — each helper is independently testable and the `_validate_requirements` orchestrator is now a flat 10-line call sequence.

## Test coverage delta

- Before (afb0f4c): 48 tests (component_score + task_contracts) — validator script rejection paths unexercised
- After (8b424e1): 61 tests (48 + 13 new) — all five MUST rejection paths covered, MUST-4 empty-list regression pinned, SHOULD-6 warning branch covered, backward-compat skip covered, helper parsing functions covered
- Branches still uncovered (deferred): SHOULD-7 warning branches (test-file coverage check), `_parse_test_requirement_tags` OSError path (stderr log now present, not exercised), `requirements is not a list` guard

## Next steps

- PASS: RFC-004 Slice 1 is clear for the guardian activation gate
- Deferred items (#7, #8, #9, #10) are suitable for a follow-up chore commit; none gate activation
- Next phase per RFC-004 Implementation Phases: Phase 3 (evaluator emit) and Phase 4 (be_01 migration)

## References

- Parent: RFC-004
- Based on: ADR-008
- Related EVIDENCE: EVID-035 (tester — independently flagged same validator test-gap concern; both resolved by 8b424e1)
- Reviewer agent: `claude-code/claude-sonnet-4-6/code-reviewer-task-rfc004-slice1`

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: review

