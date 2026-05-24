# POLLMEVALS — File Index

Последнее обновление: 2026-05-24 (Phase 2C complete + Slice A skeleton + NOTE-004 expanded vision).

**Where to start (quick navigation)**:
- Что есть в проекте → этот файл (root INDEX.md)
- Что есть в docs/ → `docs/INDEX.md` (focused docs map)
- Что есть в forgeplan/ → `forgeplan list` или `mcp__forgeplan__forgeplan_list`
- Правила работы AI-агента → `CLAUDE.md`
- Domain glossary → `CONTEXT.md`
- Expanded vision catalog (stacks, memory, tools, metrics) → **`.forgeplan/notes/NOTE-004-*.md`** (canonical) или `forgeplan get NOTE-004`

## Корень

- `README.md` — навигация и быстрый старт
- `MASTER.md` — линейный свод всей документации (151 KB)
- `INDEX.md` — этот файл (file index + migration map)
- `CLAUDE.md` — правила для AI-агента в этом проекте (auto-loaded)
- `CONTEXT.md` — ubiquitous language / domain glossary (auto-loaded via @import)
- `Makefile` — `stack-up/down`, `obs-up/down`, `smoke-dry`, `smoke-run`, `litellm-smoke`, `openrouter-smoke`, `validate-tasks`
- `.env.example` — шаблон секретов
- `.env` — `gitignored`, реальные секреты (OPENROUTER_API_KEY, OPENROUTER_API_KEY_JUDGE, LITELLM_MASTER_KEY, NATS_URL, GEMINI_API_KEY, HF_TOKEN)
- `pyproject.toml` — Python project root (uv workspace)
- `package.json` — Node.js root + lefthook devDep
- `lefthook.yml` — pre-commit hooks (secret-scan, forgeplan-validate, format-py, format-ts, typecheck)
- `.mcp.json` — MCP server config (forgeplan, hindsight, context7 в зависимости от настройки)

## docs/

### docs/00-research/ — оригинальное исследование (read-only архив)

- `00-MASTER.md` — свод исследования
- `01-problem-vision.md` — боль пользователей, UVP
- `02-methodology.md` — таксономия L0-L8, panel of judges, 9 biases
- `03-experiment-design.md` — 5-фазный factorial design (~470 прогонов)
- `04-infrastructure.md` — Inspect AI, LiteLLM, geo workers, cost estimate
- `05-product-spec.md` — продуктовая спецификация
- `06-site-architecture.md` — IA сайта, data model, eval pipeline
- `07-onboarding-flows.md` — добавление модели/стека/задачи
- `08-must-consider.md` — 20 критичных моментов
- `09-business-model.md` — Tier 0→4 монетизация
- `10-competitive-landscape.md` — карта рынка, конкуренты
- `11-roadmap.md` — v0.0 → v2.0
- `12-next-steps.md` — Week 0 actions, open questions, decision log
- `README.md`
- `examples/` — `inspect-task.yaml`, `litellm-config.yaml`, `scoring-formulas.md`
- `visuals/` — HTML/SVG диаграммы (дубль в `docs/visuals/`)

### docs/01-vision/

- `00-executive-vision.md` — executive summary
- `01-product-requirements.md` — функциональные требования
- `02-project-brief.md` — расширенный brief
- `03-product-vision-detailed.md` — детальное видение
- `04-business-and-roadmap.md` — монетизация + roadmap

### docs/02-methodology/ — frozen v0.1.0

- `methodology.md` — манифест, L0-L8 ladder
- `task-lifecycle.md` — 8 состояний задачи
- `scoring.md` — формулы по категориям (coding, docs, review)
- `judge-policy.md` — правила судейства, Krippendorff α ≥ 0.70
- `stack-adapter-spec.md` — YAML контракт стека
- `security-sandbox.md` — Docker/gVisor/Firecracker
- `decisions/2026-05-23-hybrid-stack.md` — TS + Python hybrid

### docs/03-architecture/

- `00-architecture-overview.md` — Product plane + Eval plane
- `01-stack-decision.md` — выбор стека
- `02-domain-model.md` — Model/Stack/Task/Run/Eval/Judgment
- `03-system-architecture-detailed.md` — детали
- `04-stack-decision-detailed.md` — обоснование
- `05-domain-model-detailed.md` — связи сущностей
- `06-repo-structure.md` — структура monorepo

### docs/04-runbook/

- `00-implementation-plan.md` — план Phase 0-5
- `01-operational-runbook.md` — daily/weekly ops
- `02-missing-pieces-checklist.md` — дыры P0/P1/P2
- `03-implementation-plan-detailed.md` — детали
- `04-task-authoring-guide.md` — как писать задачи
- `05-stack-adapter-guide.md` — как написать adapter
- `06-run-manifest-and-artifacts.md` — формат manifest
- `07-judge-panel.md` — судейство pipeline
- `08-scoring-contract.md` — формулы
- `09-sandbox-security.md` — Docker policy
- `10-operations-runbook-detailed.md` — детали ops
- `11-missing-pieces-checklist-detailed.md` — детали дыр
- `12-first-smoke-run-playbook.md` — playbook первого запуска
- `13-agent-handoff-brief.md` — миссия + non-negotiables

### docs/adr/

- `0001-use-hybrid-stack.md` — Accepted
- `0002-run-immutability.md` — Accepted

### docs/visuals/

- `01-radar-example.html` — радар по 12 осям
- `02-ablation-bars.html` — stacked bars по слоям
- `03-roadmap-5-phases.svg` — 5 фаз
- `04-competitive-landscape.html` — quadrant chart
- `05-site-ia.svg` — IA сайта
- `VISUALS_README.md`

### docs/PROJECT_TREE.md

### docs/INDEX.md ⚡ NEW — focused docs map (added 2026-05-24)

## .forgeplan/ — управляемые артефакты (через CLI/MCP only — red line: no direct edits)

Полный список через `forgeplan list` или `mcp__forgeplan__forgeplan_list`. Краткий снапшот (на 2026-05-24, всего 40+ artifacts):

- `epics/EPIC-001` — v0.1 launch
- `prds/PRD-001` (active, deep) — v0.1 smoke evaluation run
- `prds/PRD-002` (active, body=deep) — judge panel layer methodology
- `prds/PRD-003..005` (draft stubs) — weekly cadence, leaderboard, release pipeline
- `specs/SPEC-001` — run manifest contracts
- `rfcs/RFC-001` (active) — overall implementation plan
- `rfcs/RFC-002` (draft) — judge panel layer implementation (5 slices A-E)
- `adrs/ADR-001..003` (active, done) — concurrency, reproduce semantics, 5-model lineup
- `adrs/ADR-004` (active) — MoleculerPy adoption for PRD-003 distributed orchestrator
- `adrs/ADR-005` (draft) — median reducer + bootstrap CI lower-bound rationale
- `notes/NOTE-001` — crash recovery
- `notes/NOTE-002` — **mandatory evidence quality contract** (ADI + Trust Calculus per EVID)
- `notes/NOTE-003` — observability stack research seed (LGTM)
- `notes/NOTE-004` — **expanded vision catalog** (agent CLIs, memory variants, context tools, indexing tools, extended metrics) ← canonical reference for full vision
- `evidence/EVID-001..018` — Phase 1 prior art + reviews + audits
- `evidence/EVID-019` — OpenRouter direct smoke test
- `evidence/EVID-020` — Phase 2B stack bootstrap capture
- `evidence/EVID-021` (superseded by 022) — Phase 2C OTel code review CONCERNS
- `evidence/EVID-022` — Phase 2C fix re-review PASS
- `evidence/EVID-023` — Phase 3 W1 H1 spike — Inspect AI per-judge access SUPPORTED

Gitignored под `.forgeplan/`: `lance/`, `.fastembed_cache/`, `logs/`, `.lock`, `session.yaml`, `trash/`, `discovery/`, `claims/`.

## artifacts/ — runtime smoke run outputs (gitignored)

Каждый run = `artifacts/runs/sha256:<hash>/`:
- `manifest.json` (file mode `0o444` per ADR-002 immutability)
- `POSTMORTEM.md` (template from playbook)
- `manifest.journal.ndjson` (append-only journal of grid execution)
- `determinism-check.journal.ndjson` (re-run verification log)
- `evals/<eval_id>/` (raw_output, normalized_output, evaluator_json — content-addressed)

## packages/

### packages/contracts/

- `package.json` — npm pkg для типов и схем
- `tsconfig.json`
- `schemas/task.schema.json` — JSON Schema задачи (draft 2020-12)
- `schemas/stack.schema.json` — JSON Schema стека
- `schemas/run-manifest.schema.json` — JSON Schema run manifest
- `src/types.ts` — TypeScript интерфейсы

### packages/db/migrations/

- `0001_initial.sql` — 8 таблиц: `models`, `model_providers`, `stacks`, `tasks`, `runs`, `evals`, `judgments`, `calibration_runs`

## apps/

### apps/eval-core-py/ — Python orchestrator (Phase 2A/B/C complete)

- `pyproject.toml` + `uv.lock` — Python deps (pydantic v2, httpx, inspect-ai, opentelemetry-{api,sdk,exporter-otlp-proto-http}, ruff, mypy)
- `src/orchestrator/grid_runner.py` — GridRunner (asyncio + Semaphore(3) + budget gate); has `SMOKE_MODELS` constant per ADR-003
- `src/orchestrator/eval_caller.py` — `EvalCaller` Protocol + `FakeEvalCaller` + **`InspectEvalCaller` real impl** (HTTP to LiteLLM proxy + 429 retry + httpx.TimeoutException handling)
- `src/orchestrator/journal.py` — `JournalWriter` (NDJSON append + fsync + OTel span error recording)
- `src/orchestrator/manifest_writer.py` — `ManifestWriter` (state machine + `chmod 0o444` write-once)
- `src/orchestrator/cost.py` — `BudgetGate` (Decimal precision + 80% abort threshold) + `CostReconciler` (with OTel spans)
- `src/orchestrator/judge_panel.py` ⚡ NEW — RFC-002 Slice A skeleton: `JudgePanel` + `SelfJudgingError` + `_normalise_model_family` (cross-route family detection)
- `src/orchestrator/telemetry.py` — OTel bootstrap (`init_tracing()`, OTLP HTTP exporter to localhost:4318)
- `src/contracts/` — Pydantic v2 models (EvalRow, ManifestPin, GridSpec, ArtifactRef, Judgment, JudgeAggregation, ...)
- `src/contracts/judge.py` ⚡ NEW — `Judgment` + `JudgeAggregation` Pydantic models (Slice A)
- `src/evaluators/__init__.py` — STUB (Phase 2D scope: real cyclomatic/coverage/lint/type-safety evaluators)
- `scripts/smoke_run.py` ⚡ NEW — Phase 2B coda entrypoint (playbook steps 1-14, dry-run / --confirm-spend gates)
- `tests/` — 425 tests pass (test_grid_runner, test_journal, test_manifest_writer, test_cost, test_eval_caller, test_telemetry, test_judge_panel, test_smoke_runner, test_integration, test_contracts)

### apps/api/ — Hono TypeScript API (Phase 4+)
### apps/site/ — Next.js 15 публичный сайт (Phase 4+)

## evals/

### evals/tasks/ — task.yaml для исполнения

- `be_01_jwt_auth/task.yaml`
- `doc_01_cli_readme/task.yaml`
- `fe_01_multistep_form/task.yaml`

### evals/task-packs/ — полные пакеты с prompt + gold

- `be_01_jwt_auth/` — README, prompt.md, task.yaml, gold/README.md
- `doc_01_cli_readme/` — README, prompt.md, task.yaml, gold/README.md
- `fe_01_multistep_form/` — README, prompt.md, task.yaml, gold/README.md

### evals/rubrics/

- `documentation-rubric.md` — 5 критериев для docs

### evals/calibration/

- `README.md` — описание формата (perfect/good/mediocre/poor/broken samples)

## stacks/

- `raw-llm/stack.yaml` — L0 only
- `claude-code-basic/stack.yaml` — L1 + L2
- `forgeplan-framework/stack.yaml` — L3+L4+L6+L7+L8

## data/

- `models.json` — 3 пример-модели (Qwen 2.5 14B Local, Claude Sonnet, GPT-5)
- `stacks.json` — summary 3 стеков
- `tasks.json` — summary 3 задач
- `sample-leaderboard.json` — пример агрегации
- `sample-run-manifest.json` — skeleton manifest

## infra/ (Phase 2B + 2C additions)

### infra/docker-compose.*.yml

- `docker-compose.litellm.yml` — Postgres + NATS + LiteLLM proxy (data plane)
- `docker-compose.observability.yml` — Grafana + Loki + Tempo + Prometheus + OTel Collector (LGTM stack)

### infra/litellm-config.yaml

5 candidate model routes (per ADR-003: claude-sonnet-4-6, gpt-5-mini, gemini-3-flash, qwen-3-14b, llama-3-3-70b) + 2 judge routes (claude-sonnet-4-6-judge, gpt-5-mini-judge) с `OPENROUTER_API_KEY_JUDGE` billing isolation per RFC-002 NFR-005.

### infra/observability/

- `otel-collector-config.yaml` — OTLP receivers (gRPC + HTTP) + Tempo/Loki/Prometheus exporters
- `prometheus.yml` — scrapes LiteLLM `/metrics` with Bearer auth
- `tempo-config.yaml`, `loki-config.yaml`, `grafana-datasources.yaml` — auto-provisioned

### infra/scripts/

- `validate-task-specs.py` — JSON Schema validation на `evals/task-packs/*/task.yaml`
- `validate-stack-specs.py` — JSON Schema validation на `stacks/*/stack.yaml`
- `smoke-openrouter.py` — direct OpenRouter pre-flight (ADR-003 model availability check)
- `smoke-litellm.py` — через LiteLLM proxy pre-flight (proxy routing + master key validation)
- `inspect_ai_h1_spike.py` ⚡ NEW — Phase 3 W1 H1 spike (verifies Inspect AI per-judge access — EVID-023)
- `litellm-proxy-up.sh`, `litellm-proxy-down.sh` — legacy helpers (use `make stack-up` instead)
- `reproduce-local-run.sh` — evaluator-only reproduce из manifest (per ADR-002 immutability)

## Migration Map (от старого `_draft/` к новому)

> **Note:** эта таблица — историческая справка о том, как файлы попали в monorepo. После удаления `_draft/` пути слева перестанут существовать, но связь «откуда взято» остаётся ценной для понимания истории решений.


| Старый путь | Новый путь |
|---|---|
| `_draft/pollmevals-research/` | `docs/00-research/` |
| `_draft/pollmevals-docs-pack/source-archive/` | (удалить — дубль research) |
| `_draft/pollmevals-docs-pack/00-MASTER-DOCUMENTATION.md` | `MASTER.md` |
| `_draft/pollmevals-docs-pack/docs/00-executive-vision.md` | `docs/01-vision/00-executive-vision.md` |
| `_draft/pollmevals-docs-pack/docs/01-product-requirements.md` | `docs/01-vision/01-product-requirements.md` |
| `_draft/pollmevals-docs-pack/docs/02-architecture.md` | `docs/03-architecture/00-architecture-overview.md` |
| `_draft/pollmevals-docs-pack/docs/03-stack-decision.md` | `docs/03-architecture/01-stack-decision.md` |
| `_draft/pollmevals-docs-pack/docs/04-domain-model.md` | `docs/03-architecture/02-domain-model.md` |
| `_draft/pollmevals-docs-pack/docs/05-implementation-plan.md` | `docs/04-runbook/00-implementation-plan.md` |
| `_draft/pollmevals-docs-pack/docs/06-operational-runbook.md` | `docs/04-runbook/01-operational-runbook.md` |
| `_draft/pollmevals-docs-pack/docs/07-missing-pieces-checklist.md` | `docs/04-runbook/02-missing-pieces-checklist.md` |
| `_draft/pollmevals-docs-pack/docs-generated/01-project-brief.md` | `docs/01-vision/02-project-brief.md` |
| `_draft/pollmevals-docs-pack/docs-generated/02-product-vision.md` | `docs/01-vision/03-product-vision-detailed.md` |
| `_draft/pollmevals-docs-pack/docs-generated/03..06-*.md` | `docs/03-architecture/03..06-*.md` |
| `_draft/pollmevals-docs-pack/docs-generated/07..14,16..18-*.md` | `docs/04-runbook/03..13-*.md` |
| `_draft/pollmevals-docs-pack/docs-generated/15-business-and-roadmap.md` | `docs/01-vision/04-business-and-roadmap.md` |
| `_draft/pollmevals-docs-pack/methodology/` | `docs/02-methodology/` |
| `_draft/pollmevals-docs-pack/adrs/` | `docs/adr/` |
| `_draft/pollmevals-docs-pack/packages/` | `packages/` |
| `_draft/pollmevals-docs-pack/evals/` | `evals/` (rubrics, calibration, tasks) |
| `_draft/pollmevals-docs-pack/task-packs/` | `evals/task-packs/` |
| `_draft/pollmevals-docs-pack/stacks/` | `stacks/` |
| `_draft/pollmevals-docs-pack/data/` | `data/` |
| `_draft/pollmevals-docs-pack/starter-files/Makefile` | `Makefile` (расширен) |
| `_draft/pollmevals-docs-pack/starter-files/README.md` | `README.md` (переписан под новую структуру) |
| `_draft/pollmevals-docs-pack/starter-files/scripts/` | `infra/scripts/` |
| `_draft/pollmevals-docs-pack/starter-files/.env.example` | `.env.example` |
| `_draft/pollmevals-docs-pack/starter-files/PROJECT_TREE.md` | `docs/PROJECT_TREE.md` |
