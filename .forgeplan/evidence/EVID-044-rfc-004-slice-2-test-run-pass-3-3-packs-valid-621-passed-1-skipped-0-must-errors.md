---
depth: standard
id: EVID-044
kind: evidence
last_modified_at: 2026-05-30T11:08:25.809063+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-004
  relation: informs
status: draft
title: 'RFC-004 Slice 2 test run — PASS: 3/3 packs valid, 621 passed / 1 skipped, 0 MUST errors'
---

## Verdict

**PASS**

3/3 task packs valid (0 MUST errors). Python suite 621 passed / 1 skipped (unaffected by migration). Ruff lint + format clean. All RFC-004 Slice 2 AC met. One expected SHOULD warning on doc_01 (15 items < 20 target — judge-only pack, acceptable per RFC-004).

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: test

## Runner detected

- Ecosystem: python
- Runner: pytest (via `uv run --project`)
- Output format: text (dot-progress + summary line)
- Config source: `apps/eval-core-py/pyproject.toml`

Secondary runner (validator script):
- Runner: `uv run -- python infra/scripts/validate-task-specs.py`
- Output format: text (per-pack ✓/⚠ lines + summary)

## Commands run

```bash
# Command 1 — PRIMARY GATE
uv run -- python infra/scripts/validate-task-specs.py
# Exit code: 0

# Command 2 — regression suite
uv run --project apps/eval-core-py pytest apps/eval-core-py/tests/ -q
# Exit code: 0

# Command 3 — lint
uv run --project apps/eval-core-py ruff check apps/eval-core-py/
# Exit code: 0

# Command 4 — format
uv run --project apps/eval-core-py ruff format --check apps/eval-core-py/
# Exit code: 0
```

Commit under test: `58a4fd1` on branch `feat/rfc-004-slice-2-pack-migration`

## Summary

| Metric | Value |
|---|---|
| Task packs validated | 3/3 |
| MUST errors | 0 |
| SHOULD warnings | 1 (doc_01 item-count — expected/acceptable) |
| Python tests passed | 621 |
| Python tests skipped | 1 |
| Python tests failed | 0 |
| Flaky (passed on retry) | 0 |
| Total Python tests | 622 |
| Pytest duration | 7.57 s |
| Ruff lint | clean (0 issues) |
| Ruff format | clean (54 files already formatted) |

## AC coverage delta

Parent: RFC-004
Acceptance criteria (from RFC-004 Slice 2 dispatch):

| AC item | Expected | Actual | Delta |
|---|---|---|---|
| 3 packs validate (0 MUST errors) | 3/3, 0 errors | 3/3, 0 errors | 0 — MET |
| be_01 requirement count | 27 (25 auto + 2 judge) | 27 (25 auto + 2 judge) | 0 — MET |
| fe_01 requirement count | ~27 (24 auto + 3 judge) | 27 (24 auto + 3 judge) | 0 — MET |
| doc_01 structure | judge-only | 15 judge items, 0 auto | MET |
| [Rn] tag coverage be_01/fe_01 | no untagged-auto SHOULD-7 warnings | 0 untagged-auto warnings | 0 — MET |
| Python suite unaffected | ≥621 passed / 1 skipped | 621 passed / 1 skipped | 0 — MET |

AC target on coverage %: n/a — RFC-004 specifies no statement-coverage threshold for this slice.

## Per-pack validator output

```
  ✓ evals/task-packs/be_01_jwt_auth/task.yaml
  ⚠ evals/task-packs/doc_01_cli_readme/task.yaml: [SHOULD-6] only 15 requirement items
      (target ≥ 20). Consider adding more atomic items for better auditing.
  ✓ evals/task-packs/doc_01_cli_readme/task.yaml
  ✓ evals/task-packs/fe_01_multistep_form/task.yaml

3/3 task specs valid
```

## Requirement counts (verified by Python introspection of task.yaml files)

| Pack | Total | Auto | Judge | maps_to distribution |
|---|---|---|---|---|
| be_01_jwt_auth | 27 | 25 | 2 | correctness=20, type_safety=5, test_alignment=1, code_clarity=1 |
| fe_01_multistep_form | 27 | 24 | 3 | correctness=9, accessibility=7, type_safety=6, pattern_match=3, ux_states=2 |
| doc_01_cli_readme | 15 | 0 | 15 | structural_completeness=7, factual_accuracy=3, actionability=2, consistency=2, clarity=1 |

Note on be_01 security folding: RFC-004 notes that 6 security `auto` requirements (R18–R19, R21–R22, R24–R25) currently `maps_to: correctness` rather than a dedicated `security` component — the security-component proposal is deferred per RFC-004 Invariant C5. The validator passed these without error (correctness is a valid auto-allowed target for be_01). This is consistent with the RFC's "default fallback" path.

## Failing tests

None — all tests passed.

## Slow tests (top 5)

Individual test timings not available (text output mode; no per-test JSON). Total suite 7.57 s for 622 tests (~12 ms/test average). No slowness concern.

## Flaky candidates

None observed. Single run, no retries needed.

## Score-neutrality calibration — DEFERRED

The α ≥ 0.70 / MAD ≤ 1.5 score-neutrality calibration is a **live-run gate** requiring judge LLM calls and the Docker eval sandbox. It cannot be executed in this static test run.

Status: **deferred — requires a live calibration run; baseline TBD.**

This is the primary outstanding gate before be_01/fe_01 1.1 packs can be promoted from draft. Per RFC-004 Rollback Plan: if α/MAD shifts materially, keep the 1.1 pack in `draft`, emit a separate EVID documenting the shift, re-tune requirement granularity before re-promoting.

## Next steps

- **PASS**: hand back to guardian/orchestrator for activation gate review.
- **Deferred gate**: schedule live calibration run (judge LLM calls + Docker sandbox) to verify score-neutrality (α ≥ 0.70, MAD ≤ 1.5) for be_01 1.1 and fe_01 1.1 before pack promotion.
- **Acceptable gap**: doc_01 SHOULD-6 warning (15 items < 20) is expected and acceptable for a judge-only pack — no action required.


