# 10 — Competitive Landscape

## TL;DR

Рынок LLM evaluation **очень занят**, но **никто не делает scaffolding evaluation** систематично. Это уникальная ниша.

## Карта рынка

Делю по двум осям:
- **X-axis:** что меряется (модели → стеки)
- **Y-axis:** как агрегируется (single judge → multi-source / panel)

```
Multi-source │ LMSYS Arena                     [POLLMEVALS]
             │ Artificial Analysis              ← пустая ниша!
             │ BenchLM
             │ SEAL (Scale AI)
─────────────┼───────────────────────────────────
Single judge │ HF Open LLM Leaderboard
             │ SWE-bench, Aider, BigCodeBench
             │ LiveBench, TokenMix
             │
             └───────────────────────────────────
                Модели                  Scaffolding
```

**Все существующие игроки** в левой половине — меряют только модели. **POLLMEVALS** занимает пустой правый верхний квадрант.

---

## Существующие игроки — детально

### LMSYS Arena (lmarena.ai)

- **Что:** human preference через blind A/B battles
- **Масштаб:** 6M+ голосов, 140+ моделей, $1.7B valuation
- **Сильные стороны:** реальные люди, real-time, стандарт индустрии
- **Слабые стороны:** subjective, hard to reproduce, scandal "Leaderboard Illusion" paper в 2025
- **Конкурент с POLLMEVALS?** Нет — мы про automated objective scoring, они про human preference

### Artificial Analysis (artificialanalysis.ai)

- **Что:** composite intelligence + cost + speed для 356 моделей
- **Сильные стороны:** широкое покрытие моделей, cost/speed данные
- **Слабые стороны:** только голые модели, no scaffolding, automated metrics только
- **Конкурент с POLLMEVALS?** Нет — близко по бизнес-модели (free leaderboard + paid API), но другая ниша

### BenchLM (benchlm.ai)

- **Что:** 228 моделей × 186 бенчмарков, агрегатор
- **Сильные стороны:** широкое покрытие бенчмарков
- **Слабые стороны:** только агрегация, не собственная methodology
- **Конкурент?** Нет, дополняем — они агрегируют, мы добавляем новый бенчмарк

### Hugging Face Open LLM Leaderboard

- **Что:** automated benchmarks для open-weight моделей
- **Сильные стороны:** open ecosystem, free, reproducible
- **Слабые стороны:** только open weights, single judge, академические бенчмарки
- **Конкурент?** Частично — overlap по моделям, но они не делают closed APIs

### SEAL (Scale AI)

- **Что:** expert-driven evaluations включая software engineering, finance, law
- **Сильные стороны:** enterprise-focus, high-quality task curation
- **Слабые стороны:** closed source, expensive, slow cadence
- **Конкурент?** В Tier 4 enterprise white-label — да. В Tier 0-2 — нет.

### SWE-bench / Aider Polyglot / LiveBench / BigCodeBench

- **Что:** coding-specific benchmarks с automated grading
- **Сильные стороны:** rigorous, reproducible, real tasks (для SWE-bench)
- **Слабые стороны:** single benchmark, single judge, only coding
- **Конкурент?** Нет — мы используем их **как источники задач**, а не как конкурентов

### TokenMix

- **Что:** multi-provider routing + leaderboard как side-effect
- **Сильные стороны:** practical pricing data
- **Слабые стороны:** focus на routing, eval вторичен
- **Конкурент?** Нет, complementary

### Onyx

- **Что:** crowdsourced evaluation, similar to LMSYS
- **Сильные стороны:** open source
- **Слабые стороны:** меньший масштаб
- **Конкурент?** Не прямой

### Vercel AI Gateway / Cloudflare AI Gateway

- **Что:** infrastructure для routing
- **Конкурент?** Нет, мы можем интегрироваться

---

## Что у POLLMEVALS уникально

| Фишка | Кто еще делает | Уникальность |
|---|---|---|
| Scaffolding evaluation | **Никто** | High |
| Panel of LLM judges с rotation | Никто в commercial product | High |
| Cost-per-task для стека | Никто | High |
| Geo-aware latency | Никто systematic (AA даёт TTFT но без региона) | Medium |
| Community-driven model addition | LMSYS делает закрыто, мы прозрачно | Medium |
| Drift detection для closed APIs | Никто publishes | High |
| Held-out anti-gaming set | LiveBench делает | Medium (но не для scaffolding) |
| Full reproducibility | SWE-bench Verified да, остальные нет | Medium |

---

## Стратегия позиционирования

### "Мы не Arena"

Arena про human preference на чате. Мы про automated objective scoring на production tasks. **Разные категории**, не конкурируем.

### "Мы не Artificial Analysis"

AA про cost/speed/intelligence для голых моделей. Мы про cost/quality для **стеков**. Дополняем — можно сравнить "Claude Opus голая на AA" vs "Claude Opus + ForgePlan на POLLMEVALS".

### "Мы — про практический выбор"

Engineering lead приходит и спрашивает "что мне купить". Ни Arena, ни AA, ни SWE-bench не отвечают на этот вопрос напрямую. POLLMEVALS отвечает — конкретный stack под конкретную задачу.

---

## Конкурентные угрозы

### Угроза 1: Анонимный конкурент копирует методологию

**Вероятность:** низкая в первые 6 месяцев, средняя в год 2+.

**Mitigation:** open-source всю методологию, делаем "founder's brand" вокруг Eli. Бренд + audience — harder to copy чем код.

### Угроза 2: Major player (Arena, AA) добавляет scaffolding eval

**Вероятность:** средняя в год 2+.

**Mitigation:**
- Быть первым (first-mover advantage)
- Глубже специализация (мы про CLI агентов, не general)
- Community trust (open governance vs corporate)

### Угроза 3: Vendor пытается подкупить за хорошие оценки

**Вероятность:** высокая когда станем relevant.

**Mitigation:**
- Жёсткая disclosure policy (см. 08-must-consider.md)
- Sponsored evals **maps в visibility, не в scoring**
- Independent review board (для v1.0)

### Угроза 4: Inspect AI меняется и breaks compatibility

**Вероятность:** низкая (Anthropic adopted, актив support).

**Mitigation:**
- Pinned versions
- Можно fork если что
- Alternative engines exist (lm-eval-harness как backup)

### Угроза 5: Closed-API vendor блокирует evaluation

**Вероятность:** низкая.

**Mitigation:**
- Use OpenRouter как proxy (vendor не блокирует aggregator)
- Open weights coverage strong
- Legal — это fair use under research

---

## Возможные коллаборации

- **Hugging Face** — host POLLMEVALS datasets, cross-link leaderboards
- **Inspect AI** — submit our evals upstream, become reference user
- **EleutherAI** — share tasks
- **Aider / Cursor / Cline** — they have own scaffolding, we evaluate it for them
- **OpenAI / Anthropic** — sponsored evals, internal evaluation contracts (v1.0+)

---

## Конкурентное преимущество в долгую

Через 12+ месяцев POLLMEVALS будет иметь:
- **Historical dataset** (год+ weekly runs) — невоспроизводимо для конкурентов
- **Community of contributors** — task proposals, voting
- **Citations в академических работах** — увеличивают authority
- **Brand** Eli как expert
- **Methodology refinement** — годы calibration data

Это **moat который сложно повторить**. Конкурент должен будет либо ждать год+ (slow), либо платить за access к нашим данным (Tier 1).
