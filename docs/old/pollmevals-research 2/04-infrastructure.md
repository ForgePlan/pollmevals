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
