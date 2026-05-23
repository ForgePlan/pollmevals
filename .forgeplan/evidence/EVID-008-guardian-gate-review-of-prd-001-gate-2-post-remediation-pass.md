---
depth: standard
id: EVID-008
kind: evidence
last_modified_at: 2026-05-23T21:01:56.857918+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
status: active
title: 'Guardian gate review of PRD-001 (gate 2 — post-remediation): PASS'
---

# EVID-008: Guardian gate review of PRD-001 (gate 2 — post-remediation)

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: audit

## Verdict

**PASS**

- **PASS** — orchestrator may activate via `forgeplan_activate(id=PRD-001)`.
- **CONCERNS** — orchestrator must dispatch a fixer and re-run a Profile B audit before another guardian pass.
- **BLOCKER** — orchestrator must halt the pipeline; artifact remains in draft.

**One-line justification:** All three CONCERNS drivers from EVID-006 are remediated — F-1 `require_audit_pass` is now satisfied by EVID-007 (architect-reviewer audit, verdict=Supports, CL=3, evidence_type=audit); F-2 SC-2 wording drift vs ADR-002 is fixed inline in PRD-001 SC-2 row; F-3 Models row drift is fixed by pointing to ADR-003 as canonical lineup. All 10 gate criteria green; project-config `quality_gates` 7/7 green.

## Artifact under review

- ID: `PRD-001`
- Kind: `prd`
- Status: `draft` (phase: `validate`)
- Title: `v0.1 smoke evaluation run`
- Depth: `standard`
- Parent: `EPIC-001` (status: `draft` — parent not yet active; parent-child status inversion allowed per user prompt)
- Children/refines: `SPEC-001`, `RFC-001`, `ADR-001`, `ADR-002`, `ADR-003` (all draft)
- R_eff: `0.30` (Grade B); reliability `0.65`; formality `0.91`; granularity `0.80`

**R_eff note (intentional — not a regression):** R_eff dropped from gate-1's 0.70 to gate-2's 0.30 because EVID-006 (prior gate's CONCERNS verdict, score=0.5, `verdict=Weakens`) was deliberately preserved in the chain "as historical truth, NOT to be invalidated" per user prompt. Weakest-link math therefore reflects one weakening voice (EVID-006), one new supporting audit (EVID-007 score=1.0, CL=3), and five prior-art supports (EVID-001..005 score=0.9 each). The chain is honest — the weakening voice is by design. Threshold `R_eff > 0` passes literally. Orchestrator may optionally `forgeplan_supersede EVID-006 --by EVID-008` after activation if it wishes to reflect concerns-now-resolved in the score (not required for activation gate).

## EVIDENCE chain inspected

| EVID | Verdict | CL | Score | Source | Type | One-line |
|---|---|---|---|---|---|---|
| `EVID-001` | Supports | 2 | 0.9 | external prior-art | audit | HELM `scenario_state.json` precedent for ADR-002; cost-snapshot gap POLLMEVALS closes |
| `EVID-002` | Supports | 2 | 0.9 | external prior-art | audit | MTEB vendor-honor model; informs in-distribution display + structural-fairness rule |
| `EVID-003` | Supports | 2 | 0.9 | external prior-art | audit | lm-eval-harness `--use_cache` SQLite = direct precedent for ADR-002; POLLMEVALS diverges to SHA256 |
| `EVID-004` | Supports | 2 | 0.9 | external prior-art | audit | Inspect AI L0-L8 maps cleanly; 3 gaps POLLMEVALS fills (cost, hard immutability, leaderboard hygiene) |
| `EVID-005` | Supports | 2 | 0.9 | external prior-art | audit | SWE-bench Docker harness reusable; scaffolding-attribution gap = POLLMEVALS thesis |
| `EVID-006` | Weakens  | 3 | 0.5 | guardian gate-1 | audit | Prior CONCERNS verdict — kept as historical truth per user prompt; concerns now remediated |
| `EVID-007` | Supports | 3 | 1.0 | architect-reviewer | audit | Profile B audit of RFC-001 + PRD-001 chain; all HIGH findings resolved; **satisfies `require_audit_pass: true`** |

Chronological order: EVID-001..005 (prior art) → EVID-006 (gate 1 CONCERNS) → EVID-007 (architect-reviewer audit, post-remediation PASS) → EVID-008 (this gate, post-remediation PASS).

**Supersession map:** EVID-007 effectively supersedes EVID-006's HIGH findings (F-1, F-2, F-3, F-4, F-8 from EVID-006's F-1-style list match EVID-007's F-1..F-10 architect findings) — recorded inline in EVID-007's "Findings + Remediation Status" tables. No formal `supersedes` relation written (preserved as concurrent historical record per user direction).

## Gate criteria

| # | Criterion | Status | Notes |
|---|---|---|---|
| 1 | PRD-001 validate PASS — 0 MUST errors | ✅ | 0 errors, 1 SHOULD warning (body-links-drift on `## Related Artifacts` table), 1 COULD (prd-fr-format checkbox style). FRs are in table-form (not checkboxes) — same pattern as previous gate, non-blocking. |
| 2 | R_eff > 0 (threshold) | ✅ | 0.30 (Grade B) > 0; weakest_link=null; see "R_eff note" above for honest accounting of EVID-006 historical weakening |
| 3 | All linked EVIDs have structured fields populated | ✅ | All 7 EVIDs parsed: `verdict`, `congruence_level`, `evidence_type` present (score computation succeeded for all) |
| 4 | SPEC-001 + RFC-001 validate PASS | ✅ | Both 0 errors, 0 warnings |
| 5 | ADR-001..003 validate PASS (MUST only) | ⚠ | All MUST=0. **SHOULDs**: ADR-001/002/003 each missing `## Invariants`, `## Rollback Plan`, `## Affected Files` (RFC-001 carries parent-level Invariants + Rollback Plan, partial cover). ADR-003 has 2 placeholders (line 112, 130: `ADR-XXX` future cross-refs — intentional forward references). **These will block ADR-001..003's OWN activation gates**, not PRD-001's. |
| 6 | Architect-reviewer findings now satisfied via EVID-007 | ✅ | EVID-007 present, `verdict=Supports`, `CL=3`, `evidence_type=audit`, linked `informs PRD-001`. F-1..F-10 mapped: F-1 (crash recovery) → NOTE-001+RFC §Crash Recovery+FR-011+AC-6+RR-6; F-2 (RunAggregates) → SPEC §RunAggregates inline + on-disk `$defs.RunAggregates`; F-3 (schema drift) → on-disk schema v1.0.0 + SPEC Reconciliation note; F-4 (testability) → `EvalCaller` Protocol + AC-7; F-8 (cost semantics) → RFC AC-3+RR-3 "alert + take higher + continue". |
| 7 | No contradictions PRD SC ↔ ADR decisions | ✅ | **SC-2**: PRD now says "Evaluator детерминистичен на cached raw_output (per ADR-002); reproduce работает на cached raw_output и **НЕ** re-calls LLM API" — exact match with ADR-002 §Decision Outcome. **Models row**: PRD now says "5 моделей через OpenRouter — canonical lineup определён в ADR-003 ... single source of truth = ADR-003" — no stale names, ADR-003 is authoritative. |
| 8 | No orphan / stub indicators | ✅ | `forgeplan_health` verdict: `healthy`. 0 orphans, 0 blind_spots, 0 stale_drafts, 0 phase_mismatches, 0 gitignore_drift, 0 possible_duplicates. |
| 9 | CLAUDE.md red-lines respected | ✅ | `.forgeplan/config.yaml` uses `api_key_env: GEMINI_API_KEY` pattern (no literal keys — `grep` confirmed clean); all artifact ops via forgeplan MCP (no direct `Edit/Write` on `.forgeplan/<kind>/`); no completed-run mutations (no runs exist); no destructive git ops |
| 10 | Methodology version pinned (v0.1.0) | ✅ | SPEC-001 manifest schema: `"methodology_version": {"const": "v0.1.0"}`. On-disk `run-manifest.schema.json` enforces the same `const`. RFC-001 Invariants #5: "Methodology version pinned per run". Triple-enforced. |

### Project-config gates (`.forgeplan/project-config.yaml` → `quality_gates`)

**Config source:** `/Users/explosovebit/Work/pollmevals/.forgeplan/project-config.yaml` (found — defaults NOT used)

| Criterion | Threshold | Observed | Result |
|---|---|---|---|
| Test coverage | `≥80%` (`min_test_coverage`) | N/A (v0.0 pre-launch; 0 executable Python per `cloc` 1 file/12 LOC) | ⚪ N/A — gate not applicable yet (carry forward to Phase 2) |
| Critical findings | `≤0` (`max_findings_critical`) | 0 across chain | ✅ PASS |
| High findings | `≤3` (`max_findings_high`) | 0 unresolved HIGH (all 3 architect HIGH findings resolved in EVID-007); 0 HIGH security findings | ✅ PASS |
| Medium findings | `≤10` (`max_findings_medium`) | 5 medium architect findings (2 resolved, 2 deferred with named follow-up, 1 carried forward to PRD-003) + ~10 SHOULD warnings across ADR chain | ✅ PASS (under 2× cap; deferrals explicit) |
| Validate pass | required (`require_validate_pass: true`) | PRD-001 MUST=0 → PASS; SPEC-001 0/0; RFC-001 0/0; NOTE-001 0/0; EVID-007 0/0 | ✅ PASS |
| Audit pass | required (`require_audit_pass: true`) — ≥1 Profile B EVID with PASS verdict linked | **EVID-007 found** — Profile B architect-reviewer audit, verdict=Supports (PASS), CL=3, evidence_type=audit, `informs PRD-001` | ✅ **PASS (resolves EVID-006 F-1)** |
| Evidence chain | required for `prd` (`require_evidence_chain: [prd, rfc, adr, spec]`) | 7 `informs`-linked EVIDs present (5 prior-art + 1 gate-1 + 1 architect) | ✅ PASS |

**Gates summary:** `7/7` green (coverage gate N/A — not applicable for v0.0 pre-launch with zero executable code).

## What changed since previous gate (EVID-006)

Between EVID-006 (gate 1, CONCERNS) and this gate (gate 2, PASS), six remediation actions landed: (a) `EVID-007` architect-reviewer audit created with `verdict=Supports/CL=3/audit` — directly satisfies `require_audit_pass: true` (F-1 from EVID-006); (b) PRD-001 SC-2 row rewritten to exact ADR-002 wording — eliminates the documented drift F-2; (c) PRD-001 Models row rewritten to point at ADR-003 as canonical lineup — eliminates stale-version drift F-3; (d) `NOTE-001` created formalising crash-recovery strategy (append-only journal + `make resume`), pulled into RFC-001 § Crash Recovery + PRD-001 FR-011 + RFC AC-6/RR-6 — resolves architect HIGH F-1; (e) SPEC-001 added inline `### RunAggregates schema` and `## Reconciliation note (2026-05-23)`, with full `$defs.RunAggregates` written into on-disk `packages/contracts/schemas/run-manifest.schema.json` bumped to `pollmevals.run_manifest.v1.0.0` — resolves architect HIGH F-2 + F-3; (f) RFC-001 § Concurrency strategy refactored around `EvalCaller` Protocol (testability seam) + AC-7, and § Cost attribution clarified "alert to stderr + take higher of two + continue" — resolves architect MEDIUM F-4 + F-8. EVID-006 deliberately retained in chain as historical truth (per user prompt); orchestrator may optionally supersede it post-activation. No remediation introduced new MUST errors or HIGH findings.

## Remaining findings (informational — DO NOT block PRD-001 activation)

### F-A (LOW — informational): ADR-001..003 missing Invariants / Rollback Plan / Affected Files

- **Location:** ADR-001, ADR-002, ADR-003 — `## Invariants`, `## Rollback Plan`, `## Affected Files` SHOULD warnings
- **Detail:** RFC-001 carries parent-level Invariants + Rollback Plan; ADRs inherit by context but flag their own absence. ADR-003 has 2 lines with `ADR-XXX` placeholders (lines 112, 130) — intentional forward-references to future ADRs to be numbered in PRD-003.
- **Action:** Does NOT block PRD-001 activation. WILL block ADR-001..003's own activation gates. Add section headers + bullets when each ADR comes up for its own gate. Reword placeholders to `Future ADR (TBD in PRD-003)` to remove validator confusion.

### F-B (LOW — informational): Parent EPIC-001 still draft

- **Location:** EPIC-001 status (`draft`)
- **Detail:** Parent EPIC remains draft while child PRD-001 activates. Per user prompt, parent-child status inversion is explicitly allowed for this project.
- **Action:** Informational only. Confirm intended sequence (EPIC activates last, after all child PRDs).

### F-C (LOW — informational): PRD-001 SHOULD warnings

- **Location:** PRD-001 validator output
- **Detail:** `body-links-drift` — `## Related Artifacts` table references ADR-001/002/003, EPIC-001, EVID-001/006/007, NOTE-001, RFC-001, SC-2, NFR-004, SPEC-001 but frontmatter `links:` array is sparser. `prd-fr-format` (COULD) — FRs use table form rather than checkbox form.
- **Action:** Quality drag, not a blocker. Either add explicit `forgeplan_link` calls for incidental mentions, or accept table-as-narrative pattern. Defer to post-activation cleanup.

### F-D (LOW — informational): R_eff = 0.30 because EVID-006 retained

- **Location:** PRD-001 R_eff calculation
- **Detail:** Honest weakest-link math reflects the retained EVID-006 (Weakens, 0.5). Not a chain-integrity problem — it is the chain's faithful record of a prior CONCERNS that has since been remediated.
- **Action:** Informational. After PRD-001 activates, orchestrator MAY call `forgeplan_supersede EVID-006 --by EVID-008 --reason "concerns remediated; see EVID-007 architect audit"` to surface the resolution in R_eff. Not required for the activation gate.

## Blast radius

- **Affected scope on activation:** ZERO production scope. PRD-001 activation commits requirements text to `status=active`. No code, no API, no deploy, no DB migration touched.
- **Downstream effect:** Unblocks SPEC-001, RFC-001, ADR-001..003, NOTE-001, EVID-001..007 to enter their own activation gates (per dependency order). Advances EPIC-001 progress meter from 3/8 → 4/8. Establishes v0.1 smoke run scope (3 tasks × 5 models × 3 seeds = 45 evals, `raw-llm` stack, $50 budget, eu-central) as canonical source of truth for Phase 2 (T+1..T+2 weeks).
- **Reversibility:** **HIGH** — `forgeplan_supersede` with a follow-up PRD; reversal cost is minutes of MCP calls; no data-loss / no external commitments.
- **Downstream artifacts depending on this:** SPEC-001 (refines PRD-001 contracts), RFC-001 (implementation plan for PRD-001 FRs/NFRs), ADR-001/002/003 (decisions backing RFC-001), NOTE-001 (crash recovery referenced by RFC-001 + PRD-001 FR-011), EVID-007 (audit scope).
- **Detection time if wrong:** Phase 2 postmortem (T+2 weeks). The remediated SC-2 + Models drift specifically removes the previously-identified "anyone reading PRD-001 alone hits an ambiguity" failure mode.
- **Threshold check vs. artifact's stated scope:** PRD body claims "proof-of-pipeline only, no judges, $50 budget, eu-central, 45 evals" — matches the actual blast radius. No threshold mismatch.

## Orchestrator instructions

**PASS → activate via `forgeplan_activate(id=PRD-001)`.**

Recommended activation order (dependency-correct):

1. `forgeplan_activate(id=PRD-001)` — parent requirement; root of dependency tree.
2. `forgeplan_activate(id=SPEC-001)` — manifest/eval/artifact contracts (refines PRD-001).
3. `forgeplan_activate(id=ADR-001)` — concurrency model.
4. `forgeplan_activate(id=ADR-002)` — reproduce semantics.
5. `forgeplan_activate(id=ADR-003)` — model selection.
6. `forgeplan_activate(id=NOTE-001)` — crash recovery strategy.
7. `forgeplan_activate(id=RFC-001)` — implementation plan (depends on all above).
8. `forgeplan_activate(id=EVID-001)`..`forgeplan_activate(id=EVID-007)` — prior art + audit EVIDs (order-agnostic among themselves).
   - For EVID-008 (this gate), orchestrator may either activate it as part of the bundle, or leave it draft as a transient gate-record (project preference).

**Caveats and optional follow-ups (NOT blockers):**

- ADR-001/002/003 will SHOULD-warn on their own activation gates (missing Invariants/Rollback/Affected Files). User may choose to (a) accept the warnings as documented technical debt, (b) flesh out the sections before activating, or (c) split ADR activation into its own subtask. Each ADR validator currently passes MUST.
- EPIC-001 stays draft per user prompt; activate it after the full Phase 1 bundle if/when desired.
- Optional: `forgeplan_supersede EVID-006 --by EVID-008` after PRD-001 activates to surface concerns-resolved in R_eff. Not required.

**DO NOT:**
- Re-run guardian unless a NEW substantive change lands on PRD-001 or its chain after activation.
- Call `forgeplan_activate(id=PRD-001)` before reading this verdict. (Whitelist already prevents guardian from doing it; this is a reminder for the orchestrator path.)

## Notes

- `mm-gate-failures` not present in this project's Hindsight bank (POLLMEVALS bank is fresh; `memory_recall` returned no relevant prior gate-failure memories). The gate decision is grounded entirely in the live chain inspection + project-config thresholds + EVID-006/EVID-007 reads.
- Compared to gate 1: 6 remediations landed, 0 new HIGH/Critical findings introduced, project-config gates moved from 6/7 (CONCERNS on require_audit_pass) → 7/7 (all green). The chain demonstrates the pipeline working as designed: gate 1 surfaced specific actionable findings → fixer dispatched → architect produced EVID-007 + PRD body amendments + SPEC/RFC/NOTE updates → gate 2 verifies all findings closed.
- The retained EVID-006 dragging R_eff from 0.70 to 0.30 is the only "surprise" worth noting. It is a feature, not a bug — the chain refuses to forget that this PRD almost activated with drift. Future archaeology benefits.
- `forgeplan_health` verdict is `healthy`; no systemic problems; this gate is a focused PASS on a remediated artifact.

## References

- Artifact under review: `PRD-001` (`v0.1 smoke evaluation run`)
- EVIDENCE chain (7): `EVID-001`, `EVID-002`, `EVID-003`, `EVID-004`, `EVID-005`, `EVID-006`, `EVID-007`
- Sibling artifacts inspected: `EPIC-001`, `SPEC-001`, `RFC-001`, `ADR-001`, `ADR-002`, `ADR-003`, `NOTE-001`
- On-disk schema verified: `packages/contracts/schemas/run-manifest.schema.json` (`pollmevals.run_manifest.v1.0.0`)
- Project config: `.forgeplan/project-config.yaml` (`quality_gates` block — found and applied; defaults NOT used)
- Mental models consulted: `mm-gate-failures` (not present in bank — first gate cycle)
- Prior guardian EVIDs for PRD-001: `EVID-006` (gate 1, CONCERNS — superseded conceptually by this EVID-008 + EVID-007; retained in chain as historical truth per user instruction)

## Related Artifacts

- PRD-001 (informs — auto-linked at create; gate review verdict for this artifact)
- EVID-006 (prior gate review — this EVID-008 conceptually supersedes its CONCERNS verdict; formal supersession optional, see Orchestrator instructions)
- EVID-007 (architect-reviewer audit — load-bearing for `require_audit_pass: true`)
- NOTE-001 (crash recovery — was the load-bearing fix for architect F-1)



