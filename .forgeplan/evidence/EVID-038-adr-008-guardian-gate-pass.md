---
depth: standard
id: EVID-038
kind: evidence
last_modified_at: 2026-05-29T16:03:41.616218+00:00
last_modified_by: claude-code/2.1.156
links:
- target: ADR-008
  relation: informs
status: active
title: ADR-008 guardian gate — PASS
---

# Guardian gate review of ADR-008 — pre-activation gate

## Verdict

**PASS**

- **PASS** — orchestrator may activate via `forgeplan_activate(id=ADR-008)`. **← this verdict.**
- **CONCERNS** — orchestrator dispatches a fixer, re-runs the reviewer, re-gates.
- **BLOCKER** — orchestrator halts; artifact stays draft until named blockers clear.

One-line justification: ADR-008 now has the decision evidence it lacked at the RFC-004 gate — **EVID-037 (Profile B, verdict PASS, CL3, score 1.0)** validates the H2 "Feed" decision on two independent grounds (ADI option-elimination re-confirmed by `forgeplan_reason` at HIGH confidence + Slice-1 empirical implementability via EVID-034/035); `forgeplan_validate ADR-008` passes with 0 errors; ADR-008 has no blockers in `forgeplan_blocked`; and the only residual item — the prose-format `## Revisit Trigger` — is a **non-blocking cosmetic metadata nit** that does not gate activation (decisive ruling below).

> **This PASS clears the RFC-004 chain too.** Activating ADR-008 removes the sole blocker on RFC-004 (`forgeplan_blocked`: `RFC-004 → blocked_by:[ADR-008]`). After ADR-008 is active, re-run guardian on RFC-004 — it should flip to PASS (its build already passed at EVID-036; only the draft-parent precondition was failing).

## Artifact under review

- ID: `ADR-008`
- Kind: `adr`
- Status: `draft`
- Title: Atomic binary requirements[] feed scoring components, not replace them
- Parents: `based_on ADR-007` (active), `refines RFC-003` (active), `informs SPEC-001` (active), `informs PRD-002`
- Decision: adopt FPF hypothesis **H2 "Feed"** for v0.2 (requirements[] pass-rate feeds deterministic scoring components; does not replace weight_components; judge pipeline untouched), designed forward-compatible toward H4.

## EVIDENCE chain inspected

| EVID | Verdict | Source agent | Critical findings (one-line) |
|---|---|---|---|
| `EVID-037` | **PASS** | `evidence-recorder` (Profile B fallback) | Decision-soundness validation on two independent grounds: **(1) ADI option-elimination** — H1 REFUTED (destroys calibration edge), H3 WEAKENED (leaves correctness opaque), H4 DEFERRED (risks α/MAD machinery), H2 CHOSEN (lowest blast radius, all C1–C7 satisfied); re-confirmed by `forgeplan_reason ADR-008` at HIGH confidence. **(2) Slice-1 empirical** — EVID-034 (code PASS) + EVID-035 (test PASS) confirm ADR-008's central claim (additive, no scoring-contract break) held in the first implementation (additivity 3/3, weight_components/judge/rubric.yaml untouched, Σ=1.0). Substantive `## Structured findings` with per-invariant verification table — not a thin zero-findings stamp. CL3, verdict=supports. |

Chain is sound: EVID-037 is the **right class of evidence for an ADR gate** — decision-soundness (ADI reasoning + implementability corroboration), not code/test/security (those correctly live on RFC-004, and EVID-037 cites them as corroboration without re-linking them — link direction EVID-034/035 → RFC-004 is preserved). No BLOCKER anywhere in the chain. No superseding EVID needed.

**Note on the earlier "thin review" modifier:** my gate rules downgrade a PASS EVID with zero `## Findings` to CONCERNS. EVID-037 does **not** trip this — it carries a two-ground structured-findings section, an option-elimination table, and an invariant-by-invariant (C1–C7) verification. The adversarial substance is present.

## Gate criteria

| # | Criterion | Status | Notes |
|---|---|---|---|
| 1 | Artifact body MUST validation | ✅ | `forgeplan_validate ADR-008` → passed=true, **0 errors, 0 warnings**. Context/Decision/Consequences all present and rich. Two `COULD` findings (Preconditions/Postconditions) — lowest severity, non-blocking (not even SHOULD). |
| 2 | All required EVIDENCE linked | ✅ | `require_evidence_chain` lists `adr`; EVID-037 `informs` ADR-008 → ≥1 EVID present. The missing-decision-evidence gap from the RFC-004 gate is now closed. |
| 3 | No BLOCKER in chain | ✅ | EVID-037 PASS; zero unresolved BLOCKERs |
| 4 | Unresolved CONCERNS count | 0 | No HIGH-severity concern in the chain. The Revisit-Trigger format is a non-blocking note (criterion #6 + Revisit-Trigger-check section), not a CONCERN that gates. |
| 5 | Activation policy satisfied | ✅ | ADR-008 is **NOT** in `forgeplan_blocked` (no cycles). Its parents (ADR-007 active, RFC-003 active, SPEC-001 active) are activated. Unlike RFC-004, ADR-008 has no draft-parent precondition. R_eff = 0.20 > 0 (red-line "never activate without evidence" satisfied). |
| 6 | Project-specific gates | ✅ | No `package.json check:ready-to-ship` / `Makefile gate:`/`ci-check:` target present → N/A. ADR is a decision artifact (no code), so no ruff/mypy/test surface of its own — the implementability is evidenced via RFC-004's EVID-034/035. |
| 7 | Blast radius within stated threshold | ✅ | Activating the *decision* commits the design direction, not code. See Blast radius. Matches the ADR's stated v0.2 scope (additive, lowest-blast-radius H2). |

### Project-config gates (`.forgeplan/project-config.yaml` → `quality_gates`)

**Config source:** `/Users/explosovebit/Work/pollmevals/.forgeplan/project-config.yaml` — found, thresholds applied.

| Criterion | Threshold | Observed | Result |
|---|---|---|---|
| Test coverage | ≥80% (`min_test_coverage`) | n/a for a decision artifact — no code in an ADR; implementability evidenced via RFC-004 Slice-1 (48+13 tests green, additivity 3/3) | ✅ N/A |
| Critical findings | 0 (`max_findings_critical`) | 0 in EVID-037 | ✅ |
| High findings | ≤3 (`max_findings_high`) | 0 in EVID-037 | ✅ |
| Medium findings | ≤10 (`max_findings_medium`) | 0 in EVID-037 | ✅ |
| Validate pass | required (`require_validate_pass`) | PASS (0 errors; 2 COULD non-blocking) | ✅ |
| Audit pass | required (`require_audit_pass`) — ≥1 Profile B EVID with PASS | EVID-037 PASS, Profile B | ✅ |
| Evidence chain | required for `adr` (`require_evidence_chain` includes adr) | 1 `informs`-linked EVID (EVID-037) | ✅ |

**Gates summary:** **7/7** — all green. (Coverage is N/A for a code-less decision artifact, recorded as satisfied-by-RFC-004-implementation, not skipped.)

### R_eff observation (informational — not a guardian gate threshold)

`forgeplan_score ADR-008` = **0.20** (grade C), EVID-037 scores 1.0 @ CL3. Two things matter here:

1. **The "Skipped ADR-008 (status: draft)" factor that tanked RFC-004's score is absent here** — that factor only penalises *children* of a draft ADR; it does not apply to the ADR itself. ✅
2. The residual 0.20 comes from **normal CL penalties** on the non-evidence edges (`based_on ADR-007`, `informs SPEC-001`, `informs PRD-002`) + `granularity: 0.4` (a single evidence source). This is the expected floor for a freshly-evidenced decision backed by one strong CL3 PASS audit EVID. project-config declares **no `min_r_eff` gate**, so R_eff is a trust signal, not a pass/fail threshold. R_eff > 0 satisfies the "never activate without evidence" red-line. A second corroborating EVID (e.g. the post-migration calibration EVID the ADR's own Revisit Trigger anticipates) would raise it later — that is a strengthening follow-up, not an activation precondition.

## Revisit Trigger check (Sprint Z2 — PRD-053) — THE DECISIVE QUESTION

**Inspected the actual on-disk `## Revisit Trigger (Evidence Decay)` section (ADR-008 lines 180–189), not the earlier prediction.**

Findings:
- **Format: pre-Sprint-Z2 PROSE bullets**, not the Z2 checkbox syntax. The parser regex `^- \[([ x])\] \*\*Type\*\*:\s*(date|metric|event)\s*[—\-]\s*(.+)$` matches **zero** lines → `/decay-watch` cannot machine-parse it → **LEGACY-FORMAT** (exactly as predicted at the RFC-004 gate, EVID-036).
- **No FIRED triggers** — no `[x]` checkbox exists (no checkboxes at all).
- **No DATE-FIRED triggers** — all four triggers are explicitly **event-triggered, not date-triggered**: *"No fixed `valid_until` date — the decision is event-triggered, not time-triggered, because it is gated on the first real calibration data (TBD)."* There is no ISO date anywhere for the date-firing auto-detector to act on.
- The four triggers are **complete and correct in content**: (1) calibration break post-v0.2 bumps, (2) judge-recorded-unwired backlog → schedule H4, (3) App-Bench publishes calibration parity, (4) implementing RFC resolves the security-component question changing the weight contract.

**Classification & ruling — the orchestrator asked me to pick (a)/(b)/(c) decisively:**

### → (c) NON-BLOCKING NOTE. The orchestrator MAY activate ADR-008 now and fix the format as a follow-up.

This is **not** BLOCKER and **not** CONCERNS-then-regate, for three substantive reasons:

1. **The decay rule itself says so.** My own Step 4b classification is explicit: *"No parseable triggers (pre-Sprint-Z2 prose-only format) → LEGACY-FORMAT, record as CONCERNS line in EVID body, **not BLOCKER**."* The CONCERNS-line guidance in the HARD-RULE table is written for the case where guardian gates a **downstream artifact** and finds a *dependency* ADR it cannot decay-check. Here I am gating the ADR **itself**, and the content of its triggers is fully present and correct — so the decay foundation is sound; only its machine-readability is dated.

2. **The format fix yields ~zero functional decay-automation gain for THIS ADR.** `/decay-watch`'s only automatic capability is **date-firing** (flagging a `type=date` trigger whose ISO date is past). ADR-008 has **no date triggers** — all four are `metric`/`event` type, which even in perfect Z2 format are classified PENDING ("cannot auto-verify, treat as unresolved"), i.e. they *always* require manual review regardless of format. Converting prose → checkboxes therefore buys essentially no automated coverage here. Forcing a re-gate cycle for it would be ceremony with no safety payoff — the precise "bureaucracy over substance" anti-pattern the methodology warns against.

3. **It is genuinely cosmetic for the activation decision.** The decision is sound (ADI + empirical, EVID-037 PASS), reversible (full Rollback Plan present), and the re-open conditions are documented and human-actionable today. Nothing about activating now creates a risk that the prose format would have caught. A reviewer reading ADR-008 can act on every trigger as written.

**Recommended follow-up (NOT a gate; track as a chore):** convert the `## Revisit Trigger (Evidence Decay)` section to Sprint-Z2 checkbox syntax so `/decay-watch` can parse it on future scans. Exact remediation is in the Orchestrator-instructions block below. This is a forward-hygiene improvement, not an activation precondition.

## Blast radius

- **Affected scope on activation (of the ADR-008 *decision*):** commits the v0.2 design **direction** (H2 "Feed" — requirements[] feeds deterministic components; weight_components + judge pipeline + rubric.yaml stay untouched; Σ=1.0; pack migration = new task version). It does **not** ship code or change any live Run — the code that implements it (RFC-004 Slice 1) is additive, dev-only, and gated separately (and currently still draft, correctly blocked on this ADR).
- **Reversibility:** the ADR is reversible via the methodology's `supersede` path (history-preserving), and the decision itself is low-blast by construction — the chosen H2 is the *lowest-blast-radius* option (vs rejected H1/deferred H4). The ADR carries a full Rollback Plan (5 failure modes mapped) and event-triggered revisit conditions. Activating a decision is a "soft" one-way door: superseding is always available, and no published Run is touched (ADR-002 immutability intact).
- **Downstream artifacts:** `RFC-004` (the engineering design — unblocks the moment ADR-008 is active); `SPEC-001` (informs — amendment is its own task); `RFC-003` (refined — authoring protocol gains the requirements[] step). H4 remains explicitly deferred to a future RFC+ADR.
- **Detection time if wrong:** the decision's own primary risk (score-distribution shift breaking α≥0.70/MAD≤1.5) is **detected at the first post-migration calibration session** — which is exactly the event Revisit-Trigger #1 names, and the moment the ADR anticipates a follow-up empirical EVID. So a wrong implementability assumption surfaces at the next calibration gate, not silently in production.
- **Threshold check:** actual blast radius (decision-direction commit, no live-run impact, reversible via supersede) **matches** the ADR's stated lowest-blast-radius v0.2 scope. No scope creep. Blast radius does not push the verdict off PASS.

## Why PASS (and not CONCERNS)

CONCERNS would mean "dispatch a fixer and re-run a reviewer before activating." There is **nothing that gates activation to fix**: MUST validation passes (2 COULD findings are below even SHOULD), the decision evidence is present and strong (EVID-037 PASS/CL3), all 7 project-config gates are green, the ADR is unblocked, and R_eff > 0. The single open item — the legacy-prose Revisit-Trigger format — is ruled a non-blocking follow-up on substance (see decisive ruling above), because it adds ~zero decay-automation value for an all-event-triggered ADR and the trigger *content* is complete. Holding activation for a cosmetic format conversion would be ceremony without safety payoff.

## Orchestrator instructions

**PASS → orchestrator MAY activate ADR-008 via `forgeplan_activate(id=ADR-008)`.** No fixer dispatch is required before activation; no reviewer re-run is required. Proceed.

After activation, the recommended sequence:

1. **Activate ADR-008** (`forgeplan_activate(id=ADR-008)`). Note: project-config lists `forgeplan_activate` under `human_required` — this is the gate that authorises it; the human/orchestrator makes the final call, guardian has cleared it.
2. **Re-check `forgeplan_blocked`** — `RFC-004` should drop out of the blocked set (ADR-008 was its only blocker). Then **re-run guardian on RFC-004**; with the parent now active, RFC-004 criterion #5 flips green and (its build already passed per EVID-036) the verdict becomes **PASS → `forgeplan_activate(id=RFC-004)`**.

**Optional follow-up (NOT gating ADR-008 activation — dispatch `adr-architect` at your convenience):** convert ADR-008's `## Revisit Trigger (Evidence Decay)` section to Sprint-Z2 checkbox syntax via `forgeplan_update(id=ADR-008, body=…)` so `/decay-watch` can parse it. **Exact shape** — replace the four prose bullets (lines 184–187) with one checkbox line each, keeping the existing wording as the trigger text, e.g.:

```markdown
## Revisit Trigger (Evidence Decay)

Re-open this decision if any of the following hold:

- [ ] **Type**: event — first calibration session after v0.2 task-version bumps shows the auto pass-rate derivation breaks PRD-002 α ≥ 0.70 / MAD ≤ 1.5 (change not score-contract-neutral in practice)
- [ ] **Type**: metric — count of `check_type: judge` "recorded but unwired" requirements grows large enough that partial auditability becomes the dominant complaint → schedule H4
- [ ] **Type**: event — App-Bench (or equivalent) publishes a calibration/inter-rater story that erodes our differentiator
- [ ] **Type**: event — the implementing RFC resolves the `security`-component open question in a way that changes the `weight_components` contract

No fixed `valid_until` date — event-triggered, not time-triggered (gated on the first real calibration data, TBD).
```

Keep `check_type`/`maps_to` etc. untouched; this is a pure metadata-section reshape (Context/Decision/Consequences are unaffected, so `forgeplan_validate ADR-008` will still pass). Since all four triggers are event/metric (not date), `/decay-watch` will classify them PENDING — the conversion's value is parseability/hygiene, not new auto-firing.

## Notes

- **State delta vs the RFC-004 gate (EVID-036):** at that gate ADR-008 was draft, R_eff 0.0, **zero** linked evidence — which is why RFC-004 was BLOCKED on it. Remediation step 1 (this orchestrator's action) added EVID-037 (Profile B decision evidence, PASS/CL3). ADR-008 R_eff 0.0 → 0.20, the "Skipped ADR-008 (draft)" penalty on children will clear once ADR-008 is active, and the missing-decision-evidence gap is closed. The remediation did exactly what EVID-036 prescribed.
- **Revisit-Trigger prediction confirmed:** at the RFC-004 gate I predicted ADR-008's Revisit Trigger was pre-Z2 prose (LEGACY-FORMAT). On reading the actual section this turn, that is confirmed — and I am ruling it a non-blocking follow-up (option c), not a gate, on the substance reasoning above.
- **Memory/mental-model availability:** as at the RFC-004 gate, `mm-gate-failures` is not present in the `pollmevals` Hindsight bank and `memory_recall` was unavailable last turn. The verdict rests on the deterministic artifact graph, the EVIDENCE chain, project-config thresholds (7/7 green), `forgeplan_validate`, `forgeplan_blocked`, and `forgeplan_score`. No prior-regret signal was foldable; recorded honestly per HARD RULE 6.
- The two `COULD` validator findings (missing `## Preconditions` / `## Postconditions`) are optional ADR sections — not required for activation. They could be added in the same follow-up `forgeplan_update` as the Revisit-Trigger reshape if desired, but they do not gate.

## References

- Artifact under review: `ADR-008` (draft → cleared for active)
- EVIDENCE chain inspected: `EVID-037` (decision validation, PASS, CL3, Profile B)
- Corroborating (linked to RFC-004, cited by EVID-037, not re-linked here): `EVID-034` (code review PASS), `EVID-035` (test PASS)
- Downstream unblocked by this PASS: `RFC-004` (`forgeplan_blocked`: blocked_by ADR-008) — re-gate after ADR-008 active
- Prior guardian gate in this chain: `EVID-036` (RFC-004 Slice 1 — BLOCKER, blocked on draft ADR-008; this gate resolves that blocker's root)
- Forgeplan signals: `forgeplan_validate ADR-008` (0 errors, 2 COULD); `forgeplan_blocked` (ADR-008 not blocked, no cycles); `forgeplan_score ADR-008` (R_eff 0.20, EVID-037 @ 1.0 CL3, no "skipped-draft" factor)
- Project-config: `.forgeplan/project-config.yaml` `quality_gates` — 7/7 green
- Revisit Trigger inspected: ADR-008 lines 180–189 (on-disk projection, sha256 a4636a22… per EVID-037 fingerprint)
- Mental models consulted: `mm-gate-failures` — unavailable (not in bank)

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: audit



