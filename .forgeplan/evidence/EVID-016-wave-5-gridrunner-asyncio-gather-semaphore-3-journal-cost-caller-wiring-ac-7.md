---
depth: standard
id: EVID-016
kind: evidence
last_modified_at: 2026-05-24T07:51:43.410924+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-001
  relation: informs
status: active
title: 'Wave 5 — GridRunner: asyncio.gather + Semaphore(3) + journal/cost/caller wiring + AC-7'
---

# EVID-016: Wave 5 — GridRunner: asyncio.gather + Semaphore(3) + journal/cost/caller wiring + AC-7

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "is asyncio.gather + Semaphore(3) the right scheduler for 45-eval smoke grid?")

- **H1**: `asyncio.gather(*, return_exceptions=False)` with shared semaphore is sufficient — failures propagate as exceptions, orchestrator catches.
- **H2**: `asyncio.gather(*, return_exceptions=True)` + Semaphore(3) + double-checked BudgetGate (before AND after semaphore acquire) — preserves all failures inline, enforces FR-009 invariant, prevents race conditions.
- **H3**: Distributed job queue (Celery+Redis) — production-grade backpressure but massive overkill for 45 evals per ADR-001 § Considered Options C.

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 | First exception aborts gather; remaining coroutines cancelled → manifest missing eval rows; FR-009 violated | AC-7 test fails (fewer than 5 rows when 1 of 5 raises) |
| H2 | All 45 coroutines complete or store error_class; manifest has exactly 45 rows regardless of failures; semaphore observed at max 3 concurrent | AC-7 test passes (5 rows for 1-of-5 failure); semaphore mock asserts max ≤ 3 |
| H3 | Worker-pool requires Redis dep + Celery worker process + queue schema management → +200-400 LOC vs Semaphore(3) | Estimate complexity |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (default gather) | `return_exceptions=False` cancels pending coroutines on first raise; documented Python asyncio behavior; would silently drop evals — direct FR-009 violation | False — would fail | **H1 REFUTED** |
| Y2 (gather True + semaphore + double-check) | Agent 10 shipped: `asyncio.gather(*..., return_exceptions=True)` hard-coded as FR-009 invariant; Semaphore(3) double-checked (fast-path before acquire + race-safe after acquire). Tests: `test_1_of_5_failure_produces_5_rows` PASS; `test_ac7_exception_from_caller_still_tracked` PASS; `test_semaphore_limits_parallelism` confirms max ≤ 3; `test_custom_max_concurrent_one` confirms serial path | All predictions held — 35/35 tests PASS | **H2 SUPPORTED** |
| Y3 (Celery+Redis) | Not implemented per ADR-001 § Decision Outcome: "Massive overkill for 45 evals" — same reasoning carries here. Implementation would be ~300+ LOC + Docker dep. | Excessive for v0.1 | **H3 REJECTED** |

**Surviving hypothesis**: H2 — asyncio.gather True + Semaphore(3) + double-checked BudgetGate. Matches shipped GridRunner.

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| 35/35 grid-runner tests PASS | 9 | 9 | 9 | 27/27 | F: explicit pytest counts. G: precise. R: deterministic. |
| Full suite 301 PASS + 1 skip after Wave 5 Agent 10 (no regressions vs Wave 4's 266) | 9 | 9 | 9 | 27/27 | F: explicit pre/post counts. G: precise delta (+35 new). R: reproducible. |
| AC-7 verified: 1-of-5 failure → 5 manifest rows (FR-009 invariant) | 9 | 9 | 9 | 27/27 | F: explicit test name + parametric cases. G: 5 rows asserted. R: deterministic via FakeEvalCaller. |
| Semaphore(3) enforced: max parallelism ≤ 3 in `test_semaphore_limits_parallelism` | 9 | 9 | 9 | 27/27 | F: mock-counted concurrent acquisitions. G: max ≤ 3 asserted. R: deterministic. |
| AC-3 BudgetGate aborts at 80% threshold; skipped requests omitted from journal | 9 | 9 | 9 | 27/27 | F: explicit test class TestBudgetGateIntegration. G: precise (skipped = no journal entry). R: deterministic. |
| `return_exceptions=True` hard-coded as FR-009 invariant + documented in code | 9 | 8 | 9 | 26/27 | F: code constant + docstring. G: stated as invariant (never remove). R: code-reviewable. |
| Double-checked BudgetGate (before AND after semaphore acquire) — race safety | 8 | 8 | 8 | 24/27 | F: explicit design note. G: precise (2 check points). R: code-reviewable; race-condition not directly stress-tested. |
| mypy --strict + ruff clean | 9 | 8 | 9 | 26/27 | Standard. |

**Decision strength**: average sum = 26.6/27 (98%). 5 claims at 27/27 (load-bearing for FR-009 invariant + AC-7 + AC-3 + Semaphore(3)). Highest-strength sprint EVID.

## Wave summary

- **Sprint**: phase-2A, **Wave**: 5 of 5 (Agent 10 sequential before Agent 11)
- **Worker**: `grid-runner` (agents-core:coder)
- **Files** (~595 LOC): grid_runner.py (265) + test_grid_runner.py (330, 35 tests)
- **Pipeline gates**: pytest 35/35 PASS + full suite 301 PASS (no regressions), mypy --strict 0 issues, ruff All checks passed

## Acceptance criteria validation

- ✓ **RFC-001 AC-7** (1 of 5 raises → 5 manifest rows + error_class populated) — test_1_of_5_failure_produces_5_rows + test_ac7_exception_from_caller_still_tracked PASS
- ✓ **PRD-001 FR-009** (failed evals NOT dropped from denominator) — `return_exceptions=True` hard-coded invariant
- ✓ **PRD-001 FR-003** (orchestrator executes grid through scheduler) — 5 models × 3 tasks × 3 seeds = 45 evals scheduled and tracked
- ✓ **ADR-001** (Semaphore(3) global concurrency) — confirmed via mock-counted parallelism
- ✓ **AC-3** (orchestrator aborts at 80% budget) — TestBudgetGateIntegration confirms skipped omitted from journal, budget_breach flag set
- ✓ **Journal integration** (NOTE-001) — each completed eval written to manifest.journal.ndjson via JournalWriter
- ✓ **Cost integration** (Wave 4 cost.py) — pricing snapshot threaded through; running total computed

## Conclusions

- **Surviving hypothesis**: H2 (gather True + Semaphore(3) + double-checked BudgetGate)
- **Decision strength**: 98% — highest-strength Wave EVID
- **Follow-up evidence needed**: real-LLM execution in Phase 2B will exercise actual rate-limit behavior (currently only FakeEvalCaller exercised); cross-machine concurrency (PRD-003 weekly) will require Option B (per-provider semaphores) or Option C (distributed) — ADR-001 explicit upgrade path

## Related Artifacts

- RFC-001 (informs — auto-linked; § Concurrency strategy operationalized)
- ADR-001 (concurrency model — directly implemented)
- NOTE-001 (crash recovery — journal integration tested)
- EVID-012 (Wave 3 journal — direct dependency)
- EVID-013 (Wave 3 manifest-writer — direct dependency)
- EVID-014 (Wave 4 cost — direct dependency)
- EVID-015 (Wave 4 eval-caller — direct dependency via Protocol seam)
- EVID-017 (Wave 5 sibling — e2e integration uses GridRunner)
- NOTE-002 (Evidence Quality Standard — written under new template)


