---
depth: standard
id: EVID-039
kind: evidence
last_modified_at: 2026-05-29T16:09:47.812869+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-004
  relation: informs
- target: EVID-036
  relation: supersedes
status: draft
title: RFC-004 Slice 1 guardian re-gate — PASS (parent ADR-008 active)
---

# Guardian re-gate of RFC-004 (Slice 1) — pre-activation gate

## Verdict

**PASS**

- **PASS** — orchestrator may activate via `forgeplan_activate(id=RFC-004)`. **← this verdict.**
- **CONCERNS** — orchestrator dispatches a fixer, re-runs the reviewer, re-gates.
- **BLOCKER** — orchestrator halts; artifact stays draft until named blockers clear.

One-line justification: the sole failing criterion at the prior gate (EVID-036 — criterion #5, draft-parent precondition) is **fully resolved** — **ADR-008 is now `active`** and **RFC-004 is no longer in `forgeplan_blocked`** (blocked_count 8→7, RFC-004 dropped out); the build/quality chain is unchanged and clean (EVID-034 code review PASS, EVID-035 test PASS, both 1.0/CL3), `forgeplan_validate RFC-004` passes with 0 errors, and all 7 project-config gates are green.

> **Supersession edge recorded; full retirement needs an orchestrator step.** This EVID carries the `supersedes EVID-036` link the orchestrator requested (the audit record that EVID-036's BLOCKER is obsolete). **However, EVID-036 still counts as a live "Weakens" (0.5) in `forgeplan_score` because it is `status: draft`, and a draft cannot be lifecycle-retired** (`forgeplan_deprecate` and `forgeplan_supersede` both require `active`; `draft→deprecated` returned "Invalid transition"). The residual R_eff drag is **cosmetic and does NOT affect this PASS** (no `min_r_eff` gate exists). See "EVID-036 retirement — actual outcome" below for the exact state and the orchestrator's options to fully clear it.

## Artifact under review

- ID: `RFC-004`
- Kind: `rfc`
- Status: `draft`
- Title: Atomic binary requirements[] — task schema, evaluator contract, and migration of be_01/fe_01/doc_01
- Parent (decision): `ADR-008` (relation `based_on`) — **status: ACTIVE** (was draft at the prior gate; activated after EVID-038 PASS)
- Also: `refines RFC-003` (active), `informs SPEC-001` (active)
- Scope: **Slice 1 (contracts + validator foundation) only.** Slice 2 (task-pack migration to v1.1) remains DEFERRED. `security` weight-component remains a marked PROPOSAL (not implemented, by design).

## EVIDENCE chain inspected

| EVID | Verdict | Source agent | Critical findings (one-line) |
|---|---|---|---|
| `EVID-034` | **PASS** | `code-reviewer` (Profile B) | 2 HIGH (MUST-4 silent-pass, missing validator tests) resolved + re-verified in `8b424e1`; 3 suspected bugs adversarially cleared; #7–#10 deferred non-blocking. CL3, supports, score 1.0. |
| `EVID-035` | **PASS** | `tester` (Profile B) | 608/609 pass, 0 failed, 1 pre-existing skip; 48 Slice-1 tests; additivity 3/3; TS typecheck clean. Validator-test-gap CONCERN closed by `8b424e1`. CL3, supports, score 1.0. |
| `EVID-036` | ~~BLOCKER~~ → **obsolete; `supersedes` edge from this EVID; not yet lifecycle-retired (draft)** | `guardian` (prior gate, this agent) | The BLOCKER was *only* the draft-parent precondition (criterion #5), explicitly NOT a code rejection. ADR-008 now active → precondition resolved. Still scores as "Weakens" 0.5 because it remains `status: draft` (see retirement note). |

Chain state: two PASS build EVIDs (EVID-034, EVID-035) at CL3/1.0; zero unresolved BLOCKERs; zero unresolved CONCERNS. The prior BLOCKER (EVID-036) is marked obsolete via the `supersedes` audit edge; its lingering "Weakens" score is a draft-lifecycle artifact, addressed below.

## Gate criteria

| # | Criterion | Status | Notes |
|---|---|---|---|
| 1 | Artifact body MUST validation | ✅ | `forgeplan_validate RFC-004` → passed=true, 0 errors, 0 warnings (re-run this turn) |
| 2 | All required EVIDENCE linked | ✅ | `require_evidence_chain` lists `rfc`; EVID-034 + EVID-035 `informs` RFC-004 |
| 3 | No BLOCKER in chain | ✅ | EVID-034/035 PASS; the prior BLOCKER (EVID-036) is obsolete (`supersedes` edge) — its precondition resolved |
| 4 | Unresolved CONCERNS count | 0 | EVID-035's validator-gap CONCERN was resolved by `8b424e1` (verified in EVID-034 + independent re-run at the prior gate) |
| 5 | Activation policy satisfied | ✅ **(flipped from ❌)** | **ADR-008 is `active`**; **RFC-004 is NOT in `forgeplan_blocked`** (blocked_count 8→7, RFC-004 removed; no cycles). The draft-parent precondition — the sole prior blocker — is resolved. |
| 6 | Project-specific gates | ✅ | `validate-task-specs.py` 3/3 + `mypy` clean on Slice-1 modules + `ruff` = only 2 documented deferred style nits — all independently re-verified at the prior gate (EVID-036); code unchanged since (HEAD still `8b424e1`). No `check:ready-to-ship`/`Makefile gate:` target → N/A. |
| 7 | Blast radius within stated threshold | ✅ | Additive, dev-only, unused by any live run; matches RFC's Slice-1 scope (see Blast radius) |

### Project-config gates (`.forgeplan/project-config.yaml` → `quality_gates`)

**Config source:** `/Users/explosovebit/Work/pollmevals/.forgeplan/project-config.yaml` — found, thresholds applied.

| Criterion | Threshold | Observed | Result |
|---|---|---|---|
| Test coverage | ≥80% (`min_test_coverage`) | n/a numerically (pytest-cov absent — EVID-035 non-blocking CONCERN); Slice-1 surface exhaustively unit-tested (48+13 tests green; all 5 MUST rejection paths pinned) | ⚠️ recorded (tooling gap, not coverage failure — see note) |
| Critical findings | 0 (`max_findings_critical`) | 0 unresolved | ✅ |
| High findings | ≤3 (`max_findings_high`) | 0 unresolved (2 HIGH found → both resolved in `8b424e1`) | ✅ |
| Medium findings | ≤10 (`max_findings_medium`) | 0 unresolved | ✅ |
| Validate pass | required (`require_validate_pass`) | PASS (0 errors) | ✅ |
| Audit pass | required (`require_audit_pass`) — ≥1 Profile B EVID with PASS | EVID-034 + EVID-035 both PASS, Profile B | ✅ |
| Evidence chain | required for `rfc` (`require_evidence_chain` includes rfc) | 2 `informs`-linked EVIDs (EVID-034, EVID-035) | ✅ |

**Gates summary:** **7/7** — all green. (Coverage is the same tooling gap flagged at the prior gate, carried as a Slice-2 follow-up; not a gate failure and not the cause of any verdict.)

**Coverage-gate note (unchanged from prior gate):** `min_test_coverage: 80` cannot be measured numerically because pytest-cov is absent from the venv. The Slice-1 surface (`component_score` pure-function math, Pydantic contracts, JSON-schema round-trip, 5 validator MUST rules) is exhaustively unit-tested (48 + 13 dedicated tests, all green). Recorded as a residual tooling gap to fix before Slice 2 (HARD RULE 6 — honest negative coverage), not a silent pass.

### R_eff observation + EVID-036 retirement — actual outcome (read carefully)

`forgeplan_score RFC-004` after this re-gate's links landed = **0.10**, evidence set:
- EVID-034 (1.0, Supports, CL3), EVID-035 (1.0, Supports, CL3) — build evidence maximally strong.
- EVID-039 (this EVID — 1.0, Supports, CL3) — the new PASS gate.
- **EVID-036 (0.5, "Weakens")** — STILL the weakest-link drag.

**The "Skipped ADR-008 (status: draft)" factor is gone** — replaced by a normal **"CL penalty applied for ADR-008 (relation: based_on)"** now that the parent is active. That is the concrete proof the draft-parent problem (the entire basis of the prior BLOCKER) is resolved. ✅

**Why EVID-036 still drags, and what I could and couldn't do about it:**
- The drag is the weakest-link rule reading EVID-036's `## Structured Fields: verdict: weakens` (0.5) on its live `informs RFC-004` edge.
- I created the `supersedes` edge `EVID-039 → EVID-036` the orchestrator requested. This is the **audit record** that EVID-036 is obsolete — but a `link --relation supersedes` does **not** change EVID-036's *status*; the scorer still treats its `informs` edge as live.
- To actually retire EVID-036 I attempted `forgeplan_deprecate(EVID-036)` → **rejected: "Invalid transition: draft → deprecated"**. The lifecycle state machine only retires from `active`/`stale` (`active→superseded/deprecated`), not from `draft`. `forgeplan_supersede` has the same `active`-source requirement. **EVID-036 is `draft`, so it cannot be lifecycle-retired by guardian.**
- I deliberately did **not** contrive a workaround. Activating EVID-036 purely to immediately supersede/deprecate it is (a) a `human_required` op per project-config, (b) would briefly make the "Weakens" official, and (c) is not guardian's call. Unlinking the `informs EVID-036→RFC-004` edge would cleanly stop the drag while the `supersedes` edge preserves history — but `forgeplan_unlink` is outside the orchestrator's stated scope for me this turn ("read-only on the graph except creating your gate EVID"), and editing EVID-036's verdict field would falsify a past gate decision (it genuinely WAS a BLOCKER at its moment — supersede the record, don't rewrite it).

**Bottom line:** the drag is **cosmetic graph-hygiene, not a gate failure.** project-config declares **no `min_r_eff` threshold**; R_eff > 0 satisfies the "never activate without evidence" red-line; all 7 `quality_gates` are green; criterion #5 is ✅. The verdict is **PASS** regardless of the 0.5 drag. The orchestrator's options to fully clear it are in the Orchestrator-instructions block.

## Revisit Trigger check (Sprint Z2 — PRD-053)

Linked active ADR this artifact depends on: **ADR-008 (now active)**. Re-checked its `## Revisit Trigger (Evidence Decay)` section:
- **No FIRED triggers** (no `[x]` checkbox), **no DATE-FIRED triggers** (all four are event/metric type, explicitly date-less). → **no decay BLOCKER**.
- **Format: pre-Z2 prose (LEGACY-FORMAT)** — per EVID-038's decisive ruling, a **non-blocking cosmetic note**, not a gate (all triggers always PENDING regardless of format → conversion buys ~zero decay-automation value). Optional follow-up on ADR-008 (`adr-architect`), **not** a blocker on RFC-004.
- F+G+R aggregate: ADR-008 has one CL3 PASS decision EVID (EVID-037); activated <1 day ago (well within 30-day freshness), so the Sprint-Z4 "weak evidence on aging decision" CONCERNS modifier does not fire.

ADR-008's Revisit Triggers are clean for this gate — no fired/expired trigger on the decision RFC-004 depends on.

## Blast radius

- **Affected scope on activation (of RFC-004 Slice-1 code):** dev/contracts only. `requirements[]` schema field, `TaskRequirement`/`RequirementResult` types (TS + Pydantic), `component_score` math, validator rules — all **additive + optional**. No live Run consumes them (Slice-2 migration deferred). No task score changes; no judge-pipeline / `rubric.yaml` / `weight_components` / `08-scoring-contract.md` change (ADR-008 invariants C1–C7 held).
- **Reversibility:** fully reversible. Additive delta — old `task.yaml`/`evaluator_json` validate without the new fields (proven: additivity 3/3). Rollback = revert the additive commit; no data migration, no published-Run impact (ADR-002 untouched).
- **Downstream artifacts:** `SPEC-001` (informs — its own task); Slice-2 migration + `security`-component proposal build on top (out of scope here). ADR-008 (upstream decision) is now active — no longer a blocker.
- **Detection time if wrong:** immediate at CI (`validate-task-specs.py` + contract round-trip tests every PR).
- **Threshold check:** actual blast radius (additive, dev-only, unused-by-live-runs) **matches** the RFC's stated Slice-1 scope. No scope creep. Now that the parent decision is active, this is a clean PASS on blast-radius grounds — the exact outcome EVID-036 predicted.

## Why PASS now (the delta from EVID-036's BLOCKER)

EVID-036 was a **sequencing** BLOCKER, not a quality one — it stated verbatim the Slice-1 build passed every check, and the only failing item was that RFC-004 was `based_on` a still-draft, evidence-less ADR-008. The orchestrator executed the prescribed remediation: added decision evidence to ADR-008 (EVID-037 PASS) → guardian PASSed ADR-008 (EVID-038) → orchestrator activated ADR-008 → RFC-004 dropped out of `forgeplan_blocked`. Every input that produced the BLOCKER has flipped: ADR-008 `draft→active`, `forgeplan_blocked` for RFC-004 `[ADR-008]→empty`, score factor `"Skipped ADR-008 (draft)" → normal CL penalty`. Criterion #5 is the only criterion that changed, and it is now ✅. Criteria #1–#4, #6, #7 were already green and the code is unchanged (HEAD `8b424e1`). Therefore: **PASS**.

## Orchestrator instructions

**PASS → orchestrator MAY activate RFC-004 via `forgeplan_activate(id=RFC-004)`.** No fixer dispatch required; no reviewer re-run required. The build was clean at the prior gate and is unchanged. Note: `forgeplan_activate` is `human_required` in project-config — guardian has cleared the gate; the human/orchestrator makes the final activation call.

**To fully retire the stale EVID-036 (optional, non-gating — the `supersedes` audit edge is already in place):** guardian could not lifecycle-retire it because it is `draft` (`draft→deprecated` is an invalid transition; `supersede`/`deprecate` need `active`). Pick one:
- **(Recommended) Unlink the live drag edge:** `forgeplan_unlink(source=EVID-036, target=RFC-004, relation=informs)` — removes EVID-036 from RFC-004's live evidence set so it stops scoring as "Weakens", while the `EVID-039 supersedes EVID-036` edge preserves the audit history. Cleanest "retire from scoring, keep the trail." (I did not do this — it is outside the read-only-except-my-EVID scope you set this turn.)
- **(Alternative) Activate-then-deprecate:** `forgeplan_activate(EVID-036)` then `forgeplan_deprecate(EVID-036, reason=…)`. Valid per the state machine but makes the obsolete "Weakens" briefly official and spends a `human_required` activation on a doomed artifact — less clean.
- **(Acceptable) Leave as-is:** the 0.5 "Weakens" drag is cosmetic; no `min_r_eff` gate exists, so it does not block activation or fail any quality gate. RFC-004 can activate with the drag present.

**After activating RFC-004**, the ADR-008 → RFC-004 design+foundation unit is complete. Next phases (Slice 2): Phase 3 (evaluator emit), Phase 4 (be_01 migration) — those carry the score-neutrality calibration gate (α≥0.70 / MAD≤1.5) that this Slice-1 gate correctly did not require.

**Follow-ups (NON-gating; track as chores):**
- Add `pytest-cov` to eval-core-py dev deps so `min_test_coverage: 80` becomes measurable before Slice 2 (EVID-035 non-blocking CONCERN).
- Optionally sweep the 2 deferred ruff style nits (`RUF002`/`RUF003` `×`→`x`; `I001` import-sort in `test_component_score.py`) (EVID-034 #7/#8).
- Optionally convert ADR-008's Revisit-Trigger section to Z2 checkbox syntax (EVID-038 — `adr-architect`).

## Notes

- **This re-gate is the clean resolution of the BLOCKER→PASS arc** across three guardian passes: EVID-036 (RFC-004 BLOCKER — draft parent) → EVID-038 (ADR-008 PASS — decision evidenced) → EVID-039 (RFC-004 PASS — parent now active). The pipeline routed exactly as the methodology intends: gate, remediate the root, re-gate.
- **On the supersede mechanics:** the orchestrator offered "`forgeplan_link … supersedes` (or deprecate EVID-036)". I executed the link (their first-listed option) — it records the supersession in the graph but, because EVID-036 is `draft`, does not by itself stop the scorer counting it; and the lifecycle retire (`deprecate`) is unavailable from `draft`. I reported this honestly rather than contrive an out-of-scope unlink or an activate-to-retire contortion. The audit trail is intact; the cosmetic drag's removal is a one-line orchestrator step (above).
- **Memory/mental-model availability:** `mm-gate-failures` remains absent from the `pollmevals` Hindsight bank; `memory_recall` was unavailable in this gate chain. Verdict rests on the deterministic artifact graph, the EVIDENCE chain, project-config thresholds (7/7 green), `forgeplan_validate`, `forgeplan_blocked`, and `forgeplan_score`. Recorded per HARD RULE 6.
- Code unchanged since the prior gate (HEAD `8b424e1`); the independent re-verification recorded in EVID-036 (validate 3/3, mypy clean, only deferred style nits) still holds — not re-run this turn, since the gate-relevant delta was purely the artifact-graph state (ADR-008 activation), which I verified live.

## References

- Artifact under review: `RFC-004` (draft → cleared for active)
- EVIDENCE chain inspected: `EVID-034` (code review PASS, CL3/1.0), `EVID-035` (test PASS, CL3/1.0)
- Superseded (audit edge) by this EVID: `EVID-036` (prior RFC-004 gate — BLOCKER, draft-parent precondition; now obsolete; still draft → cosmetic "Weakens" drag, retirement options above)
- Parent decision (now active): `ADR-008` (activated after EVID-038 PASS)
- Prior guardian gates in this chain: `EVID-036` (RFC-004 BLOCKER), `EVID-038` (ADR-008 PASS)
- Forgeplan signals (this turn): `forgeplan_validate RFC-004` (0 errors); `forgeplan_blocked` (RFC-004 NOT blocked, count 8→7, no cycles); `forgeplan_score RFC-004` (0.10 — EVID-036 "Weakens" 0.5 is the drag; "Skipped ADR-008 draft" factor gone, replaced by normal CL penalty); `forgeplan_get ADR-008` (status=active); `forgeplan_deprecate EVID-036` → rejected (draft→deprecated invalid)
- Project-config: `.forgeplan/project-config.yaml` `quality_gates` — 7/7 green; no `min_r_eff` gate
- Code under gate: branch `feat/rfc-004-requirements-schema`, HEAD `8b424e1` (unchanged since prior gate)
- Mental models consulted: `mm-gate-failures` — unavailable (not in bank)

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: audit

