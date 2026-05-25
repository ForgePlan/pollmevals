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
