---
depth: standard
id: EVID-007
kind: evidence
last_modified_at: 2026-05-23T20:57:34.129261+00:00
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

- **Primary artifact**: RFC-001 (`rfc-v0-1-smoke-run-implementation-plan-orchestrator-on-inspect-ai`)
- **Parent traceability**: PRD-001 (`prd-v0-1-smoke-evaluation-run`)
- **Chain inspected**: SPEC-001, ADR-001, ADR-002, ADR-003, EPIC-001, EVID-001..005
- **Source files**: `packages/contracts/schemas/{run-manifest,stack,task}.schema.json`, `infra/scripts/{reproduce-local-run.sh,validate-task-specs.py}`, `apps/eval-core-py/moon.yml`, `stacks/raw-llm/stack.yaml`, `evals/task-packs/be_01_jwt_auth/task.yaml`
- **Fitness dimensions**: Modular boundary, Coupling, Data flow, Blast radius, Operability, Scalability, Testability, PRD-Gap

## Findings + Remediation Status

### HIGH severity (3) — all resolved

| # | Finding | Initial severity | Resolution | Status |
|---|---------|---|---|---|
| F-1 | Operability + Blast radius — orchestrator crash recovery undefined in manifest state machine; no `manifest.lock`, no 2PC, no journaling, no resume command. SC-1 at risk on first failure. | HIGH | **NOTE-001** created with append-only `manifest.journal.ndjson` + atomic rename + `make resume HASH=<x>` command. RFC-001 amended with `§ Crash Recovery` section. PRD-001 added FR-011. SPEC-001 `RunAggregates` and naming conventions extended for journal. AC-6 added to RFC-001. RR-6 added. | ✅ resolved |
| F-2 | Data flow + PRD-Gap — SPEC-001 `RunAggregates` reference but no definition; RFC-001 § Manifest write order step 4 "Aggregates computed" zero specification; FR-006 unmapped. | HIGH | SPEC-001 amended with **inline `### RunAggregates schema` section** specifying `counts_by_status`, `counts_by_error_class`, `total_cost_usd`, `total_wall_clock_ms`, `per_task_metrics`, `budget_breach`, `available_models_count`. On-disk `run-manifest.schema.json` includes full `$defs.RunAggregates`. AC-5 references aggregates explicitly. | ✅ resolved |
| F-3 | Coupling + Modular boundary — `packages/contracts/schemas/run-manifest.schema.json` was thin v1 (`models`/`tasks`/`stacks`) diverging from SPEC-001 rich version (`model_pins`/`stack_pins`/`task_pins` + `aggregates`/`status`/`seed_set`/`published_at`/`inspect_eval_log_sha256`). RFC nowhere noted this drift. | HIGH | **On-disk schema bumped to `v1.0.0` (rich) aligned with SPEC-001.** Full `$defs` for `StackPin`/`ModelPin`/`TaskPin`/`EvalRow`/`ArtifactRef`/`RunAggregates`. SPEC-001 added explicit "Reconciliation note (2026-05-23)" subsection declaring on-disk schema = enforcement of SPEC-001 = canonical contract. | ✅ resolved |

### MEDIUM severity (5) — addressed via doc updates or carried forward

| # | Finding | Resolution | Status |
|---|---------|---|---|
| F-4 | Testability — orchestrator's `run_one_eval` calls `inspect_eval` directly inside semaphore; no seam for unit tests of grid runner failure propagation. | RFC-001 § Concurrency strategy now introduces `EvalCaller` Protocol + `InspectEvalCaller` impl. Implementation task 5 added. AC-7 added: "1 of 5 coroutines raises → 5 manifest rows produced with failing one's error_class populated". | ✅ resolved |
| F-5 | Scalability + Coupling — `asyncio.Semaphore(3)` single-process commitment that PRD-003 weekly run (1000+ evals) will have to undo. | RFC-001 § Trade-offs explicitly tagged "carried-forward assumption per architect finding #5". ADR-001 already calls this out in § Consequences ("При переходе к weekly run — обязательно переход на Option B/C"). PRD-001 Out of Scope explicitly excludes "Multi-process distributed orchestrator". Acknowledged, not a blocker for smoke. | ⏭ carried forward to PRD-003 |
| F-6 | Coupling — `.eval` binary format opacity (EVID-004 Open Question: stable public schema?). | RFC-001 RR-7 added: "POLLMEVALS treats `.eval` as opaque; only SHA256 cross-ref; needed fields projected into manifest at publish time". | ✅ resolved |
| F-7 | PRD-Gap — FR-002 (stack spec validation), FR-010 (postmortem reader), SC-5 (postmortem ≤ 1 page) unmapped to RFC implementation loci. | PRD-001 "Next step" footer routes "Tactical задачу для postmortem generator + stack-spec validator (FR-002, FR-010, SC-5)" as follow-up after activation. Captured in `> Next step` line. | ⏭ deferred to Tactical task post-activation |
| F-8 | Operability — RFC-001 § Cost cross-check says "alert если delta > 10%" without defining what "alert" means in single-process design. | RFC-001 § Cost attribution layer + AC-3 + RR-3 now specify: "alert to stderr + take higher of two cost sources + continue". | ✅ resolved |

### LOW severity (2)

| # | Finding | Resolution | Status |
|---|---------|---|---|
| F-9 | Existing `infra/scripts/validate-task-specs.py` imports nonexistent `pollmevals_eval_core.registry` → orphan, FR-001 coverage broken. | RFC-001 implementation task 14 added: "fix orphan import `pollmevals_eval_core.registry`". PRD-001 Affected Files notes "current state: имеет orphan import — fix в Phase 2 первой задачей". | ✅ scheduled in Phase 2 |
| F-10 | `infra/scripts/litellm-proxy-up.sh` named without health-check, restart policy, port pin, version pin. | RFC-001 implementation task 15 added: "Docker compose с healthcheck". | ✅ scheduled in Phase 2 |

## Strong positives (carry forward as patterns)

- **Parent-PRD traceability**: every RFC section names PRD requirement by ID (FR-009, NFR-001, NFR-002). Rare and welcome — borrow across future RFCs.
- **Explicit invariants section**: 5 sentences each preventing a class of bugs. Borrow pattern.
- **ADR-002 honest tension surfacing**: ADR acknowledged PRD-001 SC-2 wording bug + proposed fix. Mature design hygiene.
- **Build-vs-buy thinking with evidence**: Alternatives justified by EVID-003/004/005, not by gut.
- **Pricing snapshot fixed at run start (Invariant #3)**: closes cost-comparability gap HELM/SWE-bench leave open — real product moat made explicit at architecture level.

## Blast radius assessment (carried from initial audit)

- Single-model failure: ✅ tolerated (`return_exceptions=True` + degraded mode ≥4 models)
- LiteLLM proxy mid-run failure: ⚠ moderate (no circuit breaker; second `make smoke-run` collides on same run_hash) — acknowledged but not fixed in v0.1; collision handling in Phase 2 first-run postmortem
- **Orchestrator process crash: ✅ now addressed by NOTE-001** (was the highest blast radius finding)
- Inspect AI version bumps: ✅ small blast radius (exact pin RR-1)

**Production scope**: smoke = single-machine, single-maintainer, $50 budget, eu-central. No production traffic. Blast radius is cost + time + reputational debt (PRD-002 blocked until smoke green).

## Sources

1. forgeplan MCP — all 11 artifacts read (PRD/SPEC/RFC/3 ADR/EPIC/5 EVID + NOTE-001)
2. `/Users/explosovebit/Work/pollmevals/packages/contracts/schemas/run-manifest.schema.json` (post-fix v1.0.0)
3. `/Users/explosovebit/Work/pollmevals/packages/contracts/schemas/{stack,task}.schema.json`
4. `/Users/explosovebit/Work/pollmevals/infra/scripts/{reproduce-local-run.sh,validate-task-specs.py}`
5. `/Users/explosovebit/Work/pollmevals/apps/eval-core-py/moon.yml`
6. `/Users/explosovebit/Work/pollmevals/stacks/raw-llm/stack.yaml`
7. `/Users/explosovebit/Work/pollmevals/evals/task-packs/be_01_jwt_auth/task.yaml`
8. Static analysers run: `cloc` (116 files / 11.4k LOC; 1 Python file / 12 LOC = confirms v0.0 pre-implementation)

## Confidence

🟢 **High** — this is a design-time review (no orchestrator code exists yet — `cloc` shows 0 implementation Python). Findings are about plan fitness, not extant code. Remediations are at the artifact level (PRD/SPEC/RFC/ADR/NOTE updates) which are 1:1 verifiable via diff. The 2 deferred items (F-5 scalability, F-7 postmortem) are explicitly carried forward with named follow-up artifacts.

## Verdict (post-remediation)

**PASS** for PRD-001 + SPEC-001 + RFC-001 + ADR-001..003 activation. Remaining items (F-5, F-7) are explicit deferrals to PRD-003 / Tactical task, not blockers.

## Related Artifacts

- PRD-001 (auto-linked at create, informs)
- SPEC-001 (informs — F-2 resolution)
- RFC-001 (informs — F-1/F-4/F-6/F-8 resolution)
- ADR-001 (informs — F-5 scalability acknowledgment)
- NOTE-001 (informs — F-1 crash recovery resolution lives here)
- EVID-006 Guardian gate review (informs — sibling Profile B audit)
- EPIC-001 (audit scope grandparent)





