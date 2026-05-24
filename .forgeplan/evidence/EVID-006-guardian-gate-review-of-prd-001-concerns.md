---
depth: standard
id: EVID-006
kind: evidence
last_modified_at: 2026-05-24T07:42:40.142868+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: EVID-008
  relation: supersedes
status: superseded
title: 'Guardian gate review of PRD-001: CONCERNS'
---

# EVID-006: Guardian gate review of PRD-001 — CONCERNS

## Structured Fields

verdict: weakens
congruence_level: 3
evidence_type: audit

## Verdict

**CONCERNS**

- **PASS** — orchestrator may activate via `forgeplan_activate(id=PRD-001)`.
- **CONCERNS** — orchestrator MUST dispatch a fixer + re-run a Profile B audit before another guardian pass.
- **BLOCKER** — orchestrator must halt the pipeline; artifact remains in draft.

**One-line justification:** No unresolved BLOCKERs in the chain, but two project-config-driven downgrades fire (`require_audit_pass: true` is unsatisfied — no Profile B PASS audit EVID is linked to PRD-001) plus one HIGH-severity acknowledged-but-unmitigated drift (PRD SC-2 wording vs ADR-002 evaluator-only reproduce semantics). Activating now would commit drift into the source-of-truth requirements.

## Artifact under review

- ID: `PRD-001`
- Kind: `prd`
- Status: `draft` (phase: `validate`)
- Title: `v0.1 smoke evaluation run`
- Depth: `standard`
- Parent: `EPIC-001` (status: `draft` — parent not yet active)
- Children/refines: `SPEC-001`, `RFC-001`, `ADR-001`, `ADR-002`, `ADR-003` (all draft)
- R_eff: `0.70` (Grade A); reliability `0.85`; formality `0.86`; granularity `0.80`

## EVIDENCE chain inspected

| EVID | Verdict | Source agent | Type | Critical findings (one-line) |
|---|---|---|---|---|
| `EVID-001` | supports (CL=2) | external prior-art research | audit | HELM `scenario_state.json` validates ADR-002; HELM does not snapshot per-eval pricing — POLLMEVALS contribution confirmed |
| `EVID-002` | supports (CL=2) | external prior-art research | audit | MTEB vendor-honor model + zero-shot score; informs in-distribution fraction display (future ADR), not blocking |
| `EVID-003` | supports (CL=2) | external prior-art research | audit | lm-eval-harness `--use_cache` SQLite is direct precedent for ADR-002; POLLMEVALS diverges to SHA256 content addressing over integer task versioning |
| `EVID-004` | supports (CL=2) | external prior-art research | audit | Inspect AI Task/Solver/Scorer L0–L8 maps cleanly; 3 gaps POLLMEVALS must fill (cost, hard immutability, leaderboard hygiene) — informs RFC-001 architecture |
| `EVID-005` | supports (CL=2) | external prior-art research | audit | SWE-bench Docker harness pattern reusable; scaffolding attribution gap is POLLMEVALS's central differentiator |

**Chain semantics note:** All 5 linked EVIDs are **external prior-art research audits**, not internal Profile B reviewer EVIDs of PRD-001. They validate the design choices made downstream (RFC-001, ADRs, SPEC-001) but do **not** constitute an audit of THIS artifact's requirements completeness, correctness, or readiness-to-activate. The user-supplied prompt explicitly states the architect-reviewer is running in parallel and instructs guardian to "assume CONCERNS if you can't access them" — that assumption fires.

No EVID supersedes another. No unresolved BLOCKERs anywhere in the chain.

## Gate criteria

| # | Criterion | Status | Notes |
|---|---|---|---|
| 1 | PRD-001 validate PASS — 0 MUST errors | ✅ | 0 errors, 2 SHOULD warnings (body-links-drift, orphan FRs FR-006/007/008/010), 1 COULD (prd-fr-format checkbox style) |
| 2 | R_eff > 0 (threshold) | ✅ | 0.70 (Grade A) ≥ 0; weakest_link=null; all 5 evidence scored 0.9 |
| 3 | All linked EVIDs have structured fields populated | ✅ | All 5: `verdict`, `congruence_level`, `evidence_type` present and parsed (R_eff=0.70 proves parser accepted them) |
| 4 | SPEC-001 + RFC-001 validate PASS | ✅ | Both 0 errors, 0 warnings. Activate via separate gates after PRD-001. |
| 5 | ADR-001..003 validate PASS | ⚠️ | All MUST=0. **SHOULDs**: ADR-001/002/003 each missing `## Invariants`, `## Rollback Plan`, `## Affected Files`. ADR-003 has 2 placeholders (line 112, 130: `ADR-XXX` future cross-refs — intentional, not unfilled). RFC-001 carries parent-level Invariants + Rollback Plan, partially covering. **These will block ADR-001..003's OWN activation gates**, not PRD-001's. |
| 6 | Architect-reviewer findings | ⚠️ | Per user prompt, assume CONCERNS — not accessible. Treat as missing Profile B PASS audit. |
| 7 | No contradictions PRD SC ↔ ADR decisions | ⚠️ | **SC-2 drift**: PRD SC-2 says "score variance = 0 at reproduce" but ADR-002 narrows to evaluator-only (LLM not re-called). ADR-002 explicitly self-flags this. **PRD-001 body has not been updated** — drift remains live. **Model version drift**: PRD body lists Claude Sonnet / GPT-4o-mini / Gemini Flash / Qwen 2.5 14B / Llama 3.1 70B; ADR-003 lists Claude Sonnet 4.6 / GPT-5 mini / Gemini 3 Flash / Qwen 3 14B / Llama 4 70B. PRD lineup names stale. |
| 8 | No orphan / stub indicators | ✅ | `forgeplan_health` verdict: `healthy`. 0 orphans, 0 blind_spots, 0 stale_drafts, 0 phase_mismatches, 0 gitignore_drift. |
| 9 | CLAUDE.md red-lines respected | ✅ | `.forgeplan/config.yaml` uses `api_key_env`; no direct artifact edits; no completed-run mutations; no destructive git ops |
| 10 | Methodology version pinned (v0.1.0) | ✅ | SPEC-001 manifest schema: `"methodology_version": {"const": "v0.1.0"}`. RFC-001 Invariants #5. Explicit and enforced. |

### Project-config gates summary: 6/7 (1 CONCERNS — `require_audit_pass`)

## Findings (3 actionable for fixer dispatch)

- **F-1 (HIGH)** `require_audit_pass` unsatisfied — 5 linked EVIDs are prior-art, not Profile B audits of PRD-001
- **F-2 (HIGH)** SC-2 wording drift vs ADR-002 — acknowledged but unmitigated
- **F-3 (MEDIUM)** Model lineup drift between PRD body and ADR-003
- **F-4..F-6 (LOW)** informational only

## ADI cycle (retrofit per NOTE-002 — audit context)

### Abduction — hypotheses for "can PRD-001 be activated?"

- **H1**: All gate criteria pass; PASS verdict applies; activation proceeds.
- **H2**: Some gate criteria fail (specifically `require_audit_pass` and SC-2 drift); CONCERNS verdict applies; orchestrator must remediate before next gate pass.
- **H3**: A BLOCKER-class finding (e.g., red-line violation, MUST errors, missing methodology pin) requires halting pipeline indefinitely.

### Induction — verification per hypothesis

| Hypothesis | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (all green) | 10-criterion checklist: 7 ✅, 2 ⚠️, 0 ❌ → not all green | False | **H1 REFUTED** |
| Y2 (CONCERNS — fixable) | Criterion 6 (architect findings) + Criterion 7 (SC-2 drift) flagged ⚠️; F-1 + F-2 + F-3 actionable; orchestrator can dispatch fixers | Exactly the situation | **H2 SUPPORTED** |
| Y3 (BLOCKER) | 0 red-line violations; 0 MUST errors; methodology pin present; no unresolved BLOCKERs in chain | False | **H3 REFUTED** |

**Surviving hypothesis**: H2 — CONCERNS, remediation required. Resolved in subsequent EVID-007 (architect audit) + EVID-008 (gate 2 PASS).

## Trust Calculus per gate criterion / finding

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| PRD-001 validate PASS (0 MUST errors) | 9 | 9 | 9 | 27/27 | F: validator output. G: precise error counts. R: deterministic `forgeplan validate`. |
| R_eff = 0.70 Grade A | 9 | 9 | 9 | 27/27 | F: explicit number from `forgeplan_score`. G: precise grade + reliability sub-scores. R: deterministic. |
| All 5 EVIDs have structured fields | 9 | 9 | 9 | 27/27 | F: parser succeeded → fields parsed. G: 5/5 confirmed. R: deterministic. |
| F-1 `require_audit_pass` unsatisfied — gate-driving finding | 9 | 9 | 9 | 27/27 | F: project-config.yaml explicit threshold. G: precise (which gate, which threshold, which EVIDs don't satisfy). R: config file + chain inspection. |
| F-2 SC-2 drift acknowledged in ADR-002 self-flag | 9 | 9 | 8 | 26/27 | F: ADR-002 explicitly self-flags. G: exact wording quoted. R: ADR-002 body authoritative. |
| F-3 Model lineup drift between PRD and ADR-003 | 9 | 9 | 9 | 27/27 | F: side-by-side comparison. G: exact model names listed. R: both artifact bodies authoritative. |
| `forgeplan_health` = healthy | 9 | 8 | 9 | 26/27 | F: explicit verdict string. G: 0/0 for orphans/blind_spots/etc. R: deterministic. |
| Red-lines respected (`grep` on config.yaml clean) | 9 | 9 | 9 | 27/27 | F: regex scan executed. G: clean output. R: deterministic. |
| ADR-001..003 missing Invariants/Rollback/Affected — will block their own gates | 8 | 8 | 8 | 24/27 | F: validator SHOULD warnings. G: precise sections missing. R: validator output. |
| EPIC-001 status inversion allowed per user prompt (informational) | 7 | 7 | 8 | 22/27 | F: user direction. G: specific scenario described. R: chat prompt — high but ephemeral. |

**Decision strength**: average sum = 25.7/27 (95%). 5 claims at 27/27 (load-bearing for CONCERNS verdict). Two strong gate-driving findings (F-1, F-3) at 27/27. The verdict CONCERNS is honest and well-supported.

## Conclusions

- **Surviving hypothesis**: H2 (CONCERNS, remediation required)
- **Decision strength**: 95% — verdict CONCERNS solidly supported
- **Resolution path**: dispatch architect-reviewer + fix F-2/F-3 in PRD-001 body + re-run guardian
- **Post-remediation**: this EVID is SUPERSEDED by EVID-008 (gate 2 PASS); retained as historical truth per user direction
- **Lesson learned**: 5 prior-art EVIDs ≠ Profile B audit; `require_audit_pass` is a precise threshold that prevents weak chains from activating

## Notes

- Hindsight `memory_recall` returned no prior gate-failure memories (POLLMEVALS bank fresh — first guardian gate review).
- The 5 prior-art EVIDs are high-quality research artifacts; their value is real (validate RFC-001/ADR-002/SPEC-001 design choices). They simply don't substitute for a Profile B audit of PRD-001 itself.
- The R_eff=0.70 score is honest given CL=2 + 5 supporting evidences. **Activation eligibility ≠ R_eff eligibility.**

## Related Artifacts

- PRD-001 (informs — auto-linked at create; gate review of this artifact)
- EVID-008 (supersedes — gate 2 PASS, post-remediation)
- ADR-002 (contradicts implicit reading of PRD SC-2 — fix in PRD body F-2)
- ADR-003 (canonical model lineup — PRD body should reference F-3)
- NOTE-002 (Evidence Quality Standard — retrofit)

