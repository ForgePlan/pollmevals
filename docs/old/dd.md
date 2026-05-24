И так я хчоу локально оптестить на разыне бенчмарки под разные задчик на моем маке или например на любом дургом компе с видяхой или на sge 

я бы хотел найти или написать какой то проект или паке т или найти в сети говтоый чтобы гоянт ьего и получат ьмтерики под разнеы задачи и потмо строит ьграфик и выклдыват ьу себя в блоге


Хороший вопрос. Поскольку область быстро меняется, дай посмотрю что сейчас в топе для self-hosted эвалов и какие есть удобные варианты под Mac/GPU/сервер.Понял задачу. Под локальные эвалы на разных задачах с метриками и графиками сейчас три серьёзных кандидата — короткий разбор плюс что я бы сам взял в твоей ситуации.

## Три варианта, между которыми реально выбор

**Inspect AI** (UK AISI + Meridian Labs) — мой топ-выбор для тебя. Это фреймворк для эвалов от UK AI Security Institute, поддерживает кодинг, агентов, рассуждения, знания и мультимодалку, с коллекцией из 200+ готовых эвалов. Сейчас там 132+ зарегистрированных eval-пакетов по категориям: Coding 21, Cybersecurity 14, Mathematics 7, Reasoning 22, Knowledge 22, Multimodal 5. Уже используется внутри Anthropic, DeepMind, Grok и других — Inspect стал де-факто стандартом для серьёзных лаб. Локальные модели: vLLM, Ollama, llama-cpp-python, TransformerLens, nnterp — то есть Mac через Ollama/llama.cpp работает из коробки. Плюс есть встроенный web viewer для разглядывания результатов.

**lm-evaluation-harness** (EleutherAI) — олдскульный «золотой стандарт». Бандлит 60+ стандартных бенчмарков (MMLU, HellaSwag, Big-Bench и т.д.), поддерживает HF Transformers, vLLM, GPTQ-квантизацию, OpenAI API. Это бэкенд Open LLM Leaderboard от HF. Плюс: если хочешь чтобы твои числа были сравнимы с публикациями — это оно. Минус: кривая обучения круче — закладывай день на первый сетап. Большие прогоны медленные by design, на хорошем железе бенчмарк-suite может занимать много часов.

**lighteval** (HuggingFace) — all-in-one тулкит для эвалов LLM через несколько бэкендов, вдохновлён EleutherAI Harness и Stanford HELM, сохраняет детальные sample-by-sample результаты. Легче чем lm-eval-harness, но эвалов меньше.

## Что я бы взял лично

**Inspect AI** — по трём причинам:

Во-первых, он покрывает не только академические бенчмарки, но и **агентные задачи** (SWE-bench, GAIA, Cybench и т.д.), а у тебя контекст агентных систем. Inspect Evals включает агентные бенчи GAIA, SWE-Bench, GDM CTF, Cybench — раньше они были сложны в настройке, теперь запускаются одной командой против любой модели.

Во-вторых, он **современный и активно поддерживается**, в отличие от lm-eval-harness, где архитектура местами устаревшая. Можно писать свои эвалы как обычные Python-пакеты — близко к твоему стилю.

В-третьих, под пост в блог критичны **красивые логи и таблицы**. У Inspect есть `evals_df`, `samples_df`, `events_df` — логи трансформируются в pandas-датафреймы для слайсинга, плюс есть Inspect Viz dashboards. Это значит — пара строк pandas/plotly и у тебя готовые графики.

## Конкретный сетап под Mac (Apple Silicon)

```bash
# 1. Поднимаем Ollama (если ещё нет)
brew install ollama
ollama serve &
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
ollama pull mistral:7b

# 2. Inspect AI
pip install inspect-ai inspect-evals

# 3. Запускаем эвал на нескольких моделях разом
inspect eval inspect_evals/gsm8k --model ollama/qwen2.5:7b
inspect eval inspect_evals/mmlu --model ollama/llama3.1:8b
inspect eval inspect_evals/humaneval --model ollama/qwen2.5:7b

# 4. Смотрим результаты в web UI
inspect view
```

Для GPU-машины меняешь `ollama/...` на `vllm/...` — остальное идентично. Скриптом гоняешь матрицу `models × tasks`, складываешь логи в одну директорию, потом одним pandas-запросом достаёшь всё что надо.

## Под графики для блога

Inspect логи → pandas → plotly/altair. Примерно так:

```python
from inspect_ai.log import list_eval_logs, read_eval_log
import pandas as pd
import plotly.express as px

rows = []
for log_path in list_eval_logs("./logs"):
    log = read_eval_log(log_path)
    rows.append({
        "model": log.eval.model,
        "task": log.eval.task,
        "accuracy": log.results.scores[0].metrics["accuracy"].value,
        "samples": log.results.total_samples,
    })

df = pd.DataFrame(rows)
fig = px.bar(df, x="task", y="accuracy", color="model", barmode="group")
fig.write_html("benchmarks.html")
```

Получаешь интерактивный график, который вставляешь в блог как embed.

## Бонус — если хочется не только качество, но и скорость/энергию

Свежая работа **Bench360** (ноябрь 2025) — бенчмарк-фреймворк специально под локальный LLM inference: помогает ответить на вопрос «какая комбинация модели, квантизации и inference-фреймворка даёт лучший trade-off между computational cost, энергией и качеством для моей задачи». Закрывает дыру в существующих бенчмарках, которые редко поддерживают energy efficiency, cold start и latency для on-premise развёртывания. Если хочешь не только «кто умнее» но и «кто быстрее жжёт батарею на M-чипе» — это интересный апгрейд.

---

Если скажешь какие именно **задачи** интересны (math, code, reasoning, RAG, агенты, tool-calling, твой родной Graph-RAG?) и какое **железо** будешь гонять (только Mac, или есть машинка с 4090/H100?) — соберу тебе конкретный starter-репо со скриптами и пайплайном «прогнал → собрал → запостил».


кароч мне нужно чтобы ты изучил интеренет и сеть на тему того чтобы был какой т опроект в котром собарны тесты для разных модееолц

точнее мы даем задание в разных ьенчах и маодель ее делает потмо проверяется результат и мы видим какая модель лучше


Понял — нужно «поставил → запустил → получил сравнение моделей». Давай поищу что есть **готового** в этом виде, а не «собери сам».Понял. Есть **готовые проекты-агрегаторы**, где уже собраны датасеты+ скоринг + поддержка моделей, и ты просто запускаешь команду. Три топ-варианта по убыванию универсальности:

## 🥇 OpenCompass — главный кандидат под твой запрос

Это **именно то что ты описал**. OpenCompass — платформа для эвалов LLM, поддерживает широкий набор моделей (Llama3, Mistral, InternLM2, GPT-4, Qwen, GLM, Claude и т.д.) на 100+ датасетах. One-stop platform — воспроизведение академических и инженерных эвалов для сравнения моделей и бэкендов на стандартных задачах, плюс построение автоматизированных пайплайнов для regression-тестинга и мониторинга бенчмарков.

Запуск выглядит так:

```bash
pip install opencompass

# Прогон одной модели на одном бенче
opencompass --datasets aime2024_gen --models hf_internlm2_5_1_8b_chat

# Матрица: несколько моделей × несколько датасетов
opencompass --datasets mmlu gsm8k humaneval --models qwen2_5_7b llama3_1_8b mistral_7b
```

На выходе — таблица со сравнением + детальные логи. У OpenCompass экосистема включает VLMEvalKit для vision-language моделей (220+ LMMs, 80+ бенчмарков), CompassVerifier (легковесный verifier-модель для outcome reward), MathBench для иерархической оценки математики. Активно развивается — в феврале 2026 добавили поддержку Intern-S1-Pro benchmarks.

**Когда брать:** хочешь "стандарт индустрии" + китайский фокус (там много reasoning/math/science бенчей которые в EleutherAI не покрыты).

## 🥈 LiveBench — самый "честный" и простой

LiveBench — open AI benchmark от команды Abacus.AI, NYU, Nvidia, U.Maryland и USC, включая Yann LeCun, использует contamination-free тестовые данные с объективным скорингом. Ключевая фишка — первый бенчмарк, который содержит часто обновляемые вопросы из свежих источников, оценивает ответы автоматически по объективным ground-truth значениям, покрывает math, coding, reasoning, language, instruction following и data analysis. Вопросы основаны на свежих math-соревнованиях, arXiv-статьях, новостях и датасетах + содержит сложные contamination-limited версии задач из Big-Bench Hard, AMPS и IFEval.

То есть твоя модель не могла "запомнить" эти вопросы при обучении — это критично если хочешь честное сравнение, особенно для поста в блог.

Запуск ещё проще:

```bash
git clone https://github.com/livebench/livebench
cd livebench
pip install -e .

# vLLM или Ollama — отдай endpoint
python run_livebench.py --model my-model --bench-name live_bench
```

Для локальных моделей используется gen_model_answer.py с указанием пути к модели. Скрипт run_livebench.py покрывает весь pipeline — генерация ответов, скоринг и вывод результатов.

**Когда брать:** хочешь minimum effort + честное (без contamination) сравнение для публичного поста. Я бы для блога взял именно его, потому что аргумент "вот свежий бенч, обновляемый ежемесячно" сильнее чем "вот MMLU где все уже зазубрили".

## 🥉 Inspect Evals — 200+ эвалов с современным DX

То о чём я говорил в прошлом ответе. 132+ зарегистрированных eval-пакетов по категориям: Coding 21, Cybersecurity 14, Math 7, Reasoning 22, Knowledge 22, Multimodal 5, Safeguards 21, Assistants 10. LiveBench, кстати, тоже доступен внутри Inspect: `inspect eval inspect_evals/livebench --model openai/gpt-5-nano` — то есть Inspect — это **обёртка** которая может прогонять и LiveBench, и SWE-Bench, и GAIA, и MMLU одной командой.

```bash
pip install inspect-ai inspect-evals

# Любой бенч на любой модели
inspect eval inspect_evals/mmlu --model ollama/qwen2.5:7b
inspect eval inspect_evals/humaneval --model ollama/llama3.1:8b
inspect eval inspect_evals/livebench --model ollama/mistral:7b

# Открываешь интерактивный web-viewer с результатами
inspect view
```

**Когда брать:** хочется максимум выбора эвалов + удобный web UI + интеграция в свой Python-код.

## Если совсем простое — Ollama-only утилитки

Для быстрого "посмотреть на скорость и качество ответов на собственных промптах" есть готовые инструменты под Ollama. cumhur/Ollama_Local_LLM_Benchmark тестирует множество локальных моделей против списка промптов и генерирует HTML-dashboard (через Matplotlib) сравнивающий response time, load duration, tokens/second, плюс CSV-репорт с полными ответами. Есть готовый Docker-образ OllamaIQ — `docker run -p 9912:9912 ftsiadimos/ollamaiq` и открываешь web-интерфейс.

Но это для скоростных метрик, не для качества — там нет нормальных датасетов с ground-truth.

---

## Мой конкретный совет под твой кейс

Бери **LiveBench + Inspect AI как обёртку**. Это даст тебе:

1. Современную инфру (Inspect) → удобно гонять, удобно строить графики из pandas-логов
2. Честный, не-contaminated бенч (LiveBench) → сильный аргумент для блога
3. Поддержку Ollama на маке и vLLM на GPU-машине из коробки
4. Возможность добавить и другие эвалы (MMLU, HumanEval, GSM8K) той же командой

Минимальный пайплайн:

```bash
# Сетап
pip install inspect-ai inspect-evals
ollama pull qwen2.5:7b llama3.1:8b mistral:7b phi3.5:3.8b

# Прогон матрицы models × tasks
for model in qwen2.5:7b llama3.1:8b mistral:7b phi3.5:3.8b; do
  for task in mmlu humaneval gsm8k livebench; do
    inspect eval inspect_evals/$task --model ollama/$model --limit 100
  done
done

# Web-viewer
inspect view
```

Если хочешь — могу прямо сейчас собрать тебе **готовый репо-скелет**: docker-compose с Ollama + Inspect, набор скриптов для прогона матрицы, питон-генератор графиков (plotly), и шаблон поста для блога с заглушками под цифры. Скажи на каких моделях и каких задачах фокус — и какое железо (только Mac M-чип или есть машина с GPU?).


А еще мне нужно читать токены на входе и на выходе и стоимость 

как это делать? через какой т ороутер? 

тоже изучи

и как работать в связке с тем что выше ты мне выдал

изучи сеть и и гитхаб


Хороший вопрос. Под "роутер + tokens + cost" есть два разных слоя: **gateway** (LiteLLM, OpenRouter) и **observability** (Langfuse, Helicone). Поищу что сейчас лучше для твоего пайплайна.Понял. По вопросу разложу — это два слоя стека, не один.

## Что есть и в чём разница

**Gateway/роутер** — единая OpenAI-совместимая API перед всеми моделями (локальными и облачными), считает токены и стоимость. Лидер сейчас — **LiteLLM**. Альтернативы: OpenRouter (hosted marketplace, +5.5% наценка), Portkey (платный, observability-first), Bifrost (Go, для high-throughput).

**Observability** — UI/dashboard для логов, prompts, traces, графики costs по времени. Langfuse, Helicone, Phoenix (Arize). Это поверх gateway.

Для твоего кейса однозначный выбор — **LiteLLM**, и вот почему:

LiteLLM — это унифицированная API для 100+ LLM, drop-in OpenAI-совместимость, production-ready gateway с virtual keys, spend tracking, guardrails, load balancing и admin dashboard из коробки. Open-source, MIT, self-hosted, без наценки. Поддерживает Bedrock, Azure, OpenAI, VertexAI, Cohere, Anthropic, Sagemaker, HuggingFace, vLLM, NVIDIA NIM — и Ollama, и vLLM, и любые OpenAI-совместимые endpoints.

Главный аргумент против OpenRouter в твоей задаче: OpenRouter — cloud middleman, каждый запрос идёт через их серверы, добавляя network latency. Для прототипирования и разведки моделей сложно его побить, но для прода с compliance или строгим латенси-бюджетом эта зависимость становится проблемой. А для **локальных Ollama-моделей он вообще не работает** — это hosted aggregator только cloud-моделей.

Зато OpenRouter удобно **подключить как один из backend'ов LiteLLM** — если хочешь в той же таблице сравнить локальный Qwen с GPT-5 и Claude без отдельных API-ключей.

## Архитектура под твой пайплайн

```
┌─────────────────────────────────────────────────────┐
│ Inspect AI / OpenCompass / LiveBench (eval-фреймы)  │
└────────────────────┬────────────────────────────────┘
                     │ OpenAI-compat API
                     ▼
        ┌────────────────────────────┐
        │  LiteLLM Proxy :4000       │
        │  - virtual keys            │
        │  - cost tracking → Postgres│
        │  - logging callbacks       │
        └─────────────┬──────────────┘
                     │
   ┌─────────┬───────┴───────┬──────────────┬──────────┐
   ▼         ▼               ▼              ▼          ▼
Ollama   vLLM           OpenRouter      OpenAI    Anthropic
 :11434   :8000        (cloud models)   direct     direct
 (Mac)   (GPU box)     (300+ моделей)
```

Cost tracking сам по себе оправдывает proxy для любой команды, тратящей &gt;$100/мес на LLM API. Можно подключить LiteLLM к внешним observability-платформам типа Langfuse или Helicone для более глубокой аналитики. Дашборд показывает costs по моделям/командам в реальном времени.

## Минимальный конфиг LiteLLM

```yaml
# litellm_config.yaml
model_list:
  # Локальные через Ollama
  - model_name: qwen2.5-7b
    litellm_params:
      model: ollama/qwen2.5:7b
      api_base: http://localhost:11434
      
  - model_name: llama3.1-8b
    litellm_params:
      model: ollama/llama3.1:8b
      api_base: http://localhost:11434
  
  # Локальные через vLLM (на GPU-машине)
  - model_name: qwen2.5-32b
    litellm_params:
      model: hosted_vllm/Qwen/Qwen2.5-32B-Instruct
      api_base: http://gpu-box:8000/v1
  
  # Cloud-модели как baseline
  - model_name: gpt-5
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY
  
  - model_name: claude-opus
    litellm_params:
      model: anthropic/claude-opus-4-7
      api_key: os.environ/ANTHROPIC_API_KEY
  
  # Через OpenRouter — экзотика и cheap-tier модели
  - model_name: deepseek-via-or
    litellm_params:
      model: openrouter/deepseek/deepseek-v3
      api_key: os.environ/OPENROUTER_API_KEY

# Кастомные цены для локальных моделей (опционально — оцениваешь GPU-час)
model_alias_map:
  qwen2.5-7b:
    input_cost_per_token: 0.00000005  # условно — твоя цена GPU-времени
    output_cost_per_token: 0.00000005

# Логирование в Postgres для cost tracking + analytics
litellm_settings:
  drop_params: true
  success_callback: ["langfuse"]  # опционально, для UI

general_settings:
  database_url: "postgresql://litellm:pass@localhost:5432/litellm"
  master_key: "sk-1234"
```

Запуск:

```bash
pip install 'litellm[proxy]'
docker run -d --name pg -e POSTGRES_USER=litellm -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres
litellm --config litellm_config.yaml --port 4000
```

LiteLLM недавно починили custom price cost tracking для Ollama и добавили поддержку max_completion_token — то есть прайс на локальные модели теперь работает корректно.

## Как подключить бенч-фреймворки к LiteLLM

**Все три фреймворка из прошлого ответа работают через OpenAI-совместимый endpoint** — для них LiteLLM выглядит как обычный OpenAI:

```bash
# Inspect AI — самый удобный
export INSPECT_EVAL_MODEL=openai/qwen2.5-7b  # имя из model_list LiteLLM
export OPENAI_API_KEY=sk-1234                 # master_key LiteLLM
export OPENAI_BASE_URL=http://localhost:4000/v1

inspect eval inspect_evals/mmlu --model openai/qwen2.5-7b
inspect eval inspect_evals/humaneval --model openai/llama3.1-8b
inspect eval inspect_evals/livebench --model openai/gpt-5
```

```bash
# LiveBench
python run_livebench.py \
  --model qwen2.5-7b \
  --api-base http://localhost:4000/v1 \
  --api-key sk-1234
```

```bash
# OpenCompass через OpenAI-совместимый бэкенд
opencompass --datasets mmlu_gen \
  --models openai_api --model-kwargs "base_url=http://localhost:4000/v1"
```

## Trackинг токенов и cost — три источника правды

**1. LiteLLM Postgres** — каждый запрос пишется в `LiteLLM_SpendLogs` таблицу с полями `prompt_tokens`, `completion_tokens`, `spend`, `model`, `api_key`. Готовый SQL → pandas → график:

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

**2. Inspect AI eval logs** — Inspect captures всё что нужно для дебага и воспроизведения. Каждый прогон порождает структурированный EvalLog файл с overall status, деталями task и модели, solver plan, каждым sample с input/output/score, агрегированными результатами, token usage stats и логами. Latency трекается детально с учётом ретраев. Token usage трекается тщательно — отличный proxy для cost. То есть Inspect и сам считает токены на каждый шаг.

```python
from inspect_ai.log import list_eval_logs, read_eval_log

rows = []
for path in list_eval_logs("./logs"):
    log = read_eval_log(path)
    usage = log.stats.model_usage  # dict model → ModelUsage
    for model, u in usage.items():
        rows.append({
            "model": model,
            "task": log.eval.task,
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "accuracy": log.results.scores[0].metrics["accuracy"].value,
        })
df = pd.DataFrame(rows)
```

**3. Источник цен для локальных моделей** — LiteLLM держит каноничный price-файл по адресу `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json`. Это тот же файл, который тащит к себе `browser-use` и другие либы. Можешь либо использовать его как есть для cloud-моделей, либо прибавить свои цены за GPU-час для локальных.

## Опционально — Langfuse сверху для красивого UI

Если хочешь не только pandas-графики, но и **live-dashboard в браузере** со всеми traces, prompts, costs по моделям — подключи Langfuse как success_callback в LiteLLM. Один docker-compose, и у тебя готовый UI с фильтрами, графиками costs по дням, breakdown по моделям/задачам, и каждый prompt/response виден в трейсе. Это уже почти готовый «вид как у настоящих SaaS-платформ» для скриншотов в твой блог-пост.

## Итоговый стек

```
Ollama / vLLM / OpenAI / Anthropic / OpenRouter
                    ↓
          LiteLLM Proxy + Postgres   ← cost & tokens
                    ↓
       Inspect AI (eval engine + 200+ tasks)
                    ↓
          eval logs + spend logs
                    ↓
       pandas → plotly → блог-пост
                    +
             Langfuse UI (опционально, для скринов)
```

Все четыре слоя независимы, общаются через **OpenAI-совместимый API** — самый универсальный стандарт сейчас.

Скажи слово — соберу тебе **готовый репо-скелет**: `docker-compose.yml` (Postgres + LiteLLM + Langfuse + Ollama), `litellm_config.yaml` с твоими моделями, скрипт `run_benchmarks.py` который гоняет матрицу `models × tasks` через Inspect, и `make_report.py` который вытаскивает токены/cost/accuracy и рендерит plotly-график плюс markdown-табличку. Останется только запустить и копипастнуть в блог.

Скажи только:
1. Какие **модели** хочешь сравнивать (локальные через Ollama? + что-то облачное?)
2. Какие **задачи** интересуют (math, code, reasoning, RAG, агентика?)
3. Есть ли **GPU-машина** или только Mac?

Кароч в итоге я хчоу такой график паутинку в котрой показывает разнеы мтерики чтобы люди понмиал ичто и когда использовать

какие задачи хорошо выполняет в разных задачах

Понял идею — это паутинка от etechlead. Сразу скажу что у автора это **субъективные экспертные оценки** (видишь "10" на всех осях у GPT-5.4 — реальные бенчи так не работают). Но идея отличная для блога — даю тебе **объективный pipeline**: реальные бенчи → нормализованные 0-10 → radar.

Сначала покажу как это будет выглядеть на твоих данных (живой пример), потом разберём pipeline.Вот так это будет выглядеть. Теперь главное — **как собрать такую картинку из объективных данных**, а не из оценок на глаз.

## Маппинг: ось паутинки → реальный бенчмарк

Каждая ось — это либо один бенч, либо агрегат из нескольких. Вот рабочий маппинг под практические задачи:

| Ось | Источник | Где брать |
|---|---|---|
| Ризонинг | MMLU + GPQA Diamond + BBH | Inspect Evals |
| Длинный контекст | RULER + Needle-in-Haystack | Inspect Evals / Lighteval |
| Следование инструкциям | IFEval | Inspect Evals |
| Кодинг (basic) | HumanEval + MBPP | Inspect Evals |
| Кодинг (real) / Архитектура | SWE-bench Verified | Inspect Evals |
| Агентность | GAIA + AgentBench | Inspect Evals |
| Инструментарий | BFCL (Berkeley Function Calling) | bfcl-eval |
| Планирование | PlanBench / TravelPlanner | Inspect Evals |
| Математика | GSM8K + MATH + AIME | OpenCompass / Inspect |
| Мультиязык | Belebele / MGSM | Lighteval |
| **Стабильность** | variance того же бенча на 5 seeds | Inspect (запустить 5 раз) |
| **Скорость** | output tokens/sec | LiteLLM SpendLogs |
| **Экономность** | accuracy / $ per 1M output tokens | LiteLLM SpendLogs + eval |
| Безопасность | XSTest + StrongREJECT | Inspect Evals |

Ключевые **две оси, которых нет в обычных лидербордах** — Скорость и Экономность. Они идут не из бенч-фреймворка, а из **LiteLLM логов** которые мы уже настроили. Это твоё конкурентное преимущество как блогера: большинство сравнений показывают либо качество, либо цену, а у тебя обе оси на одной картинке.

## Нормализация — как из бенчей сделать 0-10

Это не тривиальный шаг, и тут есть варианты:

**Вариант А — min-max по моделям в твоей выборке.** Берёшь все модели которые тестируешь, по каждой оси находишь min и max, маппишь в [0, 10]. Просто, но шкала зависит от выборки — если добавишь супер-слабую модель, у всех других баллы вырастут.

**Вариант Б — фиксированные якоря.** 0 = случайный угадай, 10 = state-of-the-art (например, последняя цифра с папера). Стабильнее между постами, можно сравнивать "сегодня vs полгода назад", но требует поддерживать таблицу якорей.

**Вариант В — относительно reference-модели.** Берёшь GPT-5 или Claude Opus как 10, остальное масштабируется относительно. Хорошо для блог-постов "vs frontier".

Для блога **я бы взял Б** — фиксированные якоря, потому что это даёт честное "X стал лучше за год".

## Pipeline: от eval logs до radar

```python
import pandas as pd
import plotly.graph_objects as go
from inspect_ai.log import list_eval_logs, read_eval_log
import sqlalchemy as sa

# 1. Собираем accuracy из Inspect логов
def collect_accuracy(logs_dir):
    rows = []
    for path in list_eval_logs(logs_dir):
        log = read_eval_log(path)
        for model, usage in log.stats.model_usage.items():
            rows.append({
                "model": model,
                "task": log.eval.task.split("/")[-1],
                "accuracy": log.results.scores[0].metrics["accuracy"].value,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "duration_sec": (log.stats.completed_at - log.stats.started_at).total_seconds(),
            })
    return pd.DataFrame(rows)

# 2. Собираем cost из LiteLLM Postgres
def collect_cost(db_url):
    eng = sa.create_engine(db_url)
    return pd.read_sql("""
        SELECT api_key as run_id, model, 
               SUM(prompt_tokens) as in_tok,
               SUM(completion_tokens) as out_tok,
               SUM(spend) as cost_usd
        FROM "LiteLLM_SpendLogs"
        GROUP BY api_key, model
    """, eng)

# 3. Маппим бенчи на оси и агрегируем
AXIS_MAP = {
    "Ризонинг":          ["mmlu", "gpqa_diamond", "bbh"],
    "Длинный контекст":  ["ruler", "niah"],
    "Инструкции":        ["ifeval"],
    "Кодинг":            ["humaneval", "mbpp"],
    "Архитектура":       ["swe_bench_verified"],
    "Агентность":        ["gaia", "agentbench"],
    "Инструменты":       ["bfcl"],
    "Планирование":      ["planbench"],
    "Математика":        ["gsm8k", "math", "aime"],
    "Мультиязык":        ["belebele", "mgsm"],
    "Безопасность":      ["xstest", "strongreject"],
}

# Якоря (Вариант Б)
ANCHORS = {
    # ось: (значение_для_0, значение_для_10)
    "Ризонинг":     (0.25, 0.90),
    "Кодинг":       (0.20, 0.95),
    "Архитектура":  (0.00, 0.70),  # SWE-bench Verified
    # ...
}

def normalize(value, lo, hi):
    return max(0, min(10, 10 * (value - lo) / (hi - lo)))

def build_radar_data(df_acc, df_cost):
    result = {}
    for model in df_acc["model"].unique():
        scores = {}
        for axis, tasks in AXIS_MAP.items():
            vals = df_acc[(df_acc.model == model) & (df_acc.task.isin(tasks))].accuracy
            if len(vals):
                lo, hi = ANCHORS.get(axis, (0, 1))
                scores[axis] = normalize(vals.mean(), lo, hi)
        
        # Stability — variance по seeds (если запускал несколько раз)
        std = df_acc[df_acc.model == model].groupby("task").accuracy.std().mean()
        scores["Стабильность"] = normalize(1 - std, 0.5, 1.0)
        
        # Speed — output tokens/sec
        m_rows = df_acc[df_acc.model == model]
        tps = (m_rows.output_tokens / m_rows.duration_sec).mean()
        scores["Скорость"] = normalize(tps, 10, 200)
        
        # Экономность — accuracy per dollar
        cost_per_correct = df_cost[df_cost.model == model].cost_usd.sum() / m_rows.accuracy.sum()
        scores["Экономность"] = normalize(-cost_per_correct, -0.05, -0.001)  # обратная шкала
        
        result[model] = scores
    return result

# 4. Рендерим radar
def plot_radar(scores_by_model, out_html):
    axes = list(next(iter(scores_by_model.values())).keys())
    fig = go.Figure()
    for model, scores in scores_by_model.items():
        fig.add_trace(go.Scatterpolar(
            r=[scores[a] for a in axes] + [scores[axes[0]]],
            theta=axes + [axes[0]],
            name=model, fill='toself', opacity=0.5
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        template="plotly_dark", height=600, width=800
    )
    fig.write_html(out_html)
```

## Пара важных нюансов

**Стабильность как ось.** У etechlead на картинке "Стабильность" — субъективно. У тебя будет объективная: запусти **тот же бенч 3-5 раз с разными seeds**, посчитай std accuracy. Чем меньше std → выше балл. Это сильная техническая фишка, которую можно отдельно подсветить в посте.

**Скорость на разном железе.** Если сравниваешь локальные Ollama vs cloud API — speed несравним напрямую (твой Mac vs дата-центр OpenAI). Для честного сравнения: либо отдельные паутинки "Local на M-чипе" и "Cloud", либо нормализуй tokens/sec по типу деплоя.

**"Когда что использовать" — таблица под графиком.** Паутинка отвечает на "кто лучше где", но люди хотят явный рецепт. Под графиком в посте дай таблицу типа:

```
| Сценарий                          | Рекомендация       |
| Длинная рефактор-сессия в Cursor  | Claude Opus 4.7    |
| Агентный flow с tool-use          | GPT-5              |
| Локальный coding-assistant на Mac | Qwen 2.5 / DeepSeek|
| Bulk-обработка документов        | Qwen 2.5 72B       |
```

## Что собрать тебе для блог-поста

Готов сделать **starter-репо** с такой структурой:

```
benchmark-radar/
├── docker-compose.yml         # LiteLLM + Postgres + Ollama
├── litellm_config.yaml        # модели для бенчей
├── run_benchmarks.py          # матрица models × tasks через Inspect
├── pipeline/
│   ├── collect_accuracy.py    # из Inspect logs
│   ├── collect_cost.py        # из LiteLLM Postgres
│   ├── normalize.py           # с ANCHORS
│   └── render_radar.py        # plotly → html + png для блога
├── anchors.yaml               # фиксированные якоря по осям
└── post_template.md           # markdown-шаблон поста с заглушками
```

Скажи только три вещи и соберу:
1. Какие **модели** в твоём пуле (5-7 штук) — нужно конкретно
2. Какие **оси** оставляешь из моего списка (или хочешь добавить — например, "RAG-точность", "Скорость на твоём железе")
3. Хочешь **plotly** (интерактив для embed в блог) или **matplotlib** (просто PNG как у etechlead)?

реальные бенчи так не работают). - а как тогда сделат ьчтобы реально людям давать пользу и чтобы им было иснтерсно и чтобы познавтаельно и чтобы они делали вывод и использовали в своих заадчах те модели которые лушче подходят под задачи?

я вообще думаю показывать наверое лучше 2 графика - паутину и еще какую то - или нет?

----

еще идея такая 

делать задачу напмриер в зависимоти от бенча или задачи на чистой ллм без обвзяки - в агенте (claude code , codex, germes и тд) чистом без агентов без скиллов и бзе памяти

потмо память подрубить и показать результат той же задачи

затем + скилл
потмо + аогент и затем агент + скилл и память

потмо память взять не файловую а например hindsight или mem0 и так далее

затем встариваем разное

или например агенты и скиллы стоковые с voltagent или другого awesome ресурса

также потом намприер взять какой нибудь forgeplan и с ним и чтоыб показат ьчт оесли будет в  хранес добавле docs artefacts  шутка для создания и вдени документации технчиской и архитектруной


также что если например агентов пропустить чреез https://github.com/karpathy/autoresearch и улучишь агентов чреез нее

тоесть агент берм стоакоквый он прогоняет например и итерарует заадчи а там кто т опровреят как выполнено и таким образом видим с более высоким качество опсианый агнет и скилл дает лучший резултта




скаж икак понял щадачу и расскажи мне чтобы я понял что ты понял


Окей, дай пересказать твою идею своими словами, чтобы убедиться что я понял правильно — потом отвечу на вопрос про "сколько графиков" и autoresearch.

## Как я понял твою задачу

Ты хочешь делать **не сравнение моделей** (этого в интернете — миллиард), а **сравнение слоёв обвязки** на той же задаче. Меняется не модель, а то что вокруг неё:

```
Уровень 0:  голая LLM (один промпт, один ответ)
Уровень 1:  + системный промпт / роль
Уровень 2:  + tools (function calling)
Уровень 3:  + skills (Claude Code skills, AGENTS.md)
Уровень 4:  + память файловая (CLAUDE.md, /memories)
Уровень 5:  + память векторная (mem0, hindsight, Letta)
Уровень 6:  + агентный цикл (Claude Code, Codex, Hermes)
Уровень 7:  + validator-loop (autoresearch style — второй агент проверяет, итерирует)
Уровень 8:  + специализированная система (ForgePlan для doc/arch, voltagent для общего)
```

И на каждом уровне — **одна и та же задача**, замеряем accuracy / cost / latency. Получаем кривую: как обвязка превращает посредственную модель в полезный инструмент. И **что именно** даёт прирост, а что только cost наматывает.

Это, кстати, имеет нормальное название — **ablation study продакшен-стека** или **scaffolding evaluation**. В академии этим почти никто не занимается (там сравнивают сырые модели на сырых датасетах), а в индустрии все делают это интуитивно и без чисел. Поэтому твой пост закроет реальный пробел: люди делятся "я добавил mem0 и стало лучше" — но никто не показывает на сколько именно, на каких задачах, и где предел.

Ключевой инсайт который ты можешь показать: **дешёвая модель с правильной обвязкой часто бьёт дорогую модель без неё**. Условный Qwen 2.5 14B + skills + validator может догнать GPT-5 без обвязки на конкретной задаче за 1/20 цены. Это сильный практический вывод для читателя.

## Про "один график или два"

Один радар тут не справляется — он отвечает только на "кто где лучше" по моделям. Твоя главная история — **про обвязку**, а её радар не покажет.

Нужно **три графика**, каждый отвечает на свой вопрос:

**График 1 — Радар по моделям** (как этот выше). Отвечает: "Какая модель в чём сильна на чистых задачах?" Это контекст, начало поста.

**График 2 — Ablation ladder** (главный график поста). Отвечает: "Что даёт каждый слой обвязки?" Это столбики или waterfall, где видно: голая LLM → +tools (+8%) → +skills (+12%) → +memory (+5%) → +validator (+15%). Покажу пример ниже.

**График 3 — Scatter quality vs cost** (Pareto-фронт). Отвечает: "Какая комбинация модель+обвязка оптимальна для моего бюджета?" По оси X — cost per task в $, по Y — accuracy. Каждая точка = модель+стек. Pareto-фронт обводится линией. Читатель сам ставит свой бюджет и видит оптимум.

Вот как примерно выглядит главный график:Сразу видно историю: голая Qwen 14B на 42%, со всей обвязкой — 88%. Сонет 4.6 голый — 64%, со всем — 95%. То есть **обвязка дала Qwen +46 п.п., Сонету +31 п.п.** Маленькая модель выигрывает от обвязки больше — у неё ниже база. Это и есть основной message поста: вкладываться в стек выгоднее чем в апгрейд модели, особенно если ты на локальном железе.

## Про autoresearch и validator-loop

Идея Карпатого (и аналогов типа Self-Refine, Reflexion, AlphaCodium) — это **inference-time validation**. Берётся ответ агента, прогоняется через критика, критик находит проблемы, агент чинит, повторяется N раз. Это даёт +10-20% accuracy на сложных задачах, но **цена х5-х10** — потому что несколько раундов inference.

В твоей лесенке это **L6 validator**. Отдельный слой, который замеряется отдельно. И именно тут будет интересный момент: **на простых задачах L6 ничего не даёт** (или даже хуже — модель начинает сомневаться в правильном ответе), а **на сложных дает огромный прирост**. Это разделение полезно показать отдельным графиком — accuracy gain от L6 в зависимости от сложности задачи. Может стать четвёртым графиком если идея пойдёт.

## Про специализированные системы (ForgePlan, voltagent)

Это уровень L7 — "специализированный стек под класс задач". Тут логика чуть другая: ты замеряешь **тот же стек на разных моделях**, а не разные слои. То есть: "ForgePlan + Qwen vs ForgePlan + Sonnet vs ForgePlan + GPT-5" на задаче "напиши PRD для нового сервиса". Это уже отдельный экспериментальный кейс — отдельный пост в серии. Сначала базовая лесенка L0-L6, потом отдельные посты "что даёт ForgePlan", "что даёт voltagent" и т.д.

## Сборка серии постов

Я бы строил это как **серию из 4-5 постов**, а не один:

1. **"Как мы меряем"** — методология, маппинг бенчей, нормализация, радар (твоя текущая идея)
2. **"Голая LLM vs обвязка"** — лесенка L0→L6 на одной задаче, главный график — ablation bars
3. **"Память — какая работает"** — сравнение CLAUDE.md / mem0 / hindsight / Letta / Zep на задачах с долгим контекстом
4. **"Validator-петля — когда оно того стоит"** — autoresearch-style для разных уровней сложности
5. **"Готовые стеки"** — ForgePlan, voltagent, Claude Code на одних задачах

Каждый пост стоит на своих ногах, но они линкуются. Это и для SEO лучше, и для удержания читателя.

## Что мне нужно от тебя, чтобы пойти дальше

Прежде чем собирать репо, давай зафиксируем эксперимент. Скажи:

1. **Какие 2-3 задачи** взять как тест-кейсы для лесенки L0→L6? Хорошие кандидаты: рефакторинг модуля по описанию (твой кейс), написание PRD/RFC из заметок, дебаг кода по логам, миграция между фреймворками. Должны быть задачи **где обвязка реально влияет** — потому что на MMLU никакая память не поможет.
2. **Какие модели** в пуле? Я бы взял пару локальных (Qwen 2.5 14B + Llama 3.3 70B на M-чипе или GPU) и пару cloud (Sonnet 4.6 + GPT-5) — 4 точки достаточно, больше — каша.
3. **Что под рукой как референсные импленты** для слоёв? Мем-стеки которые ты УЖЕ умеешь крутить (например, mem0 ты упомянул — значит знаешь). Если какой-то слой собирать с нуля — это уйдёт на недели.

Скажи это — и я нарисую полный план эксперимента: какие задачи, какой evaluator (что считается "правильным ответом"), какие именно тулзы реализуют каждый слой, и какая структура репо чтобы всё гонять одной командой и складывать в SQLite или Postgres для пост-фактум анализа.

Так понял задачу или я что-то не так интерпретирую?


Какие 2-3 задачи - я думаю что нужн опримдать 2 3 типа проектво


тольок ыронт
тольок бэк
fullstack
базы данных
devops (k8s или docker)
докментация
тестирвоание
ревью может или что т оеще
что т оеще что оыбчно требуется в работе и что отнмиает время и то чт онужн очтобы сам агнет делал

Какие модели

* думаю что взять opnai, anthropic, google и еще парочку самых изветсных - например composer 2 и кто там еще есть - давай кажудю топовую модель или по 5-7 у каждог овренджора
* локальные самые исзтеные и их арзын весрии моделей по 2-4 - карчоч чтобы в одной категории были
* 
Что под рукой как референсные импленты

* claude code + file mem
* claude code + hindsight
* claude code + mem file + agents 
* claude code + file mem + agents
* claude code + file mem + agents + skills
* claude code + agents
* claude code + skills
* claude code + agents + skills
* claude code + agents + skills + file mem 
* claude code + agents + skills + hindsight
* claude code + agents + skills + forgeplan
* claude code + agents + skills + forgeplan + file mem
* claude code + agents + skills + hindsight + forgeplan


И также с codex и с gemini и hermes и c другим парочкой cli агент оркетсраторами

по дразыне модели

кароч комбинации
-----
И на каждом уровне — одна и та же задача, замеряем accuracy / cost / latency. Получаем кривую: как обвязка превращает посредственную модель в полезный инструмент. И что именно даёт прирост, а что только cost наматывает.
Это, кстати, имеет нормальное название — ablation study продакшен-стека или scaffolding evaluation. В академии этим почти никто не занимается (там сравнивают сырые модели на сырых датасетах), а в индустрии все делают это интуитивно и без чисел. Поэтому твой пост закроет реальный пробел: люди делятся "я добавил mem0 и стало лучше" — но никто не показывает на сколько именно, на каких задачах, и где предел.
Ключевой инсайт который ты можешь показать: дешёвая модель с правильной обвязкой часто бьёт дорогую модель без неё. Условный Qwen 2.5 14B + skills + validator может догнать GPT-5 без обвязки на конкретной задаче за 1/20 цены. Это сильный практический вывод для читателя.


-----
по сти это дает и показывает цену - скорост ь- качество по мделям разынм и комбианциям

так как у нас напрмиер litellm стоит мы видим сразу мтерики + то чт одал бенчмарк
----

Окей, понял. Давай я сразу скажу прямо: **то, что ты описываешь как полный grid — невозможно физически**. И покажу почему, а потом — как сделать так чтобы получилось.

## Математика комбинаторного взрыва

Считаем по твоему ТЗ:

| Ось | Размер |
|---|---|
| Модели (cloud + local) | ~33 (17 cloud + 16 local) |
| Типы задач | 8 (front, back, fullstack, db, devops, docs, tests, review) |
| Instance на тип | ~3 (нужно для статистики, один пример = шум) |
| Комбинации обвязки | ~13 на CLI |
| CLI-оркестраторы | 5 (Claude Code, Codex, Gemini, Hermes, +1) |

**Полный grid = 33 × 8 × 3 × 13 × 5 = 51 480 прогонов.**

Средний прогон агентной задачи — 5-30 минут (короткие — секунды, длинные с агентным циклом — часы). Если усреднить 5 минут, это **4 290 часов = почти полгода** непрерывного сжигания GPU и API-кредитов. По cost — на cloud-моделях это легко $30-50k. На локальных бесплатно по API, но GPU-часы или электричество на M-чипе тоже считаются.

**Это не делается. Никогда. Никто.** Даже Anthropic / OpenAI в своих internal evals режут пространство.

## Решение: factorial design + серия из 5 постов

В статистике экспериментов это называется **fractional factorial design** — не гоняешь весь куб, а **двигаешь по одной оси за раз**, остальные фиксируешь. Каждое движение — отдельный эксперимент → отдельный пост в серии.

Я предлагаю такую раскладку:Каждая фаза — отдельный пост, отвечает на ОДИН вопрос. Между фазами **только одна переменная меняется**, остальные зафиксированы. Это и есть факторный дизайн.

## Таксономия слоёв обвязки (упорядоченный твой список)

У тебя в ТЗ слои частично смешаны. Стандартизируем язык — это и для тебя как для автора, и для читателя:

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

L0-L7 — это **общий стек**. L8 — это **готовые композиции** L0-L7 заточенные под класс задач. ForgePlan, например, это по сути L3+L4+L6+L8 в одной упаковке для документации.

## Какие задачи под какую фазу

Твой список из 8 типов проектов хорош для **Фазы 1** (там разнообразие важно). Для **Фазы 2-4** наоборот — нужны 2-3 задачи где обвязка реально влияет. Иначе на простых задачах (например "напиши getEndpoint") даже голая модель даст 100%, и ablation покажет плоскую линию.

Вот разделение:

**Для Фазы 1 (радар по моделям)** — 8 типов × 2-3 задачи каждый = ~20 задач. Должны быть короткими (1 промпт → ответ → проверка), чтобы grid 33×20 был исполним:
- Frontend: компонент с состоянием, фикс CSS-бага
- Backend: REST endpoint с валидацией, JWT middleware
- Fullstack: добавить фичу через все слои (минимальное)
- DB: схема для домена, написать миграцию, оптимизировать запрос
- DevOps: Dockerfile для приложения, k8s manifest, CI/CD пайплайн
- Docs: README, JSDoc для модуля
- Tests: unit-тесты по коду, integration-тест
- Review: найти баги в diff

**Для Фазы 2-3 (лестница обвязки и память)** — 2-3 ТОЛСТЫЕ задачи где есть код, контекст, и есть куда расти:
- "Отрефакторь модуль на 500-1000 строк, сохранив API и тесты"
- "Напиши PRD на новую фичу по краткой заметке + 3 ссылкам на похожие фичи"
- "Дебажь баг по логам + 5 файлов кода → найди причину и предложи фикс"

На таких задачах голая модель проваливается, а каждый слой обвязки даёт измеримый прирост. Это где **ablation bars выглядят красиво**.

**Для Фазы 4 (CLI-агенты)** — берёшь ОДНУ задачу из Фазы 2 (например рефакторинг) и гоняешь её через Claude Code / Codex / Gemini / Hermes / +1 — каждый со своим лучшим стеком. Тогда видно различия между CLI как продуктами.

**Для Фазы 5 (Pareto)** — комбинируешь 6-8 лучших стеков из Фаз 2-4 и гоняешь на 8 типах задач из Фазы 1. Это уже финал — финальный scatter cost vs quality.

## Про composer 2, Hermes и прочие — реалити-чек

Composer 2 (это Cursor Composer) и Hermes — это **закрытые продукты, у них нет API**. Они работают только внутри IDE. Для воспроизводимого benchmark'а их брать **очень больно**: придётся через computer-use агента кликать в IDE, замерять время, копировать diff обратно. Реализуемо, но это +2 недели работы только на инфру.

Я бы для серии взял **только API-доступные CLI**: Claude Code, Codex CLI, Gemini CLI, Cline, Aider, Continue. Они все скриптуются, все умеют OpenAI-совместимый endpoint, все интегрируются с LiteLLM. Cursor/Composer оставь на отдельный пост "feel-test" с субъективным выводом (как у etechlead) — не пытайся их встраивать в quantitative ladder.

## Что нужно от тебя для старта Фазы 1

Чтобы я собрал реальный starter-репо под Фазу 1, нужно зафиксировать четыре вещи:

**1. Финальный пул моделей для Фазы 1.** Я предлагаю 12-15 штук вместо 33 — это уже даёт богатый радар, и в 2 раза меньше прогонов. Скажи "да/нет" на такой пул:

```
Cloud (8):
  - Claude Opus 4.7, Sonnet 4.6
  - GPT-5, GPT-5-mini  
  - Gemini 2.5 Pro, Gemini 2.5 Flash
  - DeepSeek V3.5, Grok 4
Local (6, через Ollama/vLLM):
  - Qwen 2.5 72B, Qwen 2.5 14B
  - Llama 3.3 70B
  - Mistral Large
  - DeepSeek-V3-local (если влезает)
  - GLM 4.6
```

**2. Финальный список 20 задач для Фазы 1** — это самое долгое, можем вместе пройти. Я могу написать первичный набор, ты приёмишь/правишь.

**3. Где гонять.** Mac M-чип для маленьких локальных, GPU-машина с ≥48GB VRAM для 70B+ (своя или rented), cloud API для остальных. Скажи что у тебя есть физически — буду планировать grid под это.

**4. Скоринг.** Кто/что определяет "правильно". Для кода — automated (тесты, линтер, типы). Для документов и архитектуры — LLM-judge с rubric'ом (Claude Opus как судья — стандартный приём). Для всех — нужен **gold answer или критерий**. Это самое затратное по подготовке: каждая из 20 задач должна иметь определение успеха.

Скажи "да поехали с пулом моделей и помоги собрать 20 задач" — и сделаем именно это следующим шагом, без распыления на остальные фазы пока. Phase 1 — это та основа, без которой Phase 2-5 бессмысленны.


1. Финальный пул моделей для Фазы 1. - да ок
2. Финальный список 20 задач для Фазы 1 - да ок
3. Где гонять. - runpod - cerebras - openrouter и что то может быт ьеще
4. Скоринг. думаю нужно построит ьнекий голд вариант с цикломатическим тетсом и про соблюдение паттернов - метрик каких то - доккментации и покрытием тестами и так адлее - на одном и ом же промте или задаче н ов разых агентах и llm

что скажешь?


Хорошо, поехали. Один уточняющий чек по компьюту, потом покажу скоринг и сразу пойду составлять 20 задач.

Дай гляну текущий список моделей в Cerebras — там часто что-то добавляется и убирается.Окей, по компьюту хорошо сложилось — это идеальная тройка для нашего пайплайна. Распределю модели по providers и потом скоринг.

## Распределение моделей по провайдерам

Из 14 моделей в пуле каждая идёт туда где она дешевле/быстрее, всё под одной крышей LiteLLM:

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
| Mistral Large | **OpenRouter** | Через Mistral API |
| DeepSeek V3.5 | **OpenRouter** (DeepInfra/DS direct) | Дешевле через aggregators |
| Qwen 2.5 14B (smoke-test) | **Mac локально** (Ollama) | Для дебага пайплайна |

Cerebras-фишка для нас критична — там Llama 3.3 70B бежит на 1800+ tok/s, в 10-20× быстрее GPU-инференса, по цене $0.60-3.90 за MTok. Это значит что **гонять 20 задач × 14 моделей** на Cerebras-моделях занимает минуты, а не часы. Free-tier — 1M tokens/day, 30 RPM, без credit card — этого на Фазу 1 может хватить для smoke-test, для full grid возьмёшь paid tier.

Runpod нужен только для **Qwen 2.5 72B** (и потенциально Mistral Large если у Mistral API будут проблемы). Можно поднять `vllm/Qwen2.5-72B-Instruct` на H100 ~$3/час, прогнать 20 задач за 1-2 часа = $3-6 за всю модель. Не больно.

## Один уточняющий момент

Mistral Large (теперь часто Mistral Medium 3 / Magistral) — это **закрытая** модель Mistral. Доступна только через их API или OpenRouter, не локально. Если хочешь именно open-weight Mistral — нужен Mixtral 8x22B или Mistral-Small, и это идёт на Runpod. Скажи какую версию имел в виду.

## Скоринг — multi-dimensional gold

Твоя идея с "gold + цикломатика + паттерны + докс + покрытие" — это **правильный путь**. Я бы оформил это так:

Для каждой задачи у нас есть **gold решение** (твоя/моя референсная реализация) и **набор автометрик**, который вычисляется на ответе модели. Итоговый балл — взвешенная сумма нормированных метрик.

**Универсальный скоринг для кодовых задач** (front/back/fullstack/db/devops/tests):

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

**Скоринг для документации/архитектуры/review** — тут automatic metrics не помогают, идёт **LLM-judge с rubric**:

```python
rubric_doc = {
    "structural_completeness": "Все нужные секции присутствуют (0-10)",
    "factual_accuracy":         "Нет фактических ошибок относительно gold (0-10)",
    "clarity":                  "Понятно ли junior-разработчику (0-10)",
    "actionability":            "Можно ли по этому работать (0-10)",
    "consistency":              "Не противоречит ли сам себе (0-10)",
}
# Каждый критерий через Claude Opus 4.7 как судью с blind labels (модель не знает кто автор)
# Усреднение → 0-10
```

**Скоринг для code review задач:**

```python
review_metrics = {
    "recall":          0.4,  # % реальных багов из ground truth списка
    "precision":       0.3,  # из найденных, % реально багов (не false positives)
    "severity_match":  0.2,  # совпадение оценок critical/major/minor с gold
    "fix_quality":     0.1,  # LLM-judge на предложенные фиксы
}
```

## Технические подводные камни LLM-judge

Чтобы судья давал честные оценки:

**Blind labeling** — судья не должен видеть имя модели. Всем ответам присваиваешь `submission_A`, `submission_B`... — это исключает bias "о, это от Claude, наверное хорошо".

**Position randomization** — порядок ответов рандомизируется. Иначе судья систематически предпочитает первые/последние.

**Length normalization** — судья имеет bias на длинные ответы. В rubric явно прописать "оценка не должна зависеть от длины".

**Self-bias** — если судья = Claude Opus, и одна из тестируемых моделей тоже Claude, у него bias в свою пользу (доказано в paперах). Лучше использовать **отдельную модель которой нет в выборке** как судью (например, GPT-5 как судья если в выборке Claude).

**Inter-judge agreement** — для критических задач прогнать через 2-3 разных судей и взять усреднение/медиану.

## Что дальше — задачи

Сейчас составлю **первичный draft 20 задач**. Формат для каждой:

```yaml
- id: be_001
  category: backend
  difficulty: medium
  description: "Напиши REST endpoint на FastAPI который..."
  inputs: [список входов с примерами]
  gold_path: ./gold/be_001/solution.py
  success_criteria:
    - All tests in ./gold/be_001/tests.py pass
    - Cyclomatic complexity ≤ 8
    - Type-safe (mypy clean)
  evaluator: pytest + radon + mypy + llm_judge
  expected_tokens_in: ~800
  expected_tokens_out: ~1500
```

Распределение по типам:

| Категория | Кол-во | Сложность |
|---|---|---|
| Frontend (React/Vue components) | 3 | easy/med/hard |
| Backend (API, auth, services) | 3 | easy/med/hard |
| Fullstack (E2E feature) | 2 | med/hard |
| Database (schema, migrations, queries) | 2 | med |
| DevOps (Docker, k8s, CI) | 2 | med |
| Documentation (README, PRD, ADR) | 3 | easy/med/hard |
| Tests (unit, integration) | 2 | med |
| Code Review (find bugs) | 2 | med/hard |
| Refactoring (большая задача, "тонкая") | 1 | hard |
| **Итого** | **20** | |

Один уточняющий вопрос пока я не начал писать:

**На каком языке/стеке делаем задачи?** У тебя в фоне Rust (ForgePlan), TypeScript/Node.js (Gerts, Orchestra), Python (CNP anti-fraud). Все три — реалистичные. Но **один эксперимент = один стек**, иначе модели с разной силой в разных языках сделают сравнение мутным. Я бы предложил:

- **TypeScript / Node.js** как основной (самый широкий — front + back + fullstack + tests + docs естественно ложатся)
- + 2-3 задачи на **Python** (DevOps скрипты, data-related)
- DB-задачи нейтрально (Postgres/SQL без привязки к языку)

Скажи это — и я выкатываю 20 задач полным yaml-файлом, ты ревьюишь, мы фиксируем, и начинаем собирать репо. Договорились?

я думаю что судьи должны быть тоже разыне тоесть те же модели но делат ьтак чтобы модель не тетсила сама себя а тетсила все другие - хотя и себя тодже н опросто не говрить ей - она недолжна занть об хтом - учест ьчтобы в комментах не ставил свою подпись и в доках - специальног это учесть


----
что еще нужно сразу учесть и какие практики использроват ьчтобы судья ьыд хорощ и сам процесс ыбл таким чтобы рельно показал правдиыве и чистые числа


чтобы это было супер круто и хороший контент дял стайте и серии статей


Отлично подметил — это самый главный технический вопрос всей серии. Если scoring дырявый, все красивые радары и pareto-чарты теряют смысл. Дам полный набор практик, которые превращают это в **публикуемое исследование**, а не "блог-пост с цифрами".

## 1. Rotating judges — твоя идея, систематизируем

Стандарт в литературе называется **LLM-as-a-Jury** или **Panel of LLM evaluators**. Ключевые правила:

**Модель не судит сама себя.** Никогда. Это исключает self-enhancement bias (доказано в paперах: Llama-judge ставит Llama-ответам на +5-15% выше, GPT — GPT, и так у всех).

**Минимум 3 разных судьи на каждый ответ.** Один судья — это subjective. Два — может быть тай. Три — есть медиана. Финальный балл = медиана трёх оценок, не среднее (медиана устойчива к выбросам).

**Судьи из разных family.** Нельзя ставить судьями три модели Anthropic — они слишком похожи и accord biases. Бери микс: например, один Anthropic, один OpenAI, один Google, один open-weight. Это даёт inter-family agreement.

Конкретная матрица для нашего пула (X = судит, — = не судит):

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

5 судей × 14 подсудимых × 20 задач = 1400 judge-calls на Фазу 1. Каждый judge-call ~$0.02-0.05 → ~$30-70 на судейство всей фазы. Терпимо.

Опционально можно добавить **Grok-4 как 6-го судью** — он не в Anthropic/OpenAI/Google семьях, даёт ещё одну точку зрения.

## 2. Anonymization — чтобы судья реально не знал

Это **больше работы чем кажется**. У моделей есть "акценты", которые их выдают:

**Лингвистические подписи:**
- Claude любит: "I'll help you with...", "Certainly!", "I'd be happy to", смешанные "—" (em-dash)
- GPT любит: "Sure!", "Here's a...", "Let me know if you need anything else"
- Gemini любит: "Absolutely! Here's...", overuse of bold
- Llama любит: ставить заголовки `**Title:**` в неподходящих местах

**Структурные подписи:**
- Claude добавляет много объяснений до кода
- GPT часто оборачивает в "```python\n# Solution\n"
- DeepSeek любит explicit reasoning блоки

**Code-style подписи:**
- Naming conventions (camelCase vs snake_case даже там где не надо)
- Indentation (2 vs 4 spaces)
- Quotes (single vs double)
- Verbose vs terse comments

**Что делать — pipeline нормализации перед судейством:**

```python
def normalize_for_judging(raw_output: str, task_type: str) -> str:
    # 1. Strip приветствий и завершалок
    text = strip_meta_phrases(text, patterns=[
        r"^(Sure|Certainly|Absolutely|Here's|I'll|Let me|I'd be happy).*?[\n.]",
        r"\n\n(Let me know|Hope this helps|Feel free).*$",
    ])
    
    # 2. Извлечь код из markdown блоков (для кодовых задач)
    if task_type == "code":
        code = extract_code_block(text)
        # Reformat через язык-специфичный formatter
        code = run_formatter(code, lang=detect_lang(code))  # prettier/black/rustfmt
    
    # 3. Анонимизировать комментарии
    code = strip_author_comments(code)  # удалить "// Created by..." и подобное
    
    # 4. Strip explanations в коде — оставить только сам код
    code = remove_explanation_blocks(code)
    
    # 5. Для документации — normalize markdown formatting
    if task_type == "doc":
        text = normalize_markdown_headers(text)  # H1 → H2 unified levels
        text = strip_emoji_decoration(text)
    
    return text
```

**Анти-подпись в промпте генерации.** В system prompt каждой модели пишем:

```
Important: Do not introduce yourself, do not greet, do not say "Here's the 
solution" or similar phrases. Do not sign code with your name or model 
identifier. Output ONLY the solution itself, nothing else. Do not include 
explanatory prose unless explicitly asked.
```

Это снижает 70-80% подписей. Остальное добивает нормализация.

**Проверка работы нормализации:** прогоняем small batch (5 ответов) через **identification probe** — даём ответ другой модели и спрашиваем "guess which model wrote this". Если accuracy угадывания > 30% — нормализация недостаточна, доработать.

## 3. Таксономия biases судей и как с ними бороться

Это самое ценное для статьи — никто этого не описывает в блогах:

| Bias | Что это | Mitigation |
|---|---|---|
| **Self-enhancement** | Любит свой "акцент" | Self-judging disabled (твоя идея) |
| **Position bias** | Первый/последний ответ получает выше балл | Рандомизировать порядок при каждом judge call |
| **Length bias** | Длинные ответы кажутся "лучше" | В rubric явно: "не оценивайте по длине". Длинные ответы > 2× медианы — penalize |
| **Verbosity bias** | Markdown/bullets кажутся "structured" | Нормализовать форматирование до судейства |
| **Authority bias** | "Expert solution" в промпте → выше балл | В промпте судье не говорить вообще нечего о происхождении |
| **Sycophancy** | Если в промпте намёк — соглашается | Промпт нейтральный, без "this is the gold answer" |
| **Anchor bias** | Первый score влияет на следующие | Каждый ответ оценивается в **отдельном judge call**, без контекста |
| **Halo effect** | Хороший в одном — высокие баллы и в другом | Скоринг по каждому критерию rubric'а **независимо**, в отдельных calls |
| **Calibration drift** | Судья дрейфует к "среднему" | Использовать **calibration set** с известными score (см. ниже) |

## 4. Calibration set — как поймать дрейфующего судью

Это **must-have** который никто не делает. Идея:

Перед судейством реальных ответов, прогоняем каждого судью через **5-10 калибровочных задач с известными "правильными" оценками**. Это включает:
- Заведомо отличное решение → должно получить ~9-10
- Заведомо среднее → ~5-6
- Заведомо плохое (но компилируется) → ~2-3
- Заведомо неправильное → ~0-1
- "Идентичные с переформулировкой" — оба должны получить ~равные баллы

Если судья **отклоняется от калибровки** (например, плохое решение получило 6 баллов), у него bias или он не понял rubric → **исключаем из пула** или переделываем rubric.

В статью идёт **таблица калибровки судей** — это очень публикуемо. Показывает что у тебя надёжный pipeline.

## 5. Pairwise vs absolute scoring

Литература говорит: **pairwise сравнения стабильнее absolute оценок**. Когда судья видит ответ A и B и говорит "B лучше" — это устойчиво. Когда говорит "B = 7.3" — это subjective.

**Best of both:** для каждого кодового решения сначала вычисляем automatic metrics (correctness, complexity, coverage), потом LLM-judge даёт **pairwise сравнение по rubric** ("которое из этих двух лучше следует паттернам gold"). Из pairwise восстанавливаем ранг через **Bradley-Terry model** или **Elo rating** — те же методы что в chess и LMSYS Arena.

**В итоге получается hybrid score:**
- Автометрики дают абсолютные числа (correctness, CC, coverage)
- Pairwise judge даёт относительный ранг
- Финальный score = weighted combination

## 6. Statistical rigor — чтобы числа были не "цифры с потолка"

Без этого блок-пост = "модель X лучше" без подтверждения. С этим — статья:

**Multiple runs.** Каждый combo (model × task) гоняем **5 раз** с разными seed/temperature. Это даёт оценку variance. В радаре показываем **mean ± std**. Если разница между моделями < std — она не значима, и об этом нужно прямо сказать в статье.

**Inter-rater reliability.** После судейства считаем согласие между судьями: **Cohen's kappa** для пар, **Krippendorff's alpha** для пула > 2 судей. Цель α > 0.7 (нормально), > 0.8 (хорошо). Если α < 0.5 — судьи спорят, твоим оценкам нельзя верить. Показывать в статье — supersильно.

**Effect size, не только p-value.** Между двумя моделями смотрим **Cohen's d**. d < 0.2 — разница незначительна (даже если "статистически достоверно" по p-value). d > 0.8 — large effect, реальная разница. В блог-пост обязательно: "разница X vs Y по reasoning — d=0.3 (small), по coding — d=1.1 (large)".

**Bootstrap confidence intervals.** Для финальных оценок на радаре считаем 95% CI через bootstrap (resample with replacement). На графике рисуем shaded zone. Это убивает все "ну а вдруг это случайность". Confidence intervals на радаре никто не делает — будет уникальный артефакт твоей серии.

**Pre-registration.** Перед прогоном записываем гипотезы и метрики в файл, коммитим в git. После прогона сравниваем — где ожидания совпали, где нет. Это исключает p-hacking ("ой я нашёл что Claude лучше в кодинге, теперь напишу пост") и делает контент **гораздо ценнее**.

## 7. Что обязательно показать в статье — "premium" артефакты

Эти штуки превращают пост из "вот цифры" в "вот исследование":

1. **Inter-judge agreement matrix** — таблица Cohen's kappa между всеми судьями. Доказывает что система надёжная.
2. **Calibration plot** — оси: "истинный score" vs "score от судьи". Точки выше/ниже диагонали показывают bias судьи. Один на каждого судью.
3. **Variance heatmap** — `model × task`, цвет = std accuracy через 5 прогонов. Жёлтое — нестабильно, синее — стабильно.
4. **Confidence intervals на радаре** — error bars или shaded zones. Уникально для серии.
5. **Cost-quality Pareto с error bars** — для финального поста. По обеим осям интервалы.
6. **Bias-check table** — после нормализации, identification probe ниже 30% accuracy → доказано что подписи срезаны.
7. **"Negative findings"** — где разница не значима. Это **сильно повышает доверие** читателя. "Мы НЕ нашли значимой разницы между Claude Sonnet и GPT-5 в frontend задачах (d=0.18, n.s.)".

## 8. Reproducibility checklist

Чтобы статья прошла техническую проверку на Хабре/Dev.to/HN:

- [ ] Все промпты в git, версионированные
- [ ] Список моделей с точными версионными tag (`claude-opus-4-7-20260315` а не "Claude Opus")
- [ ] Temperature, top_p, seed для каждой модели зафиксированы
- [ ] Версия LiteLLM, vLLM, Inspect AI — pinned
- [ ] Все 20 задач + gold + tests — публичный репо
- [ ] Хеш каждой задачи — proof что не менял после запуска
- [ ] Сырые ответы моделей в репо (`/raw_outputs/{model}/{task}/{seed}.txt`)
- [ ] Сырые judge-оценки в репо (`/judgments/{judge}/{task}/{model_anon}.json`)
- [ ] Скрипт reproduce.sh который воспроизводит из сырых данных
- [ ] Лицензия CC-BY-SA на данные, MIT на код

Это **золотой стандарт ML research**. Если у тебя это есть — пост уровнем выше большинства публикаций про LLM-сравнения.

## 9. Что я не буду включать в скоринг

Чтобы потом не было вопросов:

- ❌ **"Subjective vibe check"** — никаких "мне нравится этот ответ". Только rubric и автометрики.
- ❌ **Human-in-the-loop оценки от тебя одного** — это твой bias. Если человеческое judging нужно — нанимай 3+ человека для каждой задачи и считай их kappa.
- ❌ **Single-run результаты** — только multi-seed.
- ❌ **Aggregating discrete metrics через mean** — например, "passed_tests" должно агрегироваться как proportion, не как сумма.

## По стэку для задач

Не ответил мне на это в прошлый раз — повторю вопрос. Тебе как **основной стек** TypeScript/Node.js окей? Это даёт цельную картину (front + back + tests + docs), модели в нём сильны, easy to dockerize for evaluation. Плюс 2-3 задачи на Python для DevOps/data, и SQL-задачи как нейтральные.

Скажи "TS + Python + SQL" или предложи другое — и я выкатываю **20 задач с gold + rubric + evaluation scripts** одним yaml-файлом + структурой папок. Это займёт пару итераций с тобой на review, но после этого вся машинерия Фазы 1 готова к запуску.


TypeScript/Node.js окей? Это даёт цельную картину (front + back + tests + docs), модели в нём сильны, easy to dockerize for evaluation. Плюс 2-3 задачи на Python для DevOps/data, и SQL-задачи как нейтральные

задачи должны быть максимально prodcution ready на реальном кейсе котоырй встречается повсеместно - реально раьотчачя задача которая дает профит и пользу тоснее проеет котоырй должен быт ьнаписан но при этом он должен быть небольщим но при этом там должны быть учтено то что нужно на оснвое чего метрики строить - давай продумай что э то модет быть и найди такие рещения - моджет ресерч сдетать в сети или на гитхабе или еще где то 
------
Panel of LLM evaluators - POLLMEVALS - крутой домен и навзанеи для созданяи целого сервиса котоырй бы показывал метрики и полное оспиание тог очто просихоит - от идеи до задачи и решения и то как соьираются метрики и сама архиутеруа и решение

например запуск идет раз в 1 недеою + с появлением флагмантсих моделей 

и такде отдлеьный под разные модели котоыре комьюнити пошуат или голосуют

Две темы — сначала research реальных production-задач, потом обсудим POLLMEVALS как продукт. Поищу что есть в сети.Окей, отвечаю по двум темам отдельно — research для задач и стратегический анализ POLLMEVALS.

## Часть 1: Задачи — что есть готового и как делать

Хорошая новость: эту работу частично сделали за нас. Самый ценный источник для нашей цели — **SWE-Lancer от OpenAI**, специально про реальный freelance. SWE-Lancer — это бенчмарк OpenAI на 1488 реальных задач из Upwork общей стоимостью $1M, тесты triple-verified опытными инженерами, охватывает bug fixes от $50 до feature implementations за $32k. Это первый бенчмарк который мапит производительность модели на денежную ценность задачи. 764 IC SWE-задач на $414k используют end-to-end тесты через Playwright browser automation — это устойчиво к grader hacking.

Это **именно то что ты хочешь** — настоящие production-задачи которые реально оплачивались, с автоматической верификацией через E2E тесты. Из 1488 задач берём 20 разных по сложности и категориям. Это легитимный, воспроизводимый, защищённый от critique источник.

Дополнительные источники для разнообразия:

DevBench от Microsoft — telemetry-driven бенчмарк на 1800 instance'ов по 6 языкам и 6 категориям задач из реальной developer-телеметрии. Уникален тем что отражает аутентичные developer-вызовы, валидирован экспертами. TypeScript стабильно оказывается самым сложным языком — модели показывают на 20-30% ниже из-за строгой системы типов. Это аргумент за TS как основной стек — он реально дифференциирует модели.

BigCodeBench содержит 1140 function-level задач challenging LLMs к follow instructions и compose multiple function calls как tools из 139 библиотек, 5.6 test cases на задачу, average branch coverage 99%. Хорошо для backend/data-задач.

### Принципы отбора 20 задач

Каждая задача должна:
1. Быть **выполнимой за 1 промпт → 1 ответ** (без многораундовой агентности — это уже Фаза 2)
2. Иметь **gold solution** ~50-200 строк кода
3. Иметь **automated evaluator** который дает ≥3 численных метрики
4. Решаться **за < 5 минут wall-clock** даже на медленных моделях
5. Покрывать **реальный сценарий** который встречается в работе еженедельно

### Концепт-список 20 задач

Покажу draft, потом ты валидируешь и я допиливаю YAML:

**Backend / API (4 задачи) — TypeScript/Node.js:**

| ID | Задача | Метрики |
|---|---|---|
| be_01 | JWT auth middleware с refresh tokens, secure cookie, CSRF | Tests pass, CC≤8, type-safe, no security warnings |
| be_02 | REST endpoint POST /users с Zod валидацией, dedup email | Tests pass, branches covered, error responses RFC 7807 |
| be_03 | Webhook handler с HMAC signature, idempotency key, retry | Tests pass, replay-safe, timing-attack-safe |
| be_04 | Cursor-based pagination для GET /posts с N+1 prevention | Tests pass, query count constant, type-safe |

**Frontend (3 задачи) — React + TypeScript:**

| ID | Задача | Метрики |
|---|---|---|
| fe_01 | Multi-step form с валидацией, persisted draft, a11y | Tests pass, WCAG 2.1 AA via axe-core, keyboard nav |
| fe_02 | Debounced search input с loading/error/empty states | Tests pass, no race conditions (testing-library), 60fps |
| fe_03 | Drag-and-drop kanban list с persistent order | Tests pass, optimistic UI, conflict resolution |

**Fullstack (2 задачи):**

| ID | Задача | Метрики |
|---|---|---|
| fs_01 | Feature flag system: backend toggle + frontend hook | E2E tests pass, type-safe contract, no flicker |
| fs_02 | File upload с resumable chunks (frontend + backend) | E2E tests pass, abort safety, integrity check |

**Database (2 задачи) — PostgreSQL:**

| ID | Задача | Метрики |
|---|---|---|
| db_01 | Migration: split users.address в нормализованную таблицу с zero-downtime strategy | Migration applies, rollback safe, no data loss |
| db_02 | Оптимизировать query который делает full scan на 10M rows | Query plan uses index, latency p95 < gold × 1.2 |

**DevOps (2 задачи):**

| ID | Задача | Метрики |
|---|---|---|
| ops_01 | Multi-stage Dockerfile для Node app — image size < 150MB, non-root user, healthcheck | Image builds, Trivy scan clean, size threshold |
| ops_02 | GitHub Actions workflow: matrix tests, cache, deploy on tag | Workflow validates (actionlint), idempotent, no secret leaks |

**Tests (2 задачи):**

| ID | Задача | Метрики |
|---|---|---|
| tst_01 | Написать тесты для legacy функции (даны функция + ТЗ что она должна делать) | Coverage ≥ 90%, mutation score ≥ 70%, no flaky |
| tst_02 | Integration test для REST API с Testcontainers Postgres | Tests pass, isolation, < 5s runtime |

**Documentation (2 задачи):**

| ID | Задача | Метрики |
|---|---|---|
| doc_01 | README для open-source CLI tool (даны код + примеры использования) | Все секции по rubric присутствуют, judge score ≥ 7 |
| doc_02 | ADR на тему "выбрали Postgres вместо MongoDB" с контекстом | Структура match, factual accuracy, judge ≥ 7 |

**Refactor / Review (3 задачи):**

| ID | Задача | Метрики |
|---|---|---|
| rev_01 | Найти баги в diff (5 PRs, в каждом по 1-3 бага разной критичности) | Recall, precision, severity F1 |
| ref_01 | Отрефакторить 200-строчную God-функцию по SOLID — сохранить тесты | Tests still pass, CC снижается, no API change |
| ref_02 | Mitigate N+1 query в ORM-коде, сохранить контракт | Tests pass, query count -50%, type-safe |

Это 20 задач, ~6-8 часов на gold реализацию каждой = ~150 часов всего. Это **2-3 недели плотной работы**. Можем сократить до 12-15 задач для MVP, остальные добавить позже.

Подтверди этот список (или скажи "убери X, добавь Y") — и я выкатываю первую YAML-спеку с full gold + evaluator для 3-4 задач как proof-of-concept. Ты прогоняешь их у себя, мы fine-tune'им формат, и дальше пайплайнно делаем остальные.

---

## Часть 2: POLLMEVALS — анализ продукта

Дай я сразу скажу честно: **рынок занят, но твоя ниша есть**. Покажу landscape:Видно невооружённым глазом — все жмутся к левой стороне. **Никто не измеряет scaffolding stacks** (модель + Claude Code + skills + память) систематично. LMSYS Arena — $1.7B valuation, 6M голосов от пользователей, Elo-рейтинг на 140+ моделях, но это human preference на голых ответах. Artificial Analysis отслеживает 356 моделей по скорости, цене и capability одновременно, но опять — голые модели. Все остальные тоже.

### Что у POLLMEVALS уникально

**1. Scaffolding-first методология.** Главная фишка. Все остальные говорят "какая модель лучше". Ты говоришь "какая *комбинация* стека лучше под класс задач". Это другая категория, не конкурент Arena.

**2. Panel of LLM judges with rotation.** В академии это best practice, в продукте — нигде. Single-judge сервисы дают biased оценки. У тебя матрица "судья не судит сам себя", 3-5 судей на ответ, median scoring. Это **methodological selling point** — серьёзные команды это ценят.

**3. Cost-aware leaderboard.** Артикул Артикул Артикул — Artificial Analysis это делает для моделей. Никто не делает **cost-per-task** для *стека*. Например, "ForgePlan + Sonnet 4.6 = $0.12/task at 92% quality" vs "GPT-5 голый = $0.05/task at 88%". Это **прямой ответ инженеру** "что мне взять под мой бюджет".

**4. Community-driven model addition.** Arena добавляет модели когда model publisher просит, и из-за этого был скандал ["Leaderboard Illusion" paper](https://arxiv.org/abs/2504.20879) в апреле 2025 что показал bias. У тебя — голосование сообществом, прозрачные критерии. Это **transparency angle**.

**5. Cadence: weekly + flagship-triggered.** Идея отличная. Weekly — постоянный пульс, ловишь маленькие изменения. Flagship-trigger (релиз Opus 5, GPT-6) — emergency run, всё пересчитывается за 24-48 часов. Это **новостной формат** — каждую неделю можно постить апдейт.

### Архитектура MVP

```
┌─────────────────────────────────────────────────────────┐
│ Frontend (Next.js + Vercel)                            │
│  - Live leaderboards (по типу задач, по стекам)        │
│  - Per-model deep-dive страницы                        │
│  - Community voting на модели и стеки                  │
│  - Public datasets download                            │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  Backend API (Hono) │ ← stats, votes, datasets
        └──────────┬──────────┘
                   │
       ┌───────────▼───────────┐
       │  Postgres + Redis     │
       │  - results            │
       │  - judgments          │
       │  - votes              │
       └───────────▲───────────┘
                   │
       ┌───────────┴───────────┐
       │   Eval Orchestrator   │ ← cron weekly + webhook on release
       │   (Inspect AI core)   │
       └───────────┬───────────┘
                   │
       ┌───────────▼───────────────┐
       │   LiteLLM Gateway         │
       └───┬─────────┬─────────┬───┘
           │         │         │
      ┌────▼──┐  ┌──▼───┐  ┌──▼────────┐
      │Runpod │  │Cereb │  │OpenRouter │
      │vLLM   │  │ras   │  │           │
      └───────┘  └──────┘  └───────────┘
```

**MVP scope (4-6 недель):**
- 14 моделей × 20 задач × 5 seeds × 5 judges = ~5k completions weekly
- Cost при текущих ценах: ~$80-200/неделю inference + $50/мес инфра
- Простой dashboard с поиском + filter + export

**Что НЕ делать в MVP:**
- Все 8 фаз сразу — только Фаза 1 (модели на голых задачах) + кусочек Фазы 2 (scaffolding ladder для top-5 моделей)
- Самописная инфра для оркестрации — Inspect AI делает это за тебя
- Real-time eval — только weekly batch

### Бизнес-модель — 4 варианта по росту риска

**Тier 0: Open data, no monetization.** Просто публичный leaderboard + open datasets + блог-серия. Это **reputation play** — Eli как expert на тему scaffolding evaluation, дальше консалтинг/курс/SaaS. Самая безопасная схема для начала.

**Tier 1: API access ($).** Бесплатный leaderboard, платный доступ к raw data через API. Цена $50-500/мес. Купит кто? — model producers (для маркетинга "мы первые на POLLMEVALS"), исследователи, кокурсы AI. Artificial Analysis именно так монетизирует — public dashboard + private API.

**Tier 2: Custom evals for clients ($$).** Компания приходит: "у нас свой стек, запустите его через POLLMEVALS методологию на наших задачах". $5-20k за исследование. Это classic консалтинг под бренд платформы.

**Tier 3: Sponsored evals ($$).** Model producer платит чтобы их новую модель прогнали с приоритетом и опубликовали. Тут нужна **прозрачная политика чтобы не стать compromised** как LMSYS. Платный = быстрее в очереди, не лучше в результатах. Disclosure обязательна.

**Tier 4: Enterprise white-label ($$$).** "Запустите POLLMEVALS платформу на нашем приватном codebase для оценки внутренних агентов". Это рынок Scale AI и Surge AI — там money есть. Но это **отдельная компания**, не пет-проект.

### Reality check — твои ресурсы

У тебя в активе ForgePlan, Orchestra, Gerts.ai, спа, AI-курс, консалтинг. **Шестой полноценный продукт ты не потянешь.** Это надо честно сказать.

Реалистичный путь:

1. **Сначала серия постов** (3-4 месяца). Это и есть proof-of-concept. Контент сам по себе ценен, и репутация выстраивается. Доступ к Eli как эксперту в "scaffolding evaluation" — это активе.

2. **Если посты заходят** (10k+ просмотров, обсуждения в HN/Reddit/Twitter), **запускаешь MVP**. На этом этапе можно привлечь со-основателя или нанять 1 девелопера через консалтинг-деньги.

3. **Если MVP получает 100+ MAU аудитории**, тогда коммерциализация. До этого момента — open data + блог + Tier 0.

Это **3-фазная стратегия с реальными gating critera**. Не "буду строить платформу" → выгораешь через 3 месяца. Не "буду писать блог в стол" → не получаешь network effects от продукта.

### Что делаем сейчас — конкретно

Зафиксируем фокус: **сначала Фаза 1 как первая статья + open dataset**. POLLMEVALS как продукт — это уже после.

Подтверди:
1. **20 задач из моего списка выше** — ок? Что-то убрать/добавить?
2. **TypeScript/Node.js основной + Python для DevOps/data + SQL для DB** — ок?
3. **Старт: я делаю YAML-спеку для 3 задач** (например be_01, fe_01, doc_01) с полной gold + evaluator. Ты гоняешь на 2-3 моделях, проверяешь что пайплайн работает, потом масштабируем до 20.

Скажи "поехали с этими тремя задачами" — и я сразу начинаю писать спеку. Если хочешь сменить какие-то задачи в списке — называй какие и какими заменить.

итого нам нужен полное опсианеи продукта - какую задачу рещаем - чт оиспользуем ои отда беерм - какая тсруркура проекта - сайта

и полное оспаиние процесса ввода новго иснуормента или модели и вендора - подрубание например api и чтобы новый серси можно было протестирвоать

стоиисоть скорость из разных старн и тд

----
и дава ты сам ещзе скажи что нужно учесть

Окей, делаю полную спеку. Сделаю её как PRD-документ, чтобы это можно было сохранить и показывать дальше. Сначала визуально покажу IA сайта, потом текстом полная спека + мои добавления того что обязательно учесть.# POLLMEVALS — Product Specification v0.1

## 1. Задача которую решаем

**Главная боль:** инженеры тратят дни/недели чтобы понять "какая модель + обвязка реально лучше под мою задачу". Существующие лидерборды отвечают только "какая модель умнее на абстрактных тестах". Они не учитывают:
- Какой агентный CLI и стек обвязки даёт реальный профит
- Стоимость задачи (а не цена за токен)
- Латенси из твоего региона
- Стабильность через несколько запусков
- Влияние памяти, skills, validator-петель

POLLMEVALS отвечает на конкретный вопрос: **"Возьми задачу класса X, бюджет Y, регион Z — какой стек тебе оптимален?"**

## 2. Целевые юзеры

**Persona A — Engineering lead.** Выбирает стек для команды. Нужны: cost-quality Pareto, регион-aware latency, стабильность. Платит за Tier 1 API access.

**Persona B — Indie hacker / founder.** Гонит локальные модели + cloud по необходимости. Нужны: какие комбинации Ollama-моделей + skills дают приличный результат на M-чипе. Бесплатный leaderboard.

**Persona C — Researcher / Industry analyst.** Пишет отчёты, статьи, делает запросы для VC. Нужны: raw data export, methodology transparency, citation. Платит за Tier 1.

**Persona D — Model creator (Anthropic, OpenAI, open-weights teams).** Хочет увидеть свою модель честно оценённой. Может спонсировать ускоренное добавление (Tier 3, всегда disclosed).

## 3. Уникальное ценностное предложение

| Фишка | Что это даёт |
|---|---|
| Scaffolding evaluation | Меряем не модели, а **полные стеки** (модель + agent CLI + skills + память + validator) |
| Panel of judges | 5 ротирующихся LLM-судей, никто не судит сам себя, blind labels, median scoring |
| Cost-aware results | $/task, $/correct answer — не просто accuracy |
| Geo-aware latency | TTFT и tok/s измеряются из 4 регионов (US-East, EU-Central, APAC, SA) |
| Weekly + triggered cadence | Каждую неделю + emergency run при релизе флагмана |
| Community-driven additions | Сообщество голосует какие модели/стеки добавлять |
| Reproducibility | Все промпты, версии, seeds, raw outputs — публичные, проверяемые |
| Versioned tasks | Изменение задачи = новая версия. Старые сравнения остаются валидными |

## 4. Технический стек

**Frontend.** Next.js 15 (App Router) + Tailwind + shadcn/ui. Хостинг на Vercel (edge functions для landing/leaderboards, SSG для статичных страниц моделей). Без State management кроме React Query — данные тянем напрямую из API.

**Backend API.** Hono на Bun (быстрый, легкий) или Express на Node. Деплой как Docker контейнер на Fly.io или Railway. Endpoint structure: `/api/v1/{leaderboards|models|stacks|tasks|runs|judges}`.

**Database.** Postgres (Supabase или Neon для managed). Все нормализованные данные. Schema migrations через Prisma или Drizzle.

**Object storage.** S3-compatible (Cloudflare R2 — bandwidth бесплатный) для raw model outputs, judge responses, full transcripts. Каждый file имеет content-hash в имени для immutability.

**Cache + Queue.** Redis (Upstash) для leaderboard cache (10-min TTL), task queue для eval-prog onов, rate limiting.

**Eval orchestrator.** Inspect AI core (Python) обёрнут в собственный Python-сервис. Гоняет одну фазу одной модели как Inspect run, агрегирует, складывает в Postgres.

**Inference gateway.** LiteLLM proxy на отдельном Docker. Все вызовы моделей идут через него. Это даёт автоматический cost tracking, virtual keys, rate limiting.

**Workers (geo-aware).** 4 docker контейнера в 4 регионах (US-East, EU-Central Frankfurt, APAC Tokyo, SA São Paulo). Каждый делает inference-вызовы из своего региона и пишет measurements. Используем DigitalOcean droplets или Hetzner Cloud (дешевле AWS).

**Self-hosted models.** Runpod (vLLM) для тяжёлых open-weights моделей (Qwen 72B+, Llama 70B+). Cerebras и OpenRouter для остальных.

**CI/Observability.** GitHub Actions для deploy. Sentry для errors. Grafana + Prometheus для metrics. Posthog для analytics.

## 5. Структура страниц — что на каждой

### `/leaderboards`
Главная посадочная. Три tab-таба: by Model, by Stack, by Task class. Фильтры: тип задачи, регион, бюджет. Дефолтная сортировка по quality. Сверху — last-week deltas (что улучшилось).

### `/models/[slug]`
Деталка одной модели. Радар по 8 категориям задач, история через все запуски, latency по регионам, $/task. Список 3 лучших стеков обвязки для этой модели. Raw outputs ссылки на S3.

### `/stacks/[slug]`
Деталка одного стека (например `claude-opus-4.7 + claude-code + skills + mem0`). Какие модели дают лучший прирост от этого стека. На каких задачах работает. Cost/Quality vs голая модель.

### `/tasks/[slug]`
Деталка задачи. Полное описание, gold solution, evaluator code, история результатов по моделям. Может посмотреть кто как решал. **Public после первого еженедельного run** (чтобы не было contamination для свежей задачи).

### `/compare`
Side-by-side comparison: выбираешь до 4 моделей/стеков → таблица + радар + cost-quality scatter. Shareable URL.

### `/runs/[hash]`
Один конкретный weekly run. Доказательство воспроизводимости: версии моделей с pinned tags, версии Inspect AI / LiteLLM / vLLM, временные метки, total tokens, total cost. Raw outputs download.

### `/methodology`
Полная методика: как считаем, какие веса, как анонимизируем, как калибруем судей. Это **обязательно публично** — без этого никакого доверия. Версионируется.

### `/judges`
Список текущих судей с их calibration scores, inter-judge agreement matrix, history смены.

### `/calibration`
Калибровочные задачи с известными score'ами. Прозрачность того, как мы понимаем что судья работает.

### `/scoring`
Документация формул scoring по типам задач (code/doc/review). Конкретные веса метрик.

### `/blog`
Еженедельные апдейты + длинные посты с анализом. Это где Eli публикует контент серии.

### `/vote`
Community голосование за модели. "Какую модель добавить следующей?" GitHub OAuth для voting (anti-spam).

### `/propose-{model|task|stack}`
Форма предложения. Модель — JSON со ссылкой на API/endpoint. Задача — YAML с описанием + gold. Стек — combo описание.

### `/discuss`
Можно встроить github discussions или Discourse — отдельный продукт не пишем.

### `/api`
API документация. OpenAPI/Swagger UI. Аутентификация через API keys. Rate limits.

### `/datasets`
Bulk download всех eval results в Parquet/CSV. Версионирование как у HuggingFace datasets.

### `/status`
Cron health, latest run status, next scheduled run. Uptime per worker по регионам.

### `/pricing`
Tier 0 (free) / Tier 1 (API $50/мес) / Tier 2 (custom evals).

### `/changelog`
Список всех изменений в методологии, новых моделях, новых задачах. С RSS.

## 6. Data Model — основные таблицы

```sql
-- Модели
models (
  id, slug, name, vendor, version_tag, 
  is_open_weight, context_window, max_output_tokens,
  added_at, deprecated_at, proposed_by, votes_count
)

-- Провайдеры (как модель хостится)
model_providers (
  id, model_id, provider_name, endpoint_url, 
  region, price_input_per_mtok, price_output_per_mtok,
  rate_limit_rpm, rate_limit_tpm
)

-- Стеки (комбинации обвязки)
stacks (
  id, slug, name, description, 
  base_model_id, agent_cli, 
  has_tools, has_skills, has_file_memory, 
  has_vector_memory, vector_memory_type,
  has_subagents, has_validator, has_framework, framework_name
)

-- Задачи
tasks (
  id, slug, version, category, difficulty, 
  description_md, prompt_template,
  gold_solution_uri, evaluator_uri,
  expected_tokens_in, expected_tokens_out,
  added_at, retired_at, parent_task_id  -- для версионирования
)

-- Runs (один weekly прогон)
runs (
  id, hash, run_type, -- 'weekly', 'flagship_triggered'
  started_at, completed_at, 
  inspect_ai_version, litellm_version, vllm_version,
  total_cost_usd, total_input_tokens, total_output_tokens
)

-- Eval results (model × stack × task × seed)
evals (
  id, run_id, model_id, stack_id, task_id, 
  seed, region,  -- !!! из какого региона измерено
  raw_output_uri, 
  ttft_ms, total_latency_ms, tokens_in, tokens_out, cost_usd,
  automatic_metrics_json, -- correctness, CC, coverage, lint и т.д.
  final_score, -- 0-10 после композитного скоринга
  created_at
)

-- Judgments (panel of judges)
judgments (
  id, eval_id, judge_model_id, judge_order, -- порядок в randomized batch
  rubric_scores_json, -- по каждому критерию
  total_score, reasoning_text_uri,
  agreement_with_consensus -- для inter-rater stats
)

-- Calibration results
calibration_runs (
  id, judge_model_id, calibration_task_id, 
  expected_score, given_score, deviation,
  ran_at
)

-- Community votes
votes (
  id, user_id, voted_at, vote_type, -- 'model', 'task', 'stack'
  target_id, weight  -- больше веса у проверенных аккаунтов
)
```

## 7. Eval pipeline — как один weekly run устроен

1. **Cron триггер** в понедельник 03:00 UTC создаёт `run` с уникальным hash
2. **Snapshot стейта**: версии всех моделей с current `version_tag`, версии всех инструментов
3. **Worker'ы в 4 регионах поднимаются** через docker-compose
4. **Каждый worker** прогоняет матрицу (модели × задачи × 5 seeds) которые ему назначены через round-robin queue
5. **Сырые outputs** → S3 с content-hash имени
6. **Automatic metrics** считаются сразу после каждого eval (pytest, eslint, radon и т.д.)
7. **Anonymization pipeline** превращает каждый output в "submission_xyz" без метаданных
8. **Judge phase**: панель 5 судей × все eval'ы, каждый судья в отдельном LiteLLM call, randomized order, blind labels
9. **Aggregation**: median scores, inter-judge agreement, bootstrap CI
10. **Drift detection**: сравнение с прошлой неделей. Если delta > 2σ — alert
11. **Calibration check**: судьи прогнаны через golden set. Если deviate — flag + degrade priority
12. **Database update** atomically — либо весь run, либо ничего
13. **Cache invalidation** + leaderboard rebuild
14. **Public announcement** в blog + Twitter + Telegram + RSS

## 8. Onboarding новой модели/вендора — пошагово

**Step 1. Predложение** через `/propose-model` форма:
```yaml
slug: claude-opus-4.8
name: Claude Opus 4.8
vendor: anthropic
context_window: 200000
api_endpoint: https://api.anthropic.com/v1/messages
api_format: anthropic_native  # или openai, gemini, ollama
official_docs_url: https://docs.anthropic.com/...
pricing_input_per_mtok: 15.00
pricing_output_per_mtok: 75.00
is_open_weight: false
proposed_reason: "Just released, sets new SOTA on..."
```

**Step 2. Автоматическая проверка:**
- API endpoint достижим
- Модель отвечает на ping prompt
- Tokens counter возвращает корректные числа
- Pricing соответствует официальной странице vendor'а
- Имя/slug уникален

**Step 3. Community vote.** Модель попадает в `/vote` страницу. Нужно X голосов за 7 дней (X начинаем с 20, увеличиваем по росту аудитории). Для критичных моделей (флагман от major vendor) — fast track без голосования с disclosure.

**Step 4. Manual review.** Один из maintainers (на старте — Eli один) проверяет:
- Не дубликат
- Реально новая модель, не rebrand
- Не нарушает ToS vendor'а
- Стабильно отвечает на 10 sanity-check промптов

**Step 5. Calibration run.** Перед добавлением в weekly grid, модель прогоняется через мини-grid: 5 calibration tasks + 3 регулярных задачи. Это даёт первичный baseline и проверяет что pipeline работает с её API/токенизацией.

**Step 6. LiteLLM config update.** Модель добавляется в `litellm_config.yaml` с pinned version tag.

**Step 7. Public announcement** в `/changelog` + RSS. Модель попадает в следующий weekly run.

Тот же flow для **новых стеков** (`/propose-stack`) и **новых задач** (`/propose-task`), но с разными формами и validation. Для задач — обязателен gold + evaluator script + 3 примера решений разной quality для калибровки.

## 9. Geo-aware metrics — ключевая фишка

Каждый eval запускается из 4 регионов. Storage в таблице `evals` имеет колонку `region`. На фронте — фильтр.

**Что мерим в каждом регионе:**
- TTFT (time-to-first-token) — самое чувствительное к geo
- Total wall-clock latency — включает inference + network
- Tokens/sec output — обычно стабильно по регионам у одного vendor'а

**Регионы воркеров:**
- US-East (Virginia) — основной для North American audience
- EU-Central (Frankfurt — где Eli) — основной для Europe
- APAC (Tokyo или Singapore) — для Asia
- SA (São Paulo) — для Latin America (опционально, expensive)

**Особая ценность:**
- Anthropic/OpenAI имеют разные endpoints по регионам — pure direct API на US, через Cloudfront/edge на других
- Cerebras сейчас только US-West — это **критичная информация** для EU пользователя
- Locally hosted (Runpod) — выбор региона = выбор стоимости + latency
- Self-hosted = TTFT 50ms vs cloud = 800ms — это другой класс UX

**Презентация на сайте:**
- Карта мира с heatmap latency
- Фильтр "show latency from my region" (geo-IP)
- На странице модели — таблица регионов

## 10. Что ещё обязательно учесть — мои добавления

Часть которая критична но Eli не упоминал явно:

**Reproducibility & immutability.** Каждый run — immutable после завершения. Никаких "потом подправим оценку". Если ошибка — новый run с тем же task hash, но другим run hash. Это required для научного credibility.

**Task versioning.** Когда задачу меняешь — это новая версия с тем же `slug` но другим `version`. Старые eval'ы остаются валидными для своей версии. Comparison "v1.0 → v1.1" — отдельная страница которая показывает что изменилось.

**Model drift detection.** Closed-API модели (Claude, GPT, Gemini) меняются "за кулисами" даже при том же tag. Мы это ловим: если результаты конкретной модели за неделю drift > 2σ от трёхмесячного baseline — alert. Это **публикуется** — "Claude Opus 4.7 показал значимое изменение поведения в week 23". Это уникальный insight который никто другой не делает.

**Contamination detection.** Каждая задача имеет content hash. Регулярно гуглим этот hash и кусочки описания — если задача появилась в обучающем датасете, GitHub readme, blog post — она compromised и retired. У LiveBench это есть, нам тоже нужно.

**Anti-gaming через rotation.** 20% задач — **held-out** в private set, не публикуются. Они меняются ежемесячно. Это страховка от того что vendors начнут оптимизировать на public set.

**Code execution safety.** Сгенерированный моделями код выполняется в изолированных Docker контейнерах с:
- Без network access (Docker без `--network=host`, специальный `none` network)
- CPU/RAM/disk лимиты
- Read-only filesystem кроме `/tmp`
- Timeout 60 секунд hard kill
- Никаких mount-волюмов от host

**Privacy / Legal:**
- Лицензия датасета задач: CC BY-SA 4.0 (требует attribution, не запрещает commercial use)
- Лицензия кода: MIT
- GDPR-compliance для community аккаунтов (right to deletion)
- Disclosure policy для sponsored evals — отдельная страница `/disclosures`
- Tos vendor'ов — некоторые запрещают benchmark publication, проверять каждого
- IP authors of tasks — если задача basis from production code, нужно permission

**Statistical rigor.** Эту часть я уже разбирал, но напомню: multiple seeds (≥5), inter-judge kappa ≥ 0.7, bootstrap CI на всех числах, effect sizes (Cohen's d) рядом с p-values. Без этого статья ≠ исследование.

**Cost transparency.** Total inference cost каждого run опубликован в `/runs/[hash]`. Это и про честность, и про показ читателю "вот столько стоит это исследование". Хорошо для credibility.

**Sponsored evaluations protocol.** Если vendor платит за accelerated addition или extra eval — **обязательная маркировка**. На странице модели: бейдж "Sponsored addition" с датой. В `/disclosures` — кто платил, сколько, что включено. Это спасает от scandal по типу LMSYS leaderboard illusion.

**API rate limiting & fair use.** Public API: 100 requests/hour free, 10k/hour за $50/мес. Защита от scraping через Cloudflare. Bulk download — только через `/datasets` (raw files, не API).

**Operational transparency.** `/status` показывает: last run timestamp, next scheduled run, current health (each worker по регионам). Если что сломалось — публичный postmortem в `/blog`.

**Multilingual support.** Все промпты задач сначала только английский. Multilingual задачи — отдельная категория (русский, китайский, испанский) с native-speaker judges. Это **версия 2** — не для MVP.

**Disclosure of conflicts.** Eli явно ведёт ForgePlan — Stack `claude-code + forgeplan` будет evaluated рядом с конкурентами. Это **обязательно disclosed** на странице того стека: "POLLMEVALS оператор является разработчиком ForgePlan. Методология калибрована независимо. Третий-сторон review TBD."

**Anti-bot для community vote.** GitHub OAuth обязательно. Аккаунту минимум 6 месяцев + 10 contributions. Это убирает spam без надоедливого captcha.

**Sunset policy.** Deprecated модели остаются в database с пометкой "deprecated" + дата. Их данные сохраняются для historical context. Не отвергать → не нарушать citation тех кто ссылался на them.

**Backup & disaster recovery.** Postgres daily snapshot в R2. Raw outputs в R2 уже redundant. Если домен/инфра умерла — публичный архив на HF Datasets обновляется weekly с лагом.

## 11. Roadmap

**MVP (3-4 месяца, solo).** Только Фаза 1 (модели на голых задачах) + базовый сайт + один weekly run для 14 моделей × 20 задач из одного региона (Frankfurt). 4 страницы: leaderboard, model detail, task detail, methodology. Без community vote.

**v0.2 (5-6 мес).** Geo workers (4 региона). Scaffolding stacks (Фаза 2). Compare page. Public datasets.

**v0.3 (7-9 мес).** Community vote. API public. Tier 1 pricing.

**v1.0 (10-12 мес).** Validator loop (Фаза 3). Full ablation series Фазы 2-5 как weekly rotating focus.

**v2.0 (год+).** Enterprise white-label, multilingual, sponsored evals protocol.

## 12. Метрики успеха

**Quality signals:**
- Inter-judge agreement (Krippendorff α) ≥ 0.75
- Calibration deviation < 1.5 баллов
- Run reproducibility — повтор того же run дает delta < 0.5 балла

**Audience signals:**
- /leaderboards unique visitors / неделя
- /api active keys
- GitHub stars on open-source eval repo
- HN / Reddit / Twitter mentions
- Citation в академических papers (это золотой стандарт)

**Business signals (Tier 1+):**
- Tier 1 paid users
- Tier 2 deals signed
- Sponsored evals (count, $)

---

## Что я ещё не учёл — открытые вопросы которые надо ответить

1. **Где брать gold solutions для 20 задач** — пишешь сам или нанимаешь freelancers? Если сам — 100-150 часов работы. Если нанимаешь — $5-10k за все 20 + надо проверять качество.

2. **Кто пишет evaluator scripts** — это python/JS код который запускает тесты, считает CC, и т.д. Тоже 40-80 часов работы.

3. **Юридическая структура** — если это коммерциализируется, нужна LLC/Ltd (UK/EU подходит). Это $500-1500 разово.

4. **Domain** — pollmevals.com нужно зарегистрировать **сейчас**, пока никто не успел. $10-15/год. Также .ai (~$70), .com.

5. **Brand check** — Google "pollmevals" — должно быть пусто. Trademark check (опционально, $1500 заявка в EU/US).

6. **Open-source repo organisation** — `github.com/pollmevals/{core,tasks,site,litellm-config}`. Готово к публикации с MIT license.

---
