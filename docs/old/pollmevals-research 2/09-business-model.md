# 09 — Business Model

## Tier-based монетизация (4 уровня риска)

### Tier 0: Open data, no monetization

**Что:** публичный leaderboard + open datasets + блог-серия.

**Кто платит:** никто. Это **reputation play**.

**Что даёт Eli:**
- Авторитет как expert на тему scaffolding evaluation
- Network effects — позже легче конвертировать в продукт
- Source for консалтинг/курс/SaaS leads

**Стоимость maintain:** ~$1000/мес на inference + инфра + время.

**Recommended для старта — все начинают здесь.**

---

### Tier 1: API access ($-$$$)

**Что:** бесплатный leaderboard, **платный** доступ к raw data через API.

**Pricing:**
- **Hobby** $0 — 100 req/hour, basic data
- **Pro** $50/mo — 10 000 req/hour, full data, historical
- **Team** $500/mo — 100 000 req/hour, bulk datasets, priority support

**Кто платит:**
- Model producers (для маркетинга "мы первые на POLLMEVALS")
- Researchers / analysts
- VC firms для due diligence
- Enterprise teams для internal dashboards

**Реализация:** Stripe + Cloudflare API gateway.

**Аналог:** Artificial Analysis работает по этой схеме.

---

### Tier 2: Custom evals for clients ($$)

**Что:** компания приходит "у нас свой стек, запустите его через POLLMEVALS методологию на наших задачах".

**Pricing:**
- Quick eval (existing stack, new task set): $5-10k
- Full eval (custom stack + custom tasks + custom report): $15-30k

**Кто платит:**
- Engineering teams выбирающие LLM-стек
- Consultancies (Accenture, Deloitte) которые делают AI advisory
- Companies оценивающие свой AI investment

**Реализация:** ручная работа. Eli как expert + 1-2 контрактора.

**Это classic консалтинг под бренд платформы.**

---

### Tier 3: Sponsored evals ($$)

**Что:** model producer платит чтобы их новую модель прогнали с приоритетом и опубликовали.

**Pricing (черновик):**
- Expedited model addition: $500
- Priority weekly run inclusion: $1000
- Custom region testing: $2000
- Custom task eval: $5-20k

**Кто платит:**
- Anthropic, OpenAI, Google — для launch новых моделей
- Open-weight teams (Meta, Mistral, DeepSeek)
- New entrants (xAI, Alibaba)

**Реализация:**
- Чёткая disclosure policy (см. 08-must-consider.md, секция 10)
- Sponsored = быстрее в очереди, **не лучше в результатах**
- Прозрачные badges на страницах

**Risk:** scandal по типу LMSYS leaderboard illusion. Mitigation: радикальная прозрачность.

---

### Tier 4: Enterprise white-label ($$$)

**Что:** "запустите POLLMEVALS платформу на нашем приватном codebase для оценки внутренних агентов".

**Pricing:** $50k - $500k per контракт.

**Кто платит:**
- FAANG-tier компании с internal AI tooling
- Financial services с compliance-критичными use cases
- Government (US, EU) для evaluating AI suppliers

**Реализация:**
- Self-hosted POLLMEVALS instance
- Custom task pool под их domain
- White-label dashboard
- Support contract

**Это рынок Scale AI и Surge AI** — там money есть, но это **отдельная компания**, не пет-проект.

---

## Подъёмность по фазам

### Pre-MVP (months 0-3)
- **Tier 0** only
- Cost: ~$500/мес (low-volume runs)
- Revenue: $0
- Goal: первые 5 blog posts серии, audience build

### MVP launch (months 3-6)
- **Tier 0 + Tier 1 Hobby**
- Cost: ~$1500/мес (weekly runs)
- Revenue: $0-500/мес (early adopters)
- Goal: 100 MAU, 10 GitHub stars/week growth

### Early growth (months 6-12)
- **Tier 0 + Tier 1 full**
- Cost: ~$3000/мес
- Revenue: $2-10k/мес
- Goal: break even, 500 MAU

### Established (year 2+)
- **All tiers active**
- Cost: ~$10-20k/мес (full team)
- Revenue: $30-100k/мес
- Hire: 1-2 engineers, 1 community manager
- Goal: profitable business

---

## Reality check — твои ресурсы

У Eli уже есть:
- ForgePlan
- Orchestra
- Gerts.ai
- Spa бизнес
- AI-курс
- Консалтинг

**Шестой полноценный продукт ты не потянешь** при текущей загрузке. Это надо честно сказать.

### Реалистичный путь

1. **Сначала серия постов** (3-4 месяца). Это и есть proof-of-concept. Контент сам по себе ценен, репутация выстраивается. Доступ к Eli как эксперту в "scaffolding evaluation" — это актив.

2. **Если посты заходят** (10k+ просмотров, обсуждения в HN/Reddit/Twitter), **запускаешь MVP**. На этом этапе можно:
   - Привлечь со-основателя
   - Нанять 1 девелопера через консалтинг-деньги
   - Запустить freelance contributor program

3. **Если MVP получает 100+ MAU аудитории**, тогда коммерциализация. До этого момента — open data + блог + Tier 0.

Это **3-фазная стратегия с реальными gating criteria**.

---

## Метрики чтобы понять "идёт ли"

### После 1 серии постов (week 4)
- 1000+ unique visitors на blog
- 20+ comments / discussions on HN/Reddit
- 50+ GitHub stars on demo repo
- 5+ mentions от credible accounts in AI space
- **Если меньше — не идёт. Стоп, делай другое.**

### После MVP launch (month 6)
- 100+ MAU
- 10+ Tier 1 Hobby signups
- 1+ Tier 1 Pro signup
- 1+ Tier 2 inquiry
- **Если меньше — фокусируйся на контенте, не продукте.**

### После 12 месяцев
- 500+ MAU
- $5k+ MRR
- Citations в academic papers (это серьёзно)
- **Если меньше — это side project, не business.**

---

## Что НЕ делать

- **Не пытаться сразу делать всё** — outdoors можно прогореть на инфраструктуре до того как audience сформирована
- **Не превращать в платный сразу** — сначала reputation, потом monetization
- **Не конкурировать с Arena напрямую** — у них $1.7B valuation, не победишь, фокус на свою нишу
- **Не обещать enterprise white-label** до того как есть solid product
- **Не запускать sponsored evals** до того как methodology зафиксирована и проверена independent reviewers
