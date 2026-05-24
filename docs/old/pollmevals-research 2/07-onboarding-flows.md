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
