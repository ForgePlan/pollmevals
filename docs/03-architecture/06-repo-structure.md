# 06 — Repository Structure

## Recommended monorepo

```text
pollmevals/
  apps/
    site/
    api/
    eval-core-py/
    worker-py/
    judge-py/
    stats-py/
    sandbox-runner/

  packages/
    contracts/
    db/
    ui/
    shared-types/

  evals/
    tasks/
    rubrics/
    calibration/
    fixtures/

  stacks/
    raw-llm/
    claude-code-basic/
    forgeplan-framework/

  infra/
    docker-compose.dev.yml
    docker-compose.eval.yml
    litellm/
    sandbox/
    postgres/
    nats/
    redis/

  methodology/
    methodology.md
    scoring.md
    judge-policy.md
    task-policy.md
    sponsored-policy.md
    stack-adapter-spec.md
    security-sandbox.md
    decisions/

  docs/
    00-executive-vision.md
    01-product-requirements.md
    02-architecture.md
    03-stack-decision.md
    04-domain-model.md
    05-implementation-plan.md
    06-operational-runbook.md
    07-missing-pieces-checklist.md

  scripts/
    create-run.ts
    validate-task-specs.py
    reproduce-local-run.sh
    export-dataset.ts

  artifacts/
    .gitkeep
```

## Ownership

| Path | Owner role |
|---|---|
| `apps/site` | frontend/product engineer |
| `apps/api` | fullstack/backend engineer |
| `apps/eval-core-py` | eval infrastructure engineer |
| `evals/tasks` | task author / benchmark maintainer |
| `methodology` | research lead |
| `infra` | DevOps/platform engineer |
| `packages/contracts` | architecture owner |

## Rule

Anything that changes scoring, task validity, judge behavior, or run reproducibility must be documented in `methodology/decisions/`.
