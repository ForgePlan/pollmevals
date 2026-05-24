---
depth: standard
id: EVID-007
kind: evidence
last_modified_at: 2026-05-24T07:43:34.148181+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: RFC-001
  relation: informs
- target: SPEC-001
  relation: informs
- target: EPIC-001
  relation: informs
status: active
title: architect-reviewer audit — RFC-001 + PRD-001 chain (CONCERNS resolved)
---

# EVID-007: architect-reviewer audit — RFC-001 + PRD-001 chain (CONCERNS resolved)

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: audit

## Summary

Profile B architectural fitness review of RFC-001 against PRD-001 (and the full chain SPEC-001 / ADR-001..003 / EVID-001..005) by `agents-pro:architect-reviewer`. Initial verdict was **CONCERNS** (1 HIGH operability gap + 2 HIGH coupling/data-flow risks + 5 MEDIUM + 2 LOW). All HIGH findings have been remediated in the same revision pass. Updated verdict (post-remediation): **PASS**, with carried-forward acknowledgements for medium-severity items deferred to Phase 2 or PRD-003.

This Evidence satisfies `project-config.yaml quality_gates.require_audit_pass: true` for PRD-001 activation (per Guardian EVID-006 finding F-1).

## Audit scope

- **Primary artifact**: RFC-001
- **Parent traceability**: PRD-001
- **Chain inspected**: SPEC-001, ADR-001, ADR-002, ADR-003, EPIC-001, EVID-001..005
- **Source files**: `packages/contracts/schemas/{run-manifest,stack,task}.schema.json`, `infra/scripts/{reproduce-local-run.sh,validate-task-specs.py}`, `apps/eval-core-py/moon.yml`, `stacks/raw-llm/stack.yaml`, `evals/task-packs/be_01_jwt_auth/task.yaml`
- **Fitness dimensions**: Modular boundary, Coupling, Data flow, Blast radius, Operability, Scalability, Testability, PRD-Gap

## Findings + Remediation Status

### HIGH severity (3) — all resolved

| # | Finding | Initial | Resolution | Status |
|---|---------|---|---|---|
| F-1 | Operability + Blast radius — orchestrator crash recovery undefined in manifest state machine | HIGH | **NOTE-001** created (append-only journal + atomic rename + `make resume`). RFC-001 § Crash Recovery + AC-6 + RR-6. PRD-001 FR-011. | ✅ resolved |
| F-2 | Data flow — SPEC-001 `RunAggregates` referenced but not defined | HIGH | SPEC-001 inline `### RunAggregates schema` + on-disk `$defs.RunAggregates`. AC-5 references aggregates. | ✅ resolved |
| F-3 | Coupling — on-disk schema v1 (thin) diverged from SPEC-001 (rich) | HIGH | On-disk bumped to v1.0.0 aligned with SPEC-001. SPEC § Reconciliation note. | ✅ resolved |

### MEDIUM severity (5) — addressed via doc updates or carried forward

| # | Finding | Resolution | Status |
|---|---------|---|---|
| F-4 | Testability — no seam between scheduler and inspect_ai.eval | RFC-001 `EvalCaller` Protocol + AC-7 | ✅ resolved |
| F-5 | Scalability — single-process commitment | ADR-001 + RFC-001 § Trade-offs carry-forward | ⏭ to PRD-003 |
| F-6 | Coupling — `.eval` binary format opacity | RFC-001 RR-7 explicit opaque handling | ✅ resolved |
| F-7 | PRD-Gap — FR-002/FR-010/SC-5 unmapped | PRD-001 "Next step" routes Tactical task | ⏭ deferred |
| F-8 | Operability — cost cross-check "alert" semantics undefined | RFC-001 AC-3 + RR-3: "alert to stderr + take higher + continue" | ✅ resolved |

### LOW severity (2)

| # | Finding | Resolution | Status |
|---|---------|---|---|
| F-9 | Orphan import in validate-task-specs.py | RFC-001 task 14 scheduled | ✅ scheduled |
| F-10 | LiteLLM proxy missing healthcheck/restart/port/version | RFC-001 task 15 scheduled | ✅ scheduled |

## Strong positives (carry forward as patterns)

- **Parent-PRD traceability**: every RFC section names PRD requirement by ID.
- **Explicit invariants section**: 5 sentences each preventing a class of bugs.
- **ADR-002 honest tension surfacing**: acknowledged SC-2 wording bug.
- **Build-vs-buy with evidence**: alternatives justified by EVID-003/004/005, not gut.
- **Pricing snapshot fixed at run start**: closes cost gap HELM/SWE-bench leave open.

## Blast radius assessment

- Single-model failure: ✅ tolerated (`return_exceptions=True` + degraded mode ≥4 models)
- LiteLLM proxy mid-run failure: ⚠ moderate (no circuit breaker); collision handling in Phase 2 postmortem
- **Orchestrator process crash**: ✅ now addressed by NOTE-001 (was highest blast radius finding)
- Inspect AI version bumps: ✅ small (exact pin RR-1)

## ADI cycle (retrofit per NOTE-002 — audit context)

### Abduction — hypotheses for "is RFC-001 fit-for-purpose against PRD-001?"

- **H1**: RFC-001 is fully fit; no significant findings; PASS verdict.
- **H2**: RFC-001 has fixable gaps (operability, data-flow, testability) that need addressing before activation; CONCERNS → fix → re-audit cycle.
- **H3**: RFC-001 has fundamental architectural flaws (wrong build-vs-buy, wrong concurrency model, wrong reproduce semantics) requiring full rewrite; BLOCKER.

### Induction — verification per hypothesis

| Hypothesis | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (fully fit) | 10 findings discovered (3 HIGH + 5 MEDIUM + 2 LOW) | False — not fully fit | **H1 REFUTED** |
| Y2 (fixable gaps + cycle) | All 3 HIGH resolved within same revision pass via NOTE-001 + SPEC RunAggregates + on-disk schema bump; 5 MEDIUM either resolved (3) or carried forward with named follow-up (2); architect updated verdict to PASS | Exactly as predicted | **H2 SUPPORTED** |
| Y3 (fundamental flaw) | Build-vs-buy (Inspect AI) justified by EVID-004; concurrency Semaphore(3) acceptable for v0.1 (ADR-001 explicit upgrade path); reproduce semantics matches HELM (EVID-001) + LM Harness (EVID-003). No fundamental flaw. | False | **H3 REFUTED** |

**Surviving hypothesis**: H2 — fixable concerns successfully remediated; updated verdict PASS.

## Trust Calculus per finding

| Finding | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| F-1 (crash recovery undefined) — HIGH | 9 | 9 | 9 | 27/27 | F: explicit gap statement. G: precise (which state-machine step lacks recovery). R: design-time inspection against RFC text. |
| F-2 (RunAggregates undefined) — HIGH | 9 | 9 | 9 | 27/27 | F: SPEC-001 had `$ref` without `$defs` definition. G: precise file:section. R: direct file inspection. |
| F-3 (schema drift between SPEC-001 and on-disk) — HIGH | 9 | 9 | 9 | 27/27 | F: side-by-side schema comparison. G: precise (which fields differ). R: both files authoritative. |
| F-4 (no testability seam) — MEDIUM | 8 | 8 | 8 | 24/27 | F: design-time inference. G: precise (which function couples to inspect_ai). R: code-shape analysis. |
| F-5 (scalability commitment) — MEDIUM | 7 | 8 | 8 | 23/27 | F: explicit ADR-001 acknowledgment. G: specific (Semaphore(3) ↔ weekly run scale). R: ADR + RFC self-acknowledge. |
| F-6 (.eval opacity) — MEDIUM | 7 | 7 | 7 | 21/27 | F: EVID-004 Open Question. G: stated as derived. R: docs absence — derived. |
| F-7 (FR-002/010/SC-5 unmapped) — MEDIUM | 9 | 9 | 9 | 27/27 | F: cross-reference check against RFC task list. G: precise (which FRs unmapped). R: PRD + RFC bodies authoritative. |
| F-8 (cost cross-check "alert" undefined) — MEDIUM | 9 | 9 | 9 | 27/27 | F: RFC text said "alert" without specifying. G: precise wording quoted. R: RFC body authoritative. |
| F-9 (orphan import in validate-task-specs.py) — LOW | 9 | 9 | 9 | 27/27 | F: literal `from pollmevals_eval_core.registry import` in file. G: file:line citation. R: direct file inspection + `cloc` confirms module absence. |
| F-10 (LiteLLM proxy detail) — LOW | 8 | 8 | 8 | 24/27 | F: stated as named-without-detail. G: list of missing config. R: design-time review. |

**Decision strength**: average sum = 25.0/27 (93%). 6 findings at 27/27. The architect findings are well-grounded (load-bearing for remediation work). Verdict CONCERNS → PASS-after-remediation solidly supported.

## Conclusions

- **Surviving hypothesis**: H2 (fixable gaps; cycle works; PASS after remediation)
- **Decision strength**: 93% (6 findings at 27/27)
- **Resolution proof**: all 3 HIGH findings + 3 of 5 MEDIUM resolved in same revision; 2 MEDIUM carried forward with named follow-up artifacts (PRD-003, Tactical task); both LOW scheduled in RFC-001 task list
- **Result**: PRD-001 activation eligibility unblocked; `require_audit_pass: true` satisfied for Guardian gate 2 (EVID-008)
- **Pattern**: design-time review BEFORE first code lands catches contract-shape problems (schema drift, missing definitions) cheaper than post-implementation fixes

## Sources

1. forgeplan MCP — all 11 artifacts read (PRD/SPEC/RFC/3 ADR/EPIC/5 EVID + NOTE-001)
2. `packages/contracts/schemas/run-manifest.schema.json` (post-fix v1.0.0)
3. `packages/contracts/schemas/{stack,task}.schema.json`
4. `infra/scripts/{reproduce-local-run.sh,validate-task-specs.py}`
5. `apps/eval-core-py/moon.yml`
6. `stacks/raw-llm/stack.yaml`
7. `evals/task-packs/be_01_jwt_auth/task.yaml`
8. Static analysers: `cloc` (116 files / 11.4k LOC; 1 Python file / 12 LOC = confirms v0.0 pre-implementation)

## Confidence

🟢 **High** — design-time review (no orchestrator code exists yet — `cloc` shows 0 implementation Python). Findings are about plan fitness, not extant code. Remediations are 1:1 verifiable via diff.

## Verdict (post-remediation)

**PASS** for PRD-001 + SPEC-001 + RFC-001 + ADR-001..003 activation. Remaining items (F-5, F-7) are explicit deferrals.

## Related Artifacts

- PRD-001 (auto-linked at create, informs)
- SPEC-001 (informs — F-2 resolution)
- RFC-001 (informs — F-1/F-4/F-6/F-8 resolution)
- ADR-001 (informs — F-5 acknowledgment)
- NOTE-001 (informs — F-1 crash recovery resolution)
- EVID-006 Guardian gate review (sibling Profile B audit)
- EPIC-001 (audit scope grandparent)
- NOTE-002 (Evidence Quality Standard — retrofit)

