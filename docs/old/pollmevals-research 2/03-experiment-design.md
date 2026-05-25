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
