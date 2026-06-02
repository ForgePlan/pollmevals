---
depth: standard
id: EVID-046
kind: evidence
last_modified_at: 2026-05-30T11:20:34.054130+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-004
  relation: informs
status: active
title: RFC-004 Slice 2 guardian pre-merge gate — PASS
---

## Verdict

**PASS**

- **PASS** — orchestrator may open/merge the Slice 2 PR (branch `feat/rfc-004-slice-2-pack-migration`, commit `17e4301`) to `main`. No fixer dispatch required.
- This is a **pre-merge gate** on additional implementation under the already-active RFC-004 (Slice 1 merged as PR #25). There is **no `forgeplan_activate`** to call here — RFC-004 is already active; this gate authorises the PR merge only.

One-line justification: both Profile B reviewers (EVID-044 tester, EVID-045 code-reviewer) return PASS on commit `17e4301`; the two evaluator-wiring-blocking findings (be_01 C4 1:1 violation, fe_01 duplicate R10) are RESOLVED **and independently re-verified by guardian in the committed code**, not merely asserted; all ADR-008/RFC-004 invariants hold under independent inspection (Σ weight_components=1.0, no `security` key, version 1.0→1.1, scoring/rubric/judge/gold-logic untouched); the deferred score-neutrality calibration is correctly a live-run gate, not a merge gate.

## Artifact under review

- ID: `RFC-004` (already **active** — gate is on Slice 2 PR merge, not on activation)
- Kind: `rfc`
- Status: `active` (Slice 1 merged PR #25)
- Title: Atomic binary requirements[] — task schema, evaluator contract, and migration of be_01/fe_01/doc_01
- Slice 2 scope: migrate 3 task packs (be_01 / fe_01 / doc_01) onto atomic `requirements[]`
- Code under gate: branch `feat/rfc-004-slice-2-pack-migration`, commit `17e4301`, parent main `5e07840`
- Parent decision: `ADR-008` (based_on); refines `RFC-003`; informs `SPEC-001`

## EVIDENCE chain inspected

(chronological — oldest first)

| EVID | Verdict | Source agent | Critical findings (one-line) |
|---|---|---|---|
| `EVID-044` | PASS | tester (Profile B) | validator 3/3 valid (0 MUST errors); pytest 621 passed / 1 skipped; be_01=27 (25 auto+2 judge), fe_01=27 (24 auto+3 judge), doc_01=15 judge-only; [Rn] coverage complete (0 untagged-auto warnings); 1 expected SHOULD-6 warn (doc_01 15<20, judge-only — acceptable) |
| `EVID-045` | PASS (updated) | code-reviewer (Profile B) | initially CONCERNS w/ 2 evaluator-wiring-blocking findings — **both RESOLVED in `17e4301`**: #1 HIGH be_01 [R20][R21][R22] bundle → split to 3 1:1 `it()` blocks sharing `rotateActiveRefresh()` (each assertion preserved, re-verified semantically); #2 MEDIUM fe_01 duplicate [R10] → R10 now sole-owner of blur test. #3/#4 (metadata counts) RESOLVED; #5 (doc_01 R7 Licence prompt_ref) ACCEPTED INFO/non-blocking. |

**No superseding-needed gap:** EVID-045 is not a separate "fix EVID" superseding a prior BLOCKER — it is the *updated* reviewer verdict on the amended commit `17e4301`. The earlier CONCERNS state was on `58a4fd1`; the gate is on `17e4301`, on which both EVIDs are PASS. No unresolved BLOCKER exists anywhere in the chain.

## Gate criteria

| # | Criterion | Status | Notes |
|---|---|---|---|
| 1 | Artifact MUST validation | ✅ | `forgeplan_validate RFC-004` → 0 errors, 0 warnings (passed=true) |
| 2 | All required EVIDENCE linked | ✅ | 2 `informs`-linked Profile B EVIDs on RFC-004: EVID-044 (tester), EVID-045 (code-reviewer) |
| 3 | No BLOCKER in chain | ✅ | 0 unresolved BLOCKERs; the 1 HIGH + 1 MEDIUM are RESOLVED + re-verified in code at `17e4301` |
| 4 | Unresolved CONCERNS count | 0 | the prior CONCERNS (on `58a4fd1`) are resolved on `17e4301`; only #5 INFO remains (accepted, non-blocking) |
| 5 | Activation/merge policy satisfied | ✅ | additive `requirements[]`; C4 test↔requirement 1:1 now holds (be_01 split); clean lineage (5e07840 ⟶ 17e4301, single commit) |
| 6 | Project-specific gate (`validate-task-specs.py`) | ✅ | **guardian re-ran it** on the `17e4301` tree → `3/3 task specs valid`, exit 0 (reproduced EVID-044, not relayed) |
| 7 | Blast radius within stated threshold | ✅ | diff confined to `evals/task-packs/` (task-pack content only); no live/published run consumes 1.1 until a calibration run is triggered — see Blast radius |

### Project-config gates (`.forgeplan/project-config.yaml` → `quality_gates`)

**Config source:** `/Users/explosovebit/Work/pollmevals/.forgeplan/project-config.yaml` (found — thresholds applied, no defaults needed)

| Criterion | Threshold (from project-config.yaml) | Observed | Result |
|---|---|---|---|
| Test coverage | `≥80%` (`min_test_coverage`) | **N/A** — RFC-004 Slice 2 specifies no statement-coverage threshold; this slice is task-pack YAML + test-title tagging, not statement-covered application code (EVID-044 records "n/a"). pytest 621 passed / 1 skipped, unaffected. | ✅ (N/A by artifact class — not a skipped gate) |
| Critical findings | `0` (`max_findings_critical`) | 0 across chain | ✅ |
| High findings | `≤3` (`max_findings_high`) | 1 raised, **0 unresolved** (be_01 C4 fixed + re-verified) | ✅ |
| Medium findings | `≤10` (`max_findings_medium`) | 1 raised, **0 unresolved** (fe_01 R10 fixed) | ✅ |
| Validate pass | `required` (`require_validate_pass`) | `forgeplan_validate RFC-004` PASS + `validate-task-specs.py` 3/3 | ✅ |
| Audit pass | `required` — ≥1 Profile B EVID w/ PASS | EVID-045 (code-reviewer) PASS; EVID-044 (tester) PASS | ✅ |
| Evidence chain | `required` for `rfc` | 2 `informs`-linked Profile B EVIDs | ✅ |

**Gates summary: 7/7** (coverage gate N/A by artifact class — task-pack content carries no statement-coverage threshold; all other gates green).

## Independent verification (guardian re-ran, did not trust narrative)

Guardian inspected the committed code at `17e4301` directly rather than relying on the EVID prose:

| Check | Method | Result |
|---|---|---|
| be_01 1:1 split (resolved HIGH) | `git show 17e4301:.../tests.spec.ts` grep | R20/R21/R22 are 3 separate `it()` blocks (L241/251/257) sharing `rotateActiveRefresh()`; **0 duplicate [Rn] tags** in be_01 |
| fe_01 R10 dedup (resolved MEDIUM) | grep test titles | R10 appears **exactly once** |
| Σ weight_components = 1.0, no `security` key | `python3/yaml.safe_load` on all 3 packs @17e4301 | be_01 Σ=1.000000, fe_01 Σ=1.000000, doc_01 Σ=1.000000; `has security key: False` for all three |
| Version bump 1.0→1.1 (additive, no in-place edit) | `git diff` on `version:` | all 3 packs `-version: "1.0"` / `+version: "1.1"` |
| Immutability (scoring/rubric/judge/contracts/gold-logic) | `git diff --name-only` filter | diff = **only** 5 files under `evals/task-packs/` (3 task.yaml + 2 gold/tests.spec.*); **0** hits on rubric/calibration/scoring/judge/contracts/`.py`; **0** non-test gold/solution files changed |
| Lineage | `git merge-base --is-ancestor` | `5e07840` is ancestor of `17e4301`; single clean commit |
| be_01 reqs + C5 security fallback | `yaml.safe_load` introspection | 27 reqs = 25 auto + 2 judge; R18/R19/R21/R22/R24/R25 all `maps_to: correctness` (C5 fallback, no `security` component) |
| Structural gate reproducibility | guardian re-ran `uv run -- python infra/scripts/validate-task-specs.py` | `3/3 task specs valid`, exit 0 (matches EVID-044) |

(Note: working tree was checked out at `17e4301` on `feat/rfc-004-slice-2-pack-migration` — verification ran against the exact commit under gate.)

## ADR-008 / RFC-004 invariant audit (orchestrator check 2)

| Invariant | Status | Evidence |
|---|---|---|
| C1 — `requirements[]` additive, `weight_components` weighted-sum unchanged | ✅ | `requirements[]` added as optional block; no scoring-contract file in diff |
| C2 — judge pipeline / rubric.yaml / α-MAD calibration untouched | ✅ | 0 rubric/judge/calibration files in diff |
| C3 — `judge` reqs recorded not scored | ✅ | be_01 2 judge + fe_01 3 judge + doc_01 15 judge present as records |
| C4 — `test_id ↔ requirement_id` 1:1 for auto | ✅ | **the be_01 split is exactly this fix**; 0 duplicate tags; tester confirms 0 untagged-auto warnings |
| C5 — Σ weight_components = 1.0; `security` ships as proposal only | ✅ | all 3 packs Σ=1.0 (yaml-verified); no `security` key; 6 security reqs → `correctness` fallback |
| C6 — migration = new task version, 1.0 not edited in place | ✅ | version 1.0→1.1 in diff; additive |
| C7 — no App-Bench content imported | ✅ | diff is own-authored task-pack content only |

## Blast radius

- **Affected scope on merge:** repository task-pack content only (`evals/task-packs/{be_01,fe_01,doc_01}/` — 3 `task.yaml` + 2 `gold/tests.spec.*`). **No** production service, **no** scoring engine, **no** judge pipeline, **no** published run.
- **Reversibility:** fully reversible — task-pack content is versioned (1.0 retained immutably; 1.1 is a new version). A bad 1.1 pack is reverted by a follow-up commit; the published 1.0 is never touched (ADR-002 immutability). No data migration, no irreversible side effect.
- **Downstream artifacts:** RFC-004 (this content lands its migration), SPEC-001 (gains `requirement_results[]` description — separate amendment task), RFC-003 (gains authoring step). None are broken by this merge; the migration *unblocks* the deferred calibration run.
- **Detection time if wrong:** immediate at the next calibration run — the RFC-004 score-neutrality gate (α≥0.70 / MAD≤1.5) measures the migration before any 1.1 pack is promoted into a live run, and holds the pack in `draft` if it shifts. A wrong migration cannot silently reach a published run.
- **Threshold check:** the blast radius **matches** what the RFC body claims (additive, per-task-version isolation, no scoring-machinery change). No broadening — verdict not downgraded on this axis.

## Deferred calibration gate — correctly NOT a merge gate (orchestrator check 3)

The score-neutrality calibration (Krippendorff **α ≥ 0.70** / **MAD ≤ 1.5**) is **out of scope for this merge**, by design:

- It is a **live-run gate** (RFC-004 Phase 4 / Rollback Plan / Test Strategy Hooks): it requires **judge LLM calls + the Docker eval sandbox** — neither executable in a static review. EVID-044 records it as "deferred — requires a live calibration run; baseline TBD."
- It produces **its own EVID** at the first post-migration calibration session (RFC-004: "Pending EVID (informs, to be created)").
- The migration ships **task-pack content**. **No published or live run consumes the 1.1 packs until a calibration run is explicitly triggered.** Merging the PR lands content; it does **not** promote a pack into a live run. Per RFC-004 Rollback Plan, a 1.1 pack stays in `draft` for promotion and is re-tuned if α/MAD shifts.
- Therefore deferring calibration past merge is **by-design**, not a buried BLOCKER. Guardian explicitly checked that this deferral is a genuine live-run boundary, not a skipped safety check — it is the former. **PASS.**

This is the one place a careless gate would mis-fire (treat a deferred-but-required live gate as "good enough" → silent PASS, or over-block a merge that the live gate legitimately backstops). Guardian's call: the live gate correctly backstops promotion, the merge gate correctly authorises content landing. The orchestrator MUST still schedule the live calibration run before any 1.1 pack is promoted (tracked in Orchestrator instructions).

## Orchestrator instructions

**PASS → the orchestrator may open and merge the Slice 2 PR** for branch `feat/rfc-004-slice-2-pack-migration` (commit `17e4301`) into `main`. No fixer dispatch required. No `forgeplan_activate` call applies (RFC-004 is already active).

After merge, the orchestrator MUST (tracked, not gating this merge):
1. **Schedule the live score-neutrality calibration run** (judge LLM calls + Docker sandbox) to verify α ≥ 0.70 / MAD ≤ 1.5 for **be_01 1.1** and **fe_01 1.1** *before* either 1.1 pack is promoted into a live/published run. That run emits its own EVID (the RFC-004 "Pending EVID"). If α/MAD shifts materially, hold the 1.1 pack in `draft` and re-tune granularity per RFC-004 Rollback Plan.
2. Optionally drive the SPEC-001 amendment task (describe `requirement_results[]` in `EvalRow.artifact_refs.evaluator_json`) — separate work item, not gated here.
3. No action needed on doc_01 SHOULD-6 (15<20) — expected/acceptable for a judge-only pack; and on EVID-045 Finding #5 (doc_01 Licence prompt_ref) — accepted INFO, defer to a future R addition if desired.

## Notes

- `mm-gate-failures` mental model and broad `memory_recall` were both **unavailable** in the `pollmevals` Hindsight bank this run (mental_model_list returned empty; memory_recall aborted). Recorded honestly per HARD RULE 6 — the gate proceeded on full first-party verification of the artifact + both EVIDs + the committed code, which is the load-bearing evidence; the memory layer would only have surfaced prior-regret patterns, none of which were needed to reach this binary.
- Residual risk to track even on PASS: the deferred calibration (item 1 above) is the real promotion gate for the 1.1 packs. Merging content is safe; **promoting** a 1.1 pack into a live run before calibration would not be. The orchestrator owns that sequencing.
- The session git-status snapshot named branch `fix/dynamic-eval-linux-deps` (clean); actual HEAD at gate time was `17e4301` on `feat/rfc-004-slice-2-pack-migration` (shared objects checked out at the exact commit under gate — ideal for verification).

## References

- Artifact under review: `RFC-004` (active; gate is on Slice 2 PR merge)
- EVIDENCE chain: `EVID-044` (tester PASS), `EVID-045` (code-reviewer PASS)
- Code under gate: `feat/rfc-004-slice-2-pack-migration` @ `17e4301`, parent main `5e07840`
- Project-config gates: `.forgeplan/project-config.yaml` → `quality_gates` (found; applied)
- Mental models consulted: `mm-gate-failures` — **not present in bank** (none available); broad recall aborted
- Prior guardian EVIDs for this artifact: none (first guardian gate on RFC-004 Slice 2)

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: audit



