---
depth: standard
id: EVID-028
kind: evidence
last_modified_at: 2026-05-26T13:47:25.051218+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-006
  relation: informs
- target: RFC-003
  relation: informs
- target: NOTE-007
  relation: informs
status: active
title: fe_01_multistep_form task pack — 25 calibration + gold authored, G1+G3+G4 PASS, dynamic eval deferred
---

# EVID-028: fe_01_multistep_form task pack — 25 calibration + gold authored, G1+G3+G4 PASS, dynamic eval deferred

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## Summary

`fe_01_multistep_form` task pack went from empty scaffold to production-ready calibration state via the RFC-003 team-lead protocol. The frontend pack was authored by `agents-domain:frontend-developer` in one parallel dispatch alongside 5 other agents (be_01 bands + doc_01).

- Refined `task.yaml` + new `rubric.yaml` (6 criteria: correctness 0.30 / accessibility 0.25 / type_safety 0.15 / ux_states 0.15 / code_clarity 0.10 / test_alignment 0.05).
- Gold pack: `solution.tsx` (193 LOC React 19 3-step accessible form), `tests.spec.tsx` (vitest + @testing-library/react + jsdom + axe-core), `package.json` (pinned react 19.0.0, vitest 3.2.4, axe-core 4.10.0), `tsconfig.json` (strict + JSX react-jsx), `README.md`.
- 25 calibration samples (5 per band). Initial dispatch produced G3 collisions in good (4/5 useState) and mediocre (5/5 flat-useState) bands — fixed by second parallel dispatch (7 sample rewrites) to ensure ≤2 samples per idiom per band.

## ADI cycle

### Abduction

- **H1**: A React-19 multi-step form pack can demonstrate 5 distinct quality bands through accessibility/UX-state defects (not just compilation/type defects) — making it complementary to be_01 (security/runtime) coverage.
- **H2**: Frontend-specific dynamic evaluators (axe-core for a11y, @testing-library/react for behavior) are necessary to achieve band separation — static-only (tsc + lizard) cannot detect missing `aria-live` regions, broken focus management, or non-keyboard-navigable controls.
- **H3**: Parallel agent dispatch with strict file ownership (`evals/task-packs/fe_01_multistep_form/**` exclusive) produces 0 conflicts even when 6 agents touch sibling packs concurrently.

### Deduction → Induction

| Prediction | Evidence | Status |
|---|---|---|
| 5 distinct quality bands via a11y/UX defects | Calibration samples encode: missing aria-busy / no aria-live / wrong validation timing / localStorage instead of sessionStorage / div-as-button / no labels / `any` everywhere / unmounted form / infinite re-render — each band has clear a11y or behavior axis | Confirmed — **H1 SUPPORTED** |
| Static-only evaluators fail to separate bands | `EVAL-WIRE-fe_01.md` reports all bands score 0.80-1.00 on tsc+lizard; gold 0.90, broken 0.94, mediocre 0.92 — NO separation | Confirmed — **H2 SUPPORTED** |
| Dynamic (vitest+axe) would separate | `broken/sample-002.tsx` (no labels, div-as-button) would fail axe-core's `button-name`+`label` rules; `mediocre/sample-002.tsx` (no aria-live) would fail vitest a11y assertions; predicted SCORES under dynamic eval: broken ≤ 0.20, perfect ≥ 0.85 | UNTESTED until image built — **H2 awaiting EVID-026 sandbox image** |
| Zero boundary violations across 6 parallel agents | git status clean; no other pack mutated by fe_01 author; review reports confirm | Confirmed — **H3 SUPPORTED** |

**ADI conclusion**: H1 + H3 SUPPORTED. H2 SUPPORTED for negative half (static fails); awaiting EVID-026 image build for positive half (dynamic succeeds).

## Trust Calculus

| Claim | F | G | R | Sum |
|---|---|---|---|---|
| G1 provenance: 27/27 files carry header | 9 | 9 | 9 | 27/27 |
| G3 diversity post-fix: ≤2 samples per idiom per band | 8 | 8 | 8 | 24/27 |
| G4 contamination: 0 verbatim hits on `fe01:multistep-form:draft` namespace | 8 | 7 | 8 | 23/27 |
| Gold solution scores ≥ 0.85 on host-runnable evaluators | 8 | 8 | 8 | 24/27 |
| Dynamic evaluator (vitest+axe in sandbox) WILL separate bands | 7 | 6 | 5 | 18/27 — awaits image build verification; lowest claim |
| Parallel dispatch produced 0 file conflicts | 9 | 8 | 9 | 26/27 |

Avg F+G+R = 23.6/27. Lowest single claim (dynamic-eval-success prediction, 18/27) above NOTE-002 weak-decision floor — action: prioritize Docker image build (~10 min) to elevate this row to 24+/27.

## Conclusions

**Surviving**: H1 (a11y/UX-defect band design works), H2 (static insufficient — confirms NOTE-007 for FE too), H3 (parallel dispatch conflict-free).

**Architectural implication**: Frontend task packs MUST rely on axe-core + behavior tests, not on tsc+lint. EVID-026's vitest sandbox is the dependency-target.

**Deferred**: image build + dynamic verification.

## Related Artifacts

- PRD-006 (parent), RFC-003, ADR-007, NOTE-007, EVID-026, NOTE-002
- Review artifacts: REVIEW-anti-slop-G1-G3.md, REVIEW-anti-slop-G4-contamination.md, EVAL-WIRE-fe_01.md




