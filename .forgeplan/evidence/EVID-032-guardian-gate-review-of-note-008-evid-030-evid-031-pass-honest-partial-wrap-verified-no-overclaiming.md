---
depth: standard
id: EVID-032
kind: evidence
last_modified_at: 2026-05-28T23:50:38.333944+00:00
last_modified_by: claude-code/2.1.156
links:
- target: NOTE-008
  relation: informs
status: active
title: 'Guardian gate review of NOTE-008 + EVID-030 + EVID-031: PASS (honest-partial wrap verified, no overclaiming)'
---

# EVID-032: Guardian gate review of NOTE-008 + EVID-030 + EVID-031

> Pre-activation gate for the Wave 0+1 deferred tech-debt cleanup sprint (Step 5 of Smith Plan, 2026-05-29). Reviewer: guardian (`claude-code/opus-4-8/guardian-task-wave01-cleanup-gate`). This is an HONEST-partial wrap (user chose "Stop + ship wins + defer Linux-deps"), so the gate confirms faithful representation of reality, not all-green.

## Verdict

**PASS**

- **PASS** — orchestrator may activate NOTE-008 + EVID-030 + EVID-031 and create the PR.

One-line justification: All three artifacts validate clean (0 MUST errors), and the load-bearing honesty check — does EVID-031 dress up a BLOCKED dynamic-eval run as success? — is **negative**: the raw `band_separation_results.json` confirms all 5 bands scored 0.0/skipped, and EVID-031 states this verbatim ("band separation ... has not been demonstrated end-to-end"; "do NOT promote ... on the basis of automatic-evaluator band separation"). No overclaiming detected in any of the three. The unit is internally consistent and the deferred work (lifecycle-promote, Tier 2 path, Linux deps) is explicitly fenced off, not implied done.

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: audit

## Artifacts under review

| ID | Kind | Status | Title | Verdict |
|---|---|---|---|---|
| NOTE-008 | note | draft | A3 + Fishbone — Wave 0+1 deferred cleanup | PASS |
| EVID-030 | evidence | draft | ADR-007 evidence backfill (hybrid sourcing) | PASS (1 quality nit, non-blocking) |
| EVID-031 | evidence | draft | Step 3 dynamic-eval verification (product sound, band-sep BLOCKED) | PASS — exemplary honesty |

ADR-007 (the artifact EVID-030 backfills) is **already** `status=active` (since 2026-05-26) with `R_eff=1.00` — EVID-030 is already `informs`-linked and is the sole evidence holding that score up. So this gate also implicitly validates that keeping ADR-007 at R_eff=1.00 is honest (see EVID-030 per-artifact verdict).

## EVIDENCE chain inspected (chronological)

| EVID/artifact | Verdict | Source | One-line |
|---|---|---|---|
| EVID-027 (be_01 pack) | active/PASS | task-pack author | 27/27 Trust Calculus; G1+G3+G4 PASS; cited by EVID-030 as H1 evidence |
| EVID-028 (fe_01 pack) | active/PASS | task-pack author | 25/27; a11y-defect monotonicity; cited by EVID-030 |
| EVID-029 (doc_01 pack) | active/PASS | task-pack author | 20/27; rubric-only doc scoring; single-agent heuristic (flagged) |
| EVID-001/003/005 (prior art) | active | researcher | contamination prior art; cited by EVID-030 to refute H2 |
| ADR-007 | active, R_eff=1.00 | adr-architect | the decision EVID-030 backfills (already linked) |
| **NOTE-008** | **draft → gate** | smith plan | A3 + Fishbone; honest "merge-then-patch" framing |
| **EVID-030** | **draft → gate** | evidence-gatherer | 4-hypothesis ADI; verdict=supports CL3 |
| **EVID-031** | **draft → gate** | tester/diagnosis | dynamic-eval BLOCKED; verdict=supports CL3 |

There are **no BLOCKER-verdict EVIDs anywhere in the chain**, current or historical (the only prior guardian BLOCKER-adjacent record is EVID-006 CONCERNS on PRD-001, long since superseded by EVID-008 PASS — unrelated to this sprint). Chain is clean of unresolved blockers.

## Gate criteria

| # | Criterion | Status | Notes |
|---|---|---|---|
| 1 | Artifact MUST validation | PASS | `forgeplan_validate` on all 3 → 0 errors, 0 warnings each |
| 2 | EVIDENCE chain wired | PASS | EVID-030 →informs ADR-007; EVID-031 →informs NOTE-008 (both edges confirmed in graph) |
| 3 | No BLOCKER in chain | PASS | zero unresolved BLOCKERs in current or historical EVIDs |
| 4 | Unresolved HIGH CONCERNS | 0 | EVID-030 H3-scoring nit is LOW (cosmetic, self-corrected in body); EVID-031 residuals all explicitly fenced |
| 5 | Activation policy | PASS | activating NOTE+EVID kinds; evidence artifacts ARE the audit trail; ADR-007 already active with its evidence linked |
| 6 | Project-specific gates | N/A | no `check:ready-to-ship` / `ci-check` / `gate:` target present (verified absent) |
| 7 | Blast radius within stated threshold | PASS | see Blast radius — local artifacts, fully reversible, deferred work explicitly fenced |

### Project-config gates (`.forgeplan/project-config.yaml` → `quality_gates`)

**Config source:** `.forgeplan/project-config.yaml` (found, parsed — schema_version 1)

| Criterion | Threshold | Observed | Result |
|---|---|---|---|
| Test coverage | ≥80% (`min_test_coverage`) | 28/28 unit tests PASS, but they MOCK the sandbox (EVID-031 §2 states this); dynamic path coverage is 0% (skipped). No coverage-% EVID in chain. | N/A — see note |
| Critical findings | 0 (`max_findings_critical`) | 0 | PASS |
| High findings | ≤3 (`max_findings_high`) | 0 | PASS |
| Medium findings | ≤10 (`max_findings_medium`) | ~3 documented residual uncertainties (all in EVID-030/031 bodies, fenced) | PASS |
| Validate pass | required (`require_validate_pass`) | all 3 PASS | PASS |
| Audit pass | required (`require_audit_pass`) — ≥1 Profile B EVID verdict=PASS | EVID-031 is Profile A self-diagnosis, not an independent Profile B tester audit. **EVID-032 (this gate) IS the Profile B audit record with verdict=PASS.** | PASS (satisfied by this EVID) |
| Evidence chain | required for prd/rfc/adr/spec (`require_evidence_chain`) | None of the 3 gated artifacts is prd/rfc/adr/spec — they are note + evidence. ADR-007 (active) already has EVID-030. | PASS (n/a to gated kinds) |

**Gates summary: 6/7 PASS, 1 N/A (coverage gate does not apply to a NOTE+EVID activation where the dynamic path is explicitly reported as un-run).**

Coverage-gate reasoning: `min_test_coverage=80` governs *code* shipping under a PRD/SPEC. This gate activates an A3 note and two evidence recordings. The 28/28 unit tests are real and green, but EVID-031 is scrupulously clear they mock the sandbox and do NOT prove the dynamic path — which is exactly why band-separation is reported as un-demonstrated. Applying an 80% dynamic-path-coverage floor here would be a category error; the artifacts make no coverage claim to gate against. The honest reporting of 0% dynamic coverage is the *point* of EVID-031, and it is faithfully recorded. Not a downgrade.

## Per-artifact findings

### EVID-031 — the critical honesty check — PASS (exemplary)

The orchestrator's load-bearing question: *does EVID-031 honestly represent the BLOCKED state, or dress up a failure as success?* **It is honest.** Verified against ground truth, not just the EVID text:

- Raw `artifacts/local/step3-eval-verify/fe_01/band_separation_results.json` (read in full): **all 5 bands — perfect/good/mediocre/poor/broken — scored 0.0 with `skipped: true`**, every one carrying the identical `MODULE_NOT_FOUND .../rollup/dist/native.js` Linux-portability error. `correctness_in_band: false` for perfect/good/mediocre/poor. The lone `correctness_in_band: true` (broken) is a **trivial false positive**: broken's expected range is `[0.0, 0.2]`, so a skipped-0.0 falls in-band by accident, proving nothing. Band SEPARATION (the gap between bands) was never observed.
- EVID-031 states this exactly: "live band-separation numbers could NOT be obtained"; "all bands scored 0.0/skipped"; the explicit fence "**do NOT promote fe_01/be_01/doc_01 to lifecycle_state=calibration on the basis of automatic-evaluator band separation (it has not been demonstrated end-to-end)**". No dressing-up.
- The "product pipeline is sound" claim is correctly scoped to what was actually observed: Docker image builds (verified — `pollmevals-eval-ts:0.1.0`, 215 MB, exists locally), 28/28 unit tests pass (3 test files verified present), `_TS_RUNNABLE_PREFIXES={fe_,ts_,fs_}` scope-correction verified in source, `npx --no vitest --reporter=json` command verified in `coverage_evaluator.py:132`. The EVID is explicit that "sound" rests on **code-reading + mocked unit tests**, NOT a live run — "These mock the sandbox, so they exercise evaluator logic but NOT the live Docker path." That is precisely the distinction the gate required.
- The blocker is correctly characterised as a task-pack portability invariant (macOS `node_modules` not Linux-portable), NOT a product bug — and tracked as follow-up (TaskList #6) with three candidate resolutions. This matches NOTE-008's Fishbone "circular dependency" measurement bone, so EVID-031's `verdict: supports` (it supports NOTE-008's premise that real infra debt was deferred) is sound, and CL3 is justified (same project, same pipeline, direct measurement, no analogy gap).

This is exactly what an "evidence layer" project should produce: an EVID that refuses to overstate verification. No finding.

### EVID-030 — ADR-007 backfill — PASS (1 LOW quality nit, non-blocking)

ADI rigor check (orchestrator's question): ≥3 hypotheses incl. "do nothing"? **Yes — four**: H1 hybrid (chosen), H2 all-public/licensed-only, H3 all-own-authored, H4 do-nothing. The Trust-Calculus F+G+R scoring is present per source, the deduction makes falsifiable predictions, the induction states convergence + a forward-looking falsifier + three residual uncertainties (Tier 2 untested, G4 sampling-vs-exhaustive, doc-task heuristic). The verdict `supports` honestly follows: H1 is backed by PR #22's 3 packs as **live CL3 proof** (EVID-027/028/029, all active), H2/H3/H4 refuted with cited evidence. CL3 is justified — repo-internal measurement of the same decision's operationalisation. Keeping ADR-007 at R_eff=1.00 on this basis is honest: the score reflects CL3 evidence for the Tier-1 path that PR #22 actually exercised, and EVID-030 explicitly isolates the **untested Tier 2 path** as residual uncertainty rather than claiming it proven.

- **LOW nit (non-blocking, do not require a fix to activate):** EVID-030's Deduction section contains a visible mid-stream self-correction — "Wait — these support REFUTATION of H2, not the hypothesis itself. Scoring needs to flip" — followed by a corrected table. The reasoning lands correctly (the flip is right; H2 evidence-against = 76/81, REFUTED), but the stray "Wait —" reads as un-cleaned scratch work in an artifact about to go active. Similarly, the H3 narrative carries two different sums (64/81 then "24/81 pure-own-authored") that are reconciled in prose but could confuse a future reader. **This is cosmetic, not a soundness defect** — the structured field `fgr_total_h3: 24/81` is internally consistent with the final reframe, and the verdict is unaffected. Optional polish for a future edit; it does not gate.

### NOTE-008 — A3 + Fishbone — PASS

Faithful "honest-partial" framing: the Background explicitly calls it "merge then patch / hot-fix discipline ... acceptable if cleaned up before Wave 1, unacceptable if Wave 1 starts first." Current-state enumerates the 4 NOW-block items + the ADR-007 R_eff=0 blind spot + 7 blocked upstream artifacts honestly. The Fishbone systemic-vs-local split is sound and the deferred work (lifecycle-promote, Docker-as-prereq) is named as future-RFC material, not claimed done.

- **Minor (non-blocking):** NOTE-008's Target-state lists outcomes as if all five would be achieved this sprint (e.g., "3 task packs verified at lifecycle_state=calibration", "band separation ... broken ≤0.20, perfect ≥0.85"). Two of those targets were NOT met (band separation BLOCKED per EVID-031; lifecycle-promote deferred). NOTE-008 is the *plan* artifact written at Step 1, so aspirational targets are appropriate — and EVID-031 (Step 3) now records the actual outcome that overrides them. The chain as a whole is honest because the later EVID corrects the earlier plan's optimism. The orchestrator should NOT let the PR narrative imply the packs are calibration-ready: that is covered by EVID-031's explicit fence. No fix required to the NOTE; flagged so the orchestrator writes an accurate PR body.

## Blast radius

- **Affected scope on activation:** local forgeplan artifact graph only (3 draft → active) + one `chore:` PR. **No production scope, no code activation, no deployment.** The Docker image and verify script already exist on the maintainer's laptop; activation does not run anything.
- **Reversibility:** fully reversible. Artifacts can be superseded/deprecated; the PR can be reverted. No one-way door. ADR-007 is *already* active independently of this gate.
- **Downstream artifacts:** ADR-007 stays at R_eff=1.00 (EVID-030 already linked). NOTE-008's follow-up promises a 1-week re-check. PRD-006 Wave 1 is the *next* sprint and is deliberately NOT touched here — the critical safety property is that nothing in this unit implies the 3 packs are "calibration-ready via automatic evaluators." Verified: EVID-031 explicitly forbids that promotion. So Wave 1 will not inherit a false "evaluators proven" premise.
- **Detection time if wrong:** immediate — any overclaim would surface at the next weekly judge run or the first Wave 1 dispatch. EVID-031's fence makes a wrong promotion self-evident.
- **Threshold check:** the actual blast radius (local artifacts, reversible) is **within** what the artifacts claim. No scope creep. The one risk the gate must police — that activation implies calibration-readiness — is explicitly closed by EVID-031. PASS.

## Orchestrator instructions

**PASS → activate all three via `forgeplan_activate`:**

1. `forgeplan_activate(id=NOTE-008)`
2. `forgeplan_activate(id=EVID-030)`
3. `forgeplan_activate(id=EVID-031)`

Then create the single `chore:` PR per the user's fewer-larger-PRs preference. No fixer dispatch is required to activate.

**PR-body accuracy requirement (load-bearing — the orchestrator MUST honor this so the wrap stays honest):**
- State the sprint as an **honest-partial wrap**: Docker image built + product pipeline structurally sound (mocked unit tests + code reading), ADR-007 evidence backfilled (R_eff 0.0→1.00).
- State plainly that **dynamic-eval band separation was NOT demonstrated** (blocked on task-pack `node_modules` Linux portability) and that **lifecycle-promote of the 3 packs is DEFERRED**, not done. Do NOT describe the packs as "calibration-ready via automatic evaluators."
- Reference the Linux-deps blocker as tracked follow-up (TaskList #6 / a dedicated infra item) — it is open, not closed.

**Optional polish (NOT required before activation — do not block on these):**
- EVID-030: a future edit could remove the stray "Wait — these support REFUTATION of H2 ..." scratch line and reconcile the two H3 sums (64/81 vs 24/81) inline. Cosmetic only; the verdict and structured fields are sound as-is. If the orchestrator prefers a spotless active artifact, dispatch `agents-pro:evidence-gatherer` for a 1-line cleanup — but this is elective.

**Re-gate is NOT required.** This PASS is final for activation.

## Notes

- **Hindsight memory unavailable this session** — both `memory_recall` and `mental_model_get(mm-gate-failures)` failed (recall aborted; the `mm-gate-failures` mental model does not exist in the `pollmevals` bank). NOTE-008 §Current-state independently documents "Hindsight MCP disconnected this session," so this is consistent, not anomalous. Per HARD RULE 6 I record it as a known limitation rather than a silent pass; it did not affect the verdict because the gate rests on direct artifact + filesystem inspection, which was fully performed. If Hindsight reconnects, NOTE-008's follow-up already plans to retain the relevant lessons.
- **`require_audit_pass` satisfied by this EVID.** The orchestrator's Step 5 plan named a separate "Tester EVID" that was not produced as a distinct artifact; EVID-031 is build/diagnosis evidence (Profile A). EVID-032 (this gate review, verdict=PASS) is the Profile B audit record that satisfies the project-config `require_audit_pass` gate. No additional tester dispatch is needed for this honest-partial wrap.
- **Why PASS and not CONCERNS:** the only findings are (a) one cosmetic scratch-line in EVID-030 and (b) NOTE-008's Step-1 aspirational targets that the Step-3 EVID already corrects. Neither is a HIGH-severity unmitigated concern; the chain self-corrects and the honesty bar — the entire purpose of gating an evidence-layer project — is met with margin. CONCERNS would imply a fixer must run before activation, which is not warranted here.

## References

- Artifacts under review: NOTE-008, EVID-030, EVID-031
- Parent decision validated: ADR-007 (active, R_eff=1.00, EVID-030 linked)
- EVIDENCE chain: EVID-027/028/029 (H1 measurement), EVID-001/003/005 (contamination prior art), EVID-031 (dynamic-eval diagnosis)
- Ground-truth file inspected: `artifacts/local/step3-eval-verify/fe_01/band_separation_results.json` (all bands 0.0/skipped — confirms no overclaiming)
- Source verified: `apps/eval-core-py/src/evaluators/correctness_evaluator.py:41`, `coverage_evaluator.py:132`; Docker image `pollmevals-eval-ts:0.1.0` (215 MB) present
- Project-config: `.forgeplan/project-config.yaml` quality_gates (found, applied)
- Mental models consulted: `mm-gate-failures` attempted — not present in bank; gate proceeded on direct inspection



