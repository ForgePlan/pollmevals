# 05 — Domain Model

## Core entities

| Entity | Meaning |
|---|---|
| `Model` | LLM identity: vendor, version tag, context, output limit, open/closed status |
| `ModelProvider` | Where/how model is served: OpenRouter, Cerebras, Runpod, Ollama, direct API |
| `Stack` | Model plus scaffolding layers: CLI, tools, skills, memory, validator, framework |
| `Task` | Versioned evaluation task with prompt, evaluator, gold, calibration variants |
| `Run` | Immutable evaluation campaign with deterministic hash and frozen snapshots |
| `Eval` | One model/stack/task/seed/region execution result |
| `Artifact` | Raw output, normalized output, logs, traces, patches, evaluator output |
| `Judgment` | One judge model’s scoring of one normalized submission |
| `CalibrationRun` | Judge performance on known-scored samples |
| `DatasetExport` | Published parquet/jsonl/tarball dataset for public or pro access |
| `Proposal` | Community-submitted model/task/stack candidate |
| `Disclosure` | Sponsored/conflict-of-interest/public methodology disclosure |

## Important relationships

```text
Run 1..N Eval
Eval N..1 Model
Eval N..1 Task
Eval N..0/1 Stack
Eval 1..N Artifact
Eval 0..N Judgment
Judgment N..1 JudgeModel
Task 1..N TaskVersion
Stack 1..N StackAdapterVersion
Run 1..1 MethodologyVersion
Run 1..1 PricingSnapshot
```

## Immutability rule

After a run is completed:

- no eval result can be edited;
- no score can be patched in place;
- no artifact can be overwritten;
- no pricing snapshot can be changed;
- no model version tag can be retroactively altered.

If there is a bug, create a new run and link it to the faulty run as superseding evidence.

## Run identity

A run hash must include:

- methodology version;
- task snapshot;
- model snapshot;
- stack snapshot;
- pricing snapshot;
- seed list;
- region list;
- orchestrator version;
- worker image hash;
- evaluator image hash.

## Artifact identity

Artifact path should be content-addressed:

```text
r2://pollmevals-artifacts/runs/{run_hash}/evals/{eval_id}/{artifact_type}-{sha256}.{ext}
```

Artifact types:

- `raw_output`;
- `normalized_output`;
- `patch`;
- `stdout`;
- `stderr`;
- `evaluator_json`;
- `trace_json`;
- `judge_reasoning`;
- `manifest`.
