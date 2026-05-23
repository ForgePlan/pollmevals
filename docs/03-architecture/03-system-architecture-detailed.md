# 03 — System Architecture

## Architectural principle

Проект делится на два plane:

1. **Product / Control Plane** — сайт, API, registry, datasets, proposals, auth, pricing.
2. **Eval Execution Plane** — orchestrator, workers, Inspect AI, LiteLLM, sandbox, judges, scoring.

Такой split защищает публичный продукт от падений eval-workers и позволяет менять execution runtime без миграции сайта.

## Target architecture

```text
                     ┌──────────────────────────────┐
                     │         apps/site             │
                     │ Next.js / leaderboards / blog │
                     └───────────────┬──────────────┘
                                     │
                                     ▼
                     ┌──────────────────────────────┐
                     │         apps/api              │
                     │ Hono or MoleculerJS / OpenAPI │
                     └───────────────┬──────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ Postgres          │       │ Cloudflare R2     │       │ Redis / NATS      │
│ normalized state  │       │ raw artifacts     │       │ jobs / bus/cache  │
└────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘
         │                          │                          │
         ▼                          ▼                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     apps/eval-core-py                                │
│ MoleculerPy services: orchestrator, worker, judge, stats             │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                           execution runtime                          │
│ Inspect AI + LiteLLM + CLI adapters + evaluator sandbox              │
└───────────────┬─────────────────────┬──────────────────────┬─────────┘
                ▼                     ▼                      ▼
        ┌──────────────┐      ┌──────────────┐       ┌──────────────┐
        │ LiteLLM       │      │ Agent CLIs    │       │ Sandbox      │
        │ gateway       │      │ Claude/Codex  │       │ tests/lint   │
        └──────┬───────┘      └──────────────┘       └──────────────┘
               ▼
  ┌───────────────────────────────┐
  │ OpenRouter / Cerebras / vLLM   │
  │ Ollama / direct vendor APIs    │
  └───────────────────────────────┘
```

## Component responsibilities

| Component | Responsibility |
|---|---|
| `apps/site` | public UI, methodology pages, run pages, leaderboards, blog |
| `apps/api` | public API, admin API, proposal/vote endpoints, signed dataset URLs |
| `apps/eval-core-py` | run orchestration, task loading, worker execution, scoring, judge phase |
| `packages/contracts` | shared JSON Schema and TypeScript types for tasks/stacks/runs |
| `packages/db` | Postgres migrations and domain schema |
| `evals/tasks` | task specifications, prompts, evaluator references, calibration manifests |
| `stacks` | stack adapter definitions and reproducibility metadata |
| `infra` | docker-compose, LiteLLM config, sandbox images |
| `methodology` | versioned research methodology and decision log |

## Why MoleculerPy + MoleculerJS

- Eval plane is Python-native because Inspect AI, scoring, judge orchestration and many evaluators are Python-friendly.
- Public product plane benefits from TypeScript, Next.js, Hono/MoleculerJS and typed contracts.
- Rust should be introduced later only for hardened sandbox runner, trace normalizer, artifact hashing or Firecracker integration.

## Integration rule

All cross-language calls must go through explicit contracts, not implicit framework behavior.

Required contract files:

- `task.schema.json`
- `stack.schema.json`
- `run-manifest.schema.json`
- `judgment.schema.json`
- `artifact.schema.json`
- `trace.schema.json`
