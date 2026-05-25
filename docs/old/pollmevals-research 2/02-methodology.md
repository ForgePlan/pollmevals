# 02 — Методология

## Часть 1: Scaffolding evaluation — лесенка обвязки

Ключевая концепция всей платформы: меняется не модель, а то что вокруг неё. Это **ablation study продакшен-стека** — в академии этим почти никто не занимается, в индустрии все делают это интуитивно и без чисел.

### Таксономия 9 уровней обвязки

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

L0-L7 — общий стек. L8 — готовые композиции L0-L7 заточенные под класс задач. ForgePlan, например, это по сути L3+L4+L6+L8 в одной упаковке для документации.

### Ключевая гипотеза

На простых задачах обвязка ничего не даёт (или даже мешает). На сложных задачах — каждый слой обвязки даёт измеримый прирост, и **дешёвая модель с правильной обвязкой часто бьёт дорогую модель без неё**.

Это нужно доказать числами через ablation study.

---

## Часть 2: Panel of LLM Judges (POLLM)

### Базовые правила

**Модель не судит сама себя.** Никогда. Это исключает self-enhancement bias (в paперах: Llama-judge ставит Llama-ответам на +5-15% выше, GPT — GPT, и так у всех).

**Минимум 3 разных судьи на каждый ответ.** Один судья — subjective. Два — может быть тай. Три — есть медиана. Финальный балл = **медиана**, не среднее (медиана устойчива к выбросам).

**Судьи из разных family.** Нельзя ставить судьями три модели Anthropic — они слишком похожи и accord biases. Бери микс: один Anthropic, один OpenAI, один Google, один open-weight.

### Матрица судейства (стандартный setup)

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

5 судей × 14 подсудимых × 20 задач = 1400 judge-calls на Фазу 1. ~$30-70 на судейство всей фазы.

Опционально 6-й судья — Grok-4 (не в Anthropic/OpenAI/Google семьях).

### Anonymization pipeline

Чтобы судья реально не знал что чьё, нужна **система нормализации перед судейством**:

```python
def normalize_for_judging(raw_output: str, task_type: str) -> str:
    # 1. Strip приветствий и завершалок (Claude's "Certainly!", GPT's "Sure!", etc.)
    text = strip_meta_phrases(text, patterns=[
        r"^(Sure|Certainly|Absolutely|Here's|I'll|Let me|I'd be happy).*?[\n.]",
        r"\n\n(Let me know|Hope this helps|Feel free).*$",
    ])
    
    # 2. Для кода — извлечь из markdown блоков, форматировать через language formatter
    if task_type == "code":
        code = extract_code_block(text)
        code = run_formatter(code, lang=detect_lang(code))  # prettier/black/rustfmt
        code = strip_author_comments(code)  # удалить "// Created by..."
        code = remove_explanation_blocks(code)
    
    # 3. Для документации — нормализовать markdown
    if task_type == "doc":
        text = normalize_markdown_headers(text)
        text = strip_emoji_decoration(text)
    
    return text
```

**Anti-signature в промпте генерации:**
```
Important: Do not introduce yourself, do not greet, do not say "Here's the 
solution" or similar phrases. Do not sign code with your name or model 
identifier. Output ONLY the solution itself, nothing else.
```

Это снижает 70-80% подписей. Остальное добивает нормализация.

**Проверка работы:** identification probe — отдаём ответ другой модели и спрашиваем "guess which model wrote this". Если accuracy > 30% — нормализация недостаточна.

---

## Часть 3: Таксономия biases судей

| Bias | Что это | Mitigation |
|---|---|---|
| Self-enhancement | Любит свой "акцент" | Self-judging disabled |
| Position bias | Первый/последний ответ получает выше балл | Рандомизировать порядок при каждом judge call |
| Length bias | Длинные ответы кажутся "лучше" | В rubric явно: "не оценивайте по длине". Penalize длинные > 2× медианы |
| Verbosity bias | Markdown/bullets кажутся "structured" | Нормализовать форматирование |
| Authority bias | "Expert solution" в промпте → выше балл | Не говорить о происхождении |
| Sycophancy | Если в промпте намёк — соглашается | Промпт нейтральный, без "this is the gold answer" |
| Anchor bias | Первый score влияет на следующие | Каждый ответ оценивается в отдельном judge call, без контекста |
| Halo effect | Хороший в одном — высокие баллы и в другом | Скоринг по каждому критерию rubric'а независимо |
| Calibration drift | Судья дрейфует к "среднему" | Использовать calibration set с известными score |

---

## Часть 4: Calibration set

**Must-have which никто не делает.** Перед судейством реальных ответов, прогоняем каждого судью через **5-10 калибровочных задач с известными "правильными" оценками**:

- Заведомо отличное решение → должно получить ~9-10
- Заведомо среднее → ~5-6
- Заведомо плохое (но компилируется) → ~2-3
- Заведомо неправильное → ~0-1
- Identical с переформулировкой — оба должны получить ~равные баллы

Если судья отклоняется от калибровки → исключаем из пула или переделываем rubric.

В статью идёт **таблица калибровки судей** — это очень публикуемо.

---

## Часть 5: Pairwise vs Absolute scoring

Литература говорит: **pairwise сравнения стабильнее absolute оценок**. Когда судья говорит "B лучше A" — устойчиво. Когда говорит "B = 7.3" — subjective.

**Hybrid approach:**
- Автометрики дают абсолютные числа (correctness, CC, coverage, test pass)
- Pairwise judge даёт относительный ранг через Bradley-Terry или Elo
- Финальный score = weighted combination

---

## Часть 6: Multi-dimensional scoring per task type

### Для кодовых задач

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

### Для документации / архитектуры

```python
rubric_doc = {
    "structural_completeness": "Все нужные секции присутствуют (0-10)",
    "factual_accuracy":         "Нет фактических ошибок относительно gold",
    "clarity":                  "Понятно ли junior-разработчику",
    "actionability":            "Можно ли по этому работать",
    "consistency":              "Не противоречит ли сам себе",
}
# Через panel of judges с blind labels, median scoring
```

### Для code review

```python
review_metrics = {
    "recall":          0.4,  # % реальных багов из ground truth списка
    "precision":       0.3,  # из найденных, % реально багов
    "severity_match":  0.2,  # совпадение оценок critical/major/minor
    "fix_quality":     0.1,  # LLM-judge на предложенные фиксы
}
```

---

## Часть 7: Statistical rigor

**Multiple seeds.** Каждый combo (model × task) гоняем **5 раз** с разными seed/temperature. Это даёт оценку variance. В радаре показываем **mean ± std**. Если разница между моделями < std — она не значима.

**Inter-rater reliability.** После судейства считаем согласие между судьями:
- **Cohen's kappa** для пар
- **Krippendorff's alpha** для пула > 2 судей

Цель: α > 0.7 (нормально), > 0.8 (хорошо). Если α < 0.5 — судьи спорят, твоим оценкам нельзя верить.

**Effect size, не только p-value.** Между двумя моделями смотрим **Cohen's d**:
- d < 0.2 — разница незначительна (даже если p < 0.05)
- d > 0.8 — large effect, реальная разница

В пост обязательно: "разница X vs Y по reasoning — d=0.3 (small), по coding — d=1.1 (large)".

**Bootstrap confidence intervals.** Для финальных оценок на радаре считаем 95% CI через bootstrap (resample with replacement). На графике рисуем shaded zone. Это убивает все "ну а вдруг это случайность".

**Pre-registration.** Перед прогоном записываем гипотезы и метрики в файл, коммитим в git. После прогона сравниваем. Это исключает p-hacking.

---

## Часть 8: "Premium" артефакты для публикации

Эти штуки превращают пост из "вот цифры" в "вот исследование":

1. **Inter-judge agreement matrix** — таблица Cohen's kappa между всеми судьями
2. **Calibration plot** — оси: "истинный score" vs "score от судьи". Точки выше/ниже диагонали показывают bias
3. **Variance heatmap** — `model × task`, цвет = std accuracy через 5 прогонов
4. **Confidence intervals на радаре** — error bars или shaded zones
5. **Cost-quality Pareto с error bars** — финальный график
6. **Bias-check table** — identification probe ниже 30% accuracy
7. **"Negative findings"** — где разница не значима. **Сильно повышает доверие** читателя
