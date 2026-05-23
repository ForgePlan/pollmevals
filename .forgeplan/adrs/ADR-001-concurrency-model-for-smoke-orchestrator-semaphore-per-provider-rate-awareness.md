---
depth: standard
id: ADR-001
kind: adr
last_modified_at: 2026-05-23T19:25:19.512324+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-001
  relation: refines
status: active
title: concurrency model for smoke orchestrator (semaphore + per-provider rate awareness)
---

# ADR-001: concurrency model for smoke orchestrator (semaphore + per-provider rate awareness)

## Status

draft (proposed)

## Context

POLLMEVALS smoke run выполняет 45 evals (3 tasks × 5 models × 3 seeds) через 5 моделей с разными провайдерами и rate limits. Inspect AI (EVID-004) sам не управляет concurrency между параллельными `inspect_eval()` invocations — это ответственность caller'а.

Без явного решения:
- Полная параллельность (45 одновременных HTTP calls) → rate limits → много failed evals → degraded smoke baseline (per PRD-001 ADI risk #1).
- Последовательно (1 в момент) → smoke run занимает ~30+ минут (LCM от 5 min per eval × 45 evals).

Цель: завершить 45 evals за разумное время (target ≤ 1 hour wall clock), без потери > 5% evals из-за rate limit.

## Decision Drivers

- **Provider диверситет**: 5 моделей через OpenRouter — каждый upstream-провайдер (Anthropic, OpenAI, Google, Cerebras, Runpod vLLM) имеет независимые rate limits. OpenRouter сам proxies, но per-key burst limit OpenRouter-side тоже существует.
- **Cost cap (NFR-001 PRD-001)**: $50 budget — нужна fast feedback loop для cost polling и abort.
- **Failure isolation (FR-009 PRD-001)**: одна failed eval не должна блокировать остальные.
- **Simplicity для solo maintainer**: distributed job queue overkill для 45 evals.
- **Production-readiness debt**: что мы выберем здесь, перенесётся в PRD-003 weekly run (1000+ evals).

## Considered Options

### Option A: Global asyncio.Semaphore(N), N=3

```python
SEMAPHORE = asyncio.Semaphore(3)

async def run_one_eval(task, model, seed):
    async with SEMAPHORE:
        return await inspect_eval(task, model=model, ...)

await asyncio.gather(*coros, return_exceptions=True)
```

- **Pros**: 5 строк кода; asyncio.gather дает встроенный fan-out; `return_exceptions` сохраняет failed evals (FR-009 satisfied).
- **Cons**: одинаковая concurrency для всех моделей — Claude Sonnet может tolerate 5+ parallel, Llama 4 70B на одном Runpod GPU — только 1-2.
- **Cost**: free.

### Option B: Per-provider semaphores (asyncio + dict)

```python
SEMAPHORES = {
    "anthropic": asyncio.Semaphore(5),
    "openai": asyncio.Semaphore(5),
    "google": asyncio.Semaphore(3),
    "cerebras": asyncio.Semaphore(2),
    "runpod": asyncio.Semaphore(1),  # bottleneck
}

async def run_one_eval(task, model, seed):
    provider = model.split("/")[0]
    async with SEMAPHORES[provider]:
        return await inspect_eval(...)
```

- **Pros**: respecting provider-specific limits; Llama 4 не блокирует Claude evals.
- **Cons**: hardcoded numbers без empirical evidence; per-model tuning потребуется в первом же weekly run.
- **Cost**: free.

### Option C: Distributed job queue (Celery + Redis)

- **Pros**: production-grade; nat. scales to PRD-003 weekly run; built-in retry policy.
- **Cons**: Massive overkill для 45 evals; добавляет Redis dep + Celery worker process; debugging async distributed bugs длинее MVP timeline.
- **Cost**: +1 day infrastructure setup; +1 service Docker; ongoing operational overhead.

### Option D: LiteLLM proxy native rate limiting + parallelism=∞ on orchestrator side

- **Pros**: один source of truth (proxy); orchestrator stays dumb.
- **Cons**: LiteLLM proxy rate-limit features экспериментальны; rejection logic возвращает HTTP 429 в orchestrator anyway — нужно повторно retrying там; complexity moves, не исчезает.
- **Cost**: free, но debt-shifted.

## Decision Outcome

**Chosen: Option A — Global asyncio.Semaphore(N), N=3**

Для smoke v0.1 это правильный choice потому что:
1. **Простота** — solo maintainer, 45 evals, debugability важнее tuning.
2. **N=3** — empirically безопасное число для большинства provider rate limits (на основе reading OpenRouter docs).
3. **Path to Option B** — миграция = заменить `SEMAPHORE` на `SEMAPHORES[provider_of(model)]` — 5 строк кода, без архитектурных изменений.

`MAX_CONCURRENT_EVALS=3` стартовая константа в `apps/eval-core-py/src/orchestrator/grid_runner.py`. Если первый smoke run показывает >10% failed evals из-за rate_limit → bump к 2 (не 5), затем переход к Option B при weekly run.

LiteLLM proxy остается responsibility'у inter-provider routing + per-key burst limit, но НЕ за orchestrator-side concurrency.

## Consequences

### Positive
- ✅ Реализация занимает <1 hour
- ✅ `asyncio.gather(*..., return_exceptions=True)` satisfies PRD-001 FR-009 (failed evals stored)
- ✅ Cost-polling loop работает в parallel — orchestrator может abort run при 80% budget
- ✅ Прямой path к Option B без переписывания

### Negative
- ❌ Возможны rate_limit failures на самом слабом провайдере (Runpod vLLM с 1 GPU) — будут видны в первом smoke postmortem
- ❌ N=3 не оптимизирован — Claude evals могут идти 5 одновременно безопасно, мы артифициально ждём
- ❌ Tuning переносится в Phase 2 (smoke postmortem)

### Neutral
- При переходе к weekly run (PRD-003) — обязательно переход на Option B или Option C
- Concurrency решение влияет на total wall clock → influences NFR-002 (latency budget per eval); если smoke run > 1 hour, revisit это ADR

## Compliance

- Соответствует PRD-001 FR-009 (failed evals stored), NFR-002 (per-eval timeout 5 min)
- Соответствует RFC-001 § Concurrency strategy
- Не противоречит ADR-0002 immutability (concurrency не влияет на artifact storage semantics)

## Links

- RFC-001 — uses this concurrency choice
- PRD-001 — parent requirement
- EVID-004 (Inspect AI) — confirms Inspect не managing concurrency for parallel `eval()` invocations




