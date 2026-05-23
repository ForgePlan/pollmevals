# 04 — Domain model

## Primary entities

| Entity | Meaning |
|---|---|
| Model | LLM model identity and version tag |
| Model provider | Hosting/provider endpoint, region, pricing snapshot |
| Stack | Model plus scaffolding layers L0-L8 |
| Task | Versioned evaluation task with prompt, gold, evaluator and calibration |
| Run | Immutable experiment execution snapshot |
| Eval | One model/stack/task/seed/region result |
| Judgment | One judge model scoring one normalized submission |
| Calibration run | Judge or task quality check against known expected scores |
| Artifact | Raw output, normalized output, logs, traces, manifests |
| Methodology version | Versioned rules used for scoring and publication |

## Entity relationships

```text
Run 1-* Eval
Eval *-1 Model
Eval *-0..1 Stack
Eval *-1 Task
Eval 1-* Judgment
Judgment *-1 JudgeModel(Model)
Run 1-* Artifact
Task 1-* CalibrationSample
MethodologyVersion 1-* Run
```

## Immutable boundaries

After a run completes:

- `run.hash` is immutable.
- model snapshots are immutable.
- task snapshots are immutable.
- stack snapshots are immutable.
- methodology snapshot is immutable.
- raw artifacts are content-addressed.

If an error is discovered, a new run is created with a new run hash and a link to the superseded run.
