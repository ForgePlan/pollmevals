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
