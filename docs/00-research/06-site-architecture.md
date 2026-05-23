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
