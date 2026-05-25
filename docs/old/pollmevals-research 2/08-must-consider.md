# 08 — Must Consider (то что обязательно учесть)

Список критичных вещей которые обычно упускают. Если их не учесть с самого начала — переделывать дороже чем сразу заложить.

---

## 1. Reproducibility & Immutability

### Run immutability

Каждый run — **immutable после завершения**. Никаких "потом подправим оценку". Если ошибка — **новый run** с тем же task hash, но другим run hash. Это required для научного credibility.

Хранение:
- Run record в Postgres
- Все raw outputs в R2 с content-hash именами
- Manifest файл с версиями всех инструментов

### Reproduce.sh script

В каждом run есть скрипт `reproduce.sh` который позволяет независимому исследователю **воспроизвести точно тот же run**:

```bash
#!/bin/bash
# reproduce.sh для run hash abc123...

export INSPECT_AI_VERSION=0.4.12
export LITELLM_VERSION=1.83.2
export VLLM_VERSION=0.6.3

git checkout v0.1.4  # тег версии POLLMEVALS
pip install -r requirements.lock
docker-compose -f infra/docker-compose.yml up -d

python orchestrator.py \
  --models-snapshot snapshots/abc123.models.json \
  --tasks-snapshot snapshots/abc123.tasks.json \
  --seed 1234 \
  --output ./reproduction-output
```

---

## 2. Task versioning

Когда задача меняется — это **новая версия** с тем же `slug` но другим `version`. Старые eval'ы остаются валидными для своей версии.

**Зачем:** comparison "Claude Opus 4.6 на task v1.0" vs "Claude Opus 4.7 на task v1.0" — apples to apples.

**Page:** `/tasks/[slug]` показывает все версии + diff между ними. Старые версии помечены "archived".

---

## 3. Model drift detection — уникальный insight

Closed-API модели (Claude, GPT, Gemini) меняются "за кулисами" даже при том же tag.

**Что делаем:**
- Если результаты конкретной модели за неделю drift > 2σ от трёхмесячного baseline — alert
- Это **публикуется** как отдельный пост: "Claude Opus 4.7 показал значимое изменение поведения в week 23"
- Скорее всего vendor что-то изменил без публичного announcement
- Это **уникальный insight** который никто другой не делает

---

## 4. Contamination detection

Каждая задача имеет content hash. Регулярно (раз в месяц) гуглим:
- Хеш задачи
- Уникальные кусочки описания
- Имена функций / тестов из gold

Если задача появилась:
- В обучающем датасете
- В GitHub readme
- В blog post
- На Stack Overflow

→ Задача **compromised и retired**. Замена в pool.

У LiveBench это есть, нам тоже нужно.

---

## 5. Anti-gaming через rotation

**20% задач — held-out в private set**, не публикуются. Они меняются ежемесячно. Это страховка от того что vendors начнут оптимизировать на public set.

Реализация:
- Public set: 16 задач (видны всем)
- Held-out set: 4 задачи (только у maintainers)
- Held-out набор пересоздаётся каждый месяц
- На сайте — индикация "results включают held-out tasks"

---

## 6. Code execution safety

Сгенерированный моделями код **выполняется в изолированных Docker контейнерах** с жёсткими ограничениями:

```yaml
# Docker compose для evaluator
services:
  evaluator:
    image: pollmevals/evaluator:v1
    network_mode: none           # NO network access
    read_only: true              # read-only filesystem
    tmpfs:
      - /tmp:size=100M           # ограниченный writable tmpfs
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 50
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    ulimits:
      nofile: 1024
      fsize: 10485760            # 10 MB max file size
```

И timeout 60 секунд **hard kill** на каждый evaluator.

---

## 7. Privacy / Legal

### Лицензии
- **Код:** MIT
- **Датасеты:** CC BY-SA 4.0 (требует attribution, не запрещает commercial use)
- **Tasks proprietary:** для задач basis from production code — нужно explicit permission от автора

### GDPR
Community аккаунты:
- Right to access (download my data)
- Right to deletion
- Right to portability
- Storage в EU (Hetzner Frankfurt)

### Vendor ToS
Некоторые vendors запрещают benchmark publication. Проверять каждого:
- Anthropic ToS — позволяет benchmarks
- OpenAI ToS — позволяет benchmarks с restrictions (no model training on outputs)
- Google ToS — проверить актуальное
- Open-weights — нет ограничений

### IP концов задач
Если задача basis from production code — нужно:
- Permission от автора в письменном виде
- Sufficient anonymization
- Disclosure в task page

---

## 8. Statistical rigor (критично!)

См. 02-methodology.md, секция 7. Главное:

- **Multiple seeds** (≥5) per run
- **Bootstrap CI** на всех числах
- **Effect sizes** (Cohen's d) рядом с p-values
- **Inter-judge agreement** (Krippendorff α) обязательно публикуется

Без этого блог-пост = "цифры с потолка". С этим — research.

---

## 9. Cost transparency

Total inference cost каждого run **публикован** в `/runs/[hash]`.

**Зачем:**
1. Честность с читателем
2. Credibility (вот сколько стоит это исследование)
3. Помогает другим оценить cost воспроизведения

---

## 10. Sponsored evaluations protocol

См. 07-onboarding-flows.md, Flow 5.

Ключевые принципы:
- **Всегда disclosed** (badge на странице модели)
- **Полная информация** в `/disclosures`
- **Никаких изменений в methodology** для sponsored
- Sponsored = быстрее, **не лучше**

Это спасает от scandal по типу LMSYS leaderboard illusion (paper 2025 показал что vendors могли влиять на rankings).

---

## 11. API rate limiting & fair use

**Защита от scraping** через Cloudflare:
- Public unauthenticated: 100 req/hour per IP
- Tier 1 ($50/mo): 10 000 req/hour
- Tier 1 ($500/mo): 100 000 req/hour + bulk datasets

**Bulk download** — только через `/datasets` (raw Parquet files), не через scraping API.

---

## 12. Operational transparency

`/status` показывает:
- Last run timestamp
- Next scheduled run
- Current health each worker по регионам
- Uptime statistics

Если что сломалось — **публичный postmortem** в `/blog`.

---

## 13. Multilingual support (v2)

**MVP:** все промпты задач только английский.

**v2:** multilingual задачи — отдельная категория (русский, китайский, испанский) с native-speaker judges. Это для **версии 2**, не для MVP.

---

## 14. Disclosure of conflicts (для Eli лично)

Eli ведёт ForgePlan. Stack `claude-code + forgeplan` будет evaluated рядом с конкурентами.

**Обязательно disclosed:**
- На странице того стека: "POLLMEVALS оператор является разработчиком ForgePlan"
- "Методология калибрована независимо"
- "Третий-сторон review TBD"

Это спасает от обвинений в bias.

---

## 15. Anti-bot для community vote

- **GitHub OAuth обязательно**
- Аккаунту минимум **6 месяцев + 10 contributions**
- Это убирает spam без надоедливого captcha

---

## 16. Sunset policy

Deprecated модели:
- Остаются в database с пометкой "deprecated" + дата
- Их **данные сохраняются** для historical context
- **Не отвергать** → не нарушать citation тех кто ссылался

---

## 17. Backup & disaster recovery

- **Postgres** daily snapshot в R2
- **Raw outputs** в R2 уже redundant (multi-zone)
- **Open replica** на HuggingFace Datasets обновляется weekly с лагом — если домен/инфра умерла, public архив сохранится

---

## 18. Self-bias for maintainers (Eli's role)

Поскольку Eli является и автором задач, и оператором POLLMEVALS — есть риск self-bias.

**Mitigation:**
- Open-source все задачи и evaluators
- Community challenges на каждую задачу
- 3rd party review (попросить независимого инженера прогнать pipeline и проверить)
- Public methodology — каждое решение задокументировано и justifiable

---

## 19. Maintenance overhead

Реалистичная оценка времени на maintenance после MVP launch:

- **Weekly run baby-sitting:** 2-4 часа (проверка что run прошёл, alert investigation)
- **Community moderation:** 1-3 часа (review proposals, manual quality checks)
- **Blog post weekly:** 4-6 часов (от анализа результатов до публикации)
- **Bug fixes / improvements:** 5-10 часов

**Итого ~15-25 часов в неделю** только на operate. Это **половина full-time job**.

Это нужно знать на старте — иначе burnout через 2-3 месяца.

---

## 20. Decision log

В отдельном файле `/methodology/decisions.md` — **immutable log** всех методологических решений:

```markdown
## 2026-05-21 — Решение использовать Krippendorff α (не Fleiss kappa)

**Контекст:** judges дают continuous scores, не categorical
**Decision:** использовать Krippendorff α с interval distance
**Rationale:** Krippendorff обрабатывает missing data и continuous scores
**Authors:** [E. Maintainer]
**Reviewers:** [TBD third-party review]
```

Это и для credibility, и для будущих maintainers — понимать "почему делали так".
