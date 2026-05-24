# 11 — Roadmap

## Общая стратегия

3-фазная стратегия с реальными gating criteria:

1. **Серия постов** (months 0-3) → если идёт, переход к MVP
2. **MVP** (months 3-6) → если 100+ MAU, переход к коммерции
3. **Коммерция** (months 6-12+) → Tier 1, потом Tier 2/3

---

## v0.0 — Pre-launch (weeks 1-2)

### Цели
- Зафиксировать методологию
- Зарегистрировать домены
- Создать GitHub org

### Чек-лист
- [ ] Зарегистрировать `pollmevals.com` + `.ai` + `.io`
- [ ] Создать `github.com/pollmevals` org
- [ ] Repo: `pollmevals/core` (eval engine, MIT)
- [ ] Repo: `pollmevals/tasks` (20 задач + gold + evaluators, CC BY-SA)
- [ ] Repo: `pollmevals/site` (Next.js + Tailwind)
- [ ] Repo: `pollmevals/litellm-config` (configs для разных setups)
- [ ] Trademark check (опционально, $1500)
- [ ] Twitter / Telegram / RSS подключены

### Deliverable
GitHub org с placeholder repo, домены registered.

---

## v0.1 — Smoke test (weeks 2-4)

### Цели
- Подтвердить что pipeline работает end-to-end
- 3 задачи × 5 моделей × 5 seeds × 3 судей = ~225 evaluations

### Чек-лист
- [ ] Setup LiteLLM локально
- [ ] Setup Inspect AI
- [ ] Финализировать YAML для 3 задач (be_01, fe_01, doc_01)
- [ ] Написать gold solutions для этих 3
- [ ] Написать evaluator scripts
- [ ] Первый smoke run на:
  - Claude Sonnet 4.6
  - GPT-5
  - Gemini 2.5 Pro
  - Qwen 2.5 14B (locally)
  - Llama 3.3 70B (Cerebras)
- [ ] Прогнать panel of 3 judges (Opus, GPT-5, Gemini)
- [ ] Calibration calculation
- [ ] Постмортем — что работает, что нужно дорабатывать

### Deliverable
First smoke results published в blog как "proof of concept post".

---

## v0.2 — Phase 1 launch (months 1-2)

### Цели
- Полная Фаза 1: 14 моделей × 20 задач
- Публикация **первого weekly run**
- Запуск blog с серии

### Чек-лист
- [ ] Финализировать все 20 задач (gold + evaluators)
- [ ] Calibration set из 10 задач (для судей)
- [ ] Postgres + Inspect AI orchestrator deployed
- [ ] LiteLLM с full pool моделей
- [ ] One worker региона (Frankfurt) — geo workers потом
- [ ] First full weekly run
- [ ] Inter-judge agreement >= 0.7
- [ ] Bootstrap CI на всех результатах
- [ ] Static site с лидербордами published
- [ ] First blog post: "How we eval scaffolding stacks — methodology"
- [ ] Second blog post: "Phase 1 results — model radar chart"

### Deliverable
Working POLLMEVALS site с **one full weekly run** published, blog active.

### Gating criteria для перехода в v0.3
- 1000+ unique visitors / week 4
- 20+ HN/Reddit comments
- 50+ GitHub stars
- 5+ credible AI accounts mention

Если меньше — фокусируйся на контенте, не разворачивай инфраструктуру.

---

## v0.3 — Phase 2 ablation + Geo workers (months 3-4)

### Цели
- Фаза 2: scaffolding ablation (L0→L6) на 1-2 моделях
- 4 geo workers активны
- Compare page

### Чек-лист
- [ ] 2-3 толстых задачи для Фазы 2 (refactor, PRD, debug)
- [ ] Implement Claude Code integration через CLI
- [ ] mem0 / hindsight integration
- [ ] Phase 2 run
- [ ] Ablation bars в блоге
- [ ] Geo workers: US-East, EU-Central, APAC
- [ ] `/compare` page
- [ ] `/runs/[hash]` страница reproducibility
- [ ] Blog post: "What does scaffolding give you? Ablation results"
- [ ] Public dataset download (`/datasets`)

### Deliverable
Site с 2 фазами data, ablation insight published.

---

## v1.0 — Community + API (months 5-8)

### Цели
- Community vote открыт
- API public для bulk read
- Phase 3 (memory comparison) launched

### Чек-лист
- [ ] `/vote` страница с GitHub OAuth
- [ ] `/propose-model`, `/propose-task`, `/propose-stack` формы
- [ ] Automated validation для proposals
- [ ] Public API с rate limiting
- [ ] Tier 1 Hobby (free) + Tier 1 Pro ($50/мес)
- [ ] Phase 3: memory comparison (mem0, hindsight, file-based)
- [ ] Disclosure policy published
- [ ] First sponsored eval (с full disclosure)
- [ ] 4 weekly runs published за месяц

### Deliverable
Functional community participation + revenue start.

### Gating criteria для коммерции
- 100+ MAU
- 10+ Tier 1 Hobby signups
- 1+ Tier 1 Pro signup
- 1+ Tier 2 inquiry

---

## v1.5 — Phase 4-5 + Tier 2 (months 9-12)

### Цели
- Phase 4 (CLI comparison)
- Phase 5 (final Pareto)
- First Tier 2 paid eval

### Чек-лист
- [ ] Phase 4: Claude Code vs Codex vs Gemini vs Hermes
- [ ] Phase 5: final cost-quality Pareto
- [ ] All 8 categories of tasks covered
- [ ] Tier 2 service launched
- [ ] First paying enterprise customer
- [ ] First academic citation
- [ ] Annual report "State of LLM Stacks 2026"
- [ ] Conference talk submission (NeurIPS / ICLR workshop)

### Deliverable
Complete 5-phase research series + first revenue.

---

## v2.0 — Scale (year 2)

### Цели
- Multilingual (Russian, Chinese, Spanish tasks)
- Tier 3 sponsored framework
- Possible Tier 4 enterprise white-label

### Чек-лист (high-level)
- [ ] Multilingual tasks pool (15-20 задач на каждый язык)
- [ ] Native-speaker judges
- [ ] Sponsored evals operational (3+ deals)
- [ ] Enterprise white-label pilot (1 deal)
- [ ] Possible: hire 1-2 engineers, 1 community manager
- [ ] Independent advisory board

### Gating criteria для Tier 4
- 500+ MAU
- $5k+ MRR
- 5+ Tier 2 deals closed
- Production-grade infrastructure (99.5%+ uptime)

---

## Что НЕ делать в roadmap

- **Mobile apps** — никогда. Это data product, не consumer app.
- **Free API без rate limits** — burnout инфраструктуры.
- **Open source ВСЕ** — task gold solutions могут быть premium для Tier 1.
- **Видео контент** — пока серия не доказана текстом.
- **Custom hardware** — никогда, всегда cloud + Runpod.
- **Token / Crypto / NFT integrations** — никогда.

---

## Постмортем checkpoints

После каждого quarter:
- Что работает (продолжаем)
- Что не работает (убираем или меняем)
- Что забыли (добавляем)
- Cost vs revenue ratio

Если 2 quarter подряд cost > revenue × 2 → переоценить стратегию.

---

## Exit scenarios

В порядке предпочтения:

1. **Successful indie business** ($30-100k MRR, sustainable solo or 2-3 people) — main goal
2. **Acquisition** — Scale AI, Hugging Face, vendor (Anthropic, Google) могут купить за brand + data
3. **Donated to open ecosystem** — если не получилось коммерциализировать, передать в Apache foundation или similar
4. **Sunset gracefully** — если не работает, опубликовать final report + archive datasets на HF

Все четыре сценария **planned upfront** — не surprised если случится.
