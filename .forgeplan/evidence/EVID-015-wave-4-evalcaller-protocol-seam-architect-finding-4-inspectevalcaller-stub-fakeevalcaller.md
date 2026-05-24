---
depth: standard
id: EVID-015
kind: evidence
last_modified_at: 2026-05-24T07:32:28.522384+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-001
  relation: informs
status: active
title: 'Wave 4 — EvalCaller Protocol seam (architect finding #4) + InspectEvalCaller stub + FakeEvalCaller'
---

# EVID-015: Wave 4 — EvalCaller Protocol seam (architect finding #4) + InspectEvalCaller stub + FakeEvalCaller

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "how should grid_runner invoke a single eval?")

- **H1**: Direct `await inspect_ai.eval(...)` call inside `grid_runner._run_single` — no abstraction. Simplest; relies on Inspect AI's stability and concretizes coupling.
- **H2**: `EvalCaller` Protocol seam (architect finding #4 resolution) — grid_runner depends on the Protocol, not on Inspect AI directly. Two impls: `InspectEvalCaller` (real LLM, Phase 2B) and `FakeEvalCaller` (deterministic mock for tests). Enables unit-testing grid_runner without LLM keys.
- **H3**: Full async backpressure framework (asyncio.Queue + workers + rate limiter classes) — would offer fine-grained per-provider rate control but adds significant complexity. Overkill for 45-eval smoke.

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 | grid_runner unit tests CANNOT run without OPENROUTER_API_KEY + live LiteLLM proxy; first smoke run is also the first test of the scheduler; architect finding #4 not resolved | Attempt to write a grid_runner test without LLM access — would require mock at `inspect_ai.eval` (mocking external lib boundary is brittle) |
| H2 | `isinstance(InspectEvalCaller(...), EvalCaller) == True`; `isinstance(FakeEvalCaller(), EvalCaller) == True`; grid_runner tests use `FakeEvalCaller` for full deterministic coverage including AC-7 (failure propagation); architect finding #4 closed | Tests + Protocol conformance assertions + grid_runner can run AC-7 without any LLM |
| H3 | Worker-pool implementation: ~400+ LOC, multiple queue types, rate-limiter abstractions; provides nothing for v0.1 smoke that Semaphore(3) doesn't already give | Compare estimated LOC + complexity vs ADR-001's choice |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (no seam) | Architect-reviewer EVID-007 finding #4 (MEDIUM): "no seam between scheduling logic and Inspect AI call... tests must either mock `inspect_ai.eval` (brittle) or actually call LLMs". This is exactly the friction H1 produces. PRD-001 AC-7 (failure propagation test) impossible to write deterministically without seam. | Friction confirmed by domain expert review | **H1 REFUTED** |
| Y2 (Protocol seam works) | Agent 9 shipped: `EvalCaller(Protocol, runtime_checkable=True)`; `isinstance(InspectEvalCaller(...), EvalCaller) == True` verified; `isinstance(FakeEvalCaller(), EvalCaller) == True` verified; `isinstance(NoCaller(), EvalCaller) == False` (negative case). 30/30 tests PASS + 236 existing still green = 266 total. FakeEvalCaller deterministic: same request twice → identical eval_id + artifact sha256. InspectEvalCaller stub raises NotImplementedError with "Phase 2B" + "OPENROUTER_API_KEY" in message. | All predictions held | **H2 SUPPORTED** |
| Y3 (worker-pool framework) | Not implemented. Rejected on prior-art grounds: ADR-001 explicitly says "Option A: Global asyncio.Semaphore(N=3)" is the chosen design and "Option C (Distributed job queue Celery+Redis) — Massive overkill for 45 evals". The full async backpressure framework would be in the same "overkill" category. | Excessive for v0.1 | **H3 REJECTED** |

**Surviving hypothesis**: H2 — Protocol seam. Architect finding #4 closed; grid_runner (Wave 5) now testable without LLM.

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| 30/30 eval-caller tests PASS + 236 existing still green (266 total) | 9 | 9 | 9 | 27/27 | F: explicit counts. G: precise. R: reproducible `pytest`. |
| Protocol conformance verified via `isinstance` (both positive + negative case) | 9 | 9 | 9 | 27/27 | F: explicit tests. G: 3 test cases (Inspect, Fake, NoCaller). R: deterministic — `runtime_checkable` Protocol is Python stdlib. |
| `FakeEvalCaller` deterministic: same request → same eval_id + artifact sha256s | 9 | 9 | 9 | 27/27 | F: explicit test. G: byte-equal sha256 assertion. R: hash determinism is cryptographic guarantee. |
| `InspectEvalCaller` stub raises `NotImplementedError` with required substrings | 9 | 9 | 9 | 27/27 | F: explicit test. G: substring assertions for "Phase 2B" + "OPENROUTER_API_KEY". R: deterministic. |
| `compute_eval_id` deterministic + matches `^[a-f0-9]{16}$` regex | 9 | 9 | 9 | 27/27 | F: explicit test. G: regex assertion + same-input-same-output assertion. R: sha256 is cryptographic. |
| mypy --strict 0 issues on 2 source files | 9 | 8 | 9 | 26/27 | Standard. |
| Architect finding #4 closed by this seam | 8 | 8 | 9 | 25/27 | F: explicit cross-reference to EVID-007 finding #4. G: aligns implementation with named architect concern. R: agent-reviewable. |
| Wave 5 grid_runner can be unit-tested without OPENROUTER_API_KEY | 8 | 7 | 8 | 23/27 | F: design implication of H2. G: not yet measured (Wave 5 will produce). R: high confidence based on Protocol semantics but not yet observed. |

**Decision strength**: average sum = 26.1/27 (97%) — **the highest-scoring EVID in the graph so far**. Five 27/27 claims (test counts, Protocol conformance, FakeEvalCaller determinism, InspectEvalCaller stub, eval_id determinism). Weakest is the Wave 5 testability prediction (23/27) — will become 27/27 after Wave 5 EVID lands.

## Wave summary

- **Sprint**: phase-2A, **Wave**: 4 of 5 (parallel with cost)
- **Worker**: `eval-caller` (agents-core:coder)
- **Files** (~523 LOC): eval_caller.py (262) + test_eval_caller.py (261, 30 tests)
- **Pipeline gates**: pytest 30/30 PASS (+ 236 existing green, 266 total + 1 skip), mypy --strict 0 issues, ruff All checks passed (3 auto-fixed)

## Acceptance criteria validation

- ✓ **EVID-007 architect finding #4** (HIGH — testability seam) — closed
- ✓ **RFC-001 § Concurrency strategy** — `EvalCaller` Protocol per the wording added to RFC during architect remediation
- ✓ **RFC-001 implementation task 5** (`apps/eval-core-py/src/orchestrator/eval_caller.py`) — shipped
- ✓ **PRD-001 AC-7 prerequisite** (grid_runner failure propagation test will use FakeEvalCaller — Wave 5)

## Conclusions

- **Surviving hypothesis**: H2 (Protocol seam — Inspect AI wrapping decoupled from scheduler)
- **Decision strength**: 97% — strongest EVID in graph so far
- **Follow-up evidence needed**: Wave 5 grid_runner tests demonstrating real use of FakeEvalCaller raises one claim from 23/27 → 27/27. Phase 2B will exercise InspectEvalCaller stub → real (raises that claim from "stub raises NotImplementedError" to "stub replaced with working impl").

## Related Artifacts

- RFC-001 (informs — auto-linked; § Concurrency strategy refined by this work)
- ADR-001 (concurrency semaphore lives OUTSIDE caller — grid_runner Wave 5)
- EVID-004 (Inspect AI prior art — `provider/model-name` format used in InspectEvalCaller signature; multi_scorer pattern from EVID-004 will land in PRD-002 Phase 3)
- EVID-007 architect finding #4 (directly resolved)
- EVID-014 (Wave 4 sibling — cost; together: complete pre-execution scheduler foundation)
- NOTE-002 (Evidence Quality Standard — written under new template from scratch)


