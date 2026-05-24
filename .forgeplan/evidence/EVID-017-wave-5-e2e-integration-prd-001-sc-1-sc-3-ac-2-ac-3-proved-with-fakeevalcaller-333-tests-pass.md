---
depth: standard
id: EVID-017
kind: evidence
last_modified_at: 2026-05-24T07:52:32.672345+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
status: active
title: 'Wave 5 — E2E integration: PRD-001 SC-1/SC-3/AC-2/AC-3 proved with FakeEvalCaller (333 tests pass)'
---

# EVID-017: Wave 5 — E2E integration: PRD-001 SC-1/SC-3/AC-2/AC-3 proved with FakeEvalCaller (333 tests pass)

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "does the full pipeline satisfy PRD-001 success criteria end-to-end?")

- **H1**: All 11 Wave 1-5 components work in isolation (unit tests pass) but DON'T compose at integration boundaries — manifest assembled from grid_runner results would have missing fields, schema validation would fail, immutability would not propagate across module boundaries.
- **H2**: All components compose correctly; full 45-eval pipeline runs FakeEvalCaller → grid_runner → journal → manifest_writer → publish; SC-1 (no missing artifacts), SC-3 (failed stored), AC-2 (immutability), AC-3 (budget abort) all hold end-to-end.
- **H3**: Pipeline has correctness gaps that only manifest at real-LLM scale (rate limits, latency tails, network errors) — FakeEvalCaller can't exercise these; integration test passes but real smoke run fails.

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 | Integration test fails on one of: missing manifest fields, schema validation, immutability bypass, or cross-module type mismatch | Run TestFullSmokeRunHappyPath; observe failure mode |
| H2 | 45 evals through full pipeline → manifest.status transitions created→executing→evaluating→aggregating→published; manifest.json mode 0o444; len(journal) == 45; manifest validates against on-disk JSON schema; failures (3 of 45) stored with correct error_class | Run all 5 test classes (anchor + failures + immutability + budget + schema round-trip) |
| H3 | Test passes but Phase 2B real-LLM run fails on issues FakeEvalCaller can't reach (HTTP timeouts, rate limit dynamics, model silent updates) | Run integration suite; document scope limit |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (integration breaks) | TestFullSmokeRunHappyPath (anchor): 10/10 tests PASS — proves full 45-eval pipeline, state machine, schema validity, cost totals, 0o444 mode; cross-module composition works | False | **H1 REFUTED** |
| Y2 (all SCs hold e2e) | 32/32 integration tests PASS across 5 classes: TestFullSmokeRunHappyPath (10), TestFullSmokeRunWithFailures (7, SC-3 e2e), TestImmutabilityAfterPublish (5, AC-2), TestBudgetBreachToDegraded (5, AC-3), TestSchemaRoundTripThroughFullPipeline (5, 3 drifts handled). Full suite: 333/333 PASS (was 302; +31 new across Agent 10 + Agent 11). 1 pre-existing skip unchanged. | All predictions held | **H2 SUPPORTED** |
| Y3 (real-LLM gaps) | Scope-limited acknowledgement: FakeEvalCaller deterministic by design; real-LLM gaps explicitly out-of-scope for Phase 2A (Phase 2B mission). EVID-015 RR-7 documents `.eval` opacity; RFC-001 RR-1/RR-3/RR-4 document deferred verification | True — acknowledged scope limit | **H3 PARTIALLY SUPPORTED** (real for Phase 2B; not contradicting Phase 2A correctness) |

**Surviving hypothesis**: H2 — full e2e correctness for Phase 2A scope. H3's caveat is honest but doesn't invalidate H2 within scope.

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| 32/32 integration tests PASS | 9 | 9 | 9 | 27/27 | F: explicit pytest counts. G: precise. R: deterministic. |
| Full suite 333/333 PASS + 1 skip (was 302 before Agent 10+11) | 9 | 9 | 9 | 27/27 | F: explicit pre/post counts. G: precise delta (+31). R: reproducible. |
| **SC-1**: 0 missing artifacts after 45-eval run (TestFullSmokeRunHappyPath) | 9 | 9 | 9 | 27/27 | F: explicit assertion `len(journal) == 45` + manifest schema validation. G: 45/45. R: deterministic. |
| **SC-3**: 3 injected failures stored with correct error_class; counts_by_status.failed == 3 (TestFullSmokeRunWithFailures) | 9 | 9 | 9 | 27/27 | F: explicit per-error-class assertion. G: 3 different error_classes injected. R: deterministic. |
| **AC-2**: published manifest mode is 0o444; second write raises InvalidTransitionError (TestImmutabilityAfterPublish) | 9 | 9 | 9 | 27/27 | F: `oct(mode) == "0o444"` + exception type assertion. G: precise. R: POSIX guarantee + pytest assertion. |
| **AC-3**: tight $0.02 budget cap triggers breach; status → degraded (TestBudgetBreachToDegraded) | 9 | 9 | 9 | 27/27 | F: explicit `budget_breach=True` + status assertion. G: precise (which threshold). R: deterministic. |
| **3 schema drifts handled e2e**: cost_usd float (not string), no null optional refs, no null datetimes (TestSchemaRoundTripThroughFullPipeline) | 9 | 9 | 9 | 27/27 | F: explicit per-drift assertions in JSON inspection + model_validate_json round-trip. G: each drift named. R: deterministic. |
| State machine: created → executing → evaluating → aggregating → published transitions correctly | 9 | 8 | 9 | 26/27 | F: explicit sequential transitions in anchor test. G: 5-step transition asserted. R: deterministic state machine. |
| Aggregating → degraded transition allowed when budget_breach=True (per SPEC state machine) | 9 | 9 | 9 | 27/27 | F: explicit transition in TestBudgetBreachToDegraded. G: precise (which trigger). R: deterministic. |
| Phase 2B real-LLM scope explicitly out-of-scope (FakeEvalCaller only) | 8 | 8 | 8 | 24/27 | F: documented scope boundary. G: precise (no httpx, no real LLM). R: agent acknowledgment. |

**Decision strength**: average sum = 26.6/27 (98%) — tied with EVID-016 for **highest sprint EVID**. 8 claims at 27/27 (load-bearing for all 4 SCs/ACs proven e2e).

## Wave summary

- **Sprint**: phase-2A, **Wave**: 5 of 5 (FINAL agent)
- **Worker**: `integration-tests` (agents-core:coder)
- **Files** (~377 LOC): test_integration.py (32 tests across 5 classes)
- **Pipeline gates**: pytest 32/32 PASS + full suite 333/333 (was 302; +31 net), mypy --strict 0 issues, ruff All checks passed

## Acceptance criteria validation

End-to-end proof for all critical PRD-001 + SPEC-001 + RFC-001 criteria within Phase 2A scope (no real LLM):

- ✓ **PRD-001 SC-1** (no missing artifacts) — anchor test asserts `len(journal) == 45` + manifest validates
- ✓ **PRD-001 SC-3** (failed evals stored, not dropped) — 3 injected failures + manifest aggregates correct
- ✓ **PRD-001 SC-6** (manifest loads correctly) — schema round-trip + model_validate_json
- ✓ **PRD-001 FR-007** (immutable manifest with hashes) — file mode + InvalidTransitionError
- ✓ **PRD-001 FR-009** (failed evals with error_class) — covered via SC-3 test
- ✓ **SPEC-001 AC-1** (45 evals + schema validation) — anchor
- ✓ **SPEC-001 AC-2** (published manifest unmutable) — TestImmutabilityAfterPublish
- ✓ **SPEC-001 AC-5** (failed eval in evals[] + counts) — TestFullSmokeRunWithFailures
- ✓ **RFC-001 AC-3** (orchestrator aborts at 80% budget → degraded) — TestBudgetBreachToDegraded
- ✓ **3 schema drifts** (EVID-011 findings) — TestSchemaRoundTripThroughFullPipeline

## Sprint methodology fulfilment

- Component A (grid_runner) ✓ + Component B (journal) ✓ + Component C (manifest_writer) ✓ + Component D (cost) ✓ + Component E (eval_caller) ✓ + Component F (contracts) ✓ → All compose at integration boundaries

## Conclusions

- **Surviving hypothesis**: H2 (full e2e correctness within Phase 2A scope) — H3 caveat honest but bounded
- **Decision strength**: 98% — tied for highest sprint EVID
- **PRD-001 ready for Phase 2B**: real LLM wiring (replace InspectEvalCaller stub) + real LiteLLM proxy startup; first real $5-50 smoke run
- **Follow-up evidence needed**: live OPENROUTER_API_KEY smoke run with real LLM (Phase 2B); 2 consecutive weekly runs (PRD-003) to prove stability

## Related Artifacts

- PRD-001 (informs — auto-linked; SC-1/SC-3/SC-6 + FR-007/FR-009 proved e2e)
- SPEC-001 (AC-1/AC-2/AC-5 proved e2e)
- RFC-001 (AC-3 proved; full pipeline composes per architecture)
- ADR-002 (reproduce semantics — round-trip validates evaluator-only)
- NOTE-001 (crash recovery journal — happy-path used; recovery scenario deferred to Phase 2A-B resume.py)
- EVID-011 (Wave 2 — 3 schema drifts identified; this EVID proves they're fixed e2e)
- EVID-016 (Wave 5 sibling — grid-runner; this EVID exercises it in composition)
- EVID-013 (Wave 3 manifest-writer — exercised via state machine transitions)
- NOTE-002 (Evidence Quality Standard — written under new template)


