# 17 — First Smoke Run Playbook

## Goal

Prove the pipeline works end-to-end before adding judges, community, API or paid features.

## Scope

- tasks: `be_01`, `fe_01`, `doc_01`;
- models: 5 selected models;
- stack: `raw-llm` only;
- seeds: 3;
- region: `eu-central` first;
- metrics: automatic only where possible;
- artifacts: raw output, evaluator result, manifest.

## Run steps

1. Validate task specs.
2. Validate stack specs.
3. Check LiteLLM proxy.
4. Check one prompt against each model.
5. Create run snapshot.
6. Execute task/model/seed grid.
7. Save raw outputs.
8. Run evaluators.
9. Save evaluator JSON.
10. Aggregate scores.
11. Create manifest.
12. Re-run one eval from manifest.
13. Compare deterministic fields.
14. Write smoke run postmortem.

## Success criteria

- no missing artifacts;
- every failure is explicitly represented;
- score calculation is deterministic;
- manifest can be loaded by reproduction script;
- cost is calculated or explicitly marked unknown;
- run can be explained in one page.

## Failure policy

If a model/provider fails:

- store failed eval;
- store error class;
- do not silently drop from denominator;
- retry only if retry policy allows it;
- mark provider instability in run report.

## Postmortem template

```markdown
# Smoke Run Postmortem

## Run hash

## Scope

## What worked

## What failed

## Cost

## Latency

## Task issues

## Model/provider issues

## Scoring issues

## Changes before next run
```
