# POLLMEVALS — полный documentation pack

Этот архив — единый пакет документации для сборки проекта **POLLMEVALS**: evidence-based платформы для оценки LLM-стеков, а не только отдельных моделей.

## Как читать

1. Начни с `00-MASTER-DOCUMENTATION.md` — это линейная версия всей проектной документации.
2. Затем открой `docs-generated/01-project-brief.md`, `docs-generated/02-product-vision.md`, `docs-generated/03-system-architecture.md`.
3. Для реализации смотри `docs-generated/07-implementation-plan.md` и `docs-generated/17-first-smoke-run-playbook.md`.
4. Для задач смотри `task-packs/*` и исходные specs в `evals/tasks/*/task.yaml`.
5. Для исходного research-контекста смотри `source-archive/00-MASTER.md` и остальные файлы в `source-archive/`.

## Что внутри

| Директория | Назначение |
|---|---|
| `docs-generated/` | Новый полный проектный пакет документов: vision, PRD, architecture, runbook, task authoring, stack adapter, judge policy |
| `methodology/` | Методология из starter-repo: scoring, judge-policy, security sandbox, stack adapter spec |
| `evals/tasks/` | YAML-спеки первых задач |
| `task-packs/` | Более удобные task folders для передачи агентам/разработчикам |
| `stacks/` | Описания стартовых стеков: raw LLM, Claude Code, ForgePlan |
| `packages/contracts/` | JSON Schema / TypeScript contract документы из starter-repo |
| `packages/db/` | SQL migration для доменной модели |
| `source-archive/` | Исходный research archive из предыдущих итераций |
| `starter-files/` | README/Makefile/scripts из starter-repo, чтобы видеть команды запуска |

## Что это НЕ делает

Это именно **documentation pack**. Полноценные executable benchmark tasks с готовыми `solution.ts`, `tests.spec.ts`, evaluator sandbox и calibration implementations должны быть добавлены следующим шагом в основной repo. В этом архиве есть спецификации, структура, контракты и инструкции, по которым эти файлы нужно создать.


---

# 01 — Project Brief

## One-liner

**POLLMEVALS** — открытая evidence-based платформа для выбора production LLM-стека под конкретные engineering-задачи.

Она отвечает не на вопрос “какая модель умнее?”, а на вопрос:

> Какая комбинация model + agent CLI + tools + skills + memory + validator + region + budget лучше решает задачу класса X?

## Категория

POLLMEVALS находится на пересечении:

- LLM evaluation;
- agentic workflow evaluation;
- software engineering benchmarks;
- cost/latency analytics;
- reproducible research infrastructure;
- applied AI engineering decision support.

## Главный тезис

Обычные leaderboard’ы сравнивают голые модели. Практики же покупают не модель, а рабочий контур вокруг неё: агент, правила, память, инструменты, validator loop, запуск тестов, стоимость и latency.

POLLMEVALS делает этот контур измеримым.

## Главный insight

Дешёвая или локальная модель с правильной обвязкой может выигрывать у дорогой модели без обвязки на конкретном классе задач.

## Первые пользователи

| Persona | Что хочет |
|---|---|
| Engineering lead | выбрать стек для команды и защитить решение перед CTO/finance/security |
| Indie founder | понять, когда локальная модель + обвязка достаточно хороши |
| Researcher / analyst | получить raw data, reproducibility, confidence intervals |
| Model / agent vendor | честно сравнить себя с альтернативами |

## MVP definition

Первый реальный MVP — не сайт, а воспроизводимый eval-run:

- 3 задачи;
- 5 моделей;
- 3–5 seeds;
- автоматические метрики;
- artifact store;
- run manifest;
- публикация methodology post.

Judge panel и scaffolding ablation добавляются после того, как deterministic pipeline стабилен.


---

# 02 — Product Vision

## Vision statement

POLLMEVALS becomes the evidence layer for choosing LLM stacks in production.

It measures complete working configurations rather than isolated models:

```text
model + agent CLI + system prompt + tools + skills + memory + validator + region + cost
```

## Product promise

Для пользователя продукт должен отвечать так:

> Для backend/security задач в TypeScript при бюджете до $X/task и регионе EU-Central лучший Pareto stack сейчас: Claude Sonnet + Claude Code + skills + test validator. Локальный Qwen stack дешевле в N раз, но имеет меньший recall на code review задачах.

## What the product must prove

1. Scaffolding даёт измеримый lift на сложных задачах.
2. Этот lift зависит от категории задачи.
3. Cost-per-correct-answer важнее, чем цена за миллион токенов.
4. Region-aware latency меняет UX и выбор provider’а.
5. LLM judge без calibration и self-exclusion недостаточно надёжен.
6. Reproducibility и artifact-level audit делают leaderboard credible.

## What POLLMEVALS is not

- Не Chatbot Arena: не human preference для general chat.
- Не Artificial Analysis: не только speed/cost/intelligence для голых моделей.
- Не SWE-bench clone: использует engineering tasks, но оценивает весь stack.
- Не pure academic benchmark: cadence быстрее, цель — practical decision support.
- Не enterprise consulting platform на старте: сначала open research credibility.

## Positioning language

### Short

Stack-level evals for people who actually ship with LLMs.

### Russian

POLLMEVALS показывает, какой LLM-стек реально работает в production-задачах: с учётом обвязки, стоимости, latency, стабильности и воспроизводимости.

### Website hero

**Stop choosing models. Start choosing stacks.**

Compare LLM stacks by task quality, cost-per-correct-answer, latency by region, reproducibility, and scaffold lift.


---

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


---

# 04 — Stack Decision

## Decision

Use a hybrid stack:

| Layer | Stack |
|---|---|
| Site | Next.js 15 + Tailwind + shadcn/ui |
| Public API | TypeScript + Hono first, MoleculerJS optional |
| Eval plane | Python 3.12+ + MoleculerPy |
| Eval framework | Inspect AI |
| Inference gateway | LiteLLM proxy |
| Service bus | NATS |
| Queue/cache | Redis/BullMQ or NATS JetStream |
| Database | Postgres |
| Raw artifact storage | Cloudflare R2 / S3-compatible storage |
| Sandbox MVP | Docker rootless/no-network/read-only/tmpfs |
| Sandbox future | gVisor/Kata/Firecracker |
| Rust | Future specialized runtime modules only |

## Why not Rust first

Rust is valuable for hardened execution, not for early methodology iteration.

The first bottlenecks are:

- task quality;
- run reproducibility;
- judge calibration;
- stack adapter fairness;
- artifact schema;
- scoring validity;
- content contamination detection.

None of these are solved faster by making the orchestrator Rust-first.

## Where Rust belongs later

| Module | Trigger |
|---|---|
| `sandbox-runner` | community tasks or untrusted evaluators appear |
| `trace-normalizer` | agent CLI traces become large and heterogeneous |
| `artifact-hasher` | artifact volume becomes high |
| `firecracker-runner` | enterprise/security requirements appear |
| `worker-supervisor` | Python workers need hardened lifecycle management |

## Moleculer boundary

MoleculerPy should power internal eval execution services. Public API should not depend on MoleculerPy maturity during v0.1.

```text
Public product plane:
  Next.js / Hono / MoleculerJS / Postgres

Eval execution plane:
  MoleculerPy / Python / Inspect AI / LiteLLM / Docker sandbox
```

## Versioning rule

Pin everything:

- MoleculerPy version;
- MoleculerJS version if used;
- Inspect AI version;
- LiteLLM version;
- vLLM version;
- Node version;
- Python version;
- task version;
- stack adapter version;
- methodology version.


---

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


---

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


---

# 07 — Implementation Plan

## Phase 0 — Documentation and contracts

Deliverables:

- final repo tree;
- task schema;
- stack schema;
- run manifest schema;
- artifact schema;
- methodology v0.1;
- task authoring guide;
- first 3 task specs.

Exit criteria:

- task YAML validates;
- stack YAML validates;
- demo run manifest can be produced;
- documentation explains how to reproduce.

## Phase 1 — Deterministic smoke pipeline

Scope:

- 3 tasks: `be_01`, `fe_01`, `doc_01`;
- 5 models;
- 1 stack: `raw-llm`;
- 3 seeds;
- automatic metrics only;
- no judge panel yet.

Work items:

1. Implement LiteLLM call wrapper.
2. Implement task loader.
3. Implement prompt renderer.
4. Implement raw output artifact writer.
5. Implement evaluator sandbox for TypeScript tasks.
6. Implement documentation task evaluator.
7. Implement score aggregation.
8. Create `run manifest` and content hash.

Exit criteria:

- one command produces a complete run;
- all artifacts are content-hashed;
- run is reproducible from manifest;
- failures are stored, not hidden.

## Phase 2 — Judge panel

Scope:

- blind normalization;
- self-exclusion;
- 3 judges minimum;
- calibration set;
- median scoring;
- inter-judge agreement.

Exit criteria:

- calibration deviation is published;
- judge disagreement is measured;
- final score includes judge components only where needed.

## Phase 3 — Scaffolding ablation

Scope:

- L0 raw LLM;
- L1 system prompt;
- L2 tools;
- L3 skills;
- L4 file memory;
- L5 vector memory;
- L7 validator loop;
- 2–3 thick tasks.

Exit criteria:

- quality lift is measured per layer;
- cost overhead is measured;
- latency overhead is measured;
- at least one public post proves or disproves the key hypothesis.

## Phase 4 — Public product

Scope:

- `/methodology`;
- `/runs/[hash]`;
- `/leaderboards`;
- `/models/[slug]`;
- `/tasks/[slug]`;
- `/compare`.

Exit criteria:

- public data is understandable;
- raw artifacts are downloadable where safe;
- scoring methodology is transparent;
- run page can be cited.

## Phase 5 — Community and monetization

Only after traction:

- proposals;
- voting;
- API keys;
- datasets;
- sponsored disclosures;
- custom eval service.


---

# 08 — Task Authoring Guide

## Goal

A POLLMEVALS task must be a reproducible, versioned, discriminative evaluation unit.

It must answer:

> Can this stack solve this realistic task under fixed constraints?

## Required task files

Each task should eventually have this structure:

```text
evals/tasks/{task_slug}/
  task.yaml
  prompt.md
  README.md
  gold/
    solution.*
    tests.*
    evaluator.sh
    package.json or pyproject.toml
    tsconfig.json if TypeScript
    calibration/
      perfect.*
      good.*
      mediocre.*
      poor.*
      broken.*
```

## Required metadata

`task.yaml` must include:

- `id`;
- `slug`;
- `version`;
- `category`;
- `difficulty`;
- `language`;
- `description`;
- `prompt_template`;
- `gold_solution_uri`;
- `test_path_uri` or evaluator reference;
- `evaluator_commands`;
- `success_criteria`;
- `weight_components`;
- `expected_tokens_in`;
- `expected_tokens_out`;
- `expected_wall_clock_seconds`;
- `calibration_set`;
- `license`;
- `real_world_source`.

## Task quality gates

Before a task enters active pool:

| Gate | Required condition |
|---|---|
| Gold validity | gold solution passes its own tests |
| Broken discrimination | broken calibration fails or scores near 0 |
| Medium discrimination | mediocre sample scores between poor and good |
| Runtime bound | evaluator p95 runtime stays within limit |
| Scoring bound | score never exceeds 10 or drops below 0 |
| License | source is original or permissioned |
| Contamination | unique phrases/code are not publicly indexed |
| Reproducibility | task can run in clean sandbox |
| Judge calibration | judge rank correlation with expected samples is acceptable |

## Category-specific requirements

### Coding tasks

Must include:

- executable tests;
- typecheck where applicable;
- lint or complexity check;
- clear input/output contract;
- no network dependency;
- deterministic seed where randomness exists.

### Documentation tasks

Must include:

- gold reference document;
- rubric;
- expected sections;
- factual constraints;
- scoring criteria;
- examples of good/medium/bad outputs.

### Code review tasks

Must include:

- diff or repository snapshot;
- ground truth bug list;
- severity labels;
- location matching policy;
- precision/recall scoring.

## Versioning rule

Changing prompt, tests, evaluator, scoring weights or gold solution creates a new task version.

Do not edit old task versions in place after they have been used in a public run.


---

# 09 — Stack Adapter Guide

## Goal

A stack adapter describes how a full LLM stack is executed reproducibly.

A stack is not just a model. It can include:

- base model;
- agent CLI;
- system prompt;
- tools;
- skills;
- file memory;
- vector memory;
- subagents;
- validator loop;
- domain framework.

## Required structure

```text
stacks/{stack_slug}/
  stack.yaml
  adapter.sh or adapter.py
  README.md
  reproduce.md
```

## Required fields

```yaml
stack_adapter_version: "1.0"
slug: claude-code-basic
name: Claude Code Basic
base_model_slug: claude-sonnet
agent_cli: claude-code
agent_cli_version: pinned-version
execution_mode: repository_patch
layers:
  L0_bare_llm: false
  L1_system_prompt: true
  L2_tools: true
  L3_skills: false
  L4_file_memory: false
  L5_vector_memory: null
  L6_subagents: false
  L7_validator: false
  L8_framework: null
limits:
  max_wall_clock_seconds: 600
  max_tool_calls: 50
  max_tokens_input: 50000
  max_tokens_output: 10000
sandbox:
  network: false
  writable_paths:
    - /workspace
output_contract:
  produces:
    - final_answer
    - patch
    - tool_trace
```

## Fairness policy

All stack evaluations must specify:

- token budget;
- wall-clock budget;
- whether tests can be run;
- whether retry is allowed;
- whether network access is allowed;
- whether repo-wide reading is allowed;
- how tool-call cost is counted;
- how failed partial outputs are scored.

## Stack comparison rules

1. Compare stacks only inside the same task version.
2. Publish cost overhead and quality lift together.
3. Publish latency overhead for agentic stacks.
4. Do not compare interactive agents against one-shot LLMs without explaining different execution mode.
5. If a stack uses a framework developed by the operator, disclose conflict of interest.


---

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


---

# 11 — Judge Panel Design

## Why judge panel exists

Automatic metrics work well for executable code tasks. They do not fully evaluate documentation, architecture, code review quality, design reasoning or pattern compliance.

POLLMEVALS therefore uses a panel of LLM judges only where automatic metrics are insufficient.

## Core rules

1. A model never judges itself.
2. Use at least 3 judges for each judged output.
3. Prefer judges from different model families.
4. Use blind labels and normalized submissions.
5. Use median score, not mean, for robustness.
6. Run calibration before production judging.
7. Publish inter-judge agreement.
8. Store judge version and rubric version.

## Judge workflow

```text
raw_output
  → normalization
  → anonymized submission
  → judge calls with randomized order
  → rubric JSON per judge
  → median per criterion
  → agreement calculation
  → final judged component
```

## Normalization requirements

Remove or normalize:

- greetings;
- “here is the solution” framing;
- model signatures;
- markdown noise;
- code fences when task expects code only;
- formatting differences that do not matter;
- explanatory prose when task expects implementation.

## Calibration

Each judge must score known samples:

- perfect;
- good;
- mediocre;
- poor;
- broken;
- equivalent paraphrases.

Calibration metrics:

- mean absolute deviation from expected;
- rank correlation with expected order;
- tendency to over-score;
- tendency to prefer verbosity;
- agreement with other judges.

## Publication threshold

If judge agreement is too low, publish the run as experimental or exclude judge-scored components from final leaderboard until rubric is fixed.


---

# 12 — Scoring Contract

## Global scoring principle

Every final score is normalized to 0–10.

Each task category defines its own scoring components, but all component values must be machine-readable and stored in `automatic_metrics_json` or `rubric_scores_json`.

## Coding task formula

```text
final_score_01 =
  0.40 * correctness +
  0.15 * coverage +
  0.10 * complexity_score +
  0.10 * lint_score +
  0.10 * type_safety_score +
  0.15 * pattern_match_score

final_score_10 = final_score_01 * 10
```

## Documentation task formula

Criteria:

- structural completeness;
- factual accuracy;
- clarity;
- actionability;
- consistency.

Final documentation score is the median judge score per criterion, averaged across criteria.

## Code review task formula

```text
final_score_01 =
  0.40 * recall +
  0.30 * precision +
  0.20 * severity_match +
  0.10 * fix_quality
```

## Aggregation

For leaderboards:

- aggregate per model;
- aggregate per stack;
- aggregate per task category;
- show mean, std, n, 95% bootstrap CI;
- never hide variance;
- show cost and latency next to quality.

## Negative result rule

If difference between two stacks is smaller than variance or confidence intervals overlap materially, conclusion must be:

> No statistically meaningful difference.

Do not market tiny deltas as wins.

## Pareto rule

A stack is Pareto-dominated if another stack has both:

- higher or equal quality;
- lower or equal cost;
- with at least one strict improvement.

Pareto charts must show uncertainty intervals.


---

# 13 — Sandbox Security

## Threat model

Evaluator runs untrusted or semi-trusted model-generated code. The sandbox must assume code can attempt:

- network exfiltration;
- filesystem writes;
- process spawning;
- fork bombs;
- CPU/memory exhaustion;
- reading secrets;
- modifying evaluator files;
- hiding malicious behavior in tests.

## MVP sandbox

Use Docker with:

- no network;
- read-only root filesystem;
- writable tmpfs only;
- memory limit;
- CPU limit;
- PID limit;
- no new privileges;
- cap drop all;
- hard timeout;
- max file size ulimit;
- no mounted secrets.

## Example policy

```yaml
network_mode: none
read_only: true
tmpfs:
  - /tmp:size=100M
mem_limit: 512m
cpus: 1.0
pids_limit: 50
cap_drop:
  - ALL
security_opt:
  - no-new-privileges:true
ulimits:
  nofile: 1024
  fsize: 10485760
```

## Future hardening

| Stage | Runtime |
|---|---|
| v0.1 | Docker rootless |
| v0.3 | gVisor or Kata Containers |
| v1.0 | Firecracker microVM |
| Enterprise | per-run ephemeral VM |

## Rule

Community-submitted evaluators must never run directly on the host. They must pass static inspection and execute only inside sandbox.


---

# 14 — Operations Runbook

## Daily operations during MVP

- verify API health;
- verify LiteLLM proxy health;
- verify Postgres backups;
- verify R2 artifact writes;
- check failed evals;
- check spend against budget;
- check provider rate limits;
- inspect run queue length.

## Weekly run checklist

1. Freeze task snapshot.
2. Freeze model snapshot.
3. Freeze stack snapshot.
4. Capture pricing snapshot.
5. Create run manifest draft.
6. Execute smoke sanity check.
7. Start full run.
8. Monitor failures.
9. Aggregate automatic metrics.
10. Run judge phase if enabled.
11. Compute bootstrap CI and agreement metrics.
12. Publish run page.
13. Publish postmortem if failures are material.
14. Invalidate leaderboard cache.
15. Export public dataset snapshot.

## Incident classes

| Class | Example | Action |
|---|---|---|
| Provider outage | OpenRouter/Cerebras unavailable | mark evals failed or retry per policy |
| Evaluator bug | test suite wrong | supersede run, do not edit old scores |
| Cost spike | model loop or retry storm | stop run, cap spend, investigate |
| Judge drift | calibration deviation high | exclude judge or mark run experimental |
| Contamination | task appears online | retire task, create replacement |
| Security incident | sandbox escape suspicion | disable evaluator class, rotate secrets |

## Public transparency

If a public run has material errors, publish:

- what happened;
- affected run hash;
- affected tasks/models;
- whether results are withdrawn;
- replacement run hash if any;
- prevention change.


---

# 15 — Business and Roadmap

## Business sequence

Do not monetize before credibility.

Correct order:

1. Open research series.
2. Reproducible methodology.
3. Public runs.
4. Audience proof.
5. Dataset/API access.
6. Custom evals.
7. Sponsored evals with disclosure.
8. Enterprise white-label only if traction justifies it.

## Tiers

| Tier | Description | Timing |
|---|---|---|
| Tier 0 | open leaderboard, blog, datasets | start |
| Tier 1 | API/raw data access | after repeated runs |
| Tier 2 | custom eval reports | after methodology trust |
| Tier 3 | sponsored fast-track evals | after disclosures and governance |
| Tier 4 | enterprise white-label | separate company-level effort |

## Gating criteria

After first content phase:

- 1000+ weekly visitors;
- credible technical discussion;
- GitHub stars/genuine forks;
- inbound requests from practitioners.

After MVP:

- 100+ MAU;
- repeat visitors;
- at least one serious Tier 2 inquiry;
- evidence that users compare stacks, not just models.

## Main business risk

The project can become a sixth full product competing with ForgePlan/GERTS/Orchestra/consulting. Avoid this by treating first 3 months as a research/content asset, not a SaaS commitment.

## Strategic moat

- trusted methodology;
- historical stack-level dataset;
- reproducible artifacts;
- calibrated judge panel;
- stack adapter ecosystem;
- founder credibility in AI engineering workflows.


---

# 16 — Missing Pieces Checklist

## Critical before real MVP

- [ ] executable gold solution for `be_01`;
- [ ] executable tests for `be_01`;
- [ ] evaluator sandbox for TypeScript tasks;
- [ ] executable gold solution for `fe_01`;
- [ ] React test setup for `fe_01`;
- [ ] documentation rubric evaluator for `doc_01`;
- [ ] real LiteLLM call wrapper;
- [ ] model pricing snapshot capture;
- [ ] artifact schema;
- [ ] trace schema;
- [ ] stack adapter executable contract;
- [ ] task quality gate script;
- [ ] run reproducibility script;
- [ ] judge calibration samples;
- [ ] post-run aggregation script;
- [ ] public run page spec.

## Important before public leaderboard

- [ ] methodology versioning;
- [ ] decision log process;
- [ ] contamination detection process;
- [ ] held-out task lifecycle;
- [ ] conflict-of-interest disclosure page;
- [ ] cost transparency page;
- [ ] failure policy;
- [ ] negative results policy;
- [ ] dataset export format;
- [ ] terms/license review.

## Important before community proposals

- [ ] GitHub OAuth;
- [ ] proposal validation;
- [ ] maintainer review queue;
- [ ] anti-spam rules;
- [ ] security review for submitted evaluators;
- [ ] clear rejection reasons;
- [ ] task provenance/license fields.


---

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


---

# 18 — Agent Handoff Brief

## Mission

Build POLLMEVALS as a reproducible evaluation system for production LLM stacks.

The first milestone is not a beautiful website. The first milestone is a trustworthy smoke run that produces immutable artifacts and a reproducible manifest.

## Non-negotiables

- Do not edit completed run results in place.
- Do not compare task versions as if they are the same.
- Do not let a model judge itself.
- Do not hide failed evals.
- Do not publish a leaderboard without methodology.
- Do not make paid/sponsored features before disclosure policy exists.
- Do not run untrusted code outside sandbox.

## Build order

1. Contracts.
2. Task specs.
3. Gold/evaluator files.
4. LiteLLM wrapper.
5. Raw run execution.
6. Artifact persistence.
7. Automatic scoring.
8. Manifest generation.
9. Reproduction script.
10. Judge panel.
11. Site pages.
12. API/datasets.

## First concrete implementation target

Create executable `be_01_jwt_auth` task pack:

- TypeScript Express middleware prompt;
- gold solution;
- Vitest tests;
- ESLint complexity check;
- TypeScript strict check;
- evaluator shell script;
- five calibration implementations.

Then run:

```text
3 tasks × 5 models × 3 seeds × 1 stack × 1 region = 45 evals
```

No judge panel in the first deterministic smoke.

## Definition of done for v0.1

A new engineer can clone the repository, set `.env`, run one command and produce a local run manifest with artifacts.


---

# Appendix — исходный research archive

# POLLMEVALS — MASTER DOCUMENT

Один длинный документ со всем содержанием архива в одном месте.
Сгенерирован автоматически из отдельных файлов 01-12.

---

# 01 — Проблема и видение

## Главная боль

Инженеры тратят дни и недели чтобы понять "какая модель + обвязка реально лучше под мою задачу". Существующие лидерборды отвечают только на вопрос "какая модель умнее на абстрактных тестах". Они не учитывают:

- Какой агентный CLI (Claude Code / Codex / Gemini / Hermes) и стек обвязки даёт реальный профит
- Стоимость задачи (а не цена за токен)
- Латенси из твоего региона
- Стабильность через несколько запусков
- Влияние памяти, skills, validator-петель
- Реальное cost-quality соотношение

## Что отвечает POLLMEVALS

Конкретный вопрос: **"Возьми задачу класса X, бюджет Y, регион Z — какой стек тебе оптимален?"**

Это другой класс вопросов чем "какая модель умнее". Это вопрос практика, не researcher'а.

## Vision statement

POLLMEVALS — открытая платформа evidence-based выбора LLM-стека под реальные production-задачи. Мы измеряем не модели, а **полные стеки**: модель + agent CLI + skills + память + validator. Прозрачно, воспроизводимо, с panel of judges.

## Целевые юзеры (4 persona)

### Persona A — Engineering lead

Выбирает стек для команды разработчиков. Бюджет $5-50k/мес на LLM.

**Нужно:**
- Cost-quality Pareto для разных стеков
- Регион-aware latency (где-то в EU, где-то в US, нужны числа)
- Стабильность через несколько запусков
- Документированная методология (для внутренних approvals)

**Платит за:** Tier 1 API access ($50-500/мес), Tier 2 custom evals ($5-20k).

### Persona B — Indie hacker / founder

Гоняет локальные модели + cloud по необходимости. Бюджет $50-500/мес.

**Нужно:**
- Какие комбинации Ollama-моделей + skills дают приличный результат на M-чипе
- Когда стоит платить за Cloud vs делать локально
- Конкретные working stacks для типовых задач (REST API, React components, дебаг)

**Платит:** ничего, бесплатный leaderboard.

### Persona C — Researcher / Industry analyst

Пишет отчёты, статьи, делает запросы для VC и enterprise клиентов.

**Нужно:**
- Raw data export (Parquet, JSONL)
- Methodology transparency (для citations)
- Historical data (track как модели улучшались)
- Confidence intervals на всех числах

**Платит за:** Tier 1 API access, datasets.

### Persona D — Model creator (Anthropic, OpenAI, open-weights teams)

Хочет увидеть свою модель честно оценённой и сравнённой.

**Нужно:**
- Honest, replicable eval
- Public visibility
- Возможность ускоренного добавления при релизе флагмана

**Платит за:** sponsored expedited evals (Tier 3, всегда с disclosure).

## Уникальное ценностное предложение (UVP)

| Фишка | Что это даёт |
|---|---|
| **Scaffolding evaluation** | Меряем не модели, а полные стеки (модель + agent CLI + skills + память + validator + framework) |
| **Panel of judges** | 5 ротирующихся LLM-судей, никто не судит сам себя, blind labels, median scoring |
| **Cost-aware results** | $/task, $/correct answer — не просто accuracy |
| **Geo-aware latency** | TTFT и tok/s измеряются из 4 регионов (US-East, EU-Central, APAC, SA) |
| **Weekly + triggered cadence** | Каждую неделю + emergency run при релизе флагмана |
| **Community-driven additions** | Сообщество голосует какие модели/стеки добавлять |
| **Reproducibility** | Все промпты, версии, seeds, raw outputs — публичные, проверяемые |
| **Versioned tasks** | Изменение задачи = новая версия. Старые сравнения остаются валидными |
| **Drift detection** | Если closed-API модель меняет поведение — публикуем alert |
| **Anti-gaming** | 20% задач — held-out, не публикуются |

## Главный insight который POLLMEVALS показывает

**Дешёвая модель с правильной обвязкой часто бьёт дорогую модель без неё.**

Условный Qwen 2.5 14B + skills + validator может догнать GPT-5 без обвязки на конкретной задаче за 1/20 цены. Это сильный практический вывод для читателя который никто другой системно не показывает.

## Чем POLLMEVALS НЕ является

- **Не Chatbot Arena.** Мы не меряем human preference на чате. Мы меряем automated metrics + LLM-judge.
- **Не Artificial Analysis.** Они меряют голые модели по cost/speed/intelligence. Мы меряем стеки.
- **Не leetcode benchmark.** Все задачи — реальные production-кейсы из SWE-Lancer и аналогов.
- **Не academic paper.** Мы публикуем оперативно, weekly. Это про practical guidance, не peer review.

---

# 02 — Методология

## Часть 1: Scaffolding evaluation — лесенка обвязки

Ключевая концепция всей платформы: меняется не модель, а то что вокруг неё. Это **ablation study продакшен-стека** — в академии этим почти никто не занимается, в индустрии все делают это интуитивно и без чисел.

### Таксономия 9 уровней обвязки

| L | Слой | Конкретные реализации |
|---|---|---|
| L0 | Голая LLM | API без system prompt, raw completion |
| L1 | System prompt / role | Текстовое описание роли |
| L2 | Tools (function calling) | MCP, OpenAI tools, Anthropic tool_use |
| L3 | Skills | Anthropic Skills, Cursor rules, AGENTS.md |
| L4 | Файловая память | CLAUDE.md, `/memories`, scratchpad |
| L5 | Векторная/семантическая память | mem0, Hindsight, Letta, Zep |
| L6 | Subagents / multi-agent | Claude Code subagents, AutoGen, CrewAI |
| L7 | Validator loop | AlphaCodium, Reflexion, autoresearch-стиль |
| L8 | Спец-фреймворк (доменный) | ForgePlan (docs/arch), voltagent, OpenSpec |

L0-L7 — общий стек. L8 — готовые композиции L0-L7 заточенные под класс задач. ForgePlan, например, это по сути L3+L4+L6+L8 в одной упаковке для документации.

### Ключевая гипотеза

На простых задачах обвязка ничего не даёт (или даже мешает). На сложных задачах — каждый слой обвязки даёт измеримый прирост, и **дешёвая модель с правильной обвязкой часто бьёт дорогую модель без неё**.

Это нужно доказать числами через ablation study.

---

## Часть 2: Panel of LLM Judges (POLLM)

### Базовые правила

**Модель не судит сама себя.** Никогда. Это исключает self-enhancement bias (в paперах: Llama-judge ставит Llama-ответам на +5-15% выше, GPT — GPT, и так у всех).

**Минимум 3 разных судьи на каждый ответ.** Один судья — subjective. Два — может быть тай. Три — есть медиана. Финальный балл = **медиана**, не среднее (медиана устойчива к выбросам).

**Судьи из разных family.** Нельзя ставить судьями три модели Anthropic — они слишком похожи и accord biases. Бери микс: один Anthropic, один OpenAI, один Google, один open-weight.

### Матрица судейства (стандартный setup)

| Подсудимый \ Судья | Opus 4.7 | GPT-5 | Gemini 2.5 Pro | Llama 3.3 70B | DeepSeek V3.5 |
|---|---|---|---|---|---|
| Claude Opus 4.7 | — | X | X | X | X |
| Claude Sonnet 4.6 | — | X | X | X | X |
| GPT-5 | X | — | X | X | X |
| GPT-5-mini | X | — | X | X | X |
| Gemini 2.5 Pro | X | X | — | X | X |
| Llama 3.3 70B | X | X | X | — | X |
| DeepSeek V3.5 | X | X | X | X | — |
| остальные | X | X | X | X | X |

5 судей × 14 подсудимых × 20 задач = 1400 judge-calls на Фазу 1. ~$30-70 на судейство всей фазы.

Опционально 6-й судья — Grok-4 (не в Anthropic/OpenAI/Google семьях).

### Anonymization pipeline

Чтобы судья реально не знал что чьё, нужна **система нормализации перед судейством**:

```python
def normalize_for_judging(raw_output: str, task_type: str) -> str:
    # 1. Strip приветствий и завершалок (Claude's "Certainly!", GPT's "Sure!", etc.)
    text = strip_meta_phrases(text, patterns=[
        r"^(Sure|Certainly|Absolutely|Here's|I'll|Let me|I'd be happy).*?[\n.]",
        r"\n\n(Let me know|Hope this helps|Feel free).*$",
    ])

    # 2. Для кода — извлечь из markdown блоков, форматировать через language formatter
    if task_type == "code":
        code = extract_code_block(text)
        code = run_formatter(code, lang=detect_lang(code))  # prettier/black/rustfmt
        code = strip_author_comments(code)  # удалить "// Created by..."
        code = remove_explanation_blocks(code)

    # 3. Для документации — нормализовать markdown
    if task_type == "doc":
        text = normalize_markdown_headers(text)
        text = strip_emoji_decoration(text)

    return text
```

**Anti-signature в промпте генерации:**
```
Important: Do not introduce yourself, do not greet, do not say "Here's the 
solution" or similar phrases. Do not sign code with your name or model 
identifier. Output ONLY the solution itself, nothing else.
```

Это снижает 70-80% подписей. Остальное добивает нормализация.

**Проверка работы:** identification probe — отдаём ответ другой модели и спрашиваем "guess which model wrote this". Если accuracy > 30% — нормализация недостаточна.

---

## Часть 3: Таксономия biases судей

| Bias | Что это | Mitigation |
|---|---|---|
| Self-enhancement | Любит свой "акцент" | Self-judging disabled |
| Position bias | Первый/последний ответ получает выше балл | Рандомизировать порядок при каждом judge call |
| Length bias | Длинные ответы кажутся "лучше" | В rubric явно: "не оценивайте по длине". Penalize длинные > 2× медианы |
| Verbosity bias | Markdown/bullets кажутся "structured" | Нормализовать форматирование |
| Authority bias | "Expert solution" в промпте → выше балл | Не говорить о происхождении |
| Sycophancy | Если в промпте намёк — соглашается | Промпт нейтральный, без "this is the gold answer" |
| Anchor bias | Первый score влияет на следующие | Каждый ответ оценивается в отдельном judge call, без контекста |
| Halo effect | Хороший в одном — высокие баллы и в другом | Скоринг по каждому критерию rubric'а независимо |
| Calibration drift | Судья дрейфует к "среднему" | Использовать calibration set с известными score |

---

## Часть 4: Calibration set

**Must-have which никто не делает.** Перед судейством реальных ответов, прогоняем каждого судью через **5-10 калибровочных задач с известными "правильными" оценками**:

- Заведомо отличное решение → должно получить ~9-10
- Заведомо среднее → ~5-6
- Заведомо плохое (но компилируется) → ~2-3
- Заведомо неправильное → ~0-1
- Identical с переформулировкой — оба должны получить ~равные баллы

Если судья отклоняется от калибровки → исключаем из пула или переделываем rubric.

В статью идёт **таблица калибровки судей** — это очень публикуемо.

---

## Часть 5: Pairwise vs Absolute scoring

Литература говорит: **pairwise сравнения стабильнее absolute оценок**. Когда судья говорит "B лучше A" — устойчиво. Когда говорит "B = 7.3" — subjective.

**Hybrid approach:**
- Автометрики дают абсолютные числа (correctness, CC, coverage, test pass)
- Pairwise judge даёт относительный ранг через Bradley-Terry или Elo
- Финальный score = weighted combination

---

## Часть 6: Multi-dimensional scoring per task type

### Для кодовых задач

```python
score_components = {
    "correctness":     0.40,  # runs without error + passes unit tests
    "test_coverage":   0.15,  # % покрытия, если задача требовала тестов
    "complexity":      0.10,  # |CC_model - CC_gold| / CC_gold (чем ближе тем выше)
    "linter":          0.10,  # 1 - (errors + warnings/3) / max_acceptable
    "type_safety":     0.10,  # 1 - (tsc/mypy errors) / loc
    "pattern_match":   0.15,  # LLM-judge на следование паттернам gold (0-1)
}
final = sum(weight × normalized_metric)  # → 0-1, потом × 10 для радара
```

### Для документации / архитектуры

```python
rubric_doc = {
    "structural_completeness": "Все нужные секции присутствуют (0-10)",
    "factual_accuracy":         "Нет фактических ошибок относительно gold",
    "clarity":                  "Понятно ли junior-разработчику",
    "actionability":            "Можно ли по этому работать",
    "consistency":              "Не противоречит ли сам себе",
}
# Через panel of judges с blind labels, median scoring
```

### Для code review

```python
review_metrics = {
    "recall":          0.4,  # % реальных багов из ground truth списка
    "precision":       0.3,  # из найденных, % реально багов
    "severity_match":  0.2,  # совпадение оценок critical/major/minor
    "fix_quality":     0.1,  # LLM-judge на предложенные фиксы
}
```

---

## Часть 7: Statistical rigor

**Multiple seeds.** Каждый combo (model × task) гоняем **5 раз** с разными seed/temperature. Это даёт оценку variance. В радаре показываем **mean ± std**. Если разница между моделями < std — она не значима.

**Inter-rater reliability.** После судейства считаем согласие между судьями:
- **Cohen's kappa** для пар
- **Krippendorff's alpha** для пула > 2 судей

Цель: α > 0.7 (нормально), > 0.8 (хорошо). Если α < 0.5 — судьи спорят, твоим оценкам нельзя верить.

**Effect size, не только p-value.** Между двумя моделями смотрим **Cohen's d**:
- d < 0.2 — разница незначительна (даже если p < 0.05)
- d > 0.8 — large effect, реальная разница

В пост обязательно: "разница X vs Y по reasoning — d=0.3 (small), по coding — d=1.1 (large)".

**Bootstrap confidence intervals.** Для финальных оценок на радаре считаем 95% CI через bootstrap (resample with replacement). На графике рисуем shaded zone. Это убивает все "ну а вдруг это случайность".

**Pre-registration.** Перед прогоном записываем гипотезы и метрики в файл, коммитим в git. После прогона сравниваем. Это исключает p-hacking.

---

## Часть 8: "Premium" артефакты для публикации

Эти штуки превращают пост из "вот цифры" в "вот исследование":

1. **Inter-judge agreement matrix** — таблица Cohen's kappa между всеми судьями
2. **Calibration plot** — оси: "истинный score" vs "score от судьи". Точки выше/ниже диагонали показывают bias
3. **Variance heatmap** — `model × task`, цвет = std accuracy через 5 прогонов
4. **Confidence intervals на радаре** — error bars или shaded zones
5. **Cost-quality Pareto с error bars** — финальный график
6. **Bias-check table** — identification probe ниже 30% accuracy
7. **"Negative findings"** — где разница не значима. **Сильно повышает доверие** читателя

---

# 03 — Дизайн эксперимента

## Часть 1: Комбинаторный взрыв — почему полный grid невозможен

Если попытаться сделать полный grid (33 модели × 8 типов задач × 3 instance × 13 комбо обвязки × 5 CLI), получится **51 480 прогонов**. При среднем 5 минут на прогон = почти полгода непрерывного сжигания GPU. Это не делается никогда.

**Решение: fractional factorial design** — двигаемся по одной оси за раз, остальные фиксируем. Каждое движение — отдельный эксперимент → отдельный пост в серии.

---

## Часть 2: 5-фазная raceкладка серии

| Фаза | Цель | Прогонов | Что меняется | Главный артефакт |
|---|---|---|---|---|
| 1 — Baseline моделей | Радар чистых моделей на голых задачах | ~260 | Только модель | Radar chart |
| 2 — Лестница обвязки L0→L6 | Ablation: что даёт каждый слой | ~50 | Только слой обвязки | Ablation bars |
| 3 — Память: file vs vector | Сравнение типов памяти | ~40 | Тип памяти | Сравнительный график |
| 4 — Сравнение CLI-агентов | Claude Code, Codex, Gemini, Hermes | ~40 | CLI на одном stack'е | Bar comparison |
| 5 — Pareto cost vs quality | Финальный scatter | ~80 | Лучшие combos × все задачи | Pareto frontier |

**Итого ~470 прогонов вместо 51 000** — реально за 2-3 недели работы.

Каждая фаза = **отдельный пост в серии**. Между фазами **только одна переменная меняется**, остальные зафиксированы. Это factorial design.

---

## Часть 3: Пул моделей для Фазы 1 (14 штук)

### Cloud (через OpenRouter, 8 моделей)

| Модель | Версия |
|---|---|
| Claude Opus 4.7 | latest |
| Claude Sonnet 4.6 | latest |
| GPT-5 | full |
| GPT-5-mini | full |
| Gemini 2.5 Pro | latest |
| Gemini 2.5 Flash | latest |
| Grok 4 | latest |
| DeepSeek V3.5 | latest |

### Open-weight fast (через Cerebras, 4 модели)

| Модель | Версия |
|---|---|
| Llama 3.3 70B | через Cerebras |
| Qwen3 32B | через Cerebras |
| GLM-4.7 | через Cerebras |
| gpt-oss-120B | через Cerebras |

### Open-weight self-hosted (через Runpod vLLM, 1 модель)

| Модель | Версия |
|---|---|
| Qwen 2.5 72B | vLLM H100 |

### Локально для smoke-test (Mac M-чип, 1 модель)

| Модель | Версия |
|---|---|
| Qwen 2.5 14B Q4 | Ollama |

---

## Часть 4: 20 задач для Фазы 1 (draft)

Все задачи на TypeScript/Node.js (основной стек) + 2-3 на Python (DevOps/data) + SQL для DB. Каждая задача:
- Выполнима за 1 промпт → 1 ответ
- Имеет gold solution ~50-200 строк кода
- Имеет automated evaluator с ≥3 численных метрик
- Решается за < 5 минут wall-clock
- Покрывает реальный сценарий из ежедневной работы

### Backend / API (4 задачи)

| ID | Задача | Метрики |
|---|---|---|
| be_01 | JWT auth middleware с refresh tokens, secure cookie, CSRF | Tests pass, CC≤8, type-safe, no security warnings |
| be_02 | REST endpoint POST /users с Zod валидацией, dedup email | Tests pass, branches covered, error responses RFC 7807 |
| be_03 | Webhook handler с HMAC signature, idempotency key, retry | Tests pass, replay-safe, timing-attack-safe |
| be_04 | Cursor-based pagination для GET /posts с N+1 prevention | Tests pass, query count constant, type-safe |

### Frontend (3 задачи)

| ID | Задача | Метрики |
|---|---|---|
| fe_01 | Multi-step form с валидацией, persisted draft, a11y | Tests pass, WCAG 2.1 AA via axe-core, keyboard nav |
| fe_02 | Debounced search input с loading/error/empty states | Tests pass, no race conditions, 60fps |
| fe_03 | Drag-and-drop kanban list с persistent order | Tests pass, optimistic UI, conflict resolution |

### Fullstack (2 задачи)

| ID | Задача | Метрики |
|---|---|---|
| fs_01 | Feature flag system: backend toggle + frontend hook | E2E tests pass, type-safe contract, no flicker |
| fs_02 | File upload с resumable chunks (frontend + backend) | E2E tests pass, abort safety, integrity check |

### Database (2 задачи)

| ID | Задача | Метрики |
|---|---|---|
| db_01 | Migration: split users.address в нормализованную таблицу с zero-downtime strategy | Migration applies, rollback safe, no data loss |
| db_02 | Оптимизировать query который делает full scan на 10M rows | Query plan uses index, latency p95 < gold × 1.2 |

### DevOps (2 задачи)

| ID | Задача | Метрики |
|---|---|---|
| ops_01 | Multi-stage Dockerfile для Node app — image size < 150MB, non-root user, healthcheck | Image builds, Trivy scan clean, size threshold |
| ops_02 | GitHub Actions workflow: matrix tests, cache, deploy on tag | Workflow validates (actionlint), idempotent, no secret leaks |

### Tests (2 задачи)

| ID | Задача | Метрики |
|---|---|---|
| tst_01 | Написать тесты для legacy функции (даны функция + ТЗ что она должна делать) | Coverage ≥ 90%, mutation score ≥ 70%, no flaky |
| tst_02 | Integration test для REST API с Testcontainers Postgres | Tests pass, isolation, < 5s runtime |

### Documentation (2 задачи)

| ID | Задача | Метрики |
|---|---|---|
| doc_01 | README для open-source CLI tool (даны код + примеры использования) | Все секции по rubric присутствуют, judge score ≥ 7 |
| doc_02 | ADR на тему "выбрали Postgres вместо MongoDB" с контекстом | Структура match, factual accuracy, judge ≥ 7 |

### Refactor / Review (3 задачи)

| ID | Задача | Метрики |
|---|---|---|
| rev_01 | Найти баги в diff (5 PRs, в каждом по 1-3 бага разной критичности) | Recall, precision, severity F1 |
| ref_01 | Отрефакторить 200-строчную God-функцию по SOLID — сохранить тесты | Tests still pass, CC снижается, no API change |
| ref_02 | Mitigate N+1 query в ORM-коде, сохранить контракт | Tests pass, query count -50%, type-safe |

### Откуда брать gold solutions

Лучший источник — **SWE-Lancer от OpenAI** (1488 реальных задач из Upwork, $1M total payouts, triple-verified tests). Тоже **DevBench от Microsoft** (1800 instances, 6 языков), **BigCodeBench** (1140 tasks, 139 libraries), **Aider Polyglot** (225 challenging tasks).

Брать **отдельные задачи как образцы**, дополнять своими реальными production patterns.

---

## Часть 5: Что нужно для каждой задачи

```yaml
- id: be_01
  category: backend
  difficulty: medium
  language: typescript
  description: |
    Write a JWT authentication middleware for Express.js that:
    - Validates JWT tokens from Authorization header
    - Implements refresh token rotation
    - Sets secure HTTP-only cookies
    - Includes CSRF protection
  inputs:
    - example_request_1
    - example_request_2
  gold_path: ./gold/be_01/solution.ts
  test_path: ./gold/be_01/tests.spec.ts
  success_criteria:
    - All tests in tests.spec.ts pass
    - Cyclomatic complexity ≤ 8
    - Type-safe (tsc --strict clean)
    - No high/critical issues from semgrep security scan
  evaluator:
    - vitest run
    - eslint --max-complexity 8
    - tsc --noEmit --strict
    - semgrep --config=p/security
  expected_tokens_in: ~800
  expected_tokens_out: ~1500
  weight_components:
    correctness: 0.40
    test_coverage: 0.15
    complexity: 0.10
    linter: 0.10
    type_safety: 0.10
    pattern_match: 0.15
```

---

## Часть 6: Иерархия задач для разных фаз

**Фаза 1 (радар моделей)** — 20 задач выше. Должны быть короткими и разнообразными.

**Фаза 2 (ablation обвязки)** — нужны **2-3 ТОЛСТЫЕ задачи** где обвязка реально влияет:
- "Отрефакторь модуль на 500-1000 строк, сохранив API и тесты"
- "Напиши PRD на новую фичу по краткой заметке + 3 ссылкам на похожие фичи"
- "Дебажь баг по логам + 5 файлов кода → найди причину и предложи фикс"

На таких задачах голая модель проваливается, а каждый слой обвязки даёт измеримый прирост.

**Фаза 4 (CLI-агенты)** — берёшь ОДНУ задачу из Фазы 2 и гоняешь через Claude Code / Codex / Gemini / Hermes / +1 — каждый со своим best стеком.

**Фаза 5 (Pareto)** — комбинируешь 6-8 лучших стеков из Фаз 2-4 и гоняешь на 8 типах задач из Фазы 1.

---

# 04 — Инфраструктура

## Часть 1: Стек сравнение и выбор

### Eval framework — Inspect AI

После исследования трёх кандидатов (Inspect AI, lm-evaluation-harness, lighteval) выбран **Inspect AI** от UK AI Security Institute. Причины:

- **200+ pre-built evals** в коллекции `inspect_evals`, включая SWE-bench, GAIA, MMLU, HumanEval, LiveBench
- **Современная архитектура** — Python пакеты, не legacy
- **Built-in token usage tracking** — отличный proxy для cost
- **Web log viewer** через `inspect view` — красивые скриншоты для блога
- **Стандарт у major labs** — Anthropic, DeepMind используют Inspect
- **Активно поддерживается** — UK AISI + Meridian Labs

Альтернативы которые НЕ берём:
- **lm-evaluation-harness** (EleutherAI) — legacy API, сложная архитектура, но academic standard
- **OpenCompass** — 100+ датасетов, китайский, тяжёлый сетап
- **lighteval** (HuggingFace) — лёгкий, но мало evals
- **LiveBench** — берём как **один из бенчмарков внутри Inspect**, а не как framework

### Inference gateway — LiteLLM

LiteLLM proxy — центральный gateway для всех вызовов моделей. Причины:

- **OpenAI-compatible endpoint** для 100+ моделей — все наши eval frameworks говорят OpenAI API
- **Cost tracking built-in** — пишет в Postgres каждый запрос с tokens и spend
- **Virtual keys** — отдельный ключ на каждый run, легко считать
- **Load balancing + fallback** — если один backend упал, переключается
- **Custom prices для local моделей** — можно поставить GPU-hour cost
- **OpenSource MIT** — self-hostable, без vendor lock-in

Альтернативы:
- **OpenRouter** — добавляет +5.5% наценки + network hop, используем как backend для cloud моделей
- **Portkey** — платный, observability-first
- **Bifrost** — Go, для high-throughput, не нужно нам сейчас

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Inspect AI (eval engine + 200+ tasks)              │
└────────────────────┬────────────────────────────────┘
                     │ OpenAI-compat API
                     ▼
        ┌────────────────────────────┐
        │  LiteLLM Proxy :4000       │
        │  - virtual keys per run    │
        │  - cost tracking → Postgres│
        │  - logging callbacks       │
        └─────────────┬──────────────┘
                     │
   ┌─────────┬───────┴───────┬──────────────┬──────────┐
   ▼         ▼               ▼              ▼          ▼
Ollama   Runpod          Cerebras        OpenRouter   Direct
 :11434   vLLM           inference       (cloud)      vendor
 (Mac)   (GPU box)       (open weights)               APIs
```

---

## Часть 2: Распределение моделей по провайдерам

| Модель | Provider | Почему |
|---|---|---|
| Claude Opus 4.7, Sonnet 4.6 | **OpenRouter** | Только закрытые API |
| GPT-5, GPT-5-mini | **OpenRouter** | Только закрытые API |
| Gemini 2.5 Pro, Flash | **OpenRouter** | Только закрытые API |
| Grok 4 | **OpenRouter** | Только закрытые API |
| Llama 3.3 70B | **Cerebras** | 1800 tok/s, $0.85/MTok |
| Qwen3 32B | **Cerebras** | 1500+ tok/s |
| GLM-4.7 | **Cerebras** | 0.47s TTFT |
| gpt-oss-120B | **Cerebras** | 3000 tok/s, $0.39/MTok |
| Qwen 2.5 72B | **Runpod** vLLM | Cerebras не хостит |
| Mistral Large (опционально) | **OpenRouter** (Mistral API) | Закрытая |
| DeepSeek V3.5 | **OpenRouter** (DeepInfra) | Дешевле через aggregators |
| Qwen 2.5 14B (smoke) | **Mac локально** (Ollama) | Для дебага пайплайна |

### Free tier у Cerebras

1M tokens/day, 30 RPM, без credit card. Хватит на smoke-test. Для полного weekly run возьмём paid tier.

### Runpod calculation

H100 = ~$3/час. Qwen 72B vLLM поднимается, прогоняем 20 задач за 1-2 часа = $3-6 за всю модель за weekly run. Не больно.

---

## Часть 3: LiteLLM config (пример)

См. `examples/litellm-config.yaml`. Ключевые моменты:

```yaml
model_list:
  - model_name: claude-opus-4.7
    litellm_params:
      model: openrouter/anthropic/claude-opus-4.7
      api_key: os.environ/OPENROUTER_API_KEY

  - model_name: llama-3.3-70b
    litellm_params:
      model: cerebras/llama3.3-70b
      api_key: os.environ/CEREBRAS_API_KEY

  - model_name: qwen-2.5-72b
    litellm_params:
      model: hosted_vllm/Qwen/Qwen2.5-72B-Instruct
      api_base: http://runpod-vllm:8000/v1
```

Кастомные цены для локальных моделей — отдельный блок, где можно учесть GPU-hour cost.

---

## Часть 4: Cost tracking — три источника правды

### Источник 1: LiteLLM Postgres

Каждый запрос пишется в `LiteLLM_SpendLogs` с полями `prompt_tokens`, `completion_tokens`, `spend`, `model`, `api_key`.

```python
import pandas as pd, sqlalchemy as sa
eng = sa.create_engine("postgresql://litellm:pass@localhost/litellm")
df = pd.read_sql("""
  SELECT model, 
         SUM(prompt_tokens) as input_tokens,
         SUM(completion_tokens) as output_tokens,
         SUM(spend) as total_cost
  FROM "LiteLLM_SpendLogs"
  GROUP BY model
""", eng)
```

### Источник 2: Inspect AI eval logs

Каждый прогон порождает структурированный EvalLog с `model_usage`, latency, retries.

```python
from inspect_ai.log import list_eval_logs, read_eval_log

rows = []
for path in list_eval_logs("./logs"):
    log = read_eval_log(path)
    for model, usage in log.stats.model_usage.items():
        rows.append({
            "model": model, "task": log.eval.task,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "accuracy": log.results.scores[0].metrics["accuracy"].value,
        })
```

### Источник 3: Pricing file от LiteLLM

`https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` — каноничный price-файл, используется browser-use и другими либами.

---

## Часть 5: Geo-aware metrics — критичная фишка

### Что мерим из каждого региона

- **TTFT** (time-to-first-token) — самое чувствительное к geo
- **Total wall-clock latency** — включает inference + network
- **Tokens/sec output** — обычно стабильно по регионам

### Регионы воркеров

- **US-East** (Virginia) — основной для North American audience
- **EU-Central** (Frankfurt — где Eli) — основной для Europe
- **APAC** (Tokyo или Singapore) — для Asia
- **SA** (São Paulo) — для Latin America (опционально)

### Особая ценность

- Anthropic/OpenAI имеют разные endpoints по регионам
- Cerebras сейчас только US-West — критично знать для EU пользователя
- Local hosted (Runpod) — выбор региона = выбор cost + latency
- Self-hosted = TTFT 50ms vs cloud = 800ms — это другой класс UX

### Реализация

4 docker контейнера в 4 регионах (DigitalOcean / Hetzner Cloud — дешевле AWS). Каждый делает inference-вызовы из своего региона и пишет measurements в Postgres с колонкой `region`.

---

## Часть 6: Worker model

### Eval orchestrator

Inspect AI core (Python) обёрнут в собственный сервис. Гоняет одну фазу одной модели как Inspect run, агрегирует, складывает в Postgres.

```python
def run_phase_1():
    for model in PHASE_1_MODELS:
        for task in PHASE_1_TASKS:
            for seed in range(5):
                for region in REGIONS:
                    result = inspect_eval(
                        task=task.path,
                        model=f"litellm/{model}@{region}",
                        seed=seed,
                    )
                    persist_to_postgres(result)
```

### Queue

Redis для task queue. BullMQ или Sidekiq-style. Воркеры берут задачи, выполняют, пишут результат.

### Storage

- Postgres — все нормализованные данные
- S3-compatible (Cloudflare R2) — raw outputs с content-hash именами
- Redis — cache и queue

---

## Часть 7: Cost estimate для weekly run

**Фаза 1 setup:**
- 14 моделей × 20 задач × 5 seeds = 1400 completions
- + 5 судей × каждый eval = ~5000 judge calls (с учётом self-exclusion)
- Total ~6400 inference calls в weekly run

**Cost breakdown:**
- Cloud моделей через OpenRouter: ~$50-100
- Cerebras моделей: ~$10-20 (или free tier для smoke)
- Runpod для Qwen 72B: ~$10
- Judges (Opus, GPT-5, Gemini Pro, Llama, DeepSeek): ~$30-70

**Итого: $100-200 / неделю** на inference. Подъёмно.

**Инфраструктура:**
- Postgres (Supabase / Neon): $25/мес
- 4 workers (Hetzner Cloud): $20/мес
- Cloudflare R2 storage: $0-15/мес
- Frontend (Vercel): $0-20/мес

**Итого: $65-80/мес фикс + $400-800/мес на 4 weekly runs.**

Тысяча в месяц на operate weekly cadence Фазы 1. Реалистично для bootstrap проекта.

---

# 05 — Product Specification: POLLMEVALS

## Quick facts

- **Название:** POLLMEVALS (Panel of LLM Evaluators)
- **Домен:** pollmevals.com (нужно зарегистрировать)
- **Статус:** v0.1 draft, pre-MVP
- **Цель:** open платформа scaffolding evaluation с panel of LLM judges
- **Лицензия:** код MIT, данные CC BY-SA 4.0

## Что мы строим

Платформа которая отвечает на конкретный вопрос: "Какой стек (модель + agent CLI + skills + память + validator) оптимален под задачу класса X с бюджетом Y и регион Z?"

Главное отличие от существующих лидербордов: меряем **полные стеки**, а не голые модели.

## Уникальное ценностное предложение (8 фишек)

1. **Scaffolding evaluation** — единственная платформа которая меряет стеки целиком
2. **Panel of LLM judges** с ротацией, blind labels, median scoring
3. **Cost-aware results** — $/task, $/correct answer
4. **Geo-aware latency** из 4 регионов
5. **Weekly + flagship-triggered cadence**
6. **Community-driven additions**
7. **Full reproducibility** — все промпты, версии, raw outputs публичные
8. **Versioned tasks** — изменения через версии, старые сравнения остаются валидными

## Целевые юзеры (см. 01-problem-vision.md)

- **A: Engineering lead** — выбирает стек для команды ($)
- **B: Indie hacker / founder** — оптимизирует свой стек (free)
- **C: Researcher / analyst** — пишет отчёты ($)
- **D: Model creator** — хочет честное сравнение (sponsored eval $$$)

## Технический стек

### Frontend
- **Next.js 15** (App Router) + Tailwind + shadcn/ui
- Vercel хостинг (edge functions для leaderboards, SSG для статичных страниц)
- React Query, без heavy state

### Backend API
- **Hono on Bun** или Express on Node
- Docker контейнер на Fly.io или Railway
- OpenAPI/Swagger

### Database
- **Postgres** (Supabase или Neon)
- Schema migrations через Drizzle или Prisma

### Object storage
- **Cloudflare R2** (bandwidth бесплатный)
- Content-hash имена файлов для immutability

### Cache + Queue
- **Upstash Redis**
- Leaderboard cache (10-min TTL)
- BullMQ для task queue

### Eval orchestrator
- **Inspect AI** обёрнут в свой Python сервис
- Гоняет phase / model / task / seed комбинации

### Inference gateway
- **LiteLLM proxy** на отдельном Docker
- Все вызовы моделей через него

### Workers
- 4 Docker контейнера в 4 регионах
- DigitalOcean droplets или Hetzner Cloud

### Self-hosted inference
- **Runpod vLLM** для open-weight 70B+
- **Cerebras** для fast inference
- **OpenRouter** для cloud closed

### CI/Observability
- GitHub Actions для deploy
- Sentry для errors
- Grafana + Prometheus для metrics
- Posthog для analytics

## Главные метрики успеха

### Quality signals
- Inter-judge agreement (Krippendorff α) ≥ 0.75
- Calibration deviation < 1.5 баллов
- Run reproducibility — повтор того же run delta < 0.5 балла

### Audience signals
- /leaderboards unique visitors / неделя
- /api active keys
- GitHub stars на open-source eval repo
- HN / Reddit / Twitter mentions
- Citation в академических papers (золотой стандарт)

### Business signals (Tier 1+)
- Tier 1 paid users
- Tier 2 deals signed
- Sponsored evals (count, $)

## Что POLLMEVALS НЕ делает

- Не меряет human preference (это Chatbot Arena)
- Не focuses на голых моделях (это Artificial Analysis, BenchLM)
- Не leetcode-style benchmark (это HumanEval, MBPP)
- Не выполняет peer review длинных формальных папера (мы публикуем еженедельно)
- Не делает custom enterprise eval за плату — это Tier 2 услуга после v1.0

## Pre-launch checklist

- [ ] Зарегистрировать pollmevals.com + .ai + .io
- [ ] Trademark check (опционально)
- [ ] Открыть GitHub org `pollmevals`
- [ ] Создать MIT-licensed core repo
- [ ] Опубликовать draft methodology в `/methodology` (можно как Gist на старте)
- [ ] Подключить Twitter, Telegram, RSS
- [ ] Финализировать 20 задач (с gold + evaluator) для Фазы 1
- [ ] Setup LiteLLM на dev-окружении
- [ ] Setup Inspect AI с custom tasks
- [ ] Первый smoke-run на 3 задачах × 5 моделях
- [ ] Postmortem smoke-run, iterate
- [ ] Первый полный weekly run + публикация

---

# 06 — Site Architecture

## Информационная архитектура

Сайт делится на 4 крупных раздела:

```
POLLMEVALS (pollmevals.com)
│
├── Data (что измерено)
│   ├── /leaderboards
│   ├── /models/[slug]
│   ├── /stacks/[slug]
│   ├── /tasks/[slug]
│   ├── /compare
│   └── /runs/[hash]
│
├── Methodology (как измеряем)
│   ├── /methodology
│   ├── /judges
│   ├── /calibration
│   ├── /scoring
│   └── /blog
│
├── Community (кто участвует)
│   ├── /vote
│   ├── /propose-model
│   ├── /propose-task
│   ├── /propose-stack
│   └── /discuss
│
└── Pro / API (для серьёзных)
    ├── /api
    ├── /datasets
    ├── /status
    ├── /pricing
    ├── /changelog
    └── /disclosures
```

---

## Описание ключевых страниц

### `/leaderboards` — главная посадочная

- Три tab: **By Model** / **By Stack** / **By Task class**
- Фильтры: тип задачи, регион, бюджет (slider $/task)
- Дефолтная сортировка: quality (composite score)
- Last-week deltas сверху ("что улучшилось / ухудшилось")
- Live data, обновление еженедельно

### `/models/[slug]` — деталка модели

- **Header:** vendor logo, версия с pinned tag, badge open-weight vs closed
- **Radar** по 8 категориям задач
- **Historical chart** через все weekly runs
- **Latency table** по регионам
- **$/task** разбивка
- **Top 3 stacks** для этой модели (после Фазы 2)
- **Raw outputs** ссылки на S3 (по hash)

### `/stacks/[slug]` — деталка стека

- **Composition:** какие L0-L8 слои использует
- **Best matched models** для этого стека
- **Categories where it shines** (типы задач)
- **Cost overhead** vs голая модель
- **Quality lift** vs голая модель

### `/tasks/[slug]` — деталка задачи

- **Description** + примеры входов
- **Gold solution** (после первого weekly run, чтобы избежать contamination для свежей задачи)
- **Evaluator code** (open source, в репо)
- **History** по моделям (radar + table)
- **Submissions browser** — посмотреть как каждая модель решала

### `/compare` — side-by-side

- Выбираешь до 4 моделей/стеков
- Радар overlay + table + cost-quality scatter
- Shareable URL (encoded в query params)

### `/runs/[hash]` — доказательство воспроизводимости

- **Версии всего** (Inspect AI, LiteLLM, vLLM, model tags с datetime)
- **Timestamps** (start, end)
- **Total tokens / cost**
- **Raw outputs download** as tarball
- **JSON manifest** для воспроизведения

### `/methodology`

- Полная методика
- **Версионируется** (v1.0, v1.1, ...)
- Diff'ы между версиями
- Без неё credibility = 0

### `/judges`

- Текущий состав судей
- **Inter-judge agreement matrix** (Cohen's kappa heatmap)
- **Calibration scores** для каждого
- **History changes** (когда и почему меняли пул судей)

### `/calibration`

- Калибровочные задачи с известными score'ами
- Live results — насколько судьи дрейфуют
- Прозрачность того что pipeline работает

---

## Data Model — Postgres schema

```sql
-- Модели
CREATE TABLE models (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL,
  vendor        TEXT NOT NULL,
  version_tag   TEXT NOT NULL,                  -- "claude-opus-4-7-20260315"
  is_open_weight BOOLEAN NOT NULL DEFAULT false,
  context_window INTEGER NOT NULL,
  max_output_tokens INTEGER NOT NULL,
  added_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deprecated_at TIMESTAMPTZ,
  proposed_by   UUID REFERENCES users(id),
  votes_count   INTEGER NOT NULL DEFAULT 0
);

-- Где модель хостится
CREATE TABLE model_providers (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_id            UUID NOT NULL REFERENCES models(id),
  provider_name       TEXT NOT NULL,           -- "openrouter" / "cerebras" / "runpod"
  endpoint_url        TEXT NOT NULL,
  region              TEXT NOT NULL,           -- "us-east" / "eu-central" / ...
  price_input_per_mtok  NUMERIC(10,4) NOT NULL,
  price_output_per_mtok NUMERIC(10,4) NOT NULL,
  rate_limit_rpm      INTEGER,
  rate_limit_tpm      INTEGER
);

-- Стеки обвязки
CREATE TABLE stacks (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            TEXT UNIQUE NOT NULL,
  name            TEXT NOT NULL,
  description     TEXT NOT NULL,
  base_model_id   UUID NOT NULL REFERENCES models(id),
  agent_cli       TEXT,                        -- "claude-code" / "codex" / "gemini" / "hermes"
  has_tools       BOOLEAN NOT NULL DEFAULT false,
  has_skills      BOOLEAN NOT NULL DEFAULT false,
  has_file_memory BOOLEAN NOT NULL DEFAULT false,
  has_vector_memory BOOLEAN NOT NULL DEFAULT false,
  vector_memory_type TEXT,                     -- "mem0" / "hindsight" / "letta" / "zep"
  has_subagents   BOOLEAN NOT NULL DEFAULT false,
  has_validator   BOOLEAN NOT NULL DEFAULT false,
  has_framework   BOOLEAN NOT NULL DEFAULT false,
  framework_name  TEXT                         -- "forgeplan" / "voltagent"
);

-- Задачи (versioned)
CREATE TABLE tasks (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            TEXT NOT NULL,
  version         TEXT NOT NULL,               -- "1.0", "1.1"
  category        TEXT NOT NULL,
  difficulty      TEXT NOT NULL,               -- "easy" / "medium" / "hard"
  language        TEXT,                        -- "typescript" / "python" / "sql"
  description_md  TEXT NOT NULL,
  prompt_template TEXT NOT NULL,
  gold_solution_uri TEXT NOT NULL,             -- s3:// path
  evaluator_uri   TEXT NOT NULL,               -- s3:// path
  expected_tokens_in  INTEGER,
  expected_tokens_out INTEGER,
  added_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  retired_at      TIMESTAMPTZ,
  parent_task_id  UUID REFERENCES tasks(id),   -- предыдущая версия
  UNIQUE(slug, version)
);

-- Weekly runs
CREATE TABLE runs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hash             TEXT UNIQUE NOT NULL,        -- detеrministic от version snapshot
  run_type         TEXT NOT NULL,               -- "weekly" / "flagship_triggered" / "smoke"
  started_at       TIMESTAMPTZ NOT NULL,
  completed_at     TIMESTAMPTZ,
  inspect_ai_version TEXT NOT NULL,
  litellm_version  TEXT NOT NULL,
  vllm_version     TEXT,
  total_cost_usd   NUMERIC(10,2),
  total_input_tokens BIGINT,
  total_output_tokens BIGINT
);

-- Eval results
CREATE TABLE evals (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id          UUID NOT NULL REFERENCES runs(id),
  model_id        UUID NOT NULL REFERENCES models(id),
  stack_id        UUID REFERENCES stacks(id),  -- NULL для Фазы 1 (голая модель)
  task_id         UUID NOT NULL REFERENCES tasks(id),
  seed            INTEGER NOT NULL,
  region          TEXT NOT NULL,
  raw_output_uri  TEXT NOT NULL,               -- s3:// path
  ttft_ms         INTEGER,
  total_latency_ms INTEGER,
  tokens_in       INTEGER,
  tokens_out      INTEGER,
  cost_usd        NUMERIC(10,6),
  automatic_metrics_json JSONB,                -- correctness, CC, coverage, lint
  final_score     NUMERIC(4,2),                -- 0-10
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Judgments (panel)
CREATE TABLE judgments (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  eval_id         UUID NOT NULL REFERENCES evals(id),
  judge_model_id  UUID NOT NULL REFERENCES models(id),
  judge_order     INTEGER NOT NULL,            -- порядок в randomized batch
  rubric_scores_json JSONB,                    -- по каждому критерию
  total_score     NUMERIC(4,2),
  reasoning_text_uri TEXT,
  agreement_with_consensus NUMERIC(4,3)        -- для inter-rater stats
);

-- Calibration
CREATE TABLE calibration_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  judge_model_id  UUID NOT NULL REFERENCES models(id),
  calibration_task_id UUID NOT NULL,
  expected_score  NUMERIC(4,2) NOT NULL,
  given_score     NUMERIC(4,2) NOT NULL,
  deviation       NUMERIC(4,2) NOT NULL,
  ran_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Community votes
CREATE TABLE votes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  voted_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  vote_type       TEXT NOT NULL,               -- "model" / "task" / "stack"
  target_id       UUID NOT NULL,
  weight          NUMERIC(3,2) NOT NULL DEFAULT 1.0
);

-- Users
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  github_id       BIGINT UNIQUE,
  github_login    TEXT UNIQUE,
  email           TEXT,
  vote_weight     NUMERIC(3,2) NOT NULL DEFAULT 1.0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Eval pipeline — как weekly run устроен

1. **Cron триггер** в понедельник 03:00 UTC создаёт `run` с уникальным hash
2. **Snapshot стейта**: версии всех моделей с current `version_tag`, версии всех инструментов
3. **Worker'ы в 4 регионах поднимаются** через docker-compose
4. **Каждый worker** прогоняет назначенные ему (модели × задачи × 5 seeds) через round-robin queue
5. **Сырые outputs** → S3 с content-hash именами
6. **Automatic metrics** считаются сразу после каждого eval (pytest, eslint, radon)
7. **Anonymization pipeline** превращает каждый output в "submission_xyz" без метаданных
8. **Judge phase**: панель 5 судей × все eval'ы, каждый судья в отдельном LiteLLM call, randomized order, blind labels
9. **Aggregation**: median scores, inter-judge agreement, bootstrap CI
10. **Drift detection**: сравнение с прошлой неделей. Если delta > 2σ — alert
11. **Calibration check**: судьи прогнаны через golden set. Если deviate — flag + degrade priority
12. **Database update** atomically — либо весь run, либо ничего
13. **Cache invalidation** + leaderboard rebuild
14. **Public announcement** в blog + Twitter + Telegram + RSS

---

## API endpoints

### Public read-only

```
GET /api/v1/leaderboards/{by-model|by-stack|by-task}
GET /api/v1/models
GET /api/v1/models/{slug}
GET /api/v1/stacks
GET /api/v1/stacks/{slug}
GET /api/v1/tasks
GET /api/v1/tasks/{slug}
GET /api/v1/runs/{hash}
GET /api/v1/evals?model={slug}&task={slug}&region={code}
GET /api/v1/judges
GET /api/v1/calibration
```

### Pro / Authenticated

```
POST /api/v1/proposals (model | task | stack)
POST /api/v1/votes
GET /api/v1/datasets (signed download URLs)
```

### Internal (только для оркестратора)

```
POST /api/v1/runs (создать новый)
POST /api/v1/runs/{hash}/evals (записать результат)
POST /api/v1/runs/{hash}/complete
```

---

## Rate limits

- **Public unauthenticated:** 100 req/hour per IP
- **Tier 1 ($50/mo):** 10 000 req/hour
- **Tier 1 ($500/mo):** 100 000 req/hour + bulk datasets
- **Bulk download** — только через `/datasets` (raw Parquet files), не через API

---

# 07 — Onboarding Flows

Три параллельных flow для добавления новых сущностей: **модель**, **стек обвязки**, **задача**. У каждого свои validation criteria и calibration steps.

---

## Flow 1: Добавление новой модели или вендора

### Step 1: Proposal через `/propose-model`

Форма принимает YAML:

```yaml
slug: claude-opus-4.8
name: Claude Opus 4.8
vendor: anthropic
context_window: 200000
max_output_tokens: 8192
api_endpoint: https://api.anthropic.com/v1/messages
api_format: anthropic_native  # или openai, gemini, ollama, vllm
official_docs_url: https://docs.anthropic.com/...
pricing_input_per_mtok: 15.00
pricing_output_per_mtok: 75.00
is_open_weight: false
release_date: 2026-06-15
proposed_reason: "Just released, sets new SOTA on..."
```

### Step 2: Автоматическая проверка

- [ ] API endpoint достижим (HEAD request)
- [ ] Модель отвечает на ping prompt
- [ ] Tokens counter возвращает корректные числа (test prompt с известным token count)
- [ ] Pricing соответствует официальной странице vendor'а (web scrape)
- [ ] Имя/slug уникален
- [ ] Не дубликат существующей записи

### Step 3: Community vote

Модель попадает в `/vote` страницу. Нужно X голосов за 7 дней:
- **Старт:** X = 20
- **Скейлится** с ростом аудитории

Для **критичных моделей** (флагман от major vendor) — **fast track без голосования**, но с обязательным disclosure: badge "Fast-tracked: flagship release".

### Step 4: Manual review

Maintainer (на старте — Eli один) проверяет:
- Не дубликат / не rebrand
- Не нарушает ToS vendor'а (некоторые ToS запрещают benchmark publication)
- Стабильно отвечает на 10 sanity-check промптов
- Pricing подтверждён

### Step 5: Calibration run

Перед добавлением в weekly grid, модель прогоняется через мини-grid:
- 5 calibration tasks (с известными expected scores)
- 3 регулярных задачи из текущего пула

Это даёт **первичный baseline** и проверяет что pipeline работает с её API/токенизацией.

### Step 6: LiteLLM config update

Модель добавляется в `litellm_config.yaml` с pinned version tag.

```yaml
- model_name: claude-opus-4.8
  litellm_params:
    model: openrouter/anthropic/claude-opus-4-8
    api_key: os.environ/OPENROUTER_API_KEY
```

### Step 7: Public announcement

- `/changelog` запись
- RSS / Twitter / Telegram пост
- Модель попадает в следующий weekly run
- На странице `/models/[slug]` появляется badge "Just added — first results in 6 days"

---

## Flow 2: Добавление нового стека (scaffolding combo)

### Step 1: Proposal через `/propose-stack`

```yaml
slug: claude-code-skills-mem0
name: Claude Code + Skills + mem0
description: |
  Стандартный Claude Code с включёнными skills и интегрированной
  семантической памятью через mem0 для cross-session context.
base_model_slug: claude-sonnet-4.6
agent_cli: claude-code
agent_cli_version: 2.1.x
layers:
  - L1_system_prompt: true
  - L2_tools: true
  - L3_skills: ["frontend-design", "pdf"]
  - L4_file_memory: false
  - L5_vector_memory: mem0
  - L6_subagents: false
  - L7_validator: false
  - L8_framework: null
implementation_repo: https://github.com/...
reproducibility_script: docker-compose.yml + Makefile
proposed_reason: "Combines best-known practices for SWE tasks"
```

### Step 2: Reproducibility check

Самое сложное в стеках. Maintainer должен:
- [ ] Запустить docker-compose у себя
- [ ] Получить тот же hash что заявлен в proposal
- [ ] Прогнать 1 тестовую задачу — получить осмысленный output

Если стек **нельзя воспроизвести** — отказ. Прозрачно.

### Step 3: Calibration

Прогоняется на 3 задачах из текущего пула + 2 calibration tasks. Сравнивается с base модель этого стека:
- Если quality_lift < 5% и cost_overhead > 50% — flag "may not be useful"
- Если variance высокая — flag "needs more seeds"

### Step 4: Public addition

Стек добавляется в `/stacks` с indication "Newly added".

---

## Flow 3: Добавление новой задачи

### Step 1: Proposal через `/propose-task`

```yaml
slug: be_05
category: backend
difficulty: medium
language: typescript
description: |
  Implement a rate limiter middleware for Express that:
  - Uses sliding window algorithm
  - Stores state in Redis
  - Returns proper headers (X-RateLimit-Limit, X-RateLimit-Remaining)
  - Handles burst traffic correctly
real_world_source: "From production code at Y company, anonymized"
permission_to_publish: yes
gold_solution: |
  // Code here, 100-200 lines
test_cases: |
  // Test code here, must cover happy path + edge cases + errors
evaluator_command: |
  vitest run && eslint --max-complexity 10 && tsc --noEmit --strict
expected_metrics:
  correctness: 0.9
  test_coverage: 0.85
  complexity: 0.8
  pattern_match: 0.85
weights:
  correctness: 0.40
  test_coverage: 0.15
  complexity: 0.10
  linter: 0.10
  type_safety: 0.10
  pattern_match: 0.15
```

### Step 2: Validation

- [ ] Gold solution runs without errors
- [ ] Gold solution passes its own tests
- [ ] Evaluator script runs without errors
- [ ] Slug уникален или это новая версия существующей задачи
- [ ] **Contamination check:** Google search по описанию и кусочкам кода — нет ли совпадений с публичными источниками

### Step 3: Calibration через "known good / bad / medium"

Чтобы задача была хорошим discriminator'ом, она должна давать **разный score** на разных уровнях качества решения. Maintainer пишет:
- One обвышенно gold version → expected ~9-10
- One mediocre version → expected ~5-6
- One buggy version → expected ~2-3

Прогоняется через panel of judges. Если **rank correlation < 0.8** между expected и given → задача плохо discriminates → переписать или отклонить.

### Step 4: Add to next weekly run

Задача попадает в pool со statusом "newly added — first results in 6 days".

---

## Flow 4: Версионирование задачи

Когда задача меняется (добавили tests, исправили описание, изменили evaluator):

1. Создаётся **новая запись** в `tasks` с инкрементированной версией
2. **Старые eval'ы** с предыдущей версией остаются валидными для своей версии
3. **На сайте** — на странице задачи показывается diff и история
4. **Новый weekly run** использует новую версию

Это позволяет:
- Apples-to-apples сравнения для конкретной версии задачи
- Fair historical tracking
- Возможность retire старой версии без потери data

---

## Flow 5: Sponsored evaluations

Vendor хочет ускоренного добавления своей модели или приоритетного eval:

### Disclosure requirements

- Бейдж "Sponsored fast-track" на странице модели
- Полная информация в `/disclosures`: who, when, how much, what was included
- **Никаких изменений в methodology** для sponsored evals
- Sponsored = быстрее в очереди, **не лучше** в результатах

### Pricing (черновик)

- Expedited model addition: $500 (в течение 3 рабочих дней vs стандартные 7 дней + community vote)
- Priority weekly run inclusion: $1000 (гарантия в следующем weekly run)
- Custom region testing: $2000 (extra workers в специфическом регионе)
- Custom task evaluation against their model: $5000-20000

Все sponsored evals публикуются с полной прозрачностью.

---

## Flow 6: Deprecation

Когда модель снимается с production (vendor sunsets, или критический баг):

1. Maintainer ставит `deprecated_at` timestamp
2. Модель **остаётся в historical data** — citation friendly
3. На странице — badge "Deprecated"
4. Из активных leaderboards убирается
5. Из weekly run выпадает
6. Постится announcement в blog

---

# 08 — Must Consider (то что обязательно учесть)

Список критичных вещей которые обычно упускают. Если их не учесть с самого начала — переделывать дороже чем сразу заложить.

---

## 1. Reproducibility & Immutability

### Run immutability

Каждый run — **immutable после завершения**. Никаких "потом подправим оценку". Если ошибка — **новый run** с тем же task hash, но другим run hash. Это required для научного credibility.

Хранение:
- Run record в Postgres
- Все raw outputs в R2 с content-hash именами
- Manifest файл с версиями всех инструментов

### Reproduce.sh script

В каждом run есть скрипт `reproduce.sh` который позволяет независимому исследователю **воспроизвести точно тот же run**:

```bash
#!/bin/bash
# reproduce.sh для run hash abc123...

export INSPECT_AI_VERSION=0.4.12
export LITELLM_VERSION=1.83.2
export VLLM_VERSION=0.6.3

git checkout v0.1.4  # тег версии POLLMEVALS
pip install -r requirements.lock
docker-compose -f infra/docker-compose.yml up -d

python orchestrator.py \
  --models-snapshot snapshots/abc123.models.json \
  --tasks-snapshot snapshots/abc123.tasks.json \
  --seed 1234 \
  --output ./reproduction-output
```

---

## 2. Task versioning

Когда задача меняется — это **новая версия** с тем же `slug` но другим `version`. Старые eval'ы остаются валидными для своей версии.

**Зачем:** comparison "Claude Opus 4.6 на task v1.0" vs "Claude Opus 4.7 на task v1.0" — apples to apples.

**Page:** `/tasks/[slug]` показывает все версии + diff между ними. Старые версии помечены "archived".

---

## 3. Model drift detection — уникальный insight

Closed-API модели (Claude, GPT, Gemini) меняются "за кулисами" даже при том же tag.

**Что делаем:**
- Если результаты конкретной модели за неделю drift > 2σ от трёхмесячного baseline — alert
- Это **публикуется** как отдельный пост: "Claude Opus 4.7 показал значимое изменение поведения в week 23"
- Скорее всего vendor что-то изменил без публичного announcement
- Это **уникальный insight** который никто другой не делает

---

## 4. Contamination detection

Каждая задача имеет content hash. Регулярно (раз в месяц) гуглим:
- Хеш задачи
- Уникальные кусочки описания
- Имена функций / тестов из gold

Если задача появилась:
- В обучающем датасете
- В GitHub readme
- В blog post
- На Stack Overflow

→ Задача **compromised и retired**. Замена в pool.

У LiveBench это есть, нам тоже нужно.

---

## 5. Anti-gaming через rotation

**20% задач — held-out в private set**, не публикуются. Они меняются ежемесячно. Это страховка от того что vendors начнут оптимизировать на public set.

Реализация:
- Public set: 16 задач (видны всем)
- Held-out set: 4 задачи (только у maintainers)
- Held-out набор пересоздаётся каждый месяц
- На сайте — индикация "results включают held-out tasks"

---

## 6. Code execution safety

Сгенерированный моделями код **выполняется в изолированных Docker контейнерах** с жёсткими ограничениями:

```yaml
# Docker compose для evaluator
services:
  evaluator:
    image: pollmevals/evaluator:v1
    network_mode: none           # NO network access
    read_only: true              # read-only filesystem
    tmpfs:
      - /tmp:size=100M           # ограниченный writable tmpfs
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 50
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    ulimits:
      nofile: 1024
      fsize: 10485760            # 10 MB max file size
```

И timeout 60 секунд **hard kill** на каждый evaluator.

---

## 7. Privacy / Legal

### Лицензии
- **Код:** MIT
- **Датасеты:** CC BY-SA 4.0 (требует attribution, не запрещает commercial use)
- **Tasks proprietary:** для задач basis from production code — нужно explicit permission от автора

### GDPR
Community аккаунты:
- Right to access (download my data)
- Right to deletion
- Right to portability
- Storage в EU (Hetzner Frankfurt)

### Vendor ToS
Некоторые vendors запрещают benchmark publication. Проверять каждого:
- Anthropic ToS — позволяет benchmarks
- OpenAI ToS — позволяет benchmarks с restrictions (no model training on outputs)
- Google ToS — проверить актуальное
- Open-weights — нет ограничений

### IP концов задач
Если задача basis from production code — нужно:
- Permission от автора в письменном виде
- Sufficient anonymization
- Disclosure в task page

---

## 8. Statistical rigor (критично!)

См. 02-methodology.md, секция 7. Главное:

- **Multiple seeds** (≥5) per run
- **Bootstrap CI** на всех числах
- **Effect sizes** (Cohen's d) рядом с p-values
- **Inter-judge agreement** (Krippendorff α) обязательно публикуется

Без этого блог-пост = "цифры с потолка". С этим — research.

---

## 9. Cost transparency

Total inference cost каждого run **публикован** в `/runs/[hash]`.

**Зачем:**
1. Честность с читателем
2. Credibility (вот сколько стоит это исследование)
3. Помогает другим оценить cost воспроизведения

---

## 10. Sponsored evaluations protocol

См. 07-onboarding-flows.md, Flow 5.

Ключевые принципы:
- **Всегда disclosed** (badge на странице модели)
- **Полная информация** в `/disclosures`
- **Никаких изменений в methodology** для sponsored
- Sponsored = быстрее, **не лучше**

Это спасает от scandal по типу LMSYS leaderboard illusion (paper 2025 показал что vendors могли влиять на rankings).

---

## 11. API rate limiting & fair use

**Защита от scraping** через Cloudflare:
- Public unauthenticated: 100 req/hour per IP
- Tier 1 ($50/mo): 10 000 req/hour
- Tier 1 ($500/mo): 100 000 req/hour + bulk datasets

**Bulk download** — только через `/datasets` (raw Parquet files), не через scraping API.

---

## 12. Operational transparency

`/status` показывает:
- Last run timestamp
- Next scheduled run
- Current health each worker по регионам
- Uptime statistics

Если что сломалось — **публичный postmortem** в `/blog`.

---

## 13. Multilingual support (v2)

**MVP:** все промпты задач только английский.

**v2:** multilingual задачи — отдельная категория (русский, китайский, испанский) с native-speaker judges. Это для **версии 2**, не для MVP.

---

## 14. Disclosure of conflicts (для Eli лично)

Eli ведёт ForgePlan. Stack `claude-code + forgeplan` будет evaluated рядом с конкурентами.

**Обязательно disclosed:**
- На странице того стека: "POLLMEVALS оператор является разработчиком ForgePlan"
- "Методология калибрована независимо"
- "Третий-сторон review TBD"

Это спасает от обвинений в bias.

---

## 15. Anti-bot для community vote

- **GitHub OAuth обязательно**
- Аккаунту минимум **6 месяцев + 10 contributions**
- Это убирает spam без надоедливого captcha

---

## 16. Sunset policy

Deprecated модели:
- Остаются в database с пометкой "deprecated" + дата
- Их **данные сохраняются** для historical context
- **Не отвергать** → не нарушать citation тех кто ссылался

---

## 17. Backup & disaster recovery

- **Postgres** daily snapshot в R2
- **Raw outputs** в R2 уже redundant (multi-zone)
- **Open replica** на HuggingFace Datasets обновляется weekly с лагом — если домен/инфра умерла, public архив сохранится

---

## 18. Self-bias for maintainers (Eli's role)

Поскольку Eli является и автором задач, и оператором POLLMEVALS — есть риск self-bias.

**Mitigation:**
- Open-source все задачи и evaluators
- Community challenges на каждую задачу
- 3rd party review (попросить независимого инженера прогнать pipeline и проверить)
- Public methodology — каждое решение задокументировано и justifiable

---

## 19. Maintenance overhead

Реалистичная оценка времени на maintenance после MVP launch:

- **Weekly run baby-sitting:** 2-4 часа (проверка что run прошёл, alert investigation)
- **Community moderation:** 1-3 часа (review proposals, manual quality checks)
- **Blog post weekly:** 4-6 часов (от анализа результатов до публикации)
- **Bug fixes / improvements:** 5-10 часов

**Итого ~15-25 часов в неделю** только на operate. Это **половина full-time job**.

Это нужно знать на старте — иначе burnout через 2-3 месяца.

---

## 20. Decision log

В отдельном файле `/methodology/decisions.md` — **immutable log** всех методологических решений:

```markdown
## 2026-05-21 — Решение использовать Krippendorff α (не Fleiss kappa)

**Контекст:** judges дают continuous scores, не categorical
**Decision:** использовать Krippendorff α с interval distance
**Rationale:** Krippendorff обрабатывает missing data и continuous scores
**Authors:** [E. Maintainer]
**Reviewers:** [TBD third-party review]
```

Это и для credibility, и для будущих maintainers — понимать "почему делали так".

---

# 09 — Business Model

## Tier-based монетизация (4 уровня риска)

### Tier 0: Open data, no monetization

**Что:** публичный leaderboard + open datasets + блог-серия.

**Кто платит:** никто. Это **reputation play**.

**Что даёт Eli:**
- Авторитет как expert на тему scaffolding evaluation
- Network effects — позже легче конвертировать в продукт
- Source for консалтинг/курс/SaaS leads

**Стоимость maintain:** ~$1000/мес на inference + инфра + время.

**Recommended для старта — все начинают здесь.**

---

### Tier 1: API access ($-$$$)

**Что:** бесплатный leaderboard, **платный** доступ к raw data через API.

**Pricing:**
- **Hobby** $0 — 100 req/hour, basic data
- **Pro** $50/mo — 10 000 req/hour, full data, historical
- **Team** $500/mo — 100 000 req/hour, bulk datasets, priority support

**Кто платит:**
- Model producers (для маркетинга "мы первые на POLLMEVALS")
- Researchers / analysts
- VC firms для due diligence
- Enterprise teams для internal dashboards

**Реализация:** Stripe + Cloudflare API gateway.

**Аналог:** Artificial Analysis работает по этой схеме.

---

### Tier 2: Custom evals for clients ($$)

**Что:** компания приходит "у нас свой стек, запустите его через POLLMEVALS методологию на наших задачах".

**Pricing:**
- Quick eval (existing stack, new task set): $5-10k
- Full eval (custom stack + custom tasks + custom report): $15-30k

**Кто платит:**
- Engineering teams выбирающие LLM-стек
- Consultancies (Accenture, Deloitte) которые делают AI advisory
- Companies оценивающие свой AI investment

**Реализация:** ручная работа. Eli как expert + 1-2 контрактора.

**Это classic консалтинг под бренд платформы.**

---

### Tier 3: Sponsored evals ($$)

**Что:** model producer платит чтобы их новую модель прогнали с приоритетом и опубликовали.

**Pricing (черновик):**
- Expedited model addition: $500
- Priority weekly run inclusion: $1000
- Custom region testing: $2000
- Custom task eval: $5-20k

**Кто платит:**
- Anthropic, OpenAI, Google — для launch новых моделей
- Open-weight teams (Meta, Mistral, DeepSeek)
- New entrants (xAI, Alibaba)

**Реализация:**
- Чёткая disclosure policy (см. 08-must-consider.md, секция 10)
- Sponsored = быстрее в очереди, **не лучше в результатах**
- Прозрачные badges на страницах

**Risk:** scandal по типу LMSYS leaderboard illusion. Mitigation: радикальная прозрачность.

---

### Tier 4: Enterprise white-label ($$$)

**Что:** "запустите POLLMEVALS платформу на нашем приватном codebase для оценки внутренних агентов".

**Pricing:** $50k - $500k per контракт.

**Кто платит:**
- FAANG-tier компании с internal AI tooling
- Financial services с compliance-критичными use cases
- Government (US, EU) для evaluating AI suppliers

**Реализация:**
- Self-hosted POLLMEVALS instance
- Custom task pool под их domain
- White-label dashboard
- Support contract

**Это рынок Scale AI и Surge AI** — там money есть, но это **отдельная компания**, не пет-проект.

---

## Подъёмность по фазам

### Pre-MVP (months 0-3)
- **Tier 0** only
- Cost: ~$500/мес (low-volume runs)
- Revenue: $0
- Goal: первые 5 blog posts серии, audience build

### MVP launch (months 3-6)
- **Tier 0 + Tier 1 Hobby**
- Cost: ~$1500/мес (weekly runs)
- Revenue: $0-500/мес (early adopters)
- Goal: 100 MAU, 10 GitHub stars/week growth

### Early growth (months 6-12)
- **Tier 0 + Tier 1 full**
- Cost: ~$3000/мес
- Revenue: $2-10k/мес
- Goal: break even, 500 MAU

### Established (year 2+)
- **All tiers active**
- Cost: ~$10-20k/мес (full team)
- Revenue: $30-100k/мес
- Hire: 1-2 engineers, 1 community manager
- Goal: profitable business

---

## Reality check — твои ресурсы

У Eli уже есть:
- ForgePlan
- Orchestra
- Gerts.ai
- Spa бизнес
- AI-курс
- Консалтинг

**Шестой полноценный продукт ты не потянешь** при текущей загрузке. Это надо честно сказать.

### Реалистичный путь

1. **Сначала серия постов** (3-4 месяца). Это и есть proof-of-concept. Контент сам по себе ценен, репутация выстраивается. Доступ к Eli как эксперту в "scaffolding evaluation" — это актив.

2. **Если посты заходят** (10k+ просмотров, обсуждения в HN/Reddit/Twitter), **запускаешь MVP**. На этом этапе можно:
   - Привлечь со-основателя
   - Нанять 1 девелопера через консалтинг-деньги
   - Запустить freelance contributor program

3. **Если MVP получает 100+ MAU аудитории**, тогда коммерциализация. До этого момента — open data + блог + Tier 0.

Это **3-фазная стратегия с реальными gating criteria**.

---

## Метрики чтобы понять "идёт ли"

### После 1 серии постов (week 4)
- 1000+ unique visitors на blog
- 20+ comments / discussions on HN/Reddit
- 50+ GitHub stars on demo repo
- 5+ mentions от credible accounts in AI space
- **Если меньше — не идёт. Стоп, делай другое.**

### После MVP launch (month 6)
- 100+ MAU
- 10+ Tier 1 Hobby signups
- 1+ Tier 1 Pro signup
- 1+ Tier 2 inquiry
- **Если меньше — фокусируйся на контенте, не продукте.**

### После 12 месяцев
- 500+ MAU
- $5k+ MRR
- Citations в academic papers (это серьёзно)
- **Если меньше — это side project, не business.**

---

## Что НЕ делать

- **Не пытаться сразу делать всё** — outdoors можно прогореть на инфраструктуре до того как audience сформирована
- **Не превращать в платный сразу** — сначала reputation, потом monetization
- **Не конкурировать с Arena напрямую** — у них $1.7B valuation, не победишь, фокус на свою нишу
- **Не обещать enterprise white-label** до того как есть solid product
- **Не запускать sponsored evals** до того как methodology зафиксирована и проверена independent reviewers

---

# 10 — Competitive Landscape

## TL;DR

Рынок LLM evaluation **очень занят**, но **никто не делает scaffolding evaluation** систематично. Это уникальная ниша.

## Карта рынка

Делю по двум осям:
- **X-axis:** что меряется (модели → стеки)
- **Y-axis:** как агрегируется (single judge → multi-source / panel)

```
Multi-source │ LMSYS Arena                     [POLLMEVALS]
             │ Artificial Analysis              ← пустая ниша!
             │ BenchLM
             │ SEAL (Scale AI)
─────────────┼───────────────────────────────────
Single judge │ HF Open LLM Leaderboard
             │ SWE-bench, Aider, BigCodeBench
             │ LiveBench, TokenMix
             │
             └───────────────────────────────────
                Модели                  Scaffolding
```

**Все существующие игроки** в левой половине — меряют только модели. **POLLMEVALS** занимает пустой правый верхний квадрант.

---

## Существующие игроки — детально

### LMSYS Arena (lmarena.ai)

- **Что:** human preference через blind A/B battles
- **Масштаб:** 6M+ голосов, 140+ моделей, $1.7B valuation
- **Сильные стороны:** реальные люди, real-time, стандарт индустрии
- **Слабые стороны:** subjective, hard to reproduce, scandal "Leaderboard Illusion" paper в 2025
- **Конкурент с POLLMEVALS?** Нет — мы про automated objective scoring, они про human preference

### Artificial Analysis (artificialanalysis.ai)

- **Что:** composite intelligence + cost + speed для 356 моделей
- **Сильные стороны:** широкое покрытие моделей, cost/speed данные
- **Слабые стороны:** только голые модели, no scaffolding, automated metrics только
- **Конкурент с POLLMEVALS?** Нет — близко по бизнес-модели (free leaderboard + paid API), но другая ниша

### BenchLM (benchlm.ai)

- **Что:** 228 моделей × 186 бенчмарков, агрегатор
- **Сильные стороны:** широкое покрытие бенчмарков
- **Слабые стороны:** только агрегация, не собственная methodology
- **Конкурент?** Нет, дополняем — они агрегируют, мы добавляем новый бенчмарк

### Hugging Face Open LLM Leaderboard

- **Что:** automated benchmarks для open-weight моделей
- **Сильные стороны:** open ecosystem, free, reproducible
- **Слабые стороны:** только open weights, single judge, академические бенчмарки
- **Конкурент?** Частично — overlap по моделям, но они не делают closed APIs

### SEAL (Scale AI)

- **Что:** expert-driven evaluations включая software engineering, finance, law
- **Сильные стороны:** enterprise-focus, high-quality task curation
- **Слабые стороны:** closed source, expensive, slow cadence
- **Конкурент?** В Tier 4 enterprise white-label — да. В Tier 0-2 — нет.

### SWE-bench / Aider Polyglot / LiveBench / BigCodeBench

- **Что:** coding-specific benchmarks с automated grading
- **Сильные стороны:** rigorous, reproducible, real tasks (для SWE-bench)
- **Слабые стороны:** single benchmark, single judge, only coding
- **Конкурент?** Нет — мы используем их **как источники задач**, а не как конкурентов

### TokenMix

- **Что:** multi-provider routing + leaderboard как side-effect
- **Сильные стороны:** practical pricing data
- **Слабые стороны:** focus на routing, eval вторичен
- **Конкурент?** Нет, complementary

### Onyx

- **Что:** crowdsourced evaluation, similar to LMSYS
- **Сильные стороны:** open source
- **Слабые стороны:** меньший масштаб
- **Конкурент?** Не прямой

### Vercel AI Gateway / Cloudflare AI Gateway

- **Что:** infrastructure для routing
- **Конкурент?** Нет, мы можем интегрироваться

---

## Что у POLLMEVALS уникально

| Фишка | Кто еще делает | Уникальность |
|---|---|---|
| Scaffolding evaluation | **Никто** | High |
| Panel of LLM judges с rotation | Никто в commercial product | High |
| Cost-per-task для стека | Никто | High |
| Geo-aware latency | Никто systematic (AA даёт TTFT но без региона) | Medium |
| Community-driven model addition | LMSYS делает закрыто, мы прозрачно | Medium |
| Drift detection для closed APIs | Никто publishes | High |
| Held-out anti-gaming set | LiveBench делает | Medium (но не для scaffolding) |
| Full reproducibility | SWE-bench Verified да, остальные нет | Medium |

---

## Стратегия позиционирования

### "Мы не Arena"

Arena про human preference на чате. Мы про automated objective scoring на production tasks. **Разные категории**, не конкурируем.

### "Мы не Artificial Analysis"

AA про cost/speed/intelligence для голых моделей. Мы про cost/quality для **стеков**. Дополняем — можно сравнить "Claude Opus голая на AA" vs "Claude Opus + ForgePlan на POLLMEVALS".

### "Мы — про практический выбор"

Engineering lead приходит и спрашивает "что мне купить". Ни Arena, ни AA, ни SWE-bench не отвечают на этот вопрос напрямую. POLLMEVALS отвечает — конкретный stack под конкретную задачу.

---

## Конкурентные угрозы

### Угроза 1: Анонимный конкурент копирует методологию

**Вероятность:** низкая в первые 6 месяцев, средняя в год 2+.

**Mitigation:** open-source всю методологию, делаем "founder's brand" вокруг Eli. Бренд + audience — harder to copy чем код.

### Угроза 2: Major player (Arena, AA) добавляет scaffolding eval

**Вероятность:** средняя в год 2+.

**Mitigation:**
- Быть первым (first-mover advantage)
- Глубже специализация (мы про CLI агентов, не general)
- Community trust (open governance vs corporate)

### Угроза 3: Vendor пытается подкупить за хорошие оценки

**Вероятность:** высокая когда станем relevant.

**Mitigation:**
- Жёсткая disclosure policy (см. 08-must-consider.md)
- Sponsored evals **maps в visibility, не в scoring**
- Independent review board (для v1.0)

### Угроза 4: Inspect AI меняется и breaks compatibility

**Вероятность:** низкая (Anthropic adopted, актив support).

**Mitigation:**
- Pinned versions
- Можно fork если что
- Alternative engines exist (lm-eval-harness как backup)

### Угроза 5: Closed-API vendor блокирует evaluation

**Вероятность:** низкая.

**Mitigation:**
- Use OpenRouter как proxy (vendor не блокирует aggregator)
- Open weights coverage strong
- Legal — это fair use under research

---

## Возможные коллаборации

- **Hugging Face** — host POLLMEVALS datasets, cross-link leaderboards
- **Inspect AI** — submit our evals upstream, become reference user
- **EleutherAI** — share tasks
- **Aider / Cursor / Cline** — they have own scaffolding, we evaluate it for them
- **OpenAI / Anthropic** — sponsored evals, internal evaluation contracts (v1.0+)

---

## Конкурентное преимущество в долгую

Через 12+ месяцев POLLMEVALS будет иметь:
- **Historical dataset** (год+ weekly runs) — невоспроизводимо для конкурентов
- **Community of contributors** — task proposals, voting
- **Citations в академических работах** — увеличивают authority
- **Brand** Eli как expert
- **Methodology refinement** — годы calibration data

Это **moat который сложно повторить**. Конкурент должен будет либо ждать год+ (slow), либо платить за access к нашим данным (Tier 1).

---

# 11 — Roadmap

## Общая стратегия

3-фазная стратегия с реальными gating criteria:

1. **Серия постов** (months 0-3) → если идёт, переход к MVP
2. **MVP** (months 3-6) → если 100+ MAU, переход к коммерции
3. **Коммерция** (months 6-12+) → Tier 1, потом Tier 2/3

---

## v0.0 — Pre-launch (weeks 1-2)

### Цели
- Зафиксировать методологию
- Зарегистрировать домены
- Создать GitHub org

### Чек-лист
- [ ] Зарегистрировать `pollmevals.com` + `.ai` + `.io`
- [ ] Создать `github.com/pollmevals` org
- [ ] Repo: `pollmevals/core` (eval engine, MIT)
- [ ] Repo: `pollmevals/tasks` (20 задач + gold + evaluators, CC BY-SA)
- [ ] Repo: `pollmevals/site` (Next.js + Tailwind)
- [ ] Repo: `pollmevals/litellm-config` (configs для разных setups)
- [ ] Trademark check (опционально, $1500)
- [ ] Twitter / Telegram / RSS подключены

### Deliverable
GitHub org с placeholder repo, домены registered.

---

## v0.1 — Smoke test (weeks 2-4)

### Цели
- Подтвердить что pipeline работает end-to-end
- 3 задачи × 5 моделей × 5 seeds × 3 судей = ~225 evaluations

### Чек-лист
- [ ] Setup LiteLLM локально
- [ ] Setup Inspect AI
- [ ] Финализировать YAML для 3 задач (be_01, fe_01, doc_01)
- [ ] Написать gold solutions для этих 3
- [ ] Написать evaluator scripts
- [ ] Первый smoke run на:
  - Claude Sonnet 4.6
  - GPT-5
  - Gemini 2.5 Pro
  - Qwen 2.5 14B (locally)
  - Llama 3.3 70B (Cerebras)
- [ ] Прогнать panel of 3 judges (Opus, GPT-5, Gemini)
- [ ] Calibration calculation
- [ ] Постмортем — что работает, что нужно дорабатывать

### Deliverable
First smoke results published в blog как "proof of concept post".

---

## v0.2 — Phase 1 launch (months 1-2)

### Цели
- Полная Фаза 1: 14 моделей × 20 задач
- Публикация **первого weekly run**
- Запуск blog с серии

### Чек-лист
- [ ] Финализировать все 20 задач (gold + evaluators)
- [ ] Calibration set из 10 задач (для судей)
- [ ] Postgres + Inspect AI orchestrator deployed
- [ ] LiteLLM с full pool моделей
- [ ] One worker региона (Frankfurt) — geo workers потом
- [ ] First full weekly run
- [ ] Inter-judge agreement >= 0.7
- [ ] Bootstrap CI на всех результатах
- [ ] Static site с лидербордами published
- [ ] First blog post: "How we eval scaffolding stacks — methodology"
- [ ] Second blog post: "Phase 1 results — model radar chart"

### Deliverable
Working POLLMEVALS site с **one full weekly run** published, blog active.

### Gating criteria для перехода в v0.3
- 1000+ unique visitors / week 4
- 20+ HN/Reddit comments
- 50+ GitHub stars
- 5+ credible AI accounts mention

Если меньше — фокусируйся на контенте, не разворачивай инфраструктуру.

---

## v0.3 — Phase 2 ablation + Geo workers (months 3-4)

### Цели
- Фаза 2: scaffolding ablation (L0→L6) на 1-2 моделях
- 4 geo workers активны
- Compare page

### Чек-лист
- [ ] 2-3 толстых задачи для Фазы 2 (refactor, PRD, debug)
- [ ] Implement Claude Code integration через CLI
- [ ] mem0 / hindsight integration
- [ ] Phase 2 run
- [ ] Ablation bars в блоге
- [ ] Geo workers: US-East, EU-Central, APAC
- [ ] `/compare` page
- [ ] `/runs/[hash]` страница reproducibility
- [ ] Blog post: "What does scaffolding give you? Ablation results"
- [ ] Public dataset download (`/datasets`)

### Deliverable
Site с 2 фазами data, ablation insight published.

---

## v1.0 — Community + API (months 5-8)

### Цели
- Community vote открыт
- API public для bulk read
- Phase 3 (memory comparison) launched

### Чек-лист
- [ ] `/vote` страница с GitHub OAuth
- [ ] `/propose-model`, `/propose-task`, `/propose-stack` формы
- [ ] Automated validation для proposals
- [ ] Public API с rate limiting
- [ ] Tier 1 Hobby (free) + Tier 1 Pro ($50/мес)
- [ ] Phase 3: memory comparison (mem0, hindsight, file-based)
- [ ] Disclosure policy published
- [ ] First sponsored eval (с full disclosure)
- [ ] 4 weekly runs published за месяц

### Deliverable
Functional community participation + revenue start.

### Gating criteria для коммерции
- 100+ MAU
- 10+ Tier 1 Hobby signups
- 1+ Tier 1 Pro signup
- 1+ Tier 2 inquiry

---

## v1.5 — Phase 4-5 + Tier 2 (months 9-12)

### Цели
- Phase 4 (CLI comparison)
- Phase 5 (final Pareto)
- First Tier 2 paid eval

### Чек-лист
- [ ] Phase 4: Claude Code vs Codex vs Gemini vs Hermes
- [ ] Phase 5: final cost-quality Pareto
- [ ] All 8 categories of tasks covered
- [ ] Tier 2 service launched
- [ ] First paying enterprise customer
- [ ] First academic citation
- [ ] Annual report "State of LLM Stacks 2026"
- [ ] Conference talk submission (NeurIPS / ICLR workshop)

### Deliverable
Complete 5-phase research series + first revenue.

---

## v2.0 — Scale (year 2)

### Цели
- Multilingual (Russian, Chinese, Spanish tasks)
- Tier 3 sponsored framework
- Possible Tier 4 enterprise white-label

### Чек-лист (high-level)
- [ ] Multilingual tasks pool (15-20 задач на каждый язык)
- [ ] Native-speaker judges
- [ ] Sponsored evals operational (3+ deals)
- [ ] Enterprise white-label pilot (1 deal)
- [ ] Possible: hire 1-2 engineers, 1 community manager
- [ ] Independent advisory board

### Gating criteria для Tier 4
- 500+ MAU
- $5k+ MRR
- 5+ Tier 2 deals closed
- Production-grade infrastructure (99.5%+ uptime)

---

## Что НЕ делать в roadmap

- **Mobile apps** — никогда. Это data product, не consumer app.
- **Free API без rate limits** — burnout инфраструктуры.
- **Open source ВСЕ** — task gold solutions могут быть premium для Tier 1.
- **Видео контент** — пока серия не доказана текстом.
- **Custom hardware** — никогда, всегда cloud + Runpod.
- **Token / Crypto / NFT integrations** — никогда.

---

## Постмортем checkpoints

После каждого quarter:
- Что работает (продолжаем)
- Что не работает (убираем или меняем)
- Что забыли (добавляем)
- Cost vs revenue ratio

Если 2 quarter подряд cost > revenue × 2 → переоценить стратегию.

---

## Exit scenarios

В порядке предпочтения:

1. **Successful indie business** ($30-100k MRR, sustainable solo or 2-3 people) — main goal
2. **Acquisition** — Scale AI, Hugging Face, vendor (Anthropic, Google) могут купить за brand + data
3. **Donated to open ecosystem** — если не получилось коммерциализировать, передать в Apache foundation или similar
4. **Sunset gracefully** — если не работает, опубликовать final report + archive datasets на HF

Все четыре сценария **planned upfront** — не surprised если случится.

---

# 12 — Next Steps

## Что делаем СЕЙЧАС (week 0)

### Действие 1: Зарегистрировать домены — 1 час

```
pollmevals.com    ≈ $12/год     Namecheap или Cloudflare Registrar
pollmevals.ai     ≈ $70/год     для AI-positioning
pollmevals.io     ≈ $35/год     fallback
pollmevals.org    ≈ $12/год     для open community vibe
```

**Total ≈ $130/год.** Делать сейчас пока никто не успел.

### Действие 2: Создать GitHub org — 30 минут

- `github.com/pollmevals` создать
- Создать стартовые repo:
  - `pollmevals/core` — placeholder с README
  - `pollmevals/tasks` — placeholder с README + структура
  - `pollmevals/site` — placeholder
  - `pollmevals/litellm-config` — placeholder

### Действие 3: Подтвердить с Eli три ключевые задачи для smoke — 30 минут

Из draft списка 20, выбрать 3 которые делаем первыми:
- **be_01** — JWT auth middleware (backend, medium)
- **fe_01** — Multi-step form (frontend, medium)
- **doc_01** — README для CLI tool (docs, easy)

Если Eli согласен — поехали. Если хочет заменить — называет.

### Действие 4: Я (Claude) пишу YAML спеки для этих 3 задач — 4-6 часов работы

Для каждой:
- Полное description в Markdown
- Gold solution (TypeScript / Markdown)
- Test suite / evaluator script
- Expected metrics ranges
- 3 калибровочных версии (good / mediocre / bad)

Eli ревьюит, корректирует.

### Действие 5: Setup LiteLLM + Inspect AI локально у Eli — 2-3 часа

- Docker-compose с LiteLLM + Postgres
- Inspect AI installed
- API keys для OpenRouter (cloud) + Cerebras (open weights)
- Smoke test: один prompt через LiteLLM достигает Claude

### Действие 6: Первый smoke run — 2-3 часа

Гоним 3 задачи × 5 моделей × 3 seeds = 45 evals. Без judges пока — только automatic metrics. Чтобы поймать pipeline issues.

### Действие 7: Калибровка панели судей — 4-6 часов

- 5 калибровочных задач с known scores
- Прогнать 5 судей через них
- Считать inter-judge agreement
- Если < 0.7 — переписать rubric, повторить

### Действие 8: Полный smoke с judges — 3-4 часа

45 evals × 4 judges (self-exclusion) = 180 judgments. Считаем final scores. Сравниваем с expected.

### Действие 9: Первый blog post — 6-8 часов

"How we eval scaffolding stacks — methodology"

Это первый пост в серии. Закладывает все правила игры.

---

## Total estimate

**Pre-launch (v0.0 + v0.1):** ~30-40 часов работы Eli + parallel Claude tasks.

Реалистично за **2-3 недели** при загрузке 10-15 часов в неделю.

---

## Open Questions — нерешённые

### Q1: Кто пишет gold solutions для всех 20 задач?

**Опции:**
- Eli сам (100-150 часов) — самое надёжное по качеству, но долго
- Freelancers через Upwork ($5-10k за все 20) — быстрее, но нужен review
- Claude генерирует draft, Eli проверяет — гибрид, быстро + контроль

**Решение:** **Гибрид.** Claude пишет draft → Eli проверяет на качество → если ОК — финализируем. Если плохо — переписываем вместе.

### Q2: Какой stack для site — Next.js или что-то другое?

**Опции:**
- Next.js 15 + Tailwind + shadcn/ui (стандарт)
- Astro (быстрее для статики)
- Just static HTML + минимум JS (легче maintain)

**Решение:** **Next.js 15** — гибкость для динамических лидербордов + SSG для blog. Стандартно, легко найти контракторов если нужно.

### Q3: Mongo или Postgres?

**Решение:** **Postgres**. Schema-heavy data, relational queries, нет нужды в NoSQL flex.

### Q4: Стейт у Eli потянет maintain weekly run или нет?

**Реалистично:**
- Setup: 30-40 часов одноразово
- Weekly run baby-sitting: 2-4 часа per week
- Blog post: 4-6 часов per week
- Community moderation: 1-3 часа per week

**Total: ~10-15 часов/week** после launch.

Это **40-60% от time'а ForgePlan**. Eli уже занят. Нужно решить — отложить ForgePlan launch readiness, или distribute time.

### Q5: Что если no traction?

**После 4 недель публикации:**
- Если < 1000 visitors → серия не идёт. Стоп.
- Если 1000-5000 visitors → продолжать как hobby, не продукт.
- Если > 5000 visitors → разворачивать MVP.

**Pre-committed exit point.** Это спасает от sunk cost fallacy.

### Q6: Юридическая структура

**Когда нужно:**
- Только когда есть revenue (Tier 1+)
- До этого — все на личное имя Eli (хобби-проект)

**Когда есть revenue:**
- UK Ltd (cheap, fast, ~£100 setup)
- Estonian e-Residency company (для EU citizens, ~€500)
- Cyprus Ltd (если ожидается большая прибыль и low tax)

### Q7: Что с visibility у Eli как ForgePlan author?

**Disclosure обязателен.** В каждом посте упомянуть "POLLMEVALS оператор является разработчиком ForgePlan, методология калибрована независимо".

ForgePlan-stacks (когда дойдём до Фазы 2-5) **не fast-track**, не sponsored. Обычный community process.

---

## Decision Log — что зафиксировано

| Дата | Решение | Рационал |
|---|---|---|
| 2026-05-21 | Выбрали Inspect AI как eval engine | 200+ pre-built evals, отличный DX, Anthropic adopted |
| 2026-05-21 | Выбрали LiteLLM как gateway | Cost tracking built-in, OpenAI-compatible, MIT |
| 2026-05-21 | Cerebras + Runpod + OpenRouter как inference layers | Cerebras скорость, Runpod гибкость, OR cloud |
| 2026-05-21 | 14 моделей в пуле для Фазы 1 | Достаточно для богатого радара, в 2× меньше прогонов чем 30+ |
| 2026-05-21 | TypeScript/Node.js как основной язык + Python для DevOps | Реальный production stack, моделим сильны в нём |
| 2026-05-21 | 20 задач для Фазы 1 (draft list) | Балланс между breadth и feasibility |
| 2026-05-21 | Panel of 5 judges с rotation, no self-judging | Best practice из академии, никто в commercial не делает |
| 2026-05-21 | Median scoring через panel, не mean | Устойчивость к outliers |
| 2026-05-21 | 5 seeds per combo для bootstrap CI | Standard для statistical rigor |
| 2026-05-21 | Krippendorff α >= 0.7 как gate для publishing | Inter-rater reliability threshold |
| 2026-05-21 | 5-фазная серия постов вместо одного | Factorial design, каждая фаза = 1 post |
| 2026-05-21 | POLLMEVALS как brand для продукта | Уникальная ниша — scaffolding eval с panel |
| 2026-05-21 | Tier 0 → 1 → 2 → 3 → 4 монетизация | Постепенный, gated by audience |
| 2026-05-21 | Postgres + R2 + Redis stack | Стандарт, легко maintain |
| 2026-05-21 | Next.js 15 + Tailwind + shadcn для frontend | Стандартный modern stack |
| 2026-05-21 | 4 geo regions для latency | US-East, EU-Central, APAC, SA — реалистичные territories |
| 2026-05-21 | Weekly cadence + flagship-triggered | Не daily (слишком noisy), не monthly (slow) |
| 2026-05-21 | MIT для кода, CC BY-SA для датасетов | Стандарт для open research |
| 2026-05-21 | Code execution в Docker без network access | Security base |
| 2026-05-21 | Identification probe < 30% для anonymization | Verify подписи срезаны |
| 2026-05-21 | 20% задач — held-out private set | Anti-gaming страховка |
| 2026-05-21 | Drift detection через 2σ от baseline | Catch silent model updates |

---

## Чего я (Claude) пока не зафиксировал — нужно решение Eli

- [ ] **Финальный набор 20 задач** — apply changes if any
- [ ] **Lead time для launch** — 2 weeks, 4 weeks, 8 weeks?
- [ ] **Контрактор vs solo** для gold solutions — кто пишет
- [ ] **Бренд имени personality** — это "anonymous research project" или "Eli's project"?
- [ ] **Co-founder** — solo или искать партнёра?
- [ ] **Initial funding** — bootstrapping or seeking small angel ($25-50k)?
- [ ] **Anti-pattern: что НЕ делать** в первый год — list of "don'ts"

---

## Финал — что хочет видеть Eli по итогам

Если по итогам этого исследования через 6 месяцев:

1. ✓ Серия 5 постов опубликована
2. ✓ POLLMEVALS как brand зарекомендован в AI community
3. ✓ MVP сайт с минимум одной фазой data live
4. ✓ 100+ MAU и растёт
5. ✓ First Tier 1 paying customer

— это **успех**. Не пытаемся всё за раз.

Если что-то из этого не достигнуто — переоцениваем стратегию **до того как** добавлять complexity.

---

## Финальная команда от меня

**Скажи "поехали со smoke на 3 задачах"** — и я начинаю писать YAML спеки + gold solutions + evaluator scripts для be_01, fe_01, doc_01. Через 2 итерации с твоим ревью у нас будет работающий pipeline. Затем масштабируем на 20 задач.

Не пытайся сразу делать продукт. Сначала **proof методологии**, потом продукт.

---
