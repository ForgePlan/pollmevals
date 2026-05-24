---
depth: standard
id: PRD-001
kind: prd
last_modified_at: 2026-05-23T20:53:25.387193+00:00
last_modified_by: claude-code/2.1.150
links:
- target: EPIC-001
  relation: based_on
status: active
title: v0.1 smoke evaluation run
---

# PRD-001: v0.1 smoke evaluation run

## Executive Summary

### Vision

Доказать end-to-end работоспособность eval-пайплайна POLLMEVALS (validate → execute → score → manifest → reproduce) до того, как наслаивать судей, калибровку, лидерборд и публичный API.

### Problem

Платформа в состоянии v0.0 pre-launch: написана методология (frozen v0.1.0), контракты, документация, JSON-фикстуры — но **ни одного реального прогона не выполнено**. Все артефакты (`stacks/`, `evals/tasks/`, `apps/eval-core-py/`, `infra/scripts/`) остаются непроверенными гипотезами.

**Impact**: без smoke-прогона невозможно (а) валидировать гипотезу immutability (ADR-0002) на живых данных, (б) калибровать пайплайн затрат до решения про судей (5× стоимость на judge-panel), (в) построить честный baseline для weekly run cadence.

### Target Users

| Персона | Описание | Ключевая боль |
|---------|----------|---------------|
| Maintainer (gogocat) | Solo author, дальше масштабирует | Нет доказательства, что схема контрактов вообще запускается end-to-end |
| Methodology reviewer | Внешний рецензент перед v1.0 | Нужен reproducible artifact для критики |
| Future contributor | Заходит на проект через 1 квартал | Нужен живой пример: «вот так выглядит готовый Run» |

### Differentiators

- Smoke намеренно **без судей** — изолирует риск пайплайна от риска judge agreement.
- Manifest содержит достаточный контекст для воспроизведения evaluator'а на cached output (per ADR-002).
- Postmortem выходит в одну страницу — формат позже переиспользуется для weekly runs.

---

## Success Criteria

| ID | Criterion | Metric | Current | Target | Timeframe | How to Measure |
|----|-----------|--------|---------|--------|-----------|----------------|
| SC-1 | Все артефакты прогона на месте | missing artifacts | n/a (нет run) | 0 missing per eval | T+0 после run | `make reproduce HASH=<hash>` проходит для каждого eval_id |
| SC-2 | Evaluator детерминистичен на cached raw_output (per ADR-002) | byte-equal evaluator_json на deterministic полях (исключая timestamps, token UUIDs); reproduce работает на cached raw_output и **НЕ** re-calls LLM API | n/a | 0 diff | T+0 | `diff` evaluator_json исходного и reproduce-прогона на одном `(run_hash, eval_id)` |
| SC-3 | Каждая ошибка явно представлена | dropped evals from denominator | n/a | 0 (failed evals → stored с error_class, не выкинуты) | T+0 | Подсчёт `evals.status` в manifest |
| SC-4 | Cost под контролем | total inference cost | n/a | ≤ $50 (3×5×3=45 evals на raw-llm) | в момент прогона | LiteLLM proxy billing log cross-checked с OpenRouter `/credits` (RFC-001 § Cost) |
| SC-5 | Postmortem умещается в страницу | length | n/a | ≤ 1 markdown page (~80 строк) | T+1d | `wc -l docs/04-runbook/post/smoke-001.md` (генератор: следующая Tactical задача) |
| SC-6 | Manifest загружается reproducer'ом | reproduce script exit code | n/a | 0 | T+1d | `make reproduce HASH=<hash>` |

---

## Product Scope

### MVP (In-Scope)

- **Tasks**: `be_01_jwt_auth`, `fe_01_multistep_form`, `doc_01_cli_readme` (3 шт.)
- **Stack**: `raw-llm` only (L0 — bare LLM, без scaffolding)
- **Models**: 5 моделей через OpenRouter — **canonical lineup определён в ADR-003** (`adr-model-selection-for-v0-1-smoke-5-model-lineup-provider-routing`). Не дублировать имена здесь — single source of truth = ADR-003.
- **Seeds**: 3 на каждую (model, task) пару → 45 evals
- **Region**: `eu-central` only
- **Metrics**: только автоматические (test pass rate, lint, complexity, structural completeness for docs) — никаких LLM judges
- **Artifacts**: raw_output, normalized_output, evaluator_json, manifest. Локально на диск, content-addressed.
- **Crash recovery**: append-only `manifest.journal.ndjson` + `make resume HASH=<x>` (per NOTE-001).
- **Postmortem**: по шаблону в `docs/04-runbook/12-first-smoke-run-playbook.md` § Postmortem template.

### Out of Scope

- **Judges и JudgePanel** — методология есть, но включается отдельным PRD после smoke (PRD-002).
- **Calibration / Krippendorff α** — не имеет смысла без judges.
- **Leaderboard / публичный API** — фокус смещён к доказательству пайплайна (PRD-004).
- **Платные модели outside OpenRouter** (direct Anthropic/OpenAI) — добавим в weekly run, не в smoke.
- **Multi-region** — `eu-central` достаточно для smoke.
- **Sandbox runner (Rust)** — отложено по ADR-0001 legacy, smoke использует Python subprocess via Inspect AI's `sandbox`.
- **R2 / Cloudflare storage** — локальные артефакты в v0.1, R2 в v0.2+.
- **Multi-process distributed orchestrator** — single-process semaphore достаточен для 45 evals (см. NOTE-001 § Out of scope для weekly evolution path).

### Growth Vision

- Weekly run cadence по понедельникам 03:00 UTC после стабильного smoke (3+ smoke прогона подряд zero failed criteria) — PRD-003.
- Включение judges → расчёт Krippendorff α на той же сетке (judges layer поверх существующих evals) — PRD-002.
- Расширение grid: +stacks (`claude-code-basic`, `forgeplan-framework`), +регионы.

---

## Functional Requirements

| ID | Category | Priority | Requirement | Journey |
|----|----------|----------|-------------|---------|
| FR-001 | Core | Must | Maintainer can validate task specs against JSON Schema | Journey 1 |
| FR-002 | Core | Must | Maintainer can validate stack spec (`raw-llm`) против контракта | Journey 1 |
| FR-003 | Core | Must | Orchestrator can execute (model × task × seed) grid через LiteLLM proxy | Journey 1 |
| FR-004 | Core | Must | Orchestrator can store raw + normalized output as content-addressed artifacts | Journey 1 |
| FR-005 | Core | Must | Orchestrator can run automatic evaluator per task and store JSON result | Journey 1 |
| FR-006 | Core | Must | Orchestrator can aggregate per-eval scores into run-level summary (`RunAggregates` schema per SPEC-001) | Journey 1 |
| FR-007 | Core | Must | Orchestrator can write immutable manifest with hashes of all inputs/outputs | Journey 1 |
| FR-008 | Core | Must | Maintainer can reproduce single eval from manifest (`make reproduce HASH=...`) | Journey 2 |
| FR-009 | Core | Must | Orchestrator can store failed evals with error_class (не выкидывать из denominator) | Journey 1 |
| FR-010 | Reporting | Should | Maintainer can read 1-page postmortem from manifest + aggregated stats | Journey 2 |
| FR-011 | Reliability | Must | Maintainer can `make resume HASH=<x>` после orchestrator crash (per NOTE-001) | Journey 1 |

---

## Non-Functional Requirements

| ID | Category | Requirement | Metric | Condition | Measurement |
|----|----------|-------------|--------|-----------|-------------|
| NFR-001 | Cost | Total inference cost shall stay within budget | ≤ $50 | 45 evals on raw-llm | LiteLLM billing log cross-checked OpenRouter /credits |
| NFR-002 | Latency | Single eval shall complete within timeout | ≤ 5 min wall clock | per (model, task, seed) | orchestrator timeout enforcement |
| NFR-003 | Determinism | Re-running one eval from manifest shall yield identical evaluator_json fields | byte-equal на deterministic полях (excl timestamps, token UUIDs) | reproduce step | `diff` evaluator_json original vs reproduced |
| NFR-004 | Immutability | Once run is `published`, no DB row or artifact for it shall be mutated | 0 modifications post-publish | for life of run | file mode 0444 + R2 object-lock |
| NFR-005 | Reproducibility | Manifest shall capture all version pins (models, tasks, stacks, methodology, prompt hash, inspect_ai_version, orchestrator_version) | 100% полнота против контракта | в момент завершения run | schema validation on manifest (run-manifest.schema.json v1.0.0) |

---

## User Journeys

### Journey 1: Maintainer triggers and observes the smoke run

**Цель**: за один проход увидеть, что pipeline отрабатывает без ручных вмешательств.

| Шаг | Действие пользователя | Ответ системы | FR coverage |
|-----|----------------------|---------------|---------|
| 1 | `make validate-tasks` | exit 0 на 3 task specs + stack spec | FR-001, FR-002 |
| 2 | `make smoke-run RUN_TYPE=smoke` | стартует orchestrator, печатает run_hash | FR-003 |
| 3 | Наблюдает stream-логи | per-eval статусы (running / scored / failed); failed → с error_class | FR-009 |
| 4 | По завершении видит summary table | per-task aggregate score + cost + duration сохраняется в manifest | FR-004, FR-005, FR-006, FR-007 |
| 5 | (опционально, если crash) `make resume HASH=<x>` | reads journal, schedules missing evals | FR-011 |

**Результат**: maintainer имеет run_hash + manifest + полный набор artifacts на диске.

### Journey 2: Maintainer reproduces single eval + reads postmortem

**Цель**: убедиться в immutability и evaluator определенизме, прочитать compact отчёт.

| Шаг | Действие пользователя | Ответ системы | FR coverage |
|-----|----------------------|---------------|---------|
| 1 | `make reproduce HASH=<run_hash> EVAL_ID=<eval_id>` | загружает manifest, читает cached raw_output, перепрогоняет evaluator (НЕ LLM) | FR-008 |
| 2 | Сравнивает evaluator_json | `diff` показывает 0 различий на deterministic полях | NFR-003 |
| 3 | Читает postmortem | 1-страничный отчёт, готов для PR review | FR-010 |

**Результат**: подтверждение SC-6 (reproducer работает) и SC-2 (evaluator детерминизм).

---

## Dependencies

| Dependency | Type | Status | Owner |
|-----------|------|--------|-------|
| OpenRouter API key | External | Required (env: `OPENROUTER_API_KEY`) | maintainer |
| LiteLLM proxy | Internal | Spec exists, deployment не проверен | maintainer |
| JSON Schemas в `packages/contracts/` | Internal | `run-manifest.schema.json` aligned с SPEC-001 (v1.0.0) | maintainer |
| Methodology v0.1.0 frozen | Internal | ✅ Done (`docs/02-methodology/`) | — |
| Inspect AI `>=0.3.46` pinned exactly | External | Required per RFC-001 RR-1 | maintainer |
| Task fixtures в `evals/task-packs/` | Internal | Specified, gold solutions требуют проверки | maintainer |

---

## Related Artifacts

| Artifact | Relation | Status |
|----------|----------|--------|
| EPIC-001 | Parent epic | draft |
| SPEC-001 | Refines (manifest/eval/artifact contracts) | draft |
| RFC-001 | Implementation plan | draft |
| ADR-001 | Concurrency model | draft |
| ADR-002 | Reproduce semantics (canonical SC-2 wording) | draft |
| ADR-003 | Model selection (canonical 5-model lineup) | draft |
| NOTE-001 | Crash recovery strategy | draft |
| EVID-001..005 | Prior art (HELM, MTEB, LM Harness, Inspect AI, SWE-bench) | draft |
| EVID-006 | Guardian gate review | draft |
| EVID-007 | Architect-reviewer audit | pending |
| `docs/04-runbook/12-first-smoke-run-playbook.md` | Source of scope | active |
| `docs/02-methodology/scoring.md` | Frozen scoring formula | active v0.1.0 |
| `docs/adr/0002-run-immutability.md` (legacy) | Foundation для NFR-004 | active |

---

## Risks & Mitigations

| ID | Risk | Probability | Impact | Mitigation | Owner |
|----|------|-------------|--------|------------|-------|
| R-1 | Один из 5 провайдеров недоступен в момент прогона | Medium | Medium | Failed eval сохраняется с error_class (FR-009); не блокирует прогон. Postmortem явно фиксирует provider instability. | maintainer |
| R-2 | Inference cost превышает $50 (NFR-001) | Low | Medium | LiteLLM proxy с per-eval timeout 5 min; orchestrator считает running cost и аборtит на 80% бюджета (RFC-001 § Cost attribution). | maintainer |
| R-3 | Detected contamination (модель уже видела одну из 3 задач) | Medium | High | Smoke всё равно ценен — это baseline. Contamination check будет в weekly run (отдельный PRD per EVID-003 LM Harness findings). | maintainer |
| R-4 | Orchestrator crashes mid-run | Medium | Medium | NOTE-001 crash recovery strategy + `make resume HASH=<x>` | maintainer |
| R-5 | LiteLLM proxy не настроен корректно для всех 5 моделей | Medium | High | Step 4 плейбука («Check one prompt against each model») — pre-flight check до полного прогона. | maintainer |

---

## Affected Files

- `apps/eval-core-py/**` — orchestrator (создаётся в рамках RFC-001)
- `infra/scripts/validate-task-specs.py` — валидация task YAML (current state: имеет orphan import `pollmevals_eval_core.registry` — fix в Phase 2 первой задачей; per Architect finding #9)
- `infra/scripts/reproduce-local-run.sh` — reproducer (extends с journal recovery)
- `evals/task-packs/{be_01_jwt_auth,fe_01_multistep_form,doc_01_cli_readme}/` — fixtures
- `stacks/raw-llm/stack.yaml` — стек-адаптер
- `packages/contracts/schemas/run-manifest.schema.json` — JSON Schema **v1.0.0** (bumped 2026-05-23 to match SPEC-001 per architect finding #3)
- `packages/contracts/**` — JSON Schemas для manifest, eval, artifact
- `Makefile` — `smoke-run`, `validate-tasks`, `reproduce`, `resume` цели
- `docs/04-runbook/post/smoke-001.md` — postmortem (создаётся после прогона)

> **Next step**: после approve PRD-001 → guardian re-run → `forgeplan_activate PRD-001` (если PASS) → создать RFC-NNN или Tactical задачу для postmortem generator + stack-spec validator (FR-002, FR-010, SC-5).






