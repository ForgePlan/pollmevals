---
depth: standard
id: EVID-006
kind: evidence
last_modified_at: 2026-05-23T19:35:12.773856+00:00
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
| 7 | No contradictions PRD SC ↔ ADR decisions | ⚠️ | **SC-2 drift**: PRD SC-2 says "score variance = 0 at reproduce" but ADR-002 narrows to evaluator-only (LLM not re-called). ADR-002 explicitly self-flags this: *"PRD-001 SC-2 wording needs to be refined in next revision"*. **PRD-001 body has not been updated** — drift remains live. **Model version drift**: PRD body lists Claude Sonnet / GPT-4o-mini / Gemini Flash / Qwen 2.5 14B / Llama 3.1 70B; ADR-003 lists Claude Sonnet 4.6 / GPT-5 mini / Gemini 3 Flash / Qwen 3 14B / Llama 4 70B (Jan 2026 current). PRD lineup names are stale. |
| 8 | No orphan / stub indicators | ✅ | `forgeplan_health` verdict: `healthy`. 0 orphans, 0 blind_spots, 0 stale_drafts, 0 phase_mismatches, 0 gitignore_drift. |
| 9 | CLAUDE.md red-lines respected | ✅ | `.forgeplan/config.yaml` uses `api_key_env` pattern (no literal keys); no direct artifact edits (all via MCP); no completed-run mutations (no runs exist); no destructive git ops |
| 10 | Methodology version pinned (v0.1.0) | ✅ | SPEC-001 manifest schema: `"methodology_version": {"const": "v0.1.0"}`. RFC-001 Invariants #5: "Methodology version pinned per run". Explicit and enforced at contract level. |

### Project-config gates (`.forgeplan/project-config.yaml` → `quality_gates`)

**Config source:** `/Users/explosovebit/Work/pollmevals/.forgeplan/project-config.yaml` (found — defaults NOT used)

| Criterion | Threshold (from project-config.yaml) | Observed | Result |
|---|---|---|---|
| Test coverage | `≥80%` (`min_test_coverage`) | N/A (v0.0 pre-launch; 0 executable code) | ⚪ N/A — gate not applicable yet |
| Critical findings | `≤0` (`max_findings_critical`) | 0 across chain | ✅ PASS |
| High findings | `≤3` (`max_findings_high`) | 0 BLOCKER + 0 HIGH security findings | ✅ PASS |
| Medium findings | `≤10` (`max_findings_medium`) | ~10 SHOULD warnings across chain (PRD-001: 2, ADR-001: 3, ADR-002: 3, ADR-003: 4 incl. 2 intentional placeholders) | ✅ PASS (at cap, not over 2× cap) |
| Validate pass | required (`require_validate_pass: true`) | PRD-001 MUST=0 → PASS | ✅ PASS |
| Audit pass | required (`require_audit_pass: true`) — ≥1 Profile B EVID with PASS verdict linked | **None found** — 5 linked EVIDs are external prior-art research, not Profile B audits of PRD-001; explicit user instruction treats architect-reviewer as CONCERNS | ⚠️ **CONCERNS** |
| Evidence chain | required for `prd` (`require_evidence_chain: [prd, rfc, adr, spec]`) | 5 `informs`-linked EVIDs present | ✅ PASS |

**Gates summary:** `6/7` (1 CONCERNS, 0 BLOCKERs). Coverage gate marked N/A — not yet applicable for v0.0 pre-launch with zero executable code.

## Findings (CONCERNS-level — actionable for fixer dispatch)

### F-1 (HIGH — drives the CONCERNS verdict): `require_audit_pass` unsatisfied

- **Location:** PRD-001 link set
- **Detail:** Project-config requires ≥1 Profile B EVID with `verdict=PASS` linked to the artifact before activation. The 5 linked EVIDs (EVID-001..005) are **prior-art research** audits of external eval platforms — their `verdict` is `supports`, their CL is 2 (related context), and they audit HELM/MTEB/lm-eval-harness/Inspect AI/SWE-bench, **not PRD-001 itself**. They do not satisfy `require_audit_pass`.
- **Compounding:** User prompt explicitly states architect-reviewer is running in parallel and instructs guardian to assume CONCERNS for unaccessible findings.
- **Required action:** Wait for architect-reviewer EVID, OR dispatch `agents-pro:architect-reviewer` to produce one. Link it `informs PRD-001`. Verdict must be PASS (or CONCERNS-with-acknowledged-mitigations in PRD body).

### F-2 (HIGH — acknowledged-but-unmitigated): SC-2 wording drift vs ADR-002

- **Location:** PRD-001 `## Success Criteria` → SC-2 row vs ADR-002 § Decision Outcome
- **Detail:** PRD SC-2 states *"Скоринг детерминистичен → score variance при reproduce = 0 (бит-в-бит на deterministic полях)"*. ADR-002 explicitly clarifies this is achievable only for the evaluator (not LLM re-call), and self-flags: *"PRD-001 SC-2 wording needs to be refined in next revision: 'Reproducing one eval from manifest yields byte-equal evaluator_json on deterministic fields (excluding timestamps, token UUIDs, и любых других transient ID)'"*. PRD body has not been amended.
- **Risk if activated as-is:** PRD-001 becomes the source-of-truth requirement with an interpretation that ADR-002 has already deemed impossible. Future readers will hit the same ambiguity ADI raised; SC-2 will measure something different from what it appears to claim.
- **Required action:** Update PRD-001 SC-2 row to use ADR-002's refined wording (cite ADR-002 inline). Use `forgeplan_update id=PRD-001 body=<...>`.

### F-3 (MEDIUM): Model lineup drift between PRD body and ADR-003

- **Location:** PRD-001 `## Product Scope` → MVP `Models` line vs ADR-003 `## Decision Outcome` model table
- **Detail:** PRD body still references "Claude Sonnet, GPT-4o-mini, Gemini Flash, Qwen 2.5 14B, Llama 3.1 70B" (paren-wrapped as expected lineup). ADR-003 finalised "Claude Sonnet 4.6, GPT-5 mini, Gemini 3 Flash, Qwen 3 14B (Cerebras), Llama 4 70B (Runpod)" (Jan 2026 versions). The PRD's parenthetical is described as expected/illustrative rather than canonical, but readers will conflate it with the ADR-finalised lineup.
- **Required action:** Update PRD-001 Models row to point to ADR-003 ("see ADR-003 for canonical lineup") rather than restating stale version names.

### F-4 (LOW — informational, will block downstream gates): ADR-001..003 missing Invariants / Rollback Plan / Affected Files

- **Location:** ADR-001, ADR-002, ADR-003 — `## Invariants`, `## Rollback Plan`, `## Affected Files` (SHOULD warnings from validator)
- **Detail:** RFC-001 carries parent-level Invariants + Rollback Plan; ADRs inherit by context, but their own validation flags this. ADR-003 also has 2 lines flagged as placeholders (`ADR-XXX` on lines 112 and 130) — inspection confirms these are intentional forward-references to not-yet-numbered future ADRs in PRD-003, not unfilled fields.
- **Required action:** Does NOT block PRD-001 activation. WILL block ADR-001/002/003 activation. Fix when each ADR comes up for its own gate (add section headers + bullets even if short). The placeholder lines can be reworded to remove validator confusion (e.g. `Future ADR (TBD in PRD-003)`).

### F-5 (LOW — informational): Parent EPIC-001 still draft

- **Location:** EPIC-001 status (draft)
- **Detail:** PRD-001's parent epic is in draft. Activating PRD-001 while parent EPIC is draft creates a parent-child status inversion. No hard CLAUDE.md rule against it; EPIC tracks aggregate progress and may activate after all child PRDs reach activation.
- **Required action:** Informational only. Note for orchestrator to confirm intended sequence (EPIC activates last, or in parallel with first child PRD).

### F-6 (LOW — informational): PRD-001 SHOULD warnings

- **Location:** PRD-001 validator output
- **Detail:** body-links-drift (mentions ADR-0001/ADR-0002 legacy refs in `## Related Artifacts` table not in frontmatter `links:`); orphan FRs FR-006/007/008/010 (not referenced outside FR section).
- **Required action:** Quality drag, not blockers. Either remove incidental mentions or add explicit `forgeplan_link` calls; cross-reference orphan FRs into the Journey table where they apply.

## Blast radius

- **Affected scope on activation:** ZERO production scope. PRD-001 activation commits requirements text to `status=active`. No code, no API, no deploy, no DB migration touched.
- **Downstream effect:** Unblocks SPEC-001, RFC-001, ADR-001..003 to enter their own activation gates. Advances EPIC-001 progress meter from 3/8 → 4/8. Establishes v0.1 smoke run scope as canonical source of truth for next 2 weeks (Phase 2).
- **Reversibility:** **HIGH** — `forgeplan_supersede` with follow-up PRD; reversal cost is minutes of MCP calls; no data-loss / no external commitments.
- **Downstream artifacts depending on this:** SPEC-001 references PRD-001 SC-2 contract; RFC-001 references PRD-001 FRs/NFRs; ADRs-001..003 reference PRD-001 FR-009/NFR-001/NFR-002 and SC-2. Drift in PRD becomes drift in 4 dependents.
- **Detection time if wrong:** Phase 2 postmortem (T+2 weeks). Anyone reading PRD-001 SC-2 without ADR-002 context will encounter the wording ambiguity.
- **Threshold check vs. artifact's stated scope:** PRD body claims "proof-of-pipeline only, no judges, $50 budget, eu-central, 45 evals" — matches the actual blast radius. No threshold mismatch.

## Orchestrator instructions

**CONCERNS → halt activation. Dispatch fixers to address F-1, F-2, F-3 (in priority order), then re-run guardian.**

Specifically:

1. **Wait for / dispatch architect-reviewer** (`agents-pro:architect-reviewer`) to produce a Profile B EVID with `verdict=PASS` (or CONCERNS-with-mitigation) for PRD-001. Link it `informs PRD-001`. This addresses F-1 (the load-bearing CONCERNS driver per `require_audit_pass: true`).

2. **Dispatch a fixer (recommend `agents-core:coder` or direct user edit via `forgeplan_update`)** to:
   - Update PRD-001 SC-2 row to use ADR-002's refined wording (cite ADR-002 inline). [F-2]
   - Update PRD-001 Models row to reference ADR-003 as canonical (remove stale version names). [F-3]

3. **After fixes are recorded** (new EVID for the architect review + PRD body updated via `forgeplan_update`), re-run `guardian` for another gate pass.

4. **DO NOT call `forgeplan_activate PRD-001` until all three of the above are complete and guardian returns PASS.**

5. **Do NOT block on F-4, F-5, F-6** — those are informational at this gate. F-4 will resurface when ADR-001..003 come up for their own gates.

## Notes

- Hindsight `memory_recall` returned no prior gate-failure memories (POLLMEVALS bank is fresh — this is the project's first guardian gate review). All findings derive from the live chain inspection + project-config thresholds.
- The 5 prior-art EVIDs are **high-quality research artifacts** — their value to the chain is real (they validate RFC-001's "build on Inspect AI" decision, ADR-002's evaluator-only reproduce, SPEC-001's cost-snapshot contribution). They simply do not substitute for a Profile B audit of PRD-001 itself.
- The R_eff=0.70 score is honest given CL=2 (prior-art is "related context", not "same context") and 5 supporting evidences. Activation eligibility is not the same as R_eff eligibility.
- Project is `healthy` per `forgeplan_health`; no systemic problems — this is a focused, fixable gate failure on a single artifact.

## References

- Artifact under review: `PRD-001` (`v0.1 smoke evaluation run`)
- EVIDENCE chain: `EVID-001`, `EVID-002`, `EVID-003`, `EVID-004`, `EVID-005`
- Sibling artifacts inspected: `EPIC-001`, `SPEC-001`, `RFC-001`, `ADR-001`, `ADR-002`, `ADR-003`
- Project config: `.forgeplan/project-config.yaml` (`quality_gates` block)
- Mental models consulted: `mm-gate-failures` not present in this bank (first gate review)
- Prior guardian EVIDs for PRD-001: none (this is the first)

## Related Artifacts

- PRD-001 (informs — auto-linked at create; gate review of this artifact)
- ADR-002 (contradicts implicit reading of PRD SC-2 — fix in PRD body)
- ADR-003 (canonical model lineup — PRD body should reference)



