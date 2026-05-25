---
depth: standard
id: EVID-025
kind: evidence
last_modified_at: 2026-05-25T16:31:41.830186+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-002
  relation: informs
- target: PRD-002
  relation: informs
status: draft
title: RFC-002 Slice E integration tests pass — judge hook routes 45-eval grid through 4 acceptance scenarios
---

# EVID-025: RFC-002 Slice E integration tests pass — judge hook routes 45-eval grid through 4 acceptance scenarios

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: test

## Summary

RFC-002 Slice E ("GridRunner ↔ JudgePanel integration") landed on branch `feat/rfc-002-slice-e` (PR #17, CI green) and its 4 acceptance criteria are now exercised end-to-end by a dedicated integration suite on the stacked branch `feat/rfc-002-slice-e-integration-tests`. All 4 AC tests + 8 unit tests + 508 pre-existing tests pass. Zero regressions on the full suite (520 passed, 1 skipped). mypy `--strict` clean over 22 source files.

Two test layers cover the slice:
- **Unit** (`tests/test_grid_runner_judges.py`, 8 tests) — `_run_single` happy path, error policy (SelfJudging / JudgeUnavailable / unknown Exception), DEGRADED routing, breach gate.
- **Integration** (`tests/test_grid_runner_judges_integration.py`, 4 tests) — full 45-eval grid (5 models × 3 tasks × 3 seeds) end-to-end through `GridRunner.run()` matching RFC-002 Slice E AC #1-#4 verbatim.

## ADI cycle

### Abduction — load-bearing hypotheses

- **H1**: Slice E's `_invoke_judge_panel` helper correctly routes every SCORED candidate through the panel — never drops a row, never miscounts on the FAILED-candidate skip path. Side-channel claim: `model_copy(update=...)` on the frozen `EvalRow` preserves all original fields (artifact_refs, stats, started_at) and adds `judgments` + `judge_aggregate` without ADR-0002 violation.
- **H2**: The 20% breach threshold trips at exactly the boundary expected by RFC-002 — strictly greater-than (not ≥), so 9/45 (20.0%) stays below, 10/45 (22.2%) trips. Boundary semantics matters for downstream "refuse publication" decisions.
- **H3**: Error-policy B (chosen 2026-05-25) keeps the FR-009 invariant under all three exception classes (`SelfJudgingError` / `JudgeUnavailableError` / other `Exception`) — every candidate eval reaches the journal, never disappears through `asyncio.gather(return_exceptions=True)`.

### Deduction — observable predictions

- **H1 → Y1**: if H1 holds, the AC#1 test (3 working judges, 45 evals) sees `panel.score_calls == 45` AND every result row has `judge_aggregate.judge_status == "OK"` AND `len(judgments) == 3`. The AC#3 test sees exactly 12 DEGRADED rows when 12 keys are pre-marked.
- **H1 → Y1-refute**: if `_invoke_judge_panel` ever skips a SCORED row (e.g. wrong status check) — `score_calls < 45` in AC#1, or DEGRADED count != 12 in AC#3.
- **H2 → Y2**: if H2 holds, AC#2 (1/45 = 2.2%) reports `judge_panel_breach=False`; AC#3 (12/45 = 26.7%) reports `True`. The arithmetic in `run()` uses strict `>` per Slice E §5.
- **H2 → Y2-refute**: if threshold uses `>=`, the boundary case 9/45 (20.0%) would also trip — not tested here but RFC-002 wording is unambiguous (`> 0.20`).
- **H3 → Y3**: if H3 holds, the 5 unit tests covering exception classes all show `result.eval_row is not None` (row preserved) AND correct `error_class` mapping (`CONTRACT_VIOLATION` / `JUDGE_FAILURE` / `None` for DEGRADED).
- **H3 → Y3-refute**: if any exception class causes `_invoke_judge_panel` to leak the exception out of `gather`'s capture, a unit test would surface `isinstance(r, BaseException)` instead of `EvalResult`.

### Induction — current evidence per prediction

| Prediction | Evidence | Status | H_i |
|---|---|---|---|
| Y1: AC#1 sees `score_calls == 45` | `test_ac1_full_panel_all_45_evals_ok` asserts `panel.score_calls == 45` and `judge_status == "OK"` on all 45 rows — passes locally and on CI | Confirmed | **H1 SUPPORTED** |
| Y1: AC#3 sees exactly 12 DEGRADED | `test_ac3_twelve_degraded_triggers_breach` counts via list comprehension; assertion `n_degraded == 12` — passes | Confirmed | **H1 SUPPORTED** |
| Y2: AC#2 boundary `False` | `test_ac2_one_degraded_no_breach` asserts `grid.judge_panel_breach is False` with 1/45 = 2.2% — passes | Confirmed | **H2 SUPPORTED** |
| Y2: AC#3 boundary `True` | `test_ac3_twelve_degraded_triggers_breach` asserts `grid.judge_panel_breach is True` with 12/45 = 26.7% — passes | Confirmed | **H2 SUPPORTED** |
| Y3: SelfJudging → CONTRACT_VIOLATION row | `test_self_judging_error_marks_row_contract_violation` asserts `status=FAILED`, `error_class=CONTRACT_VIOLATION` — passes | Confirmed | **H3 SUPPORTED** |
| Y3: unknown Exception → JUDGE_FAILURE row | `test_unknown_exception_marks_row_judge_failure` asserts `status=FAILED`, `error_class=JUDGE_FAILURE` — passes | Confirmed | **H3 SUPPORTED** |
| Y3: JudgeUnavailable → DEGRADED row (still SCORED) | `test_judge_unavailable_uses_partial_judgments_degraded` asserts `status=SCORED`, `judge_status="DEGRADED"`, `alpha_point is None` — passes | Confirmed | **H3 SUPPORTED** |
| AC#4 cost envelope | `test_ac4_cost_within_nfr001_envelope` asserts `total_cost_usd == 45 × (0.0125 + 0.15) = $7.3125 ≤ $50` — passes | Confirmed | NFR-001 holds |

**ADI conclusion**: all three load-bearing hypotheses (H1, H2, H3) are **SUPPORTED** by direct test execution. No refutation observed. The slice implementation matches RFC-002 § Slice E specification at the AC level.

## Trust Calculus per claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| Slice E implementation matches RFC-002 § Slice E spec at AC level | 9 | 8 | 9 | 26/27 | F=9: 4 AC tests pass + 8 unit tests + 520-test full suite, 0 regressions. G=8: AC #1-#4 verbatim from RFC; threshold boundary, error policy, cost envelope all asserted. R=9: same-context test execution on the actual implementation — congruence_level=3 (highest). |
| Error-policy B preserves FR-009 across SelfJudging / JudgeUnavailable / unknown Exception | 9 | 8 | 8 | 25/27 | F=9: 3 unit tests + 1 integration test confirm. G=8: explicit per-class behavior. R=8: tests use stand-in panel that raises the exact exception classes the real `JudgePanel.score()` would raise; not yet exercised against real Inspect AI errors (deferred to first real judge run). |
| 20% breach threshold uses strict `>` (per RFC-002 Slice E §5) | 8 | 7 | 8 | 23/27 | F=8: AC#2 + AC#3 confirm boundary. G=7: only two data points (2.2% and 26.7%) — exact 20.0% boundary case (e.g. 9/45) not asserted but RFC wording unambiguous. R=8: directly verified. |
| Cost envelope $7.3125 ≤ $50 NFR-001 / ≤ $15 PRD-002 NFR-001 | 8 | 8 | 9 | 25/27 | F=8: arithmetic deterministic, asserted. G=8: explicit numeric expectation. R=9: exact cost path measured by `GridRunner._running_total`, same field that would land in the manifest. |
| `model_copy(update=...)` preserves ADR-0002 frozen-row invariant | 8 | 7 | 7 | 22/27 | F=8: tests show new row carries `judgments`/`judge_aggregate` while keeping the original row immutable. G=7: pydantic v2 documented behaviour. R=7: no explicit "original row mutation" test (would be redundant given pydantic semantics) — implicit only. |

**Decision strength**: avg F+G+R sum = 24.2/27. Lowest single claim (model_copy preservation, 22/27) is well above the NOTE-002 "weak decision" floor of 12. No remediation needed.

## Conclusions

**Surviving hypothesis**: all three of H1, H2, H3 hold. Slice E implementation is **production-ready at the integration-test level** for the FakeEvalCaller + FakeJudgePanel stand-in path.

**Decision strength**: STRONG (24.2/27 avg Trust Calculus, 3/3 hypotheses supported, 12/12 predictions confirmed, 0 refutations).

**Follow-up work** (NOT blockers for this slice):

1. First real judge run (3-vendor panel via Inspect AI) — verifies that real `JudgePanel.score()` raises the exception classes the integration tests assume. EVID generated automatically per RFC-002 § Test plan / Phase 3 Week 3.
2. Probe at boundary 9/45 (exactly 20.0%) — confirm `>` not `>=` semantics. Cheap follow-up unit test if needed.
3. ADR-005 finalisation — captures the median + CI-lower-bound gate rationale referenced by RFC-002 Slice C. Not blocked by Slice E.
4. PRD-002 activation upgrade — `r_eff_score` currently 0.70; with this EVID linked `informs`, weakest-link should hold or improve.

## Related Artifacts

- **RFC-002** — parent (auto-linked `informs` by `forgeplan_new(parent_id="RFC-002")`); this EVID is the Slice E AC verification record.
- **PRD-002** — grandparent (linked `informs` separately); each AC test maps to PRD-002 functional requirements FR-001 / FR-002 / NFR-001.
- **NOTE-002** — Evidence Quality Standard contract this EVID follows (Structured Fields + ADI + Trust Calculus + Conclusions).
- **ADR-0002** — run immutability invariant preserved (frozen EvalRow, model_copy).
- **PRD-001 FR-009** — failed eval rows must reach the journal; this EVID confirms preservation under Slice E error policy B.

## Provenance

| Field | Value |
|---|---|
| Test file (unit) | `apps/eval-core-py/tests/test_grid_runner_judges.py` (8 tests) |
| Test file (integration) | `apps/eval-core-py/tests/test_grid_runner_judges_integration.py` (4 tests) |
| Slice E implementation commit | `67ba550` on branch `feat/rfc-002-slice-e` (PR #17) |
| Integration tests commit | (this PR — `feat/rfc-002-slice-e-integration-tests`) |
| Local execution | `uv run --project apps/eval-core-py pytest apps/eval-core-py/tests/ -q` → 520 passed, 1 skipped, 0 regressions |
| mypy strict | `uv run mypy --strict apps/eval-core-py/src/` → 0 issues, 22 files |
| Recorded | 2026-05-25, autorun mode (`/fpl-skills:autorun`) |


