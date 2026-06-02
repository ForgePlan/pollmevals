---
depth: standard
id: EVID-036
kind: evidence
last_modified_at: 2026-05-29T14:21:48.984612+00:00
last_modified_by: claude-code/2.1.156
status: deprecated
title: RFC-004 Slice 1 guardian gate — BLOCKER
---

# Guardian gate review of RFC-004 (Slice 1) — pre-activation gate

## Verdict

**BLOCKER**

- **PASS** — orchestrator may activate via `forgeplan_activate(id=RFC-004)`.
- **CONCERNS** — orchestrator dispatches a fixer, re-runs the reviewer, re-gates.
- **BLOCKER** — orchestrator must halt; RFC-004 stays in draft until the named blocker clears. **← this verdict.**

One-line justification: The Slice-1 *code* is clean and fully proven (both Profile B EVIDs PASS at CL3/score 1.0, HIGH findings resolved + independently re-verified), **but RFC-004 cannot be activated as an artifact while its parent decision ADR-008 is still `draft`** — `forgeplan_blocked` lists `RFC-004 → blocked_by:[ADR-008]`, `forgeplan_score`=0.20 with factor "Skipped ADR-008 (status: draft)", and the activation-policy rule forbids activating an RFC ahead of the still-draft ADR it is `based_on`. This is a **sequencing blocker**, not a code-quality blocker; remediation is narrow and cheap (gate + activate ADR-008 first).

> **Read this carefully, orchestrator:** the *Slice-1 build* passed every quality check. The BLOCKER is purely the **graph state** — activating the engineering design ahead of the unactivated, evidence-less decision it implements is activated drift. The fix is to activate ADR-008 first, then RFC-004 unblocks automatically.

## Artifact under review

- ID: `RFC-004`
- Kind: `rfc`
- Status: `draft`
- Title: Atomic binary requirements[] — task schema, evaluator contract, and migration of be_01/fe_01/doc_01
- Parent (decision): `ADR-008` (relation `based_on`) — **status: draft, R_eff 0.0, zero linked EVIDENCE**
- Also: `refines RFC-003` (active, R_eff 1.0), `informs SPEC-001` (active)
- Scope of this gate: **Slice 1 (contracts + validator foundation) only.** Slice 2 (task-pack migration to v1.1) is explicitly DEFERRED to a separate PR and is **not** part of this gate. The `security` weight-component is a deferred PROPOSAL inside the RFC body (not implemented, by design).

## EVIDENCE chain inspected

| EVID | Verdict | Source agent | Critical findings (one-line) |
|---|---|---|---|
| `EVID-034` | **PASS** (updated) | `code-reviewer` (Profile B) | Initially CONCERNS w/ 2 HIGH (#1 MUST-4 silent-pass defect, #2 missing validator rejection-path tests); both fixed in `8b424e1` + re-verified (13/13 new validator tests, ruff/mypy clean). Adversarially cleared 3 suspected bugs (float Σ tolerance, ReDoS, yaml.safe_load). #7/#8/#9/#10 DEFERRED non-blocking. Substantive `## Findings` present. CL3, verdict=supports. |
| `EVID-035` | **PASS** | `tester` (Profile B) | 608/609 pass, 1 skipped (pre-existing AC-6 deferral), 0 failed; 48/48 Slice-1 tests; additivity 3/3 (be_01/fe_01/doc_01 still validate unchanged); TS contracts typecheck clean. Flagged validator-test-gap as **non-blocking CONCERN** → **resolved by the same `8b424e1`** that EVID-034 verifies. CL3, verdict=supports. |

Chronology: EVID-035 ran on `afb0f4c` (pre-fix) and flagged the validator unit-test gap → `8b424e1` added the 13 validator tests → EVID-034 was updated post-`8b424e1` and confirms they exist and pass. **Chain is self-consistent: the tester's sole concern is closed by the commit the code-reviewer re-verified.** No unresolved BLOCKER anywhere in the chain. No superseding EVID needed.

## Gate criteria

| # | Criterion | Status | Notes |
|---|---|---|---|
| 1 | Artifact body MUST validation | ✅ | `forgeplan_validate RFC-004` → passed=true, 0 errors, 0 warnings |
| 2 | All required EVIDENCE linked | ✅ | 2 EVIDs `informs` RFC-004; code-review + tester both present (the kinds an RFC-with-code needs) |
| 3 | No BLOCKER in chain | ✅ | Both linked EVIDs PASS; zero unresolved BLOCKERs in the evidence chain |
| 4 | Unresolved CONCERNS count | 0 | EVID-035's HIGH-equivalent validator-gap CONCERN is **resolved** by `8b424e1` (verified in EVID-034 + my independent re-run) |
| 5 | Activation policy satisfied | ❌ | **RFC `based_on` a still-draft ADR.** `forgeplan_blocked`: `RFC-004 → blocked_by:[ADR-008]`. ADR-008 is draft, R_eff 0.0, zero linked evidence. An RFC must not activate ahead of the decision it implements. |
| 6 | Project-specific gates | ✅ | `forgeplan validate` 3/3 task specs valid (additivity); mypy clean on Slice-1 modules; ruff = only the 2 documented DEFERRED style nits (see below). No `package.json check:ready-to-ship` / `Makefile gate:` target present → recorded N/A. |
| 7 | Blast radius within stated threshold | ✅ | Slice-1 schema/validator is additive + unused by any live run (see Blast radius). Matches the RFC's stated scope. |

### Project-config gates (`.forgeplan/project-config.yaml` → `quality_gates`)

**Config source:** `/Users/explosovebit/Work/pollmevals/.forgeplan/project-config.yaml` — **found**, thresholds applied.

| Criterion | Threshold (from project-config.yaml) | Observed | Result |
|---|---|---|---|
| Test coverage | ≥80% (`min_test_coverage`) | **n/a — instrumentation absent** (pytest-cov not in venv per EVID-035); 48/48 Slice-1 tests + 13 validator tests pass; additivity 3/3 | ⚠️ recorded — see note |
| Critical findings | 0 (`max_findings_critical`) | 0 (no Critical in either EVID; both adversarially cleared) | ✅ |
| High findings | ≤3 (`max_findings_high`) | 0 unresolved (2 HIGH found → both resolved in `8b424e1`) | ✅ |
| Medium findings | ≤10 (`max_findings_medium`) | 0 unresolved (#3 MEDIUM resolved; #9 INFO/pre-existing deferred) | ✅ |
| Validate pass | required (`require_validate_pass`) | PASS (0 errors) | ✅ |
| Audit pass | required (`require_audit_pass`) — ≥1 Profile B EVID with PASS | EVID-034 **and** EVID-035 both PASS, Profile B | ✅ |
| Evidence chain | required for `rfc` (`require_evidence_chain` includes rfc) | 2 `informs`-linked EVIDs on RFC-004 | ✅ for RFC-004 |

**Coverage-gate note:** `min_test_coverage: 80` cannot be measured numerically because pytest-cov is absent (EVID-035 flagged this as a non-blocking CONCERN; coverage instrumentation, not coverage itself, is missing). This is **not** treated as a coverage failure: the Slice-1 surface (`component_score` pure-function math, Pydantic contracts, JSON-schema round-trip, 5 validator MUST rules) is exhaustively unit-tested (48 + 13 dedicated tests, all green; all five MUST rejection paths pinned). It is recorded as a residual tooling gap to fix before Slice 2, per HARD RULE 6 (honest negative coverage), not as a silent pass and not as the cause of the BLOCKER.

**Gates summary:** **6/7** (the failing gate is criterion #5 *Activation policy* — parent ADR-008 is draft; this is the BLOCKER). All seven `quality_gates` rows above are green for the Slice-1 *build*; the gate that fails is the artifact-graph activation-policy gate.

### Independent re-verification (this gate, not re-doing upstream reviewers)

Ran on the `8b424e1` working tree to confirm the chain's claims (guardian reads EVIDs; this is a spot-check, not a re-review):

| Check | Result | Maps to |
|---|---|---|
| `validate-task-specs.py` | 3/3 valid — additivity holds | confirms EVID-035 additivity + EVID-034 |
| `mypy` (requirements.py, contracts/task.py) | Success, 0 issues | confirms EVID-034 "mypy clean" |
| `ruff check` (eval-core-py + validator) | 3 errors, all DEFERRED: `RUF002`/`RUF003` ambiguous `×` (= EVID-034 finding **#8**) at `contracts/task.py:24`, `scoring/requirements.py:87`; `I001` import-sort (= finding **#7**) at `test_component_score.py:14` | **exactly matches** EVID-034's deferred disposition — zero new findings |

The only open ruff items are the two intentionally-deferred style nits the code-reviewer already documented as non-blocking. No functional discrepancy. (The orchestrator's stated "ruff clean" almost certainly scoped the changed-file set; the 3 residual errors live in the deferred-list files — fully consistent.)

## Revisit Trigger check (Sprint Z2 — PRD-053)

Linked active ADR this artifact depends on: **none active.** RFC-004 is `based_on ADR-008`, but ADR-008 is itself **draft** (not active) — so there is no *active* decision foundation whose Revisit Triggers could have decayed. The decay check therefore does not produce an independent BLOCKER; the draft-parent problem is captured under criterion #5 instead.

For completeness, ADR-008's `## Revisit Trigger (Evidence Decay)` section was inspected:
- Format: **pre-Sprint-Z2 prose** (bulleted prose, no `- [ ] **Type**: date|metric|event — …` checkbox syntax). `/decay-watch` cannot machine-parse it → **LEGACY-FORMAT**.
- All triggers are **event-triggered, explicitly not date-triggered** ("No fixed `valid_until` date — event-triggered, gated on the first real calibration data (TBD)"). None are `[x]`-marked.
- Classification: no FIRED, no DATE-FIRED triggers → **no decay BLOCKER**. The legacy prose format is a `CONCERNS`-grade observation **to be carried into ADR-008's own activation gate** (manual trigger review required there), not a finding against RFC-004.

F+G+R aggregate (Sprint Z4): ADR-008 has **zero linked Profile B evidence** (no EVID `informs` ADR-008 in the graph), so there is no per-source F+G+R to score. This is precisely why ADR-008 is not activation-ready and why RFC-004 is blocked on it.

## Blast radius

- **Affected scope on activation (of RFC-004 Slice-1 code):** dev/contracts only. The `requirements[]` schema field, `TaskRequirement`/`RequirementResult` types (TS + Pydantic), the `component_score` math, and the validator rules are **additive + optional**. No live Run consumes them yet (Slice-2 pack migration is deferred; no `task.yaml` carries `requirements[]` in production). No task score changes. No judge-pipeline, `rubric.yaml`, `weight_components`, or `08-scoring-contract.md` change (ADR-008 invariants C1–C7 held).
- **Reversibility:** fully reversible. The contract delta is additive — old `task.yaml`/`evaluator_json` validate without the new fields (proven: additivity 3/3). Rolling back = revert the additive-only commit; no data migration, no published-Run impact (ADR-002 immutability untouched).
- **Downstream artifacts:** `SPEC-001` (informs — amendment is its own task, not in Slice 1); Slice-2 pack migration + the `security`-component proposal both build *on top of* this contract but are out of scope here. ADR-008 is the **upstream** dependency, not downstream — and it is the blocker.
- **Detection time if wrong:** immediate at CI (`validate-task-specs.py` + contract round-trip tests run on every PR); a contract regression would fail the additivity test before any run.
- **Threshold check:** actual blast radius (additive, dev-only, unused-by-live-runs) **matches** the RFC's stated Slice-1 scope. No scope creep. Blast radius does **not** drive the verdict — the BLOCKER is the draft-parent sequencing, not blast radius. If ADR-008 were active, this would be a clean PASS on blast-radius grounds.

## Why BLOCKER and not CONCERNS

CONCERNS = "dispatch a fixer, re-run a reviewer." There is **nothing for a code/test/security fixer to fix** — the build is clean. The blocker is a **graph-state precondition**: an RFC may not be `active` while the ADR it is `based_on` is `draft`. Three independent forgeplan signals make this a hard gate, not a soft note:
1. `forgeplan_blocked` → `RFC-004` is in the blocked set, `blocked_by:[ADR-008]` (no cycles).
2. `forgeplan_score RFC-004` = **0.20** (grade B, "weak"), explicit factor **"Skipped ADR-008 (status: draft)"** + CL penalty on the SPEC-001 `informs` edge; `weakest_link: SPEC-001`.
3. Activation-policy rule: activating the engineering design ahead of the unactivated, **evidence-less** decision (ADR-008 has 0 linked EVIDENCE, R_eff 0.0) is exactly the activated-drift failure this gate exists to stop.

`require_evidence_chain` in project-config lists `adr`; ADR-008 has no linked evidence and is not activated. Letting RFC-004 go active on top of it would leave an active design rooted in an unvalidated, unactivated decision. That is a halt, not a note.

## Orchestrator instructions

**BLOCKER → halt the activation pipeline; do NOT call `forgeplan_activate(id=RFC-004)` yet.**

The Slice-1 build is approved and requires **no further code/test/security fixer dispatch** — do not re-run code-reviewer or tester; their PASS verdicts stand and were independently spot-checked. The single required action is **sequencing**:

1. **Gate + activate the parent decision `ADR-008` first.** ADR-008 is draft with **zero linked evidence** (R_eff 0.0) and a pre-Z2 prose Revisit-Trigger section. Before it can activate it needs: (a) `require_evidence_chain` lists `adr` → at least one Profile B EVIDENCE linked to ADR-008 with verdict=PASS (the FPF/ADI decision record exists in the ADR body, but no EVID artifact `informs` ADR-008 in the graph); (b) its own guardian gate (a separate guardian run on ADR-008), which should also flag the legacy Revisit-Trigger prose format (LEGACY-FORMAT CONCERNS — recommend refilling to Sprint-Z2 checkbox syntax via `/supersede` or a body update so `/decay-watch` can parse it). **EVID-034 and EVID-035 are RFC-004 code evidence — they do NOT substitute for ADR-008 decision evidence.**
2. **After ADR-008 is `active`, re-check `forgeplan_blocked`** — `RFC-004` should drop out of the blocked set (its only blocker is ADR-008). Then **re-run guardian on RFC-004**; with the parent active, criterion #5 flips green and (build already PASS) the verdict becomes **PASS → `forgeplan_activate(id=RFC-004)`**.
3. **Before Slice 2 / next phase (non-gating for this activation, track as follow-up):** add `pytest-cov` to the eval-core-py dev deps so `min_test_coverage: 80` is measurable (EVID-035 non-blocking CONCERN); optionally sweep the 2 deferred ruff style nits (`RUF002`/`RUF003` `×` → `x`; `I001` import-sort in `test_component_score.py`) in a chore commit (EVID-034 #7/#8).

Do **not** activate RFC-004 before ADR-008 is active and a fresh guardian pass on RFC-004 returns PASS.

## Notes

- `mm-gate-failures` mental model: **not present** in the `pollmevals` Hindsight bank (HTTP 404); `memory_recall` for prior gate regrets **aborted** (transport error). Per HARD RULE 6, recorded as a methodology limitation rather than a silent pass — the verdict was derived from the artifact graph, the EVIDENCE chain, project-config thresholds, and independent re-verification, all of which are deterministic and sufficient. No prior-regret signal was available to fold in.
- The orchestrator's framing of the gate (checks 1–4) is correct and is upheld: (1) the chain supports the *code*; (2) ADR-008 invariants C1–C7 are respected by Slice 1 — additive schema (old packs valid, proven 3/3), `weight_components`/judge pipeline/`rubric.yaml` untouched, no pack migration, Σ=1.0 preserved, `security` is a marked proposal only; (3) the deferred items (#7–#10, judge-recorded-not-wired, Slice-2 migration, security proposal) are genuinely non-blocking for the *foundation*; (4) score-neutrality calibration (α≥0.70 / MAD≤1.5) is correctly a Slice-2 gate — no live run consumes the additive schema yet, so it is **not** required for Slice-1 code. The BLOCKER is orthogonal to all four: it is the artifact-graph rule that RFC-004 cannot be `active` while ADR-008 is `draft`.
- If the project's intent is to activate the **design + Slice-1 foundation together as a unit**, the correct sequence is ADR-008 → RFC-004, not RFC-004 alone. This gate enforces that order.

## References

- Artifact under review: `RFC-004`
- EVIDENCE chain inspected: `EVID-034` (code review, PASS), `EVID-035` (tester, PASS)
- Parent decision (blocker): `ADR-008` (draft, R_eff 0.0, 0 linked EVIDENCE)
- Active context: `RFC-003` (refined-by RFC-004, active R_eff 1.0), `SPEC-001` (informed-by RFC-004, active)
- Forgeplan signals: `forgeplan_blocked` (RFC-004 blocked_by ADR-008, no cycles); `forgeplan_score RFC-004` (R_eff 0.20, factor "Skipped ADR-008 (status: draft)"); `forgeplan_validate RFC-004` (0 errors)
- Project-config: `.forgeplan/project-config.yaml` `quality_gates` (min_test_coverage 80, max_findings_critical 0/high 3/medium 10, require_evidence_chain [prd,rfc,adr,spec], require_validate_pass true, require_audit_pass true)
- Independent re-verification: `validate-task-specs.py` 3/3; `mypy` clean on Slice-1 modules; `ruff` = only deferred `RUF002`/`RUF003`/`I001` nits
- Mental models consulted: `mm-gate-failures` — **unavailable (404)**; `memory_recall` — **aborted**
- Code under gate: branch `feat/rfc-004-requirements-schema`, commits `58635d3` (shape) / `afb0f4c` (Slice 1) / `8b424e1` (review fixes); HEAD `8b424e1`

## Structured Fields

verdict: weakens
congruence_level: 3
evidence_type: audit






