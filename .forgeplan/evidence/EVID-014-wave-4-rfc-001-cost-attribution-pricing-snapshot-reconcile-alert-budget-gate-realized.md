---
depth: standard
id: EVID-014
kind: evidence
last_modified_at: 2026-05-24T07:31:47.596918+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-001
  relation: informs
status: active
title: 'Wave 4 — RFC-001 § Cost attribution: pricing snapshot + reconcile alert + budget gate realized'
---

# EVID-014: Wave 4 — RFC-001 § Cost attribution: pricing snapshot + reconcile alert + budget gate realized

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "how to track cost in v0.1 smoke with budget enforcement?")

- **H1**: Compute cost AFTER run from final manifest data + post-hoc pricing lookup — HELM-style (per EVID-001 — HELM does not snapshot per-eval pricing; reports aggregate cost in papers only). Simplest, no in-flight enforcement.
- **H2**: Snapshot pricing at run start (frozen for entire run), cross-check orchestrator's running total against LiteLLM proxy `/credits` (or `/spend/logs`), pessimistic on mismatch (take max), abort scheduling at 80% of cap. This is the POLLMEVALS divergence from HELM (RFC-001 Invariant #3).
- **H3**: Fetch pricing per-eval (no snapshot, no cache) — most accurate at the moment of each call, but vendor rate limits + cost-fetch latency add overhead per eval.

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 | Post-hoc cost requires loading the manifest and re-multiplying token counts × current prices; no way to abort mid-run when budget exhausted; cost numbers depend on when post-hoc pricing was fetched (drift risk) | Trace HELM's data flow per EVID-001; compare to PRD-001 SC-4 + AC-3 |
| H2 | Snapshot at run start = single httpx GET; per-eval cost computed from `pricing_snapshot[model_id] × eval_stats.tokens / 1e6` with Decimal precision; running total + 80% threshold checked before scheduling each new eval | Run `pytest test_cost.py + test_grid_runner.py` (Wave 5); verify BudgetGate stops scheduling at threshold; LiteLLM cross-check raises stderr alert on >10% delta |
| H3 | Per-eval fetch adds ≥1 HTTP round-trip per eval (45 evals = 45 extra calls); OpenRouter docs note rate limits on /models endpoint; latency budget already tight (NFR-002: 5 min per eval) | Estimate latency overhead + rate-limit risk |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (HELM post-hoc) | EVID-001 (HELM analysis): "HELM does not snapshot per-eval pricing at run time; reports aggregate cost in published papers but not in the live leaderboard." Industry gap explicitly called out by EvalEval Coalition. PRD-001 SC-4 requires ≤ $50 budget WITH AC-3 abort-at-80% — post-hoc cannot satisfy AC-3. | Post-hoc fails AC-3 (no mid-run abort) | **H1 REFUTED** (for POLLMEVALS use case; HELM-style works for their use case where no budget enforcement is needed) |
| Y2 (snapshot + reconcile + gate) | Agent 8 shipped: `fetch_pricing_snapshot()` via httpx (mock-tested), `compute_cost()` Decimal-precise (test_no_float_drift PASS), `CostReconciler.reconcile_with_litellm()` stderr alert at >10% delta (verified via `capsys`), `BudgetGate(cap)` boolean gate at 80% (8 parametrized tests around threshold). 47/47 tests PASS. | All predictions held in unit-test scope | **H2 SUPPORTED** |
| Y3 (per-eval fetch) | OpenRouter /models endpoint not designed for per-request lookup (returns full catalog ~hundreds of models). 45 × full catalog fetch = unnecessary data + extra round-trip latency per eval. POLLMEVALS does not need per-eval freshness — pricing changes during a 1-hour smoke run are vanishingly rare. | Overkill + risky | **H3 REJECTED** |

**Surviving hypothesis**: H2 — snapshot + reconcile + gate. Matches shipped `cost.py` implementation and satisfies PRD-001 SC-4 + AC-3 in a way HELM-style cannot.

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| 47/47 cost tests PASS | 9 | 9 | 9 | 27/27 | F: explicit pytest counts. G: precise per-test breakdown in agent report. R: reproducible `pytest`. |
| `Decimal` precision preserved (no float drift) | 9 | 8 | 9 | 26/27 | F: `test_no_float_drift` explicitly asserts Decimal accumulation. G: tested with multiple precision-sensitive examples. R: deterministic Decimal arithmetic. |
| Reconcile alert at >10% delta returns max (pessimistic) | 9 | 9 | 9 | 27/27 | F: `CostReconciler.reconcile_with_litellm` behavior explicit. G: `capsys` verifies stderr output content + return = max. R: reproducible. |
| BudgetGate aborts at exactly 80% threshold | 9 | 9 | 9 | 27/27 | F: 8 parametrized tests covering boundary (just below, at, just above). G: precise numeric thresholds. R: deterministic. |
| `test_both_zero_no_division_error` confirms no ZeroDivisionError | 9 | 8 | 9 | 26/27 | F: explicit test. G: tests floor at `Decimal("0.01")` denominator. R: deterministic. |
| `fetch_litellm_credits_total` gracefully degrades to `Decimal("0")` on HTTP error | 8 | 8 | 8 | 24/27 | F: graceful-degradation pattern per RFC-001 Rollback Plan. G: tested via mock HTTP failure. R: reproducible. |
| mypy --strict 0 issues on 2 source files | 9 | 8 | 9 | 26/27 | Standard. |
| OpenRouter pricing endpoint shape verified via mock | 7 | 7 | 6 | 20/27 | F: mocked, not live. G: shape correct per current OpenRouter docs as of 2026-05-24. R: not yet verified against live API (Phase 2B will validate). |

**Decision strength**: average sum = 25.4/27 (94%). Three 27/27 claims (test pass count, reconcile behavior, budget gate). Weakest is OpenRouter endpoint shape (20/27) — flagged for live-API verification in Phase 2B.

## Wave summary

- **Sprint**: phase-2A, **Wave**: 4 of 5 (parallel with eval-caller)
- **Worker**: `cost` (agents-core:coder)
- **Files** (~1007 LOC): cost.py (477) + test_cost.py (530, 47 tests)
- **Pipeline gates**: pytest 47/47 PASS, mypy --strict 0 issues, ruff All checks passed

## Acceptance criteria validation

- ✓ **RFC-001 § Cost attribution layer** — pricing snapshot + cost computation + reconcile + budget gate all realized
- ✓ **PRD-001 SC-4** (cost ≤ $50) — BudgetGate enforces; abort path tested
- ✓ **PRD-001 NFR-001** (budget cap enforcement) — same
- ✓ **RFC-001 AC-3** — orchestrator stops scheduling at 80% (8 parametrized tests around boundary)
- ✓ **Architect finding #8** (alert semantics) — "stderr + take higher + continue" implemented per resolution
- ✓ **RFC-001 RR-3** (LiteLLM cost log lag) — graceful degradation via `Decimal("0")` fallback

## Conclusions

- **Surviving hypothesis**: H2 (snapshot + reconcile + gate — POLLMEVALS divergence from HELM)
- **Decision strength**: 94% (three 27/27 claims, weakest 20/27)
- **Follow-up evidence needed**: live OpenRouter API call in Phase 2B raises the endpoint-shape claim from 20/27 → 25/27; live LiteLLM proxy round-trip verifies reconcile in production-realistic environment

## Related Artifacts

- RFC-001 § Cost attribution layer (informs — auto-linked; implementation receipt)
- PRD-001 SC-4 + NFR-001 (directly satisfied)
- EVID-001 (HELM cost gap — POLLMEVALS closes per H2 choice)
- EVID-005 (SWE-bench cost gap — same)
- EVID-007 architect finding #8 (resolved by H2 wording — "alert to stderr + take higher + continue")
- ADR-0002 legacy (immutability — pricing snapshot frozen at run start)
- NOTE-002 (Evidence Quality Standard — first Wave-4 EVID written under new template from scratch)


