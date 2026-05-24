# 12 — Next Steps

## Что делаем СЕЙЧАС (week 0)

### Действие 1: Зарегистрировать домены — 1 час

```
pollmevals.com    ≈ $12/год     Namecheap или Cloudflare Registrar
pollmevals.ai     ≈ $70/год     для AI-positioning
pollmevals.io     ≈ $35/год     fallback
pollmevals.org    ≈ $12/год     для open community vibe
```

**Total ≈ $130/год.** Делать сейчас пока никто не успел.

### Действие 2: Создать GitHub org — 30 минут

- `github.com/pollmevals` создать
- Создать стартовые repo:
  - `pollmevals/core` — placeholder с README
  - `pollmevals/tasks` — placeholder с README + структура
  - `pollmevals/site` — placeholder
  - `pollmevals/litellm-config` — placeholder

### Действие 3: Подтвердить с Eli три ключевые задачи для smoke — 30 минут

Из draft списка 20, выбрать 3 которые делаем первыми:
- **be_01** — JWT auth middleware (backend, medium)
- **fe_01** — Multi-step form (frontend, medium)
- **doc_01** — README для CLI tool (docs, easy)

Если Eli согласен — поехали. Если хочет заменить — называет.

### Действие 4: Я (Claude) пишу YAML спеки для этих 3 задач — 4-6 часов работы

Для каждой:
- Полное description в Markdown
- Gold solution (TypeScript / Markdown)
- Test suite / evaluator script
- Expected metrics ranges
- 3 калибровочных версии (good / mediocre / bad)

Eli ревьюит, корректирует.

### Действие 5: Setup LiteLLM + Inspect AI локально у Eli — 2-3 часа

- Docker-compose с LiteLLM + Postgres
- Inspect AI installed
- API keys для OpenRouter (cloud) + Cerebras (open weights)
- Smoke test: один prompt через LiteLLM достигает Claude

### Действие 6: Первый smoke run — 2-3 часа

Гоним 3 задачи × 5 моделей × 3 seeds = 45 evals. Без judges пока — только automatic metrics. Чтобы поймать pipeline issues.

### Действие 7: Калибровка панели судей — 4-6 часов

- 5 калибровочных задач с known scores
- Прогнать 5 судей через них
- Считать inter-judge agreement
- Если < 0.7 — переписать rubric, повторить

### Действие 8: Полный smoke с judges — 3-4 часа

45 evals × 4 judges (self-exclusion) = 180 judgments. Считаем final scores. Сравниваем с expected.

### Действие 9: Первый blog post — 6-8 часов

"How we eval scaffolding stacks — methodology"

Это первый пост в серии. Закладывает все правила игры.

---

## Total estimate

**Pre-launch (v0.0 + v0.1):** ~30-40 часов работы Eli + parallel Claude tasks.

Реалистично за **2-3 недели** при загрузке 10-15 часов в неделю.

---

## Open Questions — нерешённые

### Q1: Кто пишет gold solutions для всех 20 задач?

**Опции:**
- Eli сам (100-150 часов) — самое надёжное по качеству, но долго
- Freelancers через Upwork ($5-10k за все 20) — быстрее, но нужен review
- Claude генерирует draft, Eli проверяет — гибрид, быстро + контроль

**Решение:** **Гибрид.** Claude пишет draft → Eli проверяет на качество → если ОК — финализируем. Если плохо — переписываем вместе.

### Q2: Какой stack для site — Next.js или что-то другое?

**Опции:**
- Next.js 15 + Tailwind + shadcn/ui (стандарт)
- Astro (быстрее для статики)
- Just static HTML + минимум JS (легче maintain)

**Решение:** **Next.js 15** — гибкость для динамических лидербордов + SSG для blog. Стандартно, легко найти контракторов если нужно.

### Q3: Mongo или Postgres?

**Решение:** **Postgres**. Schema-heavy data, relational queries, нет нужды в NoSQL flex.

### Q4: Стейт у Eli потянет maintain weekly run или нет?

**Реалистично:**
- Setup: 30-40 часов одноразово
- Weekly run baby-sitting: 2-4 часа per week
- Blog post: 4-6 часов per week
- Community moderation: 1-3 часа per week

**Total: ~10-15 часов/week** после launch.

Это **40-60% от time'а ForgePlan**. Eli уже занят. Нужно решить — отложить ForgePlan launch readiness, или distribute time.

### Q5: Что если no traction?

**После 4 недель публикации:**
- Если < 1000 visitors → серия не идёт. Стоп.
- Если 1000-5000 visitors → продолжать как hobby, не продукт.
- Если > 5000 visitors → разворачивать MVP.

**Pre-committed exit point.** Это спасает от sunk cost fallacy.

### Q6: Юридическая структура

**Когда нужно:**
- Только когда есть revenue (Tier 1+)
- До этого — все на личное имя Eli (хобби-проект)

**Когда есть revenue:**
- UK Ltd (cheap, fast, ~£100 setup)
- Estonian e-Residency company (для EU citizens, ~€500)
- Cyprus Ltd (если ожидается большая прибыль и low tax)

### Q7: Что с visibility у Eli как ForgePlan author?

**Disclosure обязателен.** В каждом посте упомянуть "POLLMEVALS оператор является разработчиком ForgePlan, методология калибрована независимо".

ForgePlan-stacks (когда дойдём до Фазы 2-5) **не fast-track**, не sponsored. Обычный community process.

---

## Decision Log — что зафиксировано

| Дата | Решение | Рационал |
|---|---|---|
| 2026-05-21 | Выбрали Inspect AI как eval engine | 200+ pre-built evals, отличный DX, Anthropic adopted |
| 2026-05-21 | Выбрали LiteLLM как gateway | Cost tracking built-in, OpenAI-compatible, MIT |
| 2026-05-21 | Cerebras + Runpod + OpenRouter как inference layers | Cerebras скорость, Runpod гибкость, OR cloud |
| 2026-05-21 | 14 моделей в пуле для Фазы 1 | Достаточно для богатого радара, в 2× меньше прогонов чем 30+ |
| 2026-05-21 | TypeScript/Node.js как основной язык + Python для DevOps | Реальный production stack, моделим сильны в нём |
| 2026-05-21 | 20 задач для Фазы 1 (draft list) | Балланс между breadth и feasibility |
| 2026-05-21 | Panel of 5 judges с rotation, no self-judging | Best practice из академии, никто в commercial не делает |
| 2026-05-21 | Median scoring через panel, не mean | Устойчивость к outliers |
| 2026-05-21 | 5 seeds per combo для bootstrap CI | Standard для statistical rigor |
| 2026-05-21 | Krippendorff α >= 0.7 как gate для publishing | Inter-rater reliability threshold |
| 2026-05-21 | 5-фазная серия постов вместо одного | Factorial design, каждая фаза = 1 post |
| 2026-05-21 | POLLMEVALS как brand для продукта | Уникальная ниша — scaffolding eval с panel |
| 2026-05-21 | Tier 0 → 1 → 2 → 3 → 4 монетизация | Постепенный, gated by audience |
| 2026-05-21 | Postgres + R2 + Redis stack | Стандарт, легко maintain |
| 2026-05-21 | Next.js 15 + Tailwind + shadcn для frontend | Стандартный modern stack |
| 2026-05-21 | 4 geo regions для latency | US-East, EU-Central, APAC, SA — реалистичные territories |
| 2026-05-21 | Weekly cadence + flagship-triggered | Не daily (слишком noisy), не monthly (slow) |
| 2026-05-21 | MIT для кода, CC BY-SA для датасетов | Стандарт для open research |
| 2026-05-21 | Code execution в Docker без network access | Security base |
| 2026-05-21 | Identification probe < 30% для anonymization | Verify подписи срезаны |
| 2026-05-21 | 20% задач — held-out private set | Anti-gaming страховка |
| 2026-05-21 | Drift detection через 2σ от baseline | Catch silent model updates |

---

## Чего я (Claude) пока не зафиксировал — нужно решение Eli

- [ ] **Финальный набор 20 задач** — apply changes if any
- [ ] **Lead time для launch** — 2 weeks, 4 weeks, 8 weeks?
- [ ] **Контрактор vs solo** для gold solutions — кто пишет
- [ ] **Бренд имени personality** — это "anonymous research project" или "Eli's project"?
- [ ] **Co-founder** — solo или искать партнёра?
- [ ] **Initial funding** — bootstrapping or seeking small angel ($25-50k)?
- [ ] **Anti-pattern: что НЕ делать** в первый год — list of "don'ts"

---

## Финал — что хочет видеть Eli по итогам

Если по итогам этого исследования через 6 месяцев:

1. ✓ Серия 5 постов опубликована
2. ✓ POLLMEVALS как brand зарекомендован в AI community
3. ✓ MVP сайт с минимум одной фазой data live
4. ✓ 100+ MAU и растёт
5. ✓ First Tier 1 paying customer

— это **успех**. Не пытаемся всё за раз.

Если что-то из этого не достигнуто — переоцениваем стратегию **до того как** добавлять complexity.

---

## Финальная команда от меня

**Скажи "поехали со smoke на 3 задачах"** — и я начинаю писать YAML спеки + gold solutions + evaluator scripts для be_01, fe_01, doc_01. Через 2 итерации с твоим ревью у нас будет работающий pipeline. Затем масштабируем на 20 задач.

Не пытайся сразу делать продукт. Сначала **proof методологии**, потом продукт.
