# 10 — Run Manifest and Artifacts

## Run manifest purpose

A run manifest is the reproducibility root. It must allow another engineer to understand what was executed, with which versions, which tasks, which models, which seeds and which artifacts.

## Required manifest fields

```json
{
  "schema_version": "pollmevals.run-manifest.v1",
  "run_hash": "sha256...",
  "run_type": "smoke",
  "created_at": "2026-05-23T00:00:00Z",
  "methodology_version": "0.1.0",
  "orchestrator_version": "0.1.0",
  "worker_image_hash": "sha256...",
  "evaluator_image_hash": "sha256...",
  "inspect_ai_version": "pinned",
  "litellm_version": "pinned",
  "models_snapshot_uri": "...",
  "tasks_snapshot_uri": "...",
  "stacks_snapshot_uri": "...",
  "pricing_snapshot_uri": "...",
  "seed_list": [1, 2, 3, 4, 5],
  "regions": ["eu-central"],
  "evals": []
}
```

## Artifact types

| Artifact | Meaning |
|---|---|
| `raw_output` | exact model/stack output before normalization |
| `normalized_output` | output after signature stripping and formatting |
| `patch` | repository patch produced by agentic stack |
| `stdout` | sandbox stdout |
| `stderr` | sandbox stderr |
| `evaluator_json` | machine-readable evaluator result |
| `trace_json` | tool/model/file trace |
| `judge_reasoning` | judge rationale if stored |
| `reproduce_script` | script to replay run or eval |

## Artifact naming

```text
runs/{run_hash}/evals/{eval_id}/{artifact_type}-{sha256}.{ext}
```

## Storage rule

Artifacts are immutable. If an artifact is wrong, do not overwrite it. Create a new run or a new artifact with a new hash and link the correction.

## Reproduction rule

Each public run must eventually expose:

- manifest JSON;
- task snapshot;
- model snapshot;
- stack snapshot;
- pricing snapshot;
- reproducibility script;
- environment lockfiles;
- raw outputs where legally safe.
