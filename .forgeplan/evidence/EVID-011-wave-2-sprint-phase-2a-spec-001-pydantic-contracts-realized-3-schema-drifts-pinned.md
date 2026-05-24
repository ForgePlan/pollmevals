---
depth: standard
id: EVID-011
kind: evidence
last_modified_at: 2026-05-24T07:28:39.696731+00:00
last_modified_by: claude-code/2.1.150
links:
- target: SPEC-001
  relation: informs
status: active
title: 'Wave 2 (sprint phase-2A): SPEC-001 — Pydantic contracts realized + 3 schema drifts pinned'
---

# EVID-011: Wave 2 — SPEC-001 Pydantic contracts realized + 3 schema drifts pinned

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "is Pydantic v2 compatible with on-disk JSON Schema 1:1?")

- **H1**: Pydantic v2 `model_dump_json()` output validates 1:1 against the on-disk JSON Schema for all our Manifest fields — no serialization-boundary coercion needed.
- **H2**: Pydantic v2 introduces specific drift cases (Decimal serialization, optional `None` handling, datetime nullability) that the on-disk schema doesn't model identically; coercion layer needed at the writer boundary.
- **H3**: The on-disk JSON Schema should be reshaped (use `anyOf: [{$ref:...}, {type:"null"}]` for optional fields, accept string-or-number for Decimal) to match Pydantic's natural output — Pydantic stays unchanged.

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 | `jsonschema.validate(json.loads(Manifest(...).model_dump_json()), on_disk_schema)` passes for a fully-populated Manifest | TestSchemaRoundTrip without any coercion helper |
| H2 | Same test fails on 1+ specific drift cases; at least Decimal serialization fails because Pydantic dumps `Decimal("0.001")` as JSON string `"0.001"` but schema says `"type": "number"` | Run the test, observe ValidationError with specific JSON pointer |
| H3 | Relaxed schema validates BOTH "type":"number" and "type":"string" for Decimal fields; this weakens the schema's discriminating power but eliminates coercion | Would require schema rewrite + tests against the relaxed schema |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (no drift) | Round-trip test ran without coercion → `jsonschema.ValidationError` at `aggregates/total_cost_usd: '0' is not of type number` | Drift exists — at minimum on Decimal | **H1 REFUTED** |
| Y2 (drift exists, coercion needed) | TestSchemaRoundTrip identified **three distinct drift classes**: (a) Decimal-as-string (5 cost/pricing fields), (b) optional ArtifactRef fields `stdout/stderr/trace_json` with None value vs schema requiring object, (c) `started_at`/`completed_at`/`published_at` None value vs schema requiring string. Coercion helpers `_to_json_number` + `model_dump(exclude_none=True)` make round-trip pass. | All 3 drifts confirmed + fix path validated | **H2 SUPPORTED** |
| Y3 (relax schema instead) | Considered but rejected: relaxing schema makes it accept e.g. `"cost_usd": "not_a_number"`-style strings (any string passes "type":"string") — weakens consumer's ability to reject garbage. Coercion at writer boundary preserves strict schema for downstream consumers (reproducer, leaderboard build). | Schema strictness preserved; complexity moved to writer (Wave 3 manifest-writer) | **H3 REJECTED** (valid but trades safety for convenience) |

**Surviving hypothesis**: H2 — drift exists, coercion layer at writer required, schema stays strict. Implemented in Wave 3 manifest-writer (EVID-013).

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| Manifest 12/12 required fields match on-disk schema exactly | 9 | 9 | 9 | 27/27 | F: explicit `test_required_fields_pin` assertion. G: 12/12 enumerated. R: reproducible `pytest` test. |
| All 5 Pydantic sub-models present (PricingSnapshot, StackPin, ModelPin, TaskPin, ArtifactRef, EvalArtifactRefs, EvalStats, EvalRow, CountsByStatus, RunAggregates, Manifest) | 9 | 9 | 9 | 27/27 | F: import test exercises every class. G: 11 classes named. R: deterministic import / type check. |
| 95 tests collected, 94 PASS + 1 skip (AC-6 → Wave 3) | 8 | 9 | 9 | 26/27 | F: explicit pytest counts. G: precise breakdown. R: `pytest` reproducible. |
| 3 drift classes identified with concrete examples | 9 | 9 | 8 | 26/27 | F: each drift has named test + pointer to schema location. G: precise (which field, which Pydantic output vs schema requirement). R: reproducible by anyone running the failing test. |
| `frozen=True` + `extra="forbid"` enforced on all BaseModel | 8 | 8 | 9 | 25/27 | F: explicit ConfigDict. G: tested for mutation rejection. R: Pydantic v2 standard behavior. |
| mypy --strict 0 issues on contracts + tests (7 files) | 9 | 8 | 9 | 26/27 | F: --strict is most rigorous. G: "0 issues, 7 files". R: deterministic. |
| Decimal precision preserved in-memory (not float drift) | 8 | 7 | 8 | 23/27 | F: Decimal type enforced. G: not all numeric paths tested for precision (only round-trip). R: well-known Python behavior. |

**Decision strength**: average sum = 25.7/27 (95%). Strongest layer in graph. Two 27/27 claims (required fields pin + sub-model coverage). Weakest is Decimal precision (23/27) — improves to 26/27 in Wave 3 EVID-013 with explicit precision-tolerance test.

## Wave summary

- **Sprint**: phase-2A, **Wave**: 2 of 5 (sequential: Agent 4 then Agent 5 due to test→model dependency)
- **Workers**: `contracts` (532 LOC), `contracts-tests` (1064 LOC) — agents-core:coder
- **Files** (~1596 LOC): 5 contract modules + 1 __init__.py + 1 test file (95 tests, 7 classes)
- **Pipeline gates**: pytest 94/95 PASS (1 skip — AC-6 to Wave 3), mypy --strict ✓ (0 issues, 7 files), ruff ✓

## Acceptance criteria validation (SPEC-001)

- ✓ AC-1 (45 evals + schema validation): test_schema_round_trip with full_manifest produces 0 ValidationError
- ✓ AC-2 (published manifest mutation fails): `m.status = X` raises `ValidationError` (frozen=True)
- ✓ AC-3 (sha256 of raw_output matches artifact_refs): test_artifact_ref_round_trip — sha256 regex enforced
- ✓ AC-4 (model_pin missing pricing_snapshot fails): test_model_pin_missing_pricing_snapshot_raises
- ✓ AC-5 (failed eval in evals[] + counts_by_status.failed += 1): test_aggregates_with_failed_evals
- ⏭ AC-6 (journal recovery): explicit `pytest.skip()` — Wave 3 EVID-012 covers

## Conclusions

- **Surviving hypothesis**: H2 (drift coercion at writer boundary; schema stays strict)
- **Decision strength**: 95% — graph's strongest sub-layer
- **Follow-up evidence needed**: production-data precision validation in Phase 2B (real LLM cost numbers test Decimal precision in non-trivial ways)

## Related Artifacts

- SPEC-001 (informs — auto-linked; this is implementation receipt)
- PRD-001 SC-2/SC-3 backed by frozen Pydantic models
- EVID-007 architect finding #3 (schema drift originally flagged at coarser granularity) — this EVID extends with 3 specific drift sub-cases
- EVID-013 (Wave 3 — resolved all 3 drifts at writer boundary)
- ADR-0002 legacy (immutability — `frozen=True` + chmod 0o444 in Wave 3 = both layers honored)
- NOTE-002 (Evidence Quality Standard — retrofit)


