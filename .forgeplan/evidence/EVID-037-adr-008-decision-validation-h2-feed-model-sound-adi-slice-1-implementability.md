---
depth: standard
id: EVID-037
kind: evidence
last_modified_at: 2026-05-29T16:00:06.475697+00:00
last_modified_by: claude-code/2.1.156
links:
- target: ADR-008
  relation: informs
status: draft
title: ADR-008 decision validation — H2 Feed model sound (ADI + Slice-1 implementability)
---

## Verdict

**PASS**

H2 "Feed" model is sound and implementable. The ADI cycle eliminated all three alternatives on principled grounds; `forgeplan_reason` independently re-confirmed H2 at HIGH confidence; RFC-004 Slice 1 (EVID-034 code review PASS + EVID-035 test PASS) demonstrates the decision's central implementability claim — additive, no scoring-contract break — holds in practice.

## Evidence type

🛠 Other

Subtype: Decision reasoning validation (ADI option-elimination + empirical implementability corroboration). No specialist agent (security-expert / code-reviewer / tester / architect-reviewer) owns this class of evidence — evidence-recorder is the correct fallback for decision-soundness recording.

## Raw input provenance

- Source: `.forgeplan/adrs/ADR-008-atomic-binary-requirements-feed-scoring-components-not-replace-them.md` (parent artifact body, read via `forgeplan_get ADR-008`) + orchestrator-inline directive (two grounds: ADI + Slice-1 corroboration) + sibling EVIDs read via `forgeplan_get EVID-034` and `forgeplan_get EVID-035`
- Size: `209 lines / 20017 bytes` (ADR-008 on-disk projection)
- Fingerprint: `sha256:a4636a22d4775c446e30eabe9c13d901f033fbd50ddcb740025cbf24a0b55843`
- Captured at: `2026-05-29T15:58Z`
- Captured by: `claude-code/sonnet-4-6/evidence-recorder-task-adr008`

## Raw input (truncated to ≤2000 chars)

```
ADR-008: Atomic binary requirements[] feed scoring components, not replace them
STATUS: draft

## Decision
Adopt the "Feed" model (FPF hypothesis H2) for v0.2, designed forward-compatible toward H4.
Introduce a structured requirements[] field on the task pack. Each item is the atomic contract
from which both the prompt and the deterministic evaluator derive:
  requirements:
    - id: req-001
      text: "Middleware returns 401 when the Authorization header is missing"
      check_type: auto
      maps_to: correctness
      prompt_ref: "§2.1"

The binary pass-rate FEEDS the mapped deterministic scoring component(s); it does NOT replace
weight_components, and it does NOT touch the judge pipeline.

## Options Considered (FPF/ADI cycle: H1 / H2 / H3 / H4)
H1 "Replace" — REJECTED: destroys judged-quality axis + calibration edge (α/MAD machinery)
H2 "Feed"    — CHOSEN: lowest blast radius; calibration edge fully preserved; forward to H4
H3 "Doc-only"— WEAKENED: leaves correctness opaque; fails the auditability driver
H4 "Spanning"— DEFERRED: reworks rubric.yaml + judge output schema + calibration mapping

## Invariants (must never be violated)
C1: requirements[] does not replace weight_components
C2: judge pipeline, rubric.yaml, calibration (α/MAD) untouched in v0.2
C3: check_type:judge requirements recorded, never wired, in v0.2
C4: test_id ↔ requirement_id is 1:1 for auto items
C5: Σ weight_components = 1.0 invariant preserved
C6: no in-place re-scoring — new task version required
C7: App-Bench content never imported (method only)
```
... [truncated, full content at `.forgeplan/adrs/ADR-008-atomic-binary-requirements-feed-scoring-components-not-replace-them.md` sha256:a4636a22d4775c446e30eabe9c13d901f033fbd50ddcb740025cbf24a0b55843]

## Structured findings

**Subtype: Decision reasoning validation**

### Ground 1 — ADI option-elimination (FPF/ADI cycle + forgeplan_reason corroboration)

The decision originated in a completed FPF/ADI cycle over four hypotheses. Each non-chosen option was eliminated on a principled ground traceable directly to ADR-008's own decision drivers:

| Hypothesis | Disposition | Eliminating reason |
|---|---|---|
| H1 "Replace" (fully binary, App-Bench style) | REFUTED | Destroys the judged-quality layer (`pattern_match`, docs 5-criteria) and the calibration edge (Krippendorff α ≥ 0.70, MAD ≤ 1.5) — the platform's stated differentiator over App-Bench. Measures presence, not quality. Directly contradicts Decision Driver "Preserve the judged-quality layer." |
| H3 "Doc-only" (requirements[] as metadata only, no scoring change) | WEAKENED / rejected | Leaves `correctness` opaque (a hidden-test ratio). Fails the primary Decision Driver "Auditability of correctness." Under-delivers on the problem statement with near-zero blast radius gain over H2. |
| H4 "Spanning hybrid" (judge-typed requirements as first-class rubric criteria) | DEFERRED | Reworks rubric.yaml + judge output schema + calibration mapping simultaneously — puts the α ≥ 0.70 / MAD ≤ 1.5 publication machinery at risk during transition. H2 is explicitly designed forward-compatible toward H4 (`check_type: judge` recorded but not wired; `maps_to` into existing criteria already present), so deferral loses no optionality. |
| **H2 "Feed"** | **CHOSEN** | Lowest blast radius. Delivers ~80% of the auditability value (per-requirement `correctness` pass-rate). `weight_components` formula and judge/calibration pipeline entirely untouched. Clean migration path to H4 via a wiring change rather than re-authoring. Satisfies all seven decision invariants (C1–C7). |

The `forgeplan_reason` tool was run independently on ADR-008 (model: gemini-2.5-pro-preview per orchestrator directive) and re-confirmed H2 at HIGH confidence, corroborating the ADI elimination. The `forgeplan_reason` run on parent RFC-003 separately recommended the strict, auditable, gate-driven authoring direction (H1 in RFC-003's local numbering = "strict multi-agent pipeline with G1–G4 gates"), which is congruent: adding structured, atomic, auditable `requirements[]` is exactly what the authoring protocol RFC-003 refines toward. Two independent reasoning passes over two parent artifacts both point at H2.

No scoring was fabricated. The ADI cycle conclusions are drawn verbatim from ADR-008's "Options Considered" and "Decision Outcome" sections, which record the completed reasoning cycle.

### Ground 2 — Slice-1 empirical implementability corroboration

ADR-008's central implementability claim: H2 is **additively implementable WITHOUT breaking the scoring contract (Σ `weight_components` = 1.0) or run immutability (ADR-0002)**. RFC-004 Slice 1 is the first implementation of ADR-008. Two independent Profile B EVIDs both returned PASS against that implementation:

**EVID-034 — RFC-004 Slice 1 code review (PASS, verdict: supports, CL3)**

Key findings confirming ADR-008 invariants held in the implementation:
- `requirements` is an **optional** field with `additionalProperties: false` in the JSON Schema — additive by construction; all 3 existing task packs (be_01/fe_01/doc_01) validate unchanged (backward-compat confirmed).
- `weight_components` is **untouched** in `packages/contracts/schemas/task.schema.json` and `apps/eval-core-py/src/contracts/task.py`.
- Judge pipeline (`judge_panel.py`), rubric.yaml, and calibration mapping are **not touched** anywhere in the diff range `58635d3..8b424e1`.
- Σ `weight_components` = 1.0 **preserved** (MUST-5 validator rule with `_WEIGHT_SUM_TOLERANCE = 1e-6`; float-tolerance-based, not exact equality).
- `security` component remains a **marked proposal** (deferred open question, not activated) — Σ invariant intact.
- ADR-008 invariants C1–C7 **all respected** as verified by the code-reviewer agent.
- 61 tests pass (48 original + 13 new validator tests added in fix commit `8b424e1`); ruff, mypy, tsc all clean.

**EVID-035 — RFC-004 Slice 1 test run (PASS, verdict: supports, CL3)**

Key measurements confirming the additive, non-breaking nature of the change:
- 608/609 tests pass, 0 failed, 1 skipped (pre-existing, unrelated to Slice 1).
- All **48 new Slice 1 tests** pass (`test_component_score.py` 20 + `test_task_contracts.py` 28).
- Task spec validator (additivity check): **3/3 existing packs valid, EXIT=0** — the 3 reference packs (be_01/fe_01/doc_01) continue to validate without modification.
- TS contracts typecheck clean (`tsc --noEmit`, EXIT=0).
- `component_score` function verified as a clean pure function with correct `None` sentinel for zero-auto-req components; formula matches RFC-004 specification.
- Pydantic models use `ConfigDict(extra="forbid", frozen=True)` — additive enforcement and immutability correct by construction.

**What these EVIDs corroborate:** They are RFC-004 *code* evidence, not ADR-008 decision evidence. They are cited here as corroboration that ADR-008's implementability claim ("additive, no scoring-contract break") held in the first real implementation. The link direction remains EVID-034/035 → RFC-004; this EVID does not re-link them to ADR-008.

### Summary of two-ground validation

| Ground | Source | Outcome |
|---|---|---|
| ADI option-elimination | FPF/ADI cycle (H1–H4) + `forgeplan_reason` independent re-confirmation | H2 is the only option satisfying all decision drivers without sacrificing the calibration differentiator |
| Empirical implementability | EVID-034 (code review PASS) + EVID-035 (test PASS) for RFC-004 Slice 1 | ADR-008 invariants C1–C7 held; additive, backward-compatible, scoring contract and judge pipeline untouched |

Both grounds are independent. The reasoning ground establishes soundness of the choice; the empirical ground validates that the decision's implementability assumption was not wishful thinking.

## Recommended next steps

- Activate ADR-008 (this EVID provides the missing decision evidence; R_eff should rise above 0.0 after link lands).
- Orchestrator / guardian runs `forgeplan_validate ADR-008` then `forgeplan_activate ADR-008` — activation is not this agent's role.
- EVID-034 and EVID-035 remain linked to RFC-004; no re-linking needed.
- When the first post-migration calibration session completes (after v0.2 task-version bumps for be_01/fe_01/doc_01), create a follow-up empirical EVID against ADR-008 recording the actual α/MAD impact — the revisit trigger stated in ADR-008 § Revisit Trigger.

## References

- Parent: `ADR-008`
- Related EVIDENCE (RFC-004 Slice 1 code): `EVID-034` (code review, PASS) — cited as implementability corroboration
- Related EVIDENCE (RFC-004 Slice 1 tests): `EVID-035` (test run, PASS) — cited as implementability corroboration
- Related ADR: `ADR-007` (hybrid sourcing + attribution — App-Bench method-only strategy ADR-008 applies)
- Related RFC: `RFC-003` (task-pack authoring protocol — ADR-008 refines this)
- Related RFC: `RFC-004` (Slice 1 implementation of ADR-008 — source of empirical corroboration)

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: reasoning

