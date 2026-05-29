---
depth: standard
id: ADR-008
kind: adr
last_modified_at: 2026-05-29T10:46:40.335512+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-003
  relation: refines
- target: ADR-007
  relation: based_on
- target: SPEC-001
  relation: informs
- target: PRD-002
  relation: informs
status: active
title: Atomic binary requirements[] feed scoring components, not replace them
---

# ADR-008: Atomic binary requirements[] feed scoring components, not replace them

> **STATUS: draft** — authored 2026-05-29 for v0.2. Decision source: completed FPF/ADI cycle (H1 Replace / H2 Feed / H3 Doc-only / H4 Spanning hybrid). `forgeplan_reason` run on parent RFC-003 confirmed the strict, auditable, gate-driven authoring direction is sound. Refines RFC-003 (task-pack authoring protocol); based on ADR-007 (hybrid sourcing + attribution). Leave in draft pending evidence + reviewer audit.

## Status

draft

## Context

POLLMEVALS tasks today bury their real testable requirements as **prose inside `prompt_template`**, while `success_criteria` is only 5-6 vague free-text items, and the `correctness` scoring component is an **opaque hidden-test ratio** (`numPassed / numTotal`). There is no 1:1 mapping between what the prompt asks for and what the evaluator checks, so a failing `correctness` score tells you *that* the model missed something, never *which* requirement it missed. That is un-auditable, and auditability is a load-bearing differentiator for an "open evidence layer for choosing production LLM stacks" (CONTEXT.md mission).

Prior-art benchmark **AfterQuery App-Bench** (HF dataset `AfterQuery/App-Bench`) demonstrates a stricter, auditable model: **20-40 atomic binary requirements per task** with a 1:1 numbered mapping between prompt and rubric, each scored strict pass/fail. We want that binary rigor and per-requirement auditability — **without** sacrificing our three differentiators that App-Bench lacks:

1. **Multi-layer weighted scoring** (`weight_components` per task type — see CONTEXT.md scoring formulas and `docs/04-runbook/08-scoring-contract.md`).
2. **LLM-judge panel with calibration** (PRD-002: Krippendorff α ≥ 0.70, MAD ≤ 1.5, median across ≥3 cross-family judges). App-Bench publishes **no inter-rater agreement** — pure binary measures *presence*, not *quality*.
3. **L0-L8 stack decomposition** (the unit POLLMEVALS evaluates is the stack, not the bare model).

Hard maintainer constraint: **must not break the scoring-contract (`docs/04-runbook/08-scoring-contract.md` weighted-sum formula) or run immutability (ADR-0002 / ADR-002).** Changing an evaluator, weight, or requirement set on a task = a **new task version** (per `task-lifecycle.md`) — that is acceptable and expected, never an in-place edit.

Strategic constraint from the maintainer: build **OUR OWN, LARGER** dataset (more atomic items than App-Bench), with AfterQuery used **only as an external reference benchmark + citation** — method borrowed, content **not** copied (App-Bench dataset license is unspecified). This sits directly under ADR-007's hybrid sourcing policy: borrowing a *method* is unconditionally allowed; borrowing *content* would require ADR-007 Tier 2 attribution + G4 contamination clearance, which we are not doing here.

Parents: refines **RFC-003** (authoring protocol — this extends how task packs encode requirements); based on **ADR-007** (the "cite the method, don't copy the content" strategy); informs **SPEC-001** (the `evaluator_json` / EvalRow contract this changes); informs **PRD-002** (the methodology + scoring parent whose `weight_components` and judge pipeline must remain untouched).

## Decision Drivers

- **Auditability of correctness** — per-requirement pass/fail, not an opaque aggregate ratio.
- **Preserve the judged-quality layer** (`pattern_match`, docs 5-criteria judging) — our edge over App-Bench, which has no calibration story.
- **No break** to the scoring-contract weighted-sum formula or to run immutability. Re-scoring = new task version, which is fine.
- **Lowest blast radius** for v0.2; deliver the bulk of the value now.
- **Forward-compatibility** to a richer model (judge-typed requirements as first-class rubric criteria) later.
- **Own, larger dataset** — AfterQuery is reference + citation only; method borrowed, content not copied.

## Decision

Adopt the **"Feed"** model (FPF hypothesis H2) for v0.2, **designed forward-compatible toward the "Spanning hybrid" (H4)**.

Introduce a structured **`requirements[]`** field on the task pack. Each item is the atomic contract from which **both** the prompt **and** the deterministic evaluator derive:

```
requirements:
  - id: req-001
    text: "Middleware returns 401 when the Authorization header is missing"
    check_type: auto            # auto | judge
    maps_to: correctness        # a scoring component (auto) OR a judge criterion (judge)
    prompt_ref: "§2.1"          # 1:1 back-reference into prompt_template
```

The binary pass-rate **FEEDS** the mapped deterministic scoring component(s); it does **not** replace `weight_components`, and it does **not** touch the judge pipeline.

**v0.2 wiring (what is actually live):**

- Only `check_type: auto` items are **wired**. A hidden test **is** the executable check for a requirement — `test_id ↔ requirement_id` (1:1). The component score is the auto pass-rate of its mapped requirements:

  `correctness(0-10) = 10 × (passed_auto_req / total_auto_req)`

  (and likewise for any other deterministic component a requirement maps to: `coverage`, `lint`, `type_safety`, …).

- `check_type: judge` items are **RECORDED for traceability only** in v0.2. They reference existing rubric criteria (e.g. `pattern_match`, the docs 5-criteria) via `maps_to`, but do **not** yet restructure the judge pipeline, rubric.yaml, or calibration mapping. They are forward-compatibility scaffolding for H4.

- **`weight_components` stay as the top-level weights.** Within a component, the score is the requirement pass-rate (auto) or the judge median (judge — unchanged from today). The weighted-sum formula in `08-scoring-contract.md` is **unchanged**; only the *derivation* of a deterministic component's 0-10 value becomes "requirement pass-rate × 10" instead of an opaque test ratio. Σ `weight_components` = 1.0 invariant preserved.

- **Target 20-40+ atomic items per task** (aim larger than App-Bench).

- **Evaluator output contract gains** `requirement_results: [{id, passed}]` inside `evaluator_json` (SPEC-001 EvalRow `artifact_refs.evaluator_json`). This is the auditable per-requirement trace.

This is additive and backward-readable: an old evaluator_json without `requirement_results[]` is still valid; new packs (new task versions) carry it.

## Consequences

### Positive

- `correctness` and every deterministic component become **transparent and per-requirement auditable** — a failure says *which* requirement (`req-017`) failed, not just a ratio.
- **1:1 prompt ↔ requirement traceability** via `prompt_ref` — closes the "requirements buried in prose" gap that RFC-003's authoring protocol cannot enforce on free-text prompts.
- Enables a **per-requirement flakiness signal** across best-of-N attempts (which atomic requirement is non-deterministically met?) — a diagnostic App-Bench cannot produce.
- **Calibration edge intact** — judge pipeline, α/MAD machinery, and `weight_components` are untouched; zero risk to the PRD-002 publication gates during this change.
- **Clean migration path to H4** — when judge-typed requirements become first-class rubric criteria, the `requirements[]` records already exist with `check_type: judge` and `maps_to`, so H4 is a wiring change, not a re-authoring.

### Negative

- **A contracts change in `packages/contracts`**: `requirement_results[]` added to `evaluator_json`, and `requirements[]` added to `task.schema`. Touches the contract package + the Python Pydantic mirror in `apps/eval-core-py/src/contracts/` + SPEC-001 (canonical) — both sides must move together (SPEC-001 reconciliation rule).
- **Migrating existing task-packs requires NEW task versions** (be_01 1.0→1.1, fe_01, doc_01) — by design under run immutability, but it is real authoring work and re-calibration cost (PRD-002 Q4: bumping task version requires re-calibrating the judge calibration set).
- **Not everything is deterministically checkable.** Requirements like "uses dependency injection" or "good error-handling style" have no executable test → they stay `check_type: judge`, recorded but not wired in v0.2, so the auditability win is *partial* until H4 lands.
- The auto pass-rate derivation makes `correctness` **sensitive to requirement granularity** — 40 fine-grained requirements vs 20 coarse ones change the score distribution for the *same* model output. Authoring discipline (RFC-003 gates) must keep granularity consistent within a task category.

### Neutral

- No change to the judge methodology (PRD-002), the median reducer, the self-judging guard, or the anonymisation pipeline.
- No change to sandbox/evaluator-boundary policy (NOTE-007) or to ADR-007 sourcing tiers — own-authored requirements are Tier 1 by default.
- App-Bench remains an external citation only; nothing is imported, so no ADR-007 Tier 2 attribution obligation is triggered.

## Options Considered

(from the completed FPF/ADI cycle)

### Option 1: H1 "Replace" — go fully binary like App-Bench
Make `correctness = pass-rate` the whole story; drop the weighted and judged layers.
- **Pros**: maximal simplicity; directly mirrors App-Bench; trivially auditable.
- **Cons**: **destroys the judged-quality axis and the calibration edge** (α/MAD machinery has nothing to score); pure binary measures *presence*, not *quality*; contradicts the cost-vs-quality thesis (CONTEXT.md). **REJECTED.**

### Option 2: H2 "Feed" — requirements[] is the structured contract feeding deterministic components (CHOSEN)
`requirements[]` derives both prompt and evaluator; auto pass-rate feeds `correctness` (and peers); `weight_components` + judge pipeline untouched.
- **Pros**: lowest blast radius; ~80% of the value; calibration edge fully preserved; clean path to H4.
- **Cons**: judge-typed requirements only *recorded*, not wired in v0.2 (partial auditability); contracts change required. **CHOSEN.**

### Option 3: H3 "Doc-only" — requirements[] as metadata for traceability, no scoring change
Add `requirements[]` purely for prompt↔rubric traceability; leave `correctness` as the opaque ratio.
- **Pros**: zero scoring risk; trivial to ship.
- **Cons**: leaves `correctness` opaque — fails the primary driver (auditability); under-delivers. **WEAKENED / rejected.**

### Option 4: H4 "Spanning hybrid" — every requirement carries check_type auto|judge AND judge-type requirements become first-class rubric criteria
Full model: judge requirements restructure rubric.yaml + judge output schema + calibration mapping.
- **Pros**: highest value; full per-requirement auditability across both deterministic *and* judged axes.
- **Cons**: reworks rubric.yaml + judge output schema + calibration mapping → **risk to the α ≥ 0.70 machinery during transition**. **DEFERRED to a later phase** (H2 is explicitly designed forward-compatible toward it).

## Decision Outcome

Chosen option: **"H2 Feed"**, because it satisfies the primary driver (auditable, per-requirement `correctness`) while honoring the hard constraint (no break to the scoring-contract weighted-sum or run immutability) at the **lowest blast radius** — the judge pipeline and `weight_components`, which carry our calibration differentiator over App-Bench, are not touched at all.

H1 was rejected because it sacrifices exactly the differentiator (judged quality + calibration) that the maintainer's constraints protect. H3 under-delivers on the core auditability goal. H4 delivers the most but puts the PRD-002 α/MAD publication machinery at risk during the transition — so it is deferred, and H2 is deliberately shaped (record-but-don't-wire `check_type: judge`, plus `maps_to` into existing criteria) so that H4 later becomes a wiring change rather than a re-authoring.

The `forgeplan_reason` ADI run on parent RFC-003 independently recommended proceeding with the strict, auditable, gate-driven authoring direction (H1 in that artifact's local numbering = "strict multi-agent pipeline with G1-G4 gates"), reinforcing that adding **structured, atomic, auditable** requirements is congruent with the authoring protocol this ADR refines.

## Open Question (deferred — do NOT decide here)

Whether to add **`security` as its own top-level `weight_components` entry for backend tasks**, so security requirements have an `auto` home. Currently security is folded into the be_01 **judge** rubric, which means a security requirement that *is* deterministically checkable has no auto component to feed. Resolving this affects the Σ `weight_components` = 1.0 invariant (a new component requires re-weighting). **Defer to the implementing RFC** — this ADR records the question, it does not answer it.

## Invariants

What MUST NEVER be violated by this decision:

1. **`requirements[]` does not replace `weight_components`.** The top-level weighted-sum formula in `08-scoring-contract.md` stays the source of truth for a task's final 0-10 score. `requirements[]` only changes how a *deterministic component's* value is derived.
2. **The judge pipeline, rubric.yaml, judge output schema, and calibration (α/MAD) mapping are untouched in v0.2.** Any change to them is H4 and requires its own ADR.
3. **`check_type: judge` requirements are recorded, never wired, in v0.2.** Wiring them = H4.
4. **`test_id ↔ requirement_id` is 1:1 for `auto` items.** A wired auto requirement without exactly one executable check, or an executable check with no requirement, is invalid.
5. **Σ `weight_components` = 1.0** remains invariant — this ADR does not add or re-weight components (the `security` component question is explicitly deferred).
6. **No in-place re-scoring.** Adding `requirements[]` to an existing pack = a new task version per `task-lifecycle.md` (run immutability, ADR-002 / ADR-0002). The old version is kept as historical record.
7. **App-Bench content is never imported.** Method only. Importing content would re-open this under ADR-007 Tier 2 (attribution + G4).

## Affected Files / Modules

- `packages/contracts/schemas/` — `task.schema` gains `requirements[]`; the `evaluator_json` schema gains `requirement_results: [{id, passed}]`.
- `apps/eval-core-py/src/contracts/` — Pydantic v2 mirror updated in lock-step (SPEC-001 reconciliation rule: both sides move together).
- `evals/task-packs/<slug>/task.yaml` — gains the `requirements[]` block; existing packs migrate via new task versions (be_01, fe_01, doc_01).
- The deterministic evaluator(s) per pack — emit `requirement_results[]` and compute component score as `10 × passed_auto_req / total_auto_req`.
- `SPEC-001` — canonical contract amended to describe `requirement_results[]` in EvalRow `artifact_refs.evaluator_json` (this ADR `informs` it; the amendment itself is a SPEC-001 update task).
- `RFC-003` — authoring protocol gains a step: author the structured `requirements[]` block with 1:1 `prompt_ref` mapping (the G1-G4 gates now audit against it).
- `infra/scripts/validate-task-specs.py` — accept the new `requirements[]` field (schema update, deferred to the first migrated pack).
- **Not touched**: `docs/04-runbook/08-scoring-contract.md` weighted-sum formula, judge-panel code (`judge_panel.py`), rubric.yaml, calibration suite.

## Rollback Plan

| Failure mode | Rollback action |
|---|---|
| Auto pass-rate derivation shifts a task's score distribution enough to break PRD-002 α ≥ 0.70 / MAD ≤ 1.5 after migration | Revert that pack to its previous task version (immutability keeps it intact); keep the new version in `draft`; emit EVID documenting the shift; re-tune requirement granularity before re-promoting. No effect on other packs (per-task-version isolation). |
| Contracts change breaks the contract package / Python mirror drift | The `requirement_results[]` field is additive and optional — old evaluator_json validates without it; roll the contract package back to the additive-only delta and re-land the Pydantic mirror in the same change. |
| Requirement granularity proves un-standardisable across authors (G3 diversity / consistency drift) | Cap the win at H3 "Doc-only" for affected categories — keep `requirements[]` as traceability metadata, revert that component's derivation to the opaque ratio — without superseding this ADR (the field still exists for traceability). |
| `check_type: judge` "recorded but unwired" backlog becomes the dominant complaint | This is the planned trigger to schedule **H4** via a new RFC + ADR; not a rollback of H2. |
| Maintainer decides the larger-own-dataset goal is infeasible and wants App-Bench content | Re-open under ADR-007 Tier 2 (license check + attribution + G4 contamination gate); requires an ADR-007 amendment, not a change to this ADR. |

## Revisit Trigger (Evidence Decay)

Re-open this decision if any of the following hold:

- **First calibration session after v0.2 task-version bumps** shows the auto pass-rate derivation shifts a task's score distribution enough to break the PRD-002 α ≥ 0.70 / MAD ≤ 1.5 gates (i.e. the change is not score-contract-neutral in practice).
- The count of `check_type: judge` "recorded but unwired" requirements grows large enough that **partial auditability becomes the dominant complaint** — that is the trigger to schedule **H4**.
- App-Bench (or an equivalent) publishes a calibration/inter-rater story that erodes our differentiator, changing the cost-benefit of staying weighted+judged.
- The implementing RFC resolves the `security`-component open question in a way that changes the `weight_components` contract.

No fixed `valid_until` date — the decision is event-triggered, not time-triggered, because it is gated on the first real calibration data (TBD; arrives with the v0.2 task-version migration).

## Related Decisions

- **RFC-003** (refines) — task-pack authoring protocol; this ADR extends how packs encode requirements (the structured `requirements[]` field the G1-G4 gates will now author against).
- **ADR-007** (based_on) — hybrid sourcing + attribution; the "AfterQuery as external reference + cite, don't copy content" strategy is this ADR's application of ADR-007's method-vs-content distinction.
- **SPEC-001** (informs) — manifest/eval/artifact contracts; `requirement_results[]` is a new field inside `evaluator_json` (EvalRow `artifact_refs`), and `automatic_metrics` derivation changes.
- **PRD-002** (informs) — judge panel / scoring infrastructure; this ADR commits to leaving `weight_components` and the judge/calibration pipeline untouched in v0.2.
- **ADR-002 / docs/adr/0002-run-immutability.md** — run immutability; re-scoring a task = new task version, never in-place edit.

## References

- `AfterQuery/App-Bench` (Hugging Face dataset) — external reference benchmark for the atomic-binary-requirements method. **Citation only; no content imported** (license unspecified).
- `docs/04-runbook/08-scoring-contract.md` — weighted-sum formula (unchanged by this ADR).
- `docs/02-methodology/scoring.md` — `weight_components` per task type.
- `docs/02-methodology/task-lifecycle.md` — task-version bump policy (governs the migration of existing packs).
- `packages/contracts/schemas/` + `apps/eval-core-py/src/contracts/` — where `requirements[]` and `requirement_results[]` land.
- FPF/ADI cycle (H1-H4) — decision source of record (supplied by orchestrator; `forgeplan_reason RFC-003` corroborates the direction).
- Metrics in this ADR (score-distribution shift, α/MAD impact) are **TBD** — they belong in an EVID artifact produced by the first post-migration calibration session, not invented here.





