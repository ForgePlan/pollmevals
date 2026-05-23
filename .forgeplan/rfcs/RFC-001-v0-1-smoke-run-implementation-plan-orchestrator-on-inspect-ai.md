---
depth: standard
id: RFC-001
kind: rfc
last_modified_at: 2026-05-23T20:56:23.048256+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: SPEC-001
  relation: based_on
status: active
title: v0.1 smoke run — implementation plan (orchestrator on Inspect AI)
---

# RFC-001: v0.1 smoke run — implementation plan (orchestrator on Inspect AI)

## Summary

POLLMEVALS smoke run v0.1 реализуется как **тонкая Python-обёртка вокруг Inspect AI**, добавляющая 3 слоя, которых нет в upstream: (1) hard run immutability (SHA256 + chmod 0444 + R2 object-lock), (2) per-eval cost attribution (pricing snapshot × token counts), (3) leaderboard hygiene (Krippendorff α calc в PRD-002, contamination flags). Concurrency — `asyncio.Semaphore(3)`; reproduce — **evaluator-only**, без re-call LLM. Crash recovery — append-only journal + `make resume` (per NOTE-001). 5 моделей через OpenRouter, 3 задачи, 3 seeds = 45 evals, budget ≤ $50, eu-central.

## Motivation

Без явного выбора в трёх точках smoke run обречён на failures:

1. **Concurrency**: ADI-разбор PRD-001 (`forgeplan reason`) показал, что без лимитов orchestrator упадёт на rate limits Llama 4 70B; SC-3 покажет много failed evals и degraded baseline.
2. **Reproduce semantics**: SC-2 требует «score variance = 0 при reproduce». Если интерпретировать буквально (полный pipeline вкл. LLM API), это **невозможно** — LLM API недетерминирована даже с seed (EVID-001 HELM, EVID-003 LM Harness). Нужен явный wording: «детерминизм evaluator'а на cached output».
3. **Build vs buy**: писать orchestrator с нуля — 2-3 недели; Inspect AI (EVID-004) уже даёт Task/Solver/Scorer/multi_scorer/epochs из коробки.

Без этого RFC код будет писаться по неявным предположениям; первая ревизия будет переписана.

## Context

PRD-001 ставит цель: 45-eval grid (3 tasks × 5 models × 3 seeds) на `raw-llm` stack, automatic metrics only, $50 budget, reproducible manifest. SPEC-001 определяет contracts. Этот RFC отвечает на **КАК** реализовать.

EVID-001..005 (HELM, MTEB, LM Harness, Inspect AI, SWE-bench) дают prior art. Особо ценны: HELM `scenario_state.json` и LM Harness `--use_cache` — оба используют evaluator-only reproduce pattern; Inspect AI L0-L8 mapping — позволяет переиспользовать всё, кроме cost attribution и hard immutability.

NOTE-001 фиксирует crash recovery strategy. EVID-007 фиксирует findings architect-reviewer и их remediation.

## Proposed approach

### Architecture (3 слоя)

```
┌─────────────────────────────────────────────────┐
│  POLLMEVALS Orchestrator (apps/eval-core-py/)   │
│  ─────────────────────────────────────────────  │
│  • Immutability envelope (SHA256, R2 push)      │
│  • Cost attribution (pricing × tokens)          │
│  • Manifest writer (POLLMEVALS schema)          │
│  • Crash recovery (journal + atomic rename)     │
│  • Reproducibility envelope (run config)        │
└────────┬────────────────────────────┬───────────┘
         │                            │
         ▼                            ▼
┌────────────────────┐      ┌──────────────────┐
│  Inspect AI core    │      │  LiteLLM proxy   │
│  ────────────────   │      │  ──────────────  │
│  • Task / Solver    │      │  • Model routing │
│  • Scorer / multi_  │      │  • Rate limit    │
│  • EvalLog (.eval)  │      │  • Budget cap    │
│  • epochs=3 (seeds) │      │  • Cost log API  │
└────────────────────┘      └──────────────────┘
```

POLLMEVALS не реализует Inspect-эквивалент с нуля — оборачивает Inspect и добавляет **то, чего у Inspect нет** (per EVID-004): hard immutability + cost attribution + leaderboard hygiene + crash recovery.

### Inspect AI mapping для smoke

Каждый stack = одна Inspect `Task`. `raw-llm` stack в Python:

```python
from inspect_ai import Task, task
from inspect_ai.solver import generate

@task
def raw_llm_be_01_jwt_auth():
    return Task(
        dataset=load_task_pack("be_01_jwt_auth"),
        solver=[generate()],
        scorer=[automatic_evaluator_be_01()],
        epochs=3,
        name="raw-llm/be_01_jwt_auth",
        version="0.1.0",
        metadata={"stack_id": "raw-llm", "stack_sha256": "...", "task_pack_sha256": "...", "methodology_version": "v0.1.0"}
    )
```

POLLMEVALS orchestrator invokes `inspect_ai.eval()` programmatically через `EvalCaller` Protocol (testability seam per architect finding #4).

### Decision points (вынесены в ADR)

| ADR | Решение |
|-----|---------|
| **ADR-001** Concurrency | Semaphore `MAX_CONCURRENT_EVALS=3` global + per-provider rate-limit через LiteLLM proxy |
| **ADR-002** Reproduce | Evaluator-only: `make reproduce` НЕ re-call LLM, работает на cached raw_output |
| **ADR-003** Model selection v0.1 | 5-model lineup — Claude Sonnet 4.6, GPT-5 mini, Gemini 3 Flash, Qwen 3 14B (Cerebras), Llama 4 70B (Runpod) |

### Concurrency strategy (per ADR-001)

```python
SEMAPHORE = asyncio.Semaphore(3)

class EvalCaller(Protocol):
    async def call(self, task, model: str, seed: int) -> EvalResult: ...

class InspectEvalCaller:
    async def call(self, task, model, seed):
        async with SEMAPHORE:
            return await inspect_eval(
                task, model=f"openrouter/{model}",
                log_dir="artifacts/inspect-logs/",
                epochs=1, seed=seed,
                max_retries=2, timeout=300,
            )

async def run_grid(caller: EvalCaller, tasks, models, seeds):
    coros = [caller.call(t, m, s) for t in tasks for m in models for s in seeds]
    return await asyncio.gather(*coros, return_exceptions=True)
```

`return_exceptions=True` — критично для PRD-001 FR-009. `EvalCaller` Protocol — тестируемый seam (per architect finding #4).

### Reproduce semantics (per ADR-002)

`make reproduce HASH=<run_hash> EVAL_ID=<eval_id>` → orchestrator читает manifest, загружает raw_output из artifact_refs (не re-call LLM), прогоняет evaluator на этом тексте, сравнивает evaluator_json с original. Разница на deterministic полях (исключая timestamps, token UUIDs) MUST быть 0.

### Crash Recovery (per NOTE-001)

Append-only `manifest.journal.ndjson` + atomic rename + `make resume HASH=<x>` command. Покрывает: mid-eval crash, between-eval-completion-and-journal-write, mid-aggregating, mid-rename. Не покрывает (deferred PRD-003): multi-process distributed coordination, cross-machine resume, concurrent resume locking.

Implementation:
- Каждый завершённый eval → `f.write(json.dumps(row) + "\n"); f.flush(); os.fsync(f.fileno())` в `manifest.journal.ndjson`.
- `manifest.json` writes только дважды: переход → `aggregating` и переход → `published`/`degraded`. Atomic rename из `.tmp`.
- `make resume`: load journal, diff vs expected grid (model × task × seed combinations from run_hash inputs), schedule missing eval_ids only.

### Error handling taxonomy (SPEC-001 enum)

| error_class | When | Retry? |
|---|---|---|
| `network` | TCP/DNS failure | Yes, 2× exponential backoff |
| `rate_limit` | HTTP 429 | Yes, respect Retry-After |
| `5xx_server` | HTTP 500-599 | Yes, 1 retry |
| `4xx_client` | HTTP 400-499 (excl 429) | No, fail-fast |
| `timeout` | > 300s wall clock | No |
| `contract_violation` | output schema mismatch | No |
| `sandbox_failure` | Docker/Inspect sandbox crash | No |

### Cost attribution layer

```python
pricing_snapshot = fetch_openrouter_pricing(model_ids)  # at run start, cached 1h

cost = (
    eval_stats.input_tokens * pricing_snapshot[model].input_per_mtoken / 1e6
    + eval_stats.output_tokens * pricing_snapshot[model].output_per_mtoken / 1e6
)

total = sum(e.stats.cost_usd for e in evals)
assert total <= 50.0, f"Budget exceeded: ${total:.2f}"  # NFR-001
```

LiteLLM proxy cost log cross-check — alert (stderr + take higher of two + continue per architect finding #8) если delta > 10%.

### Manifest write order (atomicity — расширено NOTE-001)

```
1. Run created → manifest.journal.ndjson initialized; status=created (in-memory)
2. Pre-flight passes → status=executing (in-memory)
3. Per-eval: append to journal.ndjson (fsync); on completion of all → status=evaluating (in-memory)
4. Aggregates computed → manifest.json.tmp written → atomic rename → manifest.json with status=aggregating (on disk)
5. Validate manifest against schema → manifest.json.tmp updated → atomic rename → manifest.json with status=published (or degraded) → chmod 0o444
```

Crash detection: на старте `make smoke-run`, если `manifest.json` существует с status != published/degraded → suggest `make resume`.

## Alternatives considered

### Alt 1: Write our own orchestrator without Inspect AI
- **Pros**: No external dep.
- **Cons**: ~2-3 weeks duplicating Solver/Scorer/multi_scorer. EVID-004 L0-L8 maps cleanly.
- **Decision**: Rejected.

### Alt 2: Use lm-evaluation-harness as base
- **Pros**: Wider model adapter coverage.
- **Cons**: EVID-003 — model-focused, не stack-focused.
- **Decision**: Rejected.

### Alt 3: SWE-bench's harness model (Docker-per-instance)
- **Pros**: Battle-tested для backend coding.
- **Cons**: EVID-005 — per-instance Docker, hard to layer scaffolding.
- **Decision**: Borrow только gold-test-suite-in-Docker pattern для `be_01_jwt_auth` evaluator (Inspect's `sandbox` field).

## Invariants

Что НИКОГДА не нарушается этим RFC:

1. **Failed evals NEVER dropped from denominator** — даже rate_limit / timeout / sandbox_failure storeятся в `evals[]` с `error_class`.
2. **`make reproduce` NEVER calls LLM API** — это по ADR-002 эквивалентно «доказательству детерминизма evaluator'а», а не LLM.
3. **`pricing_snapshot` taken ONCE at run start** — никакой mid-run обновления.
4. **`status: published` is terminal** — после публикации никакие in-place mutations не разрешены (file mode 0444, R2 object-lock).
5. **Methodology version pinned per run** — `methodology_version: "v0.1.0"` неизменна для всего lifetime run'а.
6. **`manifest.journal.ndjson` is append-only** — entries never modified, никогда rewritten in place (per NOTE-001).

## Rollback Plan

Если RFC implementation fails в Phase 2 (T+1..T+2 weeks):

| Failure mode | Rollback action |
|--------------|-----------------|
| Inspect AI breaking change → eval() API не работает | Pin к previous compatible version; create new ADR |
| Concurrency=3 → still hitting rate limits | Lower к 2 или 1; degraded performance, не блокирует smoke |
| Cost attribution OFF (LiteLLM proxy down) | Mark все evals' `cost_usd = null`; run goes to `degraded`; orchestrator publishes с пометкой |
| Manifest schema validation fails on completed evals | Roll back к `manifest.journal.ndjson` (still valid); revisit SPEC-001 |
| Reproduce script returns non-zero diff | Investigate per-field: evaluator nondeterminism (Python random, timestamps unfiltered) — fix evaluator |
| Crash recovery (`make resume`) loses an eval | Journal entries are independent — surviving entries still scored; only missing eval rerun |

**Worst case**: smoke даёт 0 published runs но 45 attempted evals с полными artifacts stored — postmortem использует raw data; RFC переоткрывается в новой ревизии.

**Cannot rollback**: published manifest. По ADR-0002 published runs never edited; если данные неправильные → новый run + supersedes link.

## Trade-offs

| Trade-off | Choice |
|-----------|--------|
| Build vs buy orchestrator | Buy (Inspect AI) + thin wrapper |
| Single-process vs distributed | Single-process for smoke; distributed только когда weekly run >1000 evals (carried-forward assumption per architect finding #5) |
| Async vs sync orchestrator | Async (asyncio.gather + semaphore) — required для cost cap polling |
| Manifest format | JSON Schema + Pydantic v2 + journal NDJSON для crash recovery |
| Reproduce strategy | Evaluator-only (ADR-002) — matches HELM, LM Harness; CRITICAL для SC-2 |
| Crash recovery storage | NDJSON journal (debuggable, append-only) — не SQLite WAL (см. NOTE-001 § Why not более сложно) |

## Implementation tasks (granular)

1. `apps/eval-core-py/pyproject.toml` — depend on `inspect-ai==0.3.46` **exact** (per RR-1), `pydantic>=2.0`, `httpx`, LiteLLM proxy Docker
2. `apps/eval-core-py/src/contracts/` — Pydantic models matching SPEC-001
3. `apps/eval-core-py/src/inspect_tasks/` — 3 `@task` functions (1 stack × 3 tasks для smoke)
4. `apps/eval-core-py/src/evaluators/` — 3 automatic evaluators; be_01 use Docker sandbox **pinned by digest** (per RR-4)
5. `apps/eval-core-py/src/orchestrator/eval_caller.py` — `EvalCaller` Protocol + `InspectEvalCaller` impl (testability seam per architect finding #4)
6. `apps/eval-core-py/src/orchestrator/grid_runner.py` — asyncio.gather + semaphore using `EvalCaller`
7. `apps/eval-core-py/src/orchestrator/cost.py` — pricing snapshot + per-eval cost
8. `apps/eval-core-py/src/orchestrator/journal.py` — append-only journal writer (per NOTE-001)
9. `apps/eval-core-py/src/orchestrator/manifest.py` — writer + state machine + atomic rename
10. `apps/eval-core-py/src/orchestrator/reproduce.py` — load manifest + raw_output → re-run evaluator → diff
11. `apps/eval-core-py/src/orchestrator/resume.py` — load journal, diff vs expected grid, schedule missing
12. `apps/eval-core-py/src/orchestrator/aggregates.py` — compute `RunAggregates` per SPEC-001 inline def
13. `Makefile`: `smoke-run`, `reproduce`, `resume`, `validate-tasks`
14. `infra/scripts/validate-task-specs.py` — **fix orphan import** `pollmevals_eval_core.registry` (per architect finding #9)
15. `infra/scripts/litellm-proxy-up.sh` — Docker compose с healthcheck (per architect finding #10)
16. `evals/task-packs/{be_01_jwt_auth,fe_01_multistep_form,doc_01_cli_readme}/` — finalize prompt + gold + evaluator
17. `apps/eval-core-py/tests/` — pytest: evaluator determinism, manifest schema, error_class taxonomy, **grid runner failure-propagation** (per architect finding #4)

## Acceptance Criteria

| ID | Scenario |
|----|----------|
| AC-1 | Given 5 models × 3 tasks × 3 seeds, when `make smoke-run`, then 45 evals attempted with `MAX_CONCURRENT_EVALS=3`; failed evals stored with error_class |
| AC-2 | Given completed run, when `make reproduce HASH=X EVAL_ID=Y`, then evaluator re-runs on cached raw_output (NO LLM call); diff on deterministic fields = 0 |
| AC-3 | Given run start, when LiteLLM proxy returns running cost ≥ $40 (80% budget), then orchestrator stops scheduling new evals; in-flight complete; status → `degraded` with reason; alert to stderr + take higher of two cost sources |
| AC-4 | Given Inspect EvalLog written, when orchestrator wraps into manifest, then `inspect_eval_log_sha256` matches `sha256sum inspect.eval` |
| AC-5 | Given any 4xx_client error_class, when orchestrator retries, then 0 retries attempted (fail-fast taxonomy) |
| AC-6 | Given orchestrator crash mid-eval, when `make resume HASH=<x>`, then journal loaded, missing eval_ids identified, only those re-scheduled |
| AC-7 | Given a grid runner unit test, when 1 of 5 coroutines raises, then 5 manifest rows produced with the failing one's `error_class` populated (testability per architect finding #4) |

## Risks

| ID | Risk | P | I | Mitigation |
|----|------|---|---|------------|
| RR-1 | Inspect AI breaking change in `eval()` API между pin и реальностью | L | H | Pin `inspect-ai==0.3.46` **exact** в pyproject.toml; regression test с их fixtures |
| RR-2 | OpenRouter pricing API rate-limits snapshot fetch | L | L | Cache pricing для 1 hour локально; pre-flight подтверждает свежесть |
| RR-3 | LiteLLM proxy cost log lags real cost by >1 min → budget breach | M | M | Cross-check с OpenRouter `/credits` API; pessimistic estimate (higher of two); alert to stderr per architect finding #8 |
| RR-4 | `be_01_jwt_auth` Docker sandbox без correct Node version → false test failures | M | M | **Pin Docker image by digest (not tag)** per architect finding #5 (SWE-bench EVID-005); pre-flight: gold solution → must pass |
| RR-5 | Gemini 3 Flash silently changes между smoke и reproduce | M | L | reproduce uses cached raw_output (ADR-002) — drift captured в next weekly run, не блокирует smoke |
| RR-6 | Orchestrator process crash → manifest in intermediate state | M | M | NOTE-001 crash recovery: journal + atomic rename + `make resume` |
| RR-7 | `.eval` binary format bumps between Inspect versions, breaks downstream readers | L | L | POLLMEVALS treats `.eval` as opaque (per architect finding #6); only SHA256 cross-ref; needed fields projected into manifest at publish time |

## Related Artifacts

- PRD-001 (parent — refines)
- SPEC-001 (contracts — based_on)
- ADR-001 (concurrency — extends)
- ADR-002 (reproduce semantics — extends)
- ADR-003 (model selection — extends)
- NOTE-001 (crash recovery — informs § Crash Recovery)
- EVID-001..005 (prior art — informs)
- EVID-007 (architect-reviewer findings — directly informs this revision)
- EPIC-001 (grandparent)



