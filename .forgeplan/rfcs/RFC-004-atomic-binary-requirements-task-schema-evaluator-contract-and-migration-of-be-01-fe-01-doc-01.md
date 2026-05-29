---
depth: standard
id: RFC-004
kind: rfc
last_modified_at: 2026-05-29T10:56:10.219222+00:00
last_modified_by: claude-code/2.1.156
links:
- target: ADR-008
  relation: based_on
- target: RFC-003
  relation: refines
- target: SPEC-001
  relation: informs
status: draft
title: Atomic binary requirements[] — task schema, evaluator contract, and migration of be_01/fe_01/doc_01
---

# RFC-004: Atomic binary requirements[] — task schema, evaluator contract, and migration of be_01/fe_01/doc_01

> **STATUS: draft** — implements ADR-008 (H2 "Feed"). Authored 2026-05-29 for v0.2. The design decision is already made in ADR-008; this RFC is the engineering design that lands it: exact field shapes, the evaluator-output contract, the validator rules, the score-derivation math, and the migration of the three existing packs to new task versions. `forgeplan_reason ADR-008` (gemini-3.1-pro-preview) independently re-confirmed H2 at High confidence — used here as grounding, not re-litigation.

## Summary

Introduce a structured `requirements[]` field on the task contract (`task.schema.json` + `types.ts` + the Pydantic mirror) and a `requirement_results[]` field on the evaluator output (`evaluator_json`, SPEC-001 EvalRow surface). Each requirement is an atomic, binary, prompt-traceable contract item. For `check_type: auto` items, the binary pass-rate **feeds** the deterministic scoring component it maps to (e.g. `correctness`); for `check_type: judge` items, the item is **recorded for traceability only** in v0.2 (forward-compat scaffolding for the deferred H4). `weight_components` stays the top-level weight vector and the `08-scoring-contract.md` weighted-sum is unchanged — only the *derivation* of a deterministic component's 0-10 value changes from an opaque test ratio to a per-requirement pass-rate. The three existing packs (be_01, fe_01, doc_01) migrate to new task versions (1.0 → 1.1) under run immutability. App-Bench is method-reference-and-citation only; no content is imported.

This RFC also **resolves the open question ADR-008 deferred** (whether `backend` gains a `security` top-level weight component) — with a concrete recommendation **marked as a proposal for review**, not a committed decision.

## Motivation

(Inherits the problem statement from ADR-008 — see that artifact's Context.) In one line: today the real testable requirements are buried as prose inside `prompt_template`, and `correctness` is an opaque `numPassed / numTotal` ratio, so a failing score tells you *that* the model missed something, never *which* requirement — un-auditable, and auditability is the platform's load-bearing differentiator. The atomic-binary method (1:1 prompt↔check mapping, strict pass/fail) makes correctness per-requirement auditable. ADR-008 chose to **feed** this into the existing weighted+judged pipeline rather than replace it, preserving the calibration edge (Krippendorff α ≥ 0.70, MAD ≤ 1.5) that App-Bench lacks. This RFC turns that decision into a buildable contract + migration.

Bounding constraints (from ADR-008 Invariants, carried verbatim as design constraints):
- C1: `requirements[]` does **not** replace `weight_components`; the `08-scoring-contract.md` weighted-sum stays the source of truth for the final 0-10 score.
- C2: judge pipeline, `rubric.yaml`, judge output schema, and α/MAD calibration are **untouched** in v0.2.
- C3: `check_type: judge` requirements are recorded, never wired, in v0.2.
- C4: `test_id ↔ requirement_id` is 1:1 for `auto` items.
- C5: Σ `weight_components` = 1.0 invariant preserved (so the deferred `security`-component idea ships only as a *proposal* here).
- C6: no in-place re-scoring — migrating a pack = a new task version (ADR-002 / `task-lifecycle.md`).
- C7: App-Bench content is never imported (ADR-007 method-vs-content).

## Module Breakdown

Named modules touched, one responsibility each. (Diagram described in prose under "Component Diagram".)

- **contracts-task-schema** — `packages/contracts/schemas/task.schema.json`: declares the `requirements[]` array shape. Single source of structural truth for a task pack's requirement list.
- **contracts-ts-types** — `packages/contracts/src/types.ts`: the TS `TaskRequirement` interface + `RequirementResult` interface, mirroring the JSON Schema for TS consumers (`apps/api`, `apps/site`).
- **contracts-py-mirror** — `apps/eval-core-py/src/contracts/`: Pydantic v2 models `TaskRequirement` and `RequirementResult`, moved in lock-step with the JSON Schema (SPEC-001 reconciliation rule — both sides change together).
- **spec-001-amendment** — SPEC-001 body: amends the `EvalRow.artifact_refs.evaluator_json` description to include `requirement_results: [{id, passed}]` and the new `automatic_metrics` derivation. (This RFC `informs` SPEC-001; the amendment is its own SPEC-001 update task.)
- **task-spec-validator** — `infra/scripts/validate-task-specs.py`: extended with `requirements[]`-specific rules (unique ids, maps_to allowed-set, auto→deterministic, prompt_ref resolvable, count warning, Σ weights = 1.0).
- **deterministic-evaluator** — the per-pack evaluator chain (host-side + Docker-sandboxed `CorrectnessEvaluator`): emits `requirement_results[]` and computes each deterministic component score as `10 × passed_auto_req / total_auto_req`.
- **task-pack-migration** — `evals/task-packs/<slug>/task.yaml` (be_01, fe_01, doc_01): each gains a `requirements[]` block and is bumped to a new task version (1.1).
- **rfc-003-authoring-step** — RFC-003 protocol gains a step: author the `requirements[]` block with 1:1 `prompt_ref` mapping; the G1–G4 gates now audit against it. (This RFC `refines` RFC-003.)

**Explicitly NOT touched** (C2): `docs/04-runbook/08-scoring-contract.md` weighted-sum formula, `judge_panel.py`, `rubric.yaml`, the calibration suite, the median reducer, the self-judging guard, the anonymisation pipeline.

## Component Diagram (prose)

Authoring time: a task author writes a single `requirements[]` list in `task.yaml`. From that one list, **two** artifacts derive — the numbered `prompt_template` items the candidate sees (via `prompt_ref`) and the deterministic checks the evaluator runs (via the `test_id ↔ requirement_id` 1:1 convention for `auto` items). `task-spec-validator` reads `task.yaml` against `contracts-task-schema` and rejects malformed requirement lists before the pack lands.

Run time: the candidate produces an output. The `deterministic-evaluator` runs the pack's hidden tests; each test is the executable check for exactly one `auto` requirement, so it produces one `{id, passed}` entry. The evaluator writes `requirement_results: [{id, passed}]` into `evaluator_json` (the auditable trace) and computes each deterministic component's 0-10 value as the pass-rate of the `auto` requirements mapped to that component. Those component values flow **unchanged** into the `08-scoring-contract.md` weighted-sum, alongside the judge-median values for judged components (which arrive from the untouched `judge_panel.py` path). `check_type: judge` requirements pass through to `evaluator_json` as recorded metadata (no `passed` field populated in v0.2) — they do not enter scoring.

Direction summary: `task.yaml` requirements[] → (fan-out) → {prompt items, hidden tests}; hidden tests → evaluator → requirement_results[] in evaluator_json → deterministic component pass-rate → weighted-sum (shared with judge-median path) → final_score.

## Data Flow

**Happy path (be_01, a coding task).** Author writes 27 `requirements[]` items (worked decomposition below). 23 are `check_type: auto` mapped to `correctness` or `security` (proposal; today: `correctness`); 4 are `check_type: judge` mapped to `code_clarity` / `test_alignment`. The candidate model receives the numbered prompt. The evaluator runs `npx vitest run --reporter=json`; the vitest JSON reporter yields one result per `it(...)`/`test(...)` block. Each test is tagged with its `requirement_id` (test_id ↔ requirement_id 1:1), so the evaluator maps test results to `requirement_results: [{id:"R1", passed:true}, ...]`. `correctness = 10 × (passed auto-req mapped to correctness / total auto-req mapped to correctness)`. That value enters the coding weighted-sum at weight 0.40. `judge` requirements (e.g. R24 "uses dependency injection for the store") are written into `evaluator_json.requirement_results` as `{id:"R24", check_type:"judge", passed:null}` — recorded, not scored. Final score = `0.40·correctness + 0.15·coverage + 0.10·complexity + 0.10·lint + 0.10·type_safety + 0.15·pattern_match`, identical formula to today; only `correctness` is now sourced from the pass-rate.

**Failure path (a `prompt_ref` points to a non-existent prompt item).** `task-spec-validator` resolves every `prompt_ref` against the numbered items parsed out of `prompt_template`. An unresolvable `prompt_ref` is a MUST-level validation error — the pack is rejected, never promoted. (This is the gate that closes the "requirements buried in prose with no traceability" gap.)

**Failure path (an `auto` requirement has no matching test, or a test has no requirement).** Violates C4 (1:1). The evaluator's `requirement_results[]` would contain an `auto` id with no test result, or a test result with no requirement id — both are validation/evaluator-wiring errors. The Evaluator Wiring Agent (RFC-003 topology) catches this when it confirms `len(auto requirements) == len(hidden tests)` and the id sets are equal.

**doc_01 (judge-only) path.** `evaluator_commands: []` — no host-side evaluator, no `auto` requirements. `requirements[]` is still populated but every item is `check_type: judge`, `maps_to` a docs rubric criterion (`structural_completeness`, `factual_accuracy`, …). No `requirement_results[]` is produced at run time (nothing executable). The requirements exist purely for **prompt↔criterion traceability** (which prompt clause each criterion is meant to check). Scoring is unchanged: mean of 5 criterion medians.

## Function Signatures / Component Contracts

### 1. Task schema — `requirements[]` item shape

Added to `packages/contracts/schemas/task.schema.json` as an **optional** top-level property `requirements` (additive: old packs without it remain valid). Item shape:

```jsonc
// task.schema.json  ->  properties.requirements
"requirements": {
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id", "text", "check_type", "maps_to", "prompt_ref"],
    "additionalProperties": false,
    "properties": {
      "id":         { "type": "string", "pattern": "^R[0-9]+$" },   // e.g. "R7"
      "text":       { "type": "string", "minLength": 1 },            // atomic, binary, one assertion
      "check_type": { "enum": ["auto", "judge"] },
      "maps_to":    { "type": "string" },                           // a weight_components key OR a rubric criterion name
      "prompt_ref": { "type": "integer", "minimum": 1 }             // 1-based numbered line in prompt_template
    }
  }
}
```

TS mirror in `packages/contracts/src/types.ts`:

```ts
export interface TaskRequirement {
  id: string;                       // /^R\d+$/, unique within a task
  text: string;                     // one atomic binary assertion
  check_type: "auto" | "judge";
  maps_to: string;                  // weight_components key (auto) OR rubric criterion (judge)
  prompt_ref: number;               // 1-based index into the numbered prompt_template items
}

// extend the existing PollmevalsTask interface (additive, optional):
//   requirements?: TaskRequirement[];
```

Pydantic v2 mirror in `apps/eval-core-py/src/contracts/` (moves in lock-step):

```python
class TaskRequirement(BaseModel):
    id: str = Field(pattern=r"^R\d+$")
    text: str = Field(min_length=1)
    check_type: Literal["auto", "judge"]
    maps_to: str
    prompt_ref: int = Field(ge=1)
```

### 2. Evaluator contract — `requirement_results[]` in `evaluator_json`

Added to the `evaluator_json` artifact (SPEC-001 `EvalRow.artifact_refs.evaluator_json`). Additive and backward-readable — an old `evaluator_json` without it stays valid.

```jsonc
// evaluator_json (per-eval, content-addressed)
{
  "automatic_metrics": { "correctness": 9.2, "test_coverage": 8.5, "...": "..." },
  "requirement_results": [
    { "id": "R1",  "check_type": "auto",  "passed": true  },
    { "id": "R2",  "check_type": "auto",  "passed": false },
    { "id": "R24", "check_type": "judge", "passed": null  }   // recorded only in v0.2
  ]
}
```

TS / Pydantic shape:

```ts
export interface RequirementResult {
  id: string;
  check_type: "auto" | "judge";
  passed: boolean | null;   // boolean for auto (wired); null for judge (recorded-only in v0.2)
}
```

### 3. Deterministic component derivation (the math)

For each deterministic component `c` (a `weight_components` key whose value comes from executable checks — `correctness`, `test_coverage`/`coverage`, `linter`/`lint`, `type_safety`, `complexity`, frontend `accessibility`/`ux_states`, and the proposed `security`):

```
let A_c   = { r in requirements : r.check_type == "auto" and r.maps_to == c }
let P_c   = { r in A_c : requirement_results[r.id].passed == true }
component_score(c)  =  10 * |P_c| / |A_c|        # 0..10, by definition |A_c| >= 1 when c is auto-sourced
```

- A component with **zero** mapped `auto` requirements is NOT derived from this formula — it keeps its existing derivation (e.g. `coverage` from a coverage tool, `complexity` from lizard, `lint` from eslint warning count). The pass-rate formula applies **only** to components that have ≥1 `auto` requirement mapped to them. This is what makes the change additive rather than a rewrite of every metric.
- `correctness` is the primary target: it moves from opaque `numPassed/numTotal` to `10 × passed_auto_req(correctness) / total_auto_req(correctness)` — same arithmetic shape, but now every term is a named, traceable requirement.

### 4. `test_id ↔ requirement_id` 1:1 convention

A hidden test is the **executable check for exactly one `auto` requirement**. The convention:
- Each `it(...)`/`test(...)` (TS/vitest) or test function (py/pytest) is annotated with its `requirement_id` — recommended mechanism: a leading tag in the test title, `it("[R3] returns 401 + AUTH_EXPIRED for an expired token", …)`, parsed by the evaluator from the vitest JSON reporter's `name`. (Alternative considered: a sidecar `test-map.yaml` — see Options Considered.)
- Invariant (C4): the set of `auto` requirement ids equals the set of test requirement-tags. A wired `auto` requirement with no test, or a test with no requirement, is invalid (caught by validator + Evaluator Wiring Agent).
- `judge` requirements have **no** test and appear in `requirement_results` only with `passed: null`.

### 5. Validator rules — `infra/scripts/validate-task-specs.py`

Extend `validate_one(...)` with a post-schema requirements check (these run only when `requirements` is present, so old packs are unaffected):

- **MUST — unique ids**: every `requirements[].id` is unique within the task. Duplicate → error.
- **MUST — maps_to ∈ allowed set for the category**: `auto` items map to a deterministic `weight_components` key for that category; `judge` items map to a rubric criterion name (read from the sibling `rubric.yaml`). The allowed set is category-derived: backend → `{correctness, test_coverage, complexity, linter, type_safety[, security]}` for auto and the be_01 rubric criteria for judge; frontend → `{correctness, accessibility, test_coverage, type_safety, ux_states}` for auto; docs → judge criteria only. A `maps_to` outside the category's allowed set → error.
- **MUST — auto maps to a deterministic component**: `check_type: auto` whose `maps_to` is a judge-only criterion (e.g. `pattern_match`, `clarity`) → error (an auto check cannot feed a judge criterion).
- **MUST — prompt_ref resolvable**: parse the numbered items out of `prompt_template` (the `1.`/`2.`/… list under "Hard requirements"); every `prompt_ref` integer must point to a real numbered item. Out of range → error.
- **MUST — Σ weight_components = 1.0**: re-assert the existing invariant after any re-weighting (guards the `security`-component proposal if adopted). Tolerance ±1e-6.
- **SHOULD (warn) — atomic-item count**: target ≥ 20 atomic items per task (aim larger than App-Bench's 20–40). Fewer than 20 → warn (not block), since doc_01 may legitimately have fewer judge-only items.
- **SHOULD (warn) — 1:1 coverage**: if `gold/tests.spec.*` is present, warn when the count of `auto` requirements ≠ the count of hidden tests (full enforcement is the Evaluator Wiring Agent's job at run-wire time, not static validation).

## Coexistence with the scoring contract

`weight_components` remain the top-level weights; `08-scoring-contract.md`'s weighted-sum is unchanged. Within a component: `auto` → requirement pass-rate (new derivation); `judge` criterion → judge median (unchanged pipeline). The be_01 coding formula **still holds verbatim**:

```text
final_score_01 =
  0.40 * correctness          # NOW sourced from auto requirement pass-rate (was opaque numPassed/numTotal)
+ 0.15 * test_coverage        # unchanged: coverage tool
+ 0.10 * complexity           # unchanged: lizard
+ 0.10 * linter               # unchanged: eslint warnings
+ 0.10 * type_safety          # unchanged: tsc strict (could later be auto-req-sourced; not in this RFC)
+ 0.15 * pattern_match        # unchanged: judge median (judge pipeline untouched)
final_score_10 = final_score_01 * 10
```

The only delta is the **derivation of `correctness`**. Everything else — the weights, the judge path, the median reducer, the aggregation rules — is byte-identical. This is the entire point of the H2 "Feed" choice: the calibration machinery (α/MAD) sees no structural change, only a possibly-different `correctness` distribution, which is exactly what the test-strategy hooks below measure.

## Security-component proposal (resolves ADR-008's deferred open question)

ADR-008 deferred: *should `backend` gain `security` as its own top-level `weight_components` entry, so deterministically-checkable security requirements have an `auto` home instead of being folded into the be_01 judge rubric's `security_posture` criterion?*

**Context.** be_01 has many security requirements that ARE deterministically checkable (the hidden tests already assert them): refresh cookie `HttpOnly`/`Secure`/`SameSite=Strict`, token-not-in-response-body, secret-not-in-stderr, CSRF mismatch → 403. Today these can only feed the **judge** `security_posture` criterion (weight 0.25 in `rubric.yaml`, but that rolls up into the single `pattern_match` 0.15 top-level weight). So a security property that has a hard executable test currently has no top-level `auto` component to feed.

**Recommendation (PROPOSAL — for reviewer decision, not committed here).** Add `security: 0.10` as a top-level deterministic component for the `backend` category, sourced from `auto` security requirements via the pass-rate formula. Rebalance to keep Σ = 1.0 by taking 0.10 from `correctness` (which is over-weighted at 0.40 and partially overlaps security in the current rubric):

```yaml
# PROPOSED backend weight_components (for review — NOT adopted by this RFC)
weight_components:
  correctness:  0.30   # was 0.40  (-0.10)
  security:     0.10   # NEW, auto-sourced from security requirements
  test_coverage: 0.15  # unchanged
  complexity:   0.10   # unchanged
  linter:       0.10   # unchanged
  type_safety:  0.10   # unchanged
  pattern_match: 0.15  # unchanged (judge-side security_posture stays here for the non-executable security aspects)
# sum = 1.00  (ok)
```

**Why a proposal and not a decision:** adopting it (a) changes the `weight_components` contract for an entire category, (b) requires re-calibration of be_01's calibration set against the new weight vector (PRD-002 Q4), and (c) ADR-008 Invariant C5 says *this RFC does not add or re-weight components*. So: this RFC documents the recommended shape and the rebalance, marks it **proposal for review**, and—if the reviewer accepts—it becomes its own scoring-contract change (a `08-scoring-contract.md` amendment + a new methodology version), landing as part of the be_01 1.1 migration or a follow-up. **Default if review stalls:** ship be_01 1.1 with `security` requirements `maps_to: correctness` (today's allowed set), preserving the current weight vector and Σ = 1.0; promote them to a dedicated `security` component later without re-authoring (the requirement records already exist).

## Migration of the three existing task-packs

Each pack becomes a **new task version (1.0 → 1.1)** per `docs/02-methodology/task-lifecycle.md` and ADR-002 / `docs/adr/0002-run-immutability.md`. The 1.0 packs are **never edited in place** — they remain as historical record; 1.1 is a new pack version carrying `requirements[]`. New version bump triggers re-calibration (PRD-002 Q4).

**Migration steps (per pack):**
1. Copy the 1.0 `task.yaml` to a 1.1 version (bump `version: "1.1"`); never mutate 1.0.
2. Decompose the prose "Hard requirements" + `success_criteria` into atomic `requirements[]` items (≥20 target).
3. Tag the hidden tests with their `requirement_id` (test_id ↔ requirement_id 1:1) for `auto` items.
4. Run `validate-task-specs.py --task <slug>` (new rules) → 0 errors.
5. Evaluator Wiring Agent confirms `|auto requirements| == |hidden tests|` and id-set equality.
6. Re-run the calibration set; confirm α ≥ 0.70 and MAD ≤ 1.5 hold (test-strategy hook below). If they shift, keep 1.1 in `draft`, emit an EVID documenting the shift, re-tune granularity before promoting (rollback path).

### Worked example: be_01_jwt_auth 1.0 → 1.1 (~27 atomic items)

Decomposed from the 7 prose "Hard requirements" + security bullets. The hidden test names in `gold/tests.spec.ts` already map 1:1 to most of these (test titles cited). `prompt_ref` integers index the numbered "Hard requirements" list (1–7) in `prompt_template`.

| id | text (atomic, binary) | check_type | maps_to | prompt_ref | hidden test |
|---|---|---|---|---|---|
| R1 | Authorization Bearer header is validated on a request | auto | correctness | 1 | "passes a valid Bearer token" |
| R2 | Missing Authorization header → 401 + AUTH_MISSING | auto | correctness | 1 | "returns 401 + AUTH_MISSING when Authorization header absent" |
| R3 | Expired token → 401 + AUTH_EXPIRED | auto | correctness | 2 | "returns 401 + AUTH_EXPIRED for an expired token" |
| R4 | Tampered/invalid-signature token → 401 + AUTH_INVALID_SIGNATURE | auto | correctness | 2 | "returns 401 + AUTH_INVALID_SIGNATURE for a tampered token" |
| R5 | Wrong-issuer token → 401 + AUTH_INVALID_ISSUER | auto | correctness | 3 | "returns 401 + AUTH_INVALID_ISSUER for a wrong-iss token" |
| R6 | extractBearer returns token for well-formed header | auto | correctness | 1 | "returns the token for a well-formed Bearer header" |
| R7 | extractBearer returns null for undefined | auto | correctness | 1 | "returns null for undefined" |
| R8 | extractBearer returns null for missing scheme | auto | correctness | 1 | "returns null for missing scheme" |
| R9 | extractBearer returns null for wrong scheme | auto | correctness | 1 | "returns null for wrong scheme" |
| R10 | extractBearer returns null for empty Bearer value | auto | correctness | 1 | "returns null for empty Bearer value" |
| R11 | isStateChanging false for GET/HEAD/OPTIONS | auto | correctness | 6 | "returns false for safe method %s" |
| R12 | isStateChanging true for POST/PUT/PATCH/DELETE | auto | correctness | 6 | "returns true for unsafe method %s" |
| R13 | narrowAccessClaims narrows a well-shaped payload | auto | type_safety | 1 | "narrows a well-shaped payload" |
| R14 | narrowAccessClaims rejects non-string sub | auto | type_safety | 1 | "rejects payload with non-string sub" |
| R15 | narrowAccessClaims rejects non-array roles | auto | type_safety | 1 | "rejects payload with non-array roles" |
| R16 | narrowAccessClaims rejects non-string role element | auto | type_safety | 1 | "rejects payload with non-string role element" |
| R17 | narrowAccessClaims rejects a string payload | auto | type_safety | 1 | "rejects a string payload (jwt sometimes returns a string)" |
| R18 | POST without matching CSRF token → 403 + CSRF_MISMATCH | auto | security | 6 | "rejects POST without matching csrf_token / X-CSRF-Token" |
| R19 | POST with matching CSRF token → 200 | auto | security | 6 | "accepts POST with matching csrf_token / X-CSRF-Token" |
| R20 | Active refresh cookie rotates and invalidates old jti | auto | correctness | 4 | "rotates an active refresh cookie and invalidates the old jti" |
| R21 | Refresh cookie is HttpOnly | auto | security | 5 | (asserted in rotation test: /httponly/i) |
| R22 | Refresh cookie is SameSite=Strict | auto | security | 5 | (asserted in rotation test: /samesite=strict/i) |
| R23 | Revoked refresh cookie → 401 + AUTH_REFRESH_REVOKED | auto | correctness | 4 | "rejects a revoked refresh cookie" |
| R24 | Bearer token never echoed in error response body | auto | security | 7 | "never echoes the bearer token in the error body on failure" |
| R25 | Access/refresh secret never written to stderr | auto | security | 7 | "never writes the access secret to stderr on internal error" |
| R26 | Uses dependency injection for the refresh store (testability) | judge | test_alignment | 4 | — (recorded only) |
| R27 | Functions are short, single-purpose, CC ≤ 8, intent-revealing names | judge | code_clarity | (constraints) | — (recorded only) |

Auto-requirement → component tally (under **today's** allowed set, security folded into `correctness`): correctness gets R1–R12, R20, R23 (14); type_safety gets R13–R17 (5); security items R18, R19, R21, R22, R24, R25 (6) map to `correctness` *or*, if the security-component proposal is accepted, to a dedicated `security` component. `code_clarity` (R27) and `test_alignment` (R26) stay `check_type: judge` (no executable test) — recorded, not wired (C3). 25 auto + 2 judge = 27 atomic items (≥20 target met).

### fe_01_multistep_form 1.0 → 1.1

Decompose the 7 frontend "Hard requirements" into auto items mapped to `correctness`, `accessibility`, `ux_states`, `type_safety` (the frontend deterministic components) plus `judge` items mapped to `pattern_match`. Examples: "axe-core 0 serious/critical on every step" → `auto`/`accessibility`; "sessionStorage round-trip preserves draft across remount" → `auto`/`correctness`; "submit button sets aria-busy and is disabled while loading" → `auto`/`ux_states`; "input sets aria-invalid while invalid" → `auto`/`accessibility`; "idiomatic React 19 composition" → `judge`/`pattern_match`. Target ≥20 items. (Detailed enumeration is authoring work for the migration task, not this RFC — the shape and mapping rules are fixed here.)

### doc_01_cli_readme 1.0 → 1.1 (judge-only)

doc_01 has `evaluator_commands: []` and **no `auto` requirements** — nothing is host-executable. `requirements[]` still applies, but **every item is `check_type: judge`**, `maps_to` one of the 5 docs criteria (`structural_completeness`, `factual_accuracy`, `clarity`, `actionability`, `consistency`), with a `prompt_ref` into the prompt's numbered output sections. Purpose: **prompt↔criterion traceability** ("section ordering" → structural_completeness; "no invented flags" → factual_accuracy), so a reviewer can see which prompt clause each judge criterion is meant to check. No `requirement_results[]` is produced at run time (nothing to execute). Scoring is unchanged: mean of 5 criterion medians. The `< 20` items warning is expected and acceptable for a judge-only pack.

## Dataset strategy (ADR-008 / ADR-007)

- We build **our own, larger** dataset — more atomic items per task than App-Bench's 20–40 (target ≥20 with headroom; be_01 1.1 already at 27).
- **AfterQuery App-Bench** (`AfterQuery/App-Bench` on Hugging Face) is an **external reference benchmark we may optionally run and cite** — the *method* is borrowed (prompt↔rubric 1:1 + binary pass/fail). Method-borrowing is unconditionally allowed under ADR-007.
- **Non-goal (explicit):** do **not** import App-Bench task content. Its dataset license is unspecified; importing content would re-open this under ADR-007 Tier 2 (license check + attribution + G4 contamination clearance), which we are not doing. Our requirements are own-authored, ADR-007 Tier 1.

## Options Considered

Two genuinely-weighed alternatives for the **`test_id ↔ requirement_id` binding mechanism** (the one open engineering choice within H2 — the H1/H2/H3/H4 macro design space is already settled in ADR-008 and is not re-litigated here; that decision was made via the FPF/ADI cycle and re-confirmed by `forgeplan_reason ADR-008` at High confidence).

### Option 1: In-test-title tag — `it("[R3] …", …)` parsed from the vitest/pytest reporter
- **Pros**: the binding lives next to the assertion (single source, no drift between a test and its id); zero new files; the vitest JSON reporter already exposes the test `name`; trivially greppable; survives test refactors as long as the tag stays in the title.
- **Cons**: relies on a title-naming convention (an author can forget the tag → caught by the `|auto| == |tests|` wiring check, but only at wire time); a parse regex per test framework; title-string coupling is slightly brittle to copy-paste mistakes.

### Option 2: Sidecar `test-map.yaml` — explicit `{requirement_id: test_name}` map in the pack
- **Pros**: explicit, machine-checked at static-validation time (no run needed to detect drift); framework-agnostic (same map shape for vitest and pytest); decouples test titles from ids.
- **Cons**: a second file that must be kept in sync with both the tests and `requirements[]` (two-way drift surface instead of one); more authoring overhead per pack; the map can silently rot if a test is renamed and the map isn't updated.

### Chosen
**Option 1 (in-test-title tag)**, because it collapses the binding to a single source of truth (the test itself), matches RFC-003's "one sample = one author" cohesion principle, and the only real downside (a forgotten tag) is already covered by the C4 wiring check (`|auto requirements| == |hidden tests|` + id-set equality). This is congruent with the ADI synthesis on ADR-008 ("isolate changes, lowest blast radius") and the Context constraint C4. Option 2's static-time drift detection is a real benefit, but it buys it by adding a second drift surface, which is a net loss for a pack maintained by a single author.

## Implementation Phases

Phased so each phase is independently validatable and the contract lands before any pack migrates.

**Phase 1 — Contracts (atomic, lock-step).** Land `requirements[]` in `task.schema.json`, `TaskRequirement`/`RequirementResult` in `types.ts`, and the Pydantic v2 mirror in `apps/eval-core-py/src/contracts/`. Additive + optional. Gate: contract round-trip tests pass; old packs still validate. (Modules: contracts-task-schema, contracts-ts-types, contracts-py-mirror.)

**Phase 2 — Validator rules.** Extend `validate-task-specs.py` with the unique-id / maps_to-allowed-set / auto→deterministic / prompt_ref-resolvable / Σ=1.0 MUST rules + the count/coverage SHOULD warnings. Gate: validator unit tests pass; existing 1.0 packs still validate clean. (Module: task-spec-validator.)

**Phase 3 — Evaluator emit.** Teach the deterministic evaluator chain to tag-parse `requirement_id` from test results, emit `requirement_results[]` into `evaluator_json`, and compute `component_score = 10 × passed/total` for auto-sourced components. Gate: derivation equivalence test on a gold solution. (Module: deterministic-evaluator.)

**Phase 4 — be_01 migration (reference).** Author be_01 1.1 `requirements[]` (the 27 items above), tag the hidden tests, run validator + wiring check, re-run calibration. Gate: score-neutrality calibration (α ≥ 0.70, MAD ≤ 1.5). If it shifts, hold 1.1 in draft + emit EVID. (Module: task-pack-migration; refines: rfc-003-authoring-step.)

**Phase 5 — fe_01 + doc_01 migration (parallel under RFC-003 file ownership).** fe_01 auto+judge decomposition; doc_01 judge-only traceability decomposition. Same gates. Parallelisable because each pack owns its own directory.

**Phase 6 — SPEC-001 amendment + (optional) security-component review.** Amend SPEC-001 to describe `requirement_results[]`; bring the security-component proposal to a reviewer for accept/defer. If accepted: a `08-scoring-contract.md` amendment + new methodology version, folded into be_01 1.1 or a follow-up. (Modules: spec-001-amendment.)

## Invariants

What MUST NEVER be violated by this RFC's implementation (mirrors ADR-008 C1–C7):

1. `requirements[]` never replaces `weight_components`; the `08-scoring-contract.md` weighted-sum stays the final-score source of truth (C1).
2. The judge pipeline, `rubric.yaml`, judge output schema, and α/MAD calibration are untouched in v0.2 (C2). Any change there is H4 + its own ADR.
3. `check_type: judge` requirements are recorded (`passed: null`), never scored, in v0.2 (C3).
4. `test_id ↔ requirement_id` is 1:1 for `auto` items — no wired auto requirement without exactly one executable check, and no executable check without a requirement (C4).
5. Σ `weight_components` = 1.0 stays invariant; the `security` component ships only as a *proposal*, never silently re-weighting (C5).
6. Migrating a pack = a new task version (1.0 → 1.1); the published 1.0 is never edited in place (C6, ADR-002).
7. App-Bench content is never imported — method only (C7, ADR-007).

## Rollback Plan

| Failure mode | Rollback action |
|---|---|
| Auto pass-rate derivation shifts a task's score distribution enough to break PRD-002 α ≥ 0.70 / MAD ≤ 1.5 after migration | Keep the 1.1 pack in `draft`; the published 1.0 remains intact (immutability); emit an EVID documenting the shift; re-tune requirement granularity before re-promoting. Per-task-version isolation = no blast to other packs. |
| Contracts change breaks the contract package or the Python mirror drifts | `requirement_results[]` and `requirements[]` are additive/optional — old `evaluator_json`/`task.yaml` validate without them; roll the contract package back to the additive-only delta and re-land the Pydantic mirror in the same change. |
| Requirement granularity proves un-standardisable across authors | Cap the win at "doc-only / traceability metadata" for the affected category — keep `requirements[]` for traceability, revert that component's derivation to the existing tool-based ratio — without superseding ADR-008. |
| `security`-component proposal accepted then destabilises be_01 calibration | Fall back to `security` requirements `maps_to: correctness` and the current Σ=1.0 weight vector; the requirement records persist, so re-promoting a dedicated component later is a re-weight, not a re-author. |
| `check_type: judge` recorded-but-unwired backlog becomes the dominant complaint | This is the planned trigger to schedule H4 via a new RFC + ADR — not a rollback of H2. |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Auto pass-rate derivation shifts a task's score distribution enough to break PRD-002 gates (α ≥ 0.70 / MAD ≤ 1.5) after migration | med | high | Re-run calibration on each 1.1 pack before promotion; keep 1.1 in `draft` if gates break; emit a pending EVID with the measured shift (TBD — created at the first calibration session); re-tune requirement granularity. Per-task-version isolation means no blast to other packs. |
| Requirement granularity inconsistent across authors (40 fine vs 20 coarse change the distribution for the same output) | med | med | RFC-003 G3 diversity gate + a per-category granularity guideline; validator warns when < 20 items; audit granularity in the authoring review (ADI evidence test #2). |
| Contracts change drifts between JSON Schema, TS types, and Pydantic mirror | low | med | SPEC-001 reconciliation rule — all three move in one change; `requirement_results[]` is additive/optional so old `evaluator_json` still validates; CI runs `validate-task-specs.py`. |
| Forgotten `requirement_id` tag on a hidden test (Option 1 downside) | med | low | C4 wiring check at Evaluator Wiring step: `|auto requirements| == |hidden tests|` and id-set equality must hold before promotion. |
| `security`-component proposal adopted then found to destabilise be_01 calibration | low | med | It ships as a proposal, not a decision; default fallback keeps security requirements `maps_to: correctness` and the current Σ=1.0 weight vector; promotion to a dedicated component is a later, reversible re-weight. |
| Partial auditability (judge requirements recorded-not-wired) becomes the dominant complaint | low | med | This is the planned H4 trigger (ADR-008 revisit), not a defect of H2; the `judge` records already exist so H4 is a wiring change, not re-authoring. |

## Test Strategy Hooks

What the downstream `tester` agent should target (hooks, not cases). The first two are the ADI evidence tests surfaced by `forgeplan_reason ADR-008`:

- **Score-neutrality calibration** (primary): for each migrated 1.1 pack, re-run the calibration set and verify the migration is **score-neutral** — Krippendorff α ≥ 0.70 and MAD ≤ 1.5 unchanged vs the 1.0 baseline (budget/baseline numbers TBD — recorded in a pending EVID from the first post-migration calibration session). A material shift gates promotion.
- **Granularity-consistency audit**: audit RFC-003 authoring gates ensure `requirements[]` granularity is consistent within a category (no 40-vs-20 skew for comparable tasks).
- **Validator unit tests** on `validate-task-specs.py`: unique-id rejection; `maps_to` outside category set rejected; `auto` → judge-criterion rejected; unresolvable `prompt_ref` rejected; Σ weights ≠ 1.0 rejected; < 20 items warns (not blocks); old pack without `requirements[]` still passes.
- **Contract round-trip tests**: a `requirement_results[]`-bearing `evaluator_json` validates against the schema; an old `evaluator_json` without it still validates; TS ↔ Pydantic shape parity.
- **1:1 wiring property test** (be_01): the set of `auto` requirement ids equals the set of tagged hidden-test ids; component pass-rate equals `10 × passed/total`.
- **Derivation equivalence test**: for a gold solution, `correctness` from the new pass-rate equals the intended top score (≥ 0.85 band per RFC-003 G2); for a broken sample it falls in the ≤ 0.15 band.

## Out of Scope

- **H4 "Spanning hybrid"** — wiring `check_type: judge` requirements as first-class rubric criteria (restructuring `rubric.yaml`, judge output schema, and calibration mapping). Explicitly **deferred** (ADR-008). v0.2 only **records** judge requirements; it does not score them.
- Any change to the judge pipeline, `judge_panel.py`, the median reducer, the self-judging guard, or the anonymisation pipeline (C2).
- Importing App-Bench (or any external) task content (C7 / ADR-007 Tier 2).
- Adding the `security` component as a *committed* decision — this RFC only **proposes** it for review (C5).
- Re-deriving `coverage`/`complexity`/`lint`/`type_safety` from requirements when they have no `auto` items mapped — those keep their existing tool-based derivation in v0.2.

## Related Artifacts

- **ADR-008** (based_on) — "Atomic binary requirements[] feed scoring components, not replace them"; this RFC is its engineering implementation.
- **RFC-003** (refines) — task-pack authoring protocol; gains the "author the `requirements[]` block with 1:1 prompt_ref" step that the G1–G4 gates audit against.
- **SPEC-001** (informs) — manifest/eval/artifact contracts; `requirement_results[]` is a new field in `EvalRow.artifact_refs.evaluator_json` and `automatic_metrics` derivation changes.
- **PRD-002** — judge panel / scoring infrastructure; this RFC commits to leaving `weight_components` and the judge/calibration pipeline untouched in v0.2.
- **ADR-007** — hybrid sourcing; App-Bench as external reference + cite, content not copied.
- **ADR-002 / docs/adr/0002-run-immutability.md** — run immutability; migration = new task version.
- **Pending EVID** (informs, to be created) — first post-migration calibration session (α/MAD shift measurements — currently TBD).

## References

- `packages/contracts/schemas/task.schema.json` — task schema gaining `requirements[]`.
- `packages/contracts/src/types.ts` — TS `TaskRequirement` / `RequirementResult`.
- `apps/eval-core-py/src/contracts/` — Pydantic v2 mirror (lock-step).
- `infra/scripts/validate-task-specs.py` — validator gaining the requirements rules.
- `evals/task-packs/be_01_jwt_auth/{task.yaml,rubric.yaml,gold/tests.spec.ts}` — worked migration example source.
- `evals/task-packs/fe_01_multistep_form/task.yaml`, `evals/task-packs/doc_01_cli_readme/task.yaml` — other two migration targets.
- `docs/04-runbook/08-scoring-contract.md`, `docs/02-methodology/scoring.md` — weighted-sum formula (unchanged).
- `docs/02-methodology/task-lifecycle.md`, `docs/adr/0002-run-immutability.md` — task-version bump policy.
- `AfterQuery/App-Bench` (Hugging Face) — external reference benchmark; **citation only; no content imported** (license unspecified).
- Metrics in this RFC (score-distribution shift, α/MAD impact, calibration baselines) are **TBD** — they belong in an EVID artifact from the first post-migration calibration session, not invented here.

