# POLLMEVALS

**Panel of LLM Evaluators** — открытая платформа оценки **полных LLM-стеков** (модель + agent CLI + skills + память + validator), а не голых моделей.

Главный тезис: дешёвая модель с правильной обвязкой часто бьёт дорогую без обвязки за 1/20 цены. Нужно доказать числами.

## Где начать

| Цель | Файл |
|---|---|
| Понять весь проект в один проход | [`MASTER.md`](MASTER.md) — линейный свод (4000 строк) |
| Бизнес-видение, метрики, монетизация | [`docs/01-vision/`](docs/01-vision/) |
| Frozen методология v0.1.0 (judges, scoring, sandbox) | [`docs/02-methodology/`](docs/02-methodology/) |
| Архитектура, стек, domain model | [`docs/03-architecture/`](docs/03-architecture/) |
| Implementation plan + smoke run playbook | [`docs/04-runbook/`](docs/04-runbook/) |
| Принятые решения (ADR) | [`docs/adr/`](docs/adr/) |
| Оригинальное исследование (12 глав) | [`docs/00-research/`](docs/00-research/) |

## Структура (monorepo)

```text
pollmevals/
├── README.md / MASTER.md / INDEX.md
├── Makefile / .env.example
│
├── docs/                       Документация
│   ├── 00-research/            Оригинальный research (read-only архив)
│   ├── 01-vision/              Vision, requirements, business
│   ├── 02-methodology/         Frozen methodology v0.1.0
│   ├── 03-architecture/        System architecture, stack, domain
│   ├── 04-runbook/             Implementation, ops, smoke playbook
│   ├── adr/                    Architecture Decision Records
│   ├── visuals/                HTML/SVG диаграммы
│   └── PROJECT_TREE.md
│
├── packages/                   Shared библиотеки
│   ├── contracts/              JSON Schemas + TypeScript types
│   └── db/migrations/          SQL миграции (8 таблиц)
│
├── apps/                       Будущие приложения (skeletons)
│   ├── eval-core-py/           Python eval orchestrator
│   ├── api/                    Hono TypeScript API
│   └── site/                   Next.js 15 публичный сайт
│
├── evals/                      Eval-материалы
│   ├── tasks/                  task.yaml для исполнения
│   ├── task-packs/             Полные пакеты (prompt + gold + task.yaml)
│   ├── rubrics/                Judge rubrics
│   └── calibration/            Calibration samples
│
├── stacks/                     Stack adapter specs
│   ├── raw-llm/                L0: голая LLM
│   ├── claude-code-basic/      L1-L2: prompt + tools
│   └── forgeplan-framework/    L3-L8: skills + memory + subagents + validator + framework
│
├── data/                       Sample JSON (models, stacks, tasks, leaderboard, run-manifest)
│
└── infra/scripts/              validate-task-specs.py, reproduce-local-run.sh
```

## Стек (по ADR-0001)

- **Product plane (TypeScript)**: Next.js 15 + Tailwind + shadcn/ui (site), Hono (API), Postgres + Drizzle
- **Eval plane (Python 3.12)**: Inspect AI + Pydantic + LiteLLM
- **Build system**: Moon (multi-language monorepo), pnpm для JS, uv для Python
- **Infra**: NATS (bus), Redis (queue/cache), Cloudflare R2 (artifacts), Docker rootless sandbox
- **Future**: gVisor/Firecracker sandbox, Rust для trace normalizer (после стабилизации контрактов)

## Принципы

1. **Run immutability** (ADR-0002): completed run never edited in place
2. **Model never judges itself** (judge-policy.md)
3. **Median scoring**, не mean
4. **Versioned tasks**: изменение = новая версия
5. **Full reproducibility**: всё в content-addressed R2

## Быстрый старт (когда apps/ наполнятся)

```bash
cp .env.example .env
make docker-up        # NATS, Redis, Postgres, LiteLLM proxy
make demo-run         # локальный smoke run без внешних API
make api-dev          # Hono API на :8787 (см. POLLMEVALS_API_PORT)
make site-dev         # Next.js на :3000
```

## Текущая фаза

**v0.0 — Pre-launch**. Документация и контракты готовы. Код не написан. Следующая задача: реализовать `apps/eval-core-py/` достаточно для первого smoke run (3 задачи × 5 моделей × 3 seeds = 45 evals) — см. [`docs/04-runbook/12-first-smoke-run-playbook.md`](docs/04-runbook/12-first-smoke-run-playbook.md).

## Лицензия

Код — MIT. Датасеты задач — CC BY-SA 4.0 (планируемо).
