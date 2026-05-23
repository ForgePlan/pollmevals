# POLLMEVALS — File Index

105 файлов. Сгенерировано 2026-05-23.

## Корень

- `README.md` — навигация и быстрый старт
- `MASTER.md` — линейный свод всей документации (4000 строк)
- `INDEX.md` — этот файл
- `Makefile` — `demo-run`, `docker-up`, `api-dev`, `site-dev`, `validate-tasks`, `reproduce`
- `.env.example` — шаблон секретов

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

## apps/ (skeletons, .gitkeep)

- `eval-core-py/` — Python eval orchestrator
- `api/` — Hono TypeScript API
- `site/` — Next.js 15 публичный сайт

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

## infra/scripts/

- `validate-task-specs.py` — проверка YAML спек
- `reproduce-local-run.sh` — повторный запуск из manifest

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
