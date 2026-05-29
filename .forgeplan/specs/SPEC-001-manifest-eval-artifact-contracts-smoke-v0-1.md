---
depth: standard
id: SPEC-001
kind: spec
last_modified_at: 2026-05-23T20:54:53.689603+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: refines
status: active
title: manifest + eval + artifact contracts (smoke v0.1)
---

# SPEC-001: manifest + eval + artifact contracts (smoke v0.1)

## Overview

Канонические contracts для трёх центральных сущностей smoke run: **Manifest** (snapshot всего run'а), **Eval** (одна `(model, task, seed)` точка), **Artifact** (content-addressed output). Опирается на Inspect AI's `EvalLog` (см. EVID-004), но добавляет immutability envelope и cost attribution, которых в Inspect нет.

## Reconciliation note (2026-05-23)

Per architect-reviewer finding #3: `packages/contracts/schemas/run-manifest.schema.json` существовал как thin v1 schema (`schema_version: pollmevals.run_manifest.v1`) и расходился с этим SPEC. Reconciliation: on-disk schema bumped к `v1.0.0` (rich) и aligned с этим SPEC. SPEC-001 = canonical contract; on-disk schema = enforcement. Любые изменения вносятся в обе стороны (или amend SPEC и regenerate on-disk).

## Scope

- ✅ Schemas для manifest.json, eval row, artifact metadata
- ✅ Naming conventions: content-addressed paths (R2 layout + local-cache layout)
- ✅ Required vs optional fields
- ✅ Version pin requirements (что обязательно в каждом manifest)
- ✅ Mapping Inspect AI EvalLog → POLLMEVALS Manifest
- ✅ RunAggregates definition (inline below — addresses architect finding #2)
- ❌ JudgePanel schema (PRD-002)
- ❌ Leaderboard query API (PRD-004)
- ❌ Database migrations (RFC-001 detail)

## Data Models

Три модели данных, реализованные как JSON Schema в `packages/contracts/schemas/run-manifest.schema.json` (canonical on-disk) и как Pydantic v2 классы в `apps/eval-core-py/src/contracts/`.

### Manifest schema (JSON, frozen v0.1.0)

`packages/contracts/schemas/run-manifest.schema.json` (schema_version: `pollmevals.run_manifest.v1.0.0`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "POLLMEVALS Run Manifest v0.1.0",
  "type": "object",
  "required": ["schema_version", "run_hash", "run_type", "methodology_version", "created_at", "stack_pins", "model_pins", "task_pins", "seed_set", "evals", "aggregates", "status"],
  "properties": {
    "schema_version": {"const": "pollmevals.run_manifest.v1.0.0"},
    "run_hash": {"pattern": "^sha256:[a-f0-9]{64}$"},
    "run_type": {"enum": ["smoke", "weekly", "flagship_triggered", "calibration", "ablation"]},
    "methodology_version": {"const": "v0.1.0"},
    "created_at": {"format": "date-time"},
    "published_at": {"format": "date-time"},
    "region": {"enum": ["eu-central"]},
    "stack_pins": {"items": "$ref #/$defs/StackPin"},
    "model_pins": {"items": "$ref #/$defs/ModelPin"},
    "task_pins": {"items": "$ref #/$defs/TaskPin"},
    "seed_set": {"items": "integer", "minItems": 1},
    "evals": {"items": "$ref #/$defs/EvalRow"},
    "aggregates": {"$ref": "#/$defs/RunAggregates"},
    "status": {"enum": ["created", "executing", "evaluating", "aggregating", "published", "degraded"]},
    "inspect_eval_log_sha256": {"pattern": "^[a-f0-9]{64}$"},
    "inspect_ai_version": {"description": "pinned exact in pyproject.toml"},
    "orchestrator_version": {"description": "pollmevals git tag at run time"}
  }
}
```

### StackPin / ModelPin / TaskPin

```json
"StackPin": {
  "required": ["stack_id", "stack_version", "stack_yaml_sha256"]
}

"ModelPin": {
  "required": ["model_id", "provider_id", "provider_route_id", "pricing_snapshot"],
  "pricing_snapshot": {
    "required": ["input_per_mtoken_usd", "output_per_mtoken_usd", "snapshot_at"],
    "description": "Frozen at run start. Closes industry gap (HELM/SWE-bench) per EVID-001/EVID-005."
  }
}

"TaskPin": {
  "required": ["task_id", "task_version", "task_pack_sha256"],
  "task_pack_sha256": "sha256(prompt + evaluator + gold) — content-addressed, divergence from lm-eval-harness integer versioning (EVID-003)"
}
```

### EvalRow schema

```json
"EvalRow": {
  "required": ["eval_id", "model_id", "stack_id", "task_id", "seed", "status", "artifact_refs", "stats"],
  "properties": {
    "eval_id": "sha256(run_hash + model_id + stack_id + task_id + seed)[:16]",
    "status": {"enum": ["pending", "running", "scored", "failed", "skipped"]},
    "error_class": {"enum": [null, "network", "rate_limit", "5xx_server", "4xx_client", "timeout", "contract_violation", "sandbox_failure"]},
    "artifact_refs": {
      "required": ["raw_output", "normalized_output", "evaluator_json"],
      "optional": ["stdout", "stderr", "trace_json"]
    },
    "final_score": "null in smoke; PRD-002+ = median of judge panel",
    "automatic_metrics": "task-specific (be_01: test_pass_rate/lint_errors/complexity/coverage; doc_01: structural_completeness/link_validity)",
    "stats": {
      "required": ["input_tokens", "output_tokens", "wall_clock_ms", "cost_usd"],
      "cost_usd": "POLLMEVALS layer — Inspect doesn't track (EVID-004)"
    }
  }
}
```

### ArtifactRef schema

```json
"ArtifactRef": {
  "required": ["sha256", "size_bytes", "uri", "mime_type"],
  "uri": "v0.1 local: file://artifacts/runs/{run_hash}/evals/{eval_id}/{type}-{sha256}.{ext}; v0.2+ R2: s3://pollmevals-runs/..."
}
```

### RunAggregates schema (addresses architect finding #2)

Computed at status=aggregating step. Closes FR-006 gap noted by architect-reviewer #2 — until this section was added, the manifest had an undefined `$ref` (`#/definitions/RunAggregates`).

```json
"RunAggregates": {
  "required": ["counts_by_status", "total_cost_usd", "total_wall_clock_ms"],
  "properties": {
    "counts_by_status": {
      "required": ["scored", "failed", "skipped"],
      "properties": {
        "pending": "integer >=0",
        "running": "integer >=0",
        "scored": "integer >=0",
        "failed": "integer >=0",
        "skipped": "integer >=0"
      },
      "description": "Sum MUST equal len(evals[]) — invariant for FR-009 (failed evals not dropped)"
    },
    "counts_by_error_class": {
      "description": "Distribution of error_class values among failed evals. Mirrors EvalRow.error_class enum. Smoke postmortem reads this directly."
    },
    "total_cost_usd": {
      "type": "number",
      "minimum": 0,
      "description": "Sum of evals[].stats.cost_usd. Compared with LiteLLM proxy /credits cross-check per RFC-001 (delta > 10% → alert)."
    },
    "total_wall_clock_ms": {
      "type": "integer",
      "description": "Sum of evals[].stats.wall_clock_ms. NOT wall clock of run (which may be shorter due to concurrency=3)."
    },
    "per_task_metrics": {
      "description": "Map task_id → {automatic_metric_key → {mean, median, p95, sample_count}}. For smoke (no judges) — only automatic_metrics aggregates here. Judges layer (PRD-002) will add final_score median + Krippendorff α as additional keys."
    },
    "budget_breach": {
      "type": "boolean",
      "description": "True if total_cost_usd > NFR-001 cap ($50 for smoke). When true, status transitions to `degraded` not `published`."
    },
    "available_models_count": {
      "type": "integer",
      "description": "Number of distinct model_ids with at least one scored eval. Drives status=degraded transition (< 3 → degraded per PRD-003 weekly policy, ≥ 3 OK for smoke)."
    }
  }
}
```

## API Contracts

Public surfaces consuming these data models:

| Surface | Consumer | Contract |
|---------|----------|----------|
| `apps/eval-core-py` writes manifest | local + R2 storage | JSON conformant to `manifest.schema.json`, status state machine respected |
| `apps/api` reads manifest | site SSG + future query endpoints | read-only; manifest hash MUST be verified before exposing |
| `infra/scripts/reproduce-local-run.sh` | maintainer CLI | reads manifest by run_hash, returns 0 if reproduce passes, 2 if drift detected |
| LiteLLM proxy ↔ orchestrator | inter-process | model_id format `provider/model-name` (Inspect AI convention per EVID-004) |

State machine для `status` — only allowed transitions:
```
created → executing → evaluating → aggregating → published
                                              ↘ degraded (if budget_breach || available_models_count < 3)
```
`published` and `degraded` terminal. No backwards transitions. **Crash recovery** между этими переходами — per NOTE-001 (append-only journal + atomic rename + `make resume`).

## Naming conventions

```
artifacts/runs/{run_hash}/
├── manifest.json                                          # this schema
├── manifest.journal.ndjson                                # crash-recovery append-only log (NOTE-001)
├── inspect.eval                                           # Inspect AI's binary log (parallel)
└── evals/{eval_id}/
    ├── raw_output-{sha256}.txt
    ├── normalized_output-{sha256}.txt
    ├── evaluator_json-{sha256}.json
    ├── stdout-{sha256}.txt
    ├── stderr-{sha256}.txt
    └── trace_json-{sha256}.json
```

R2 layout (v0.2+) повторяет ту же форму под `s3://pollmevals-runs/`.

## Mapping Inspect AI EvalLog → POLLMEVALS Manifest

| POLLMEVALS Manifest field | Inspect AI EvalLog field | Notes |
|---|---|---|
| `run_hash` | (not in Inspect) | Computed by POLLMEVALS wrapper |
| `methodology_version` | `eval.metadata.methodology_version` | Custom metadata at run start |
| `stack_pins[].stack_id` | `eval.task` | Inspect Task name carries stack identity |
| `model_pins[]` | `eval.model` | POLLMEVALS adds provider routing + pricing |
| `model_pins[].pricing_snapshot` | (not in Inspect) | POLLMEVALS layer (EVID-004 gap) |
| `task_pins[]` | `eval.dataset` | POLLMEVALS adds content-addressed task pack hash |
| `evals[]` | `samples[]` | 1:1 mapping |
| `evals[].stats.cost_usd` | (not in Inspect) | Computed POLLMEVALS-side |
| `evals[].artifact_refs.raw_output` | `sample.output.completion` | POLLMEVALS extracts and content-addresses |
| `aggregates` | (not in Inspect) | POLLMEVALS computes at status=aggregating |
| `status: published` | (not in Inspect — soft-immutable) | Hard-immutable: chmod 0444 |
| `inspect_eval_log_sha256` | SHA256(`inspect.eval` file) | Cross-reference back to canonical Inspect log |

## Version pinning — MANDATORY in every manifest

Cannot publish (status → `published`) без ALL of:

- `methodology_version` (const `v0.1.0`)
- `inspect_ai_version` (exact semver per RFC-001 RR-1)
- `orchestrator_version` (pollmevals git tag)
- `stack_pins[].stack_yaml_sha256` для каждого stack
- `task_pins[].task_pack_sha256` для каждой task
- `model_pins[].pricing_snapshot` для каждой model
- `seed_set` (explicit list)
- `aggregates.counts_by_status` (sum MUST equal len(evals[]))

Missing any → manifest rejected by validator; status stays `aggregating` until fixed.

## Acceptance Criteria

| ID | Scenario |
|----|----------|
| AC-1 | Given a frozen methodology v0.1.0 and 45 evals completed, when orchestrator writes manifest.json, then JSON Schema validation passes with 0 errors |
| AC-2 | Given a published manifest, when a process attempts to mutate any field, then write fails (file mode 0444 / R2 object-lock) |
| AC-3 | Given manifest.json and inspect.eval, when reproducer reads both, then for every eval_id the sha256 of raw_output matches the SHA256 in artifact_refs |
| AC-4 | Given a model with missing pricing_snapshot, when orchestrator tries to mark run as `published`, then status stays `aggregating` and error is logged |
| AC-5 | Given a failed eval (status=failed, error_class=rate_limit), when manifest is published, then eval_id is present in evals[] (NOT dropped) and aggregates.counts_by_status.failed += 1 |
| AC-6 | Given orchestrator crash mid-eval, when `make resume HASH=<x>` is invoked, then journal is loaded, missing eval_ids identified from grid, only those re-scheduled (per NOTE-001) |

## Related Artifacts

- PRD-001 (parent — refines this PRD's contracts)
- EPIC-001 (grandparent)
- RFC-001 (implementation plan that uses these contracts)
- NOTE-001 (crash recovery — manifest.journal.ndjson is part of this schema family)
- EVID-001 HELM, EVID-003 LM Harness, EVID-004 Inspect AI, EVID-005 SWE-bench
- EVID-007 (architect-reviewer audit — finding #2 RunAggregates undefined → addressed in this revision)
- `docs/adr/0002-run-immutability.md` (legacy — foundation для `published` terminal state)
- `packages/contracts/schemas/run-manifest.schema.json` (canonical on-disk, v1.0.0 — aligned with this SPEC)






