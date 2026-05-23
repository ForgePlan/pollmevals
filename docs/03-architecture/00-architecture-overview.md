# 02 — Architecture

## Plane split

POLLMEVALS has two planes.

### Public product plane

Responsible for user-facing data access.

- `apps/site`: Next.js public site.
- `apps/api`: Hono API.
- `packages/db`: SQL schema and migrations.
- `packages/contracts`: JSON schemas for external and internal contracts.

### Eval execution plane

Responsible for running experiments.

- `apps/eval-core-py`: run manifests, scoring, registry loading, demo runner.
- Future MoleculerPy services: orchestrator, worker, judge-panel, stats-engine.
- LiteLLM gateway for model access.
- Docker sandbox for evaluator execution.

## Runtime flow

```text
run.create
  -> snapshot models/tasks/stacks/methodology
  -> enqueue eval jobs
  -> execute model calls through LiteLLM or CLI adapter
  -> persist raw outputs
  -> run automatic evaluator in sandbox
  -> normalize outputs for judging
  -> run judge panel
  -> aggregate median scores and statistics
  -> publish immutable run manifest
```

## Services

| Service | Plane | Language | Responsibility |
|---|---|---|---|
| API | Product | TypeScript | read endpoints, auth later, signed dataset URLs later |
| Site | Product | TypeScript | leaderboards, methodology, run pages |
| Orchestrator | Eval | Python | creates runs, snapshots state, queues eval jobs |
| Worker | Eval | Python | executes tasks against model/stack |
| Judge panel | Eval | Python | anonymization, blind judging, median aggregation |
| Stats engine | Eval | Python | bootstrap CI, variance, drift, judge agreement |
| Sandbox runner | Eval | Python first, Rust later | safe evaluator execution |

## Why MoleculerPy + MoleculerJS

MoleculerPy belongs in the eval execution plane where Python-native libraries dominate: Inspect AI, scoring, statistics, evaluator scripts and LiteLLM integration. MoleculerJS or a simple Hono API belongs in the public product plane where TypeScript, Next.js, auth, rate limits and user-facing APIs are stronger.

The architecture must avoid making public availability dependent on the eval cluster. If the eval plane is down, historical runs and public pages should still be served.
