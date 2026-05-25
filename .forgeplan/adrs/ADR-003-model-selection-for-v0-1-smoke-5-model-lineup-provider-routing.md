---
depth: standard
id: ADR-003
kind: adr
last_modified_at: 2026-05-24T10:20:17.403116+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-001
  relation: refines
status: active
title: model selection for v0.1 smoke (5-model lineup + provider routing)
---

# ADR-003: model selection for v0.1 smoke (5-model lineup + provider routing)

## Status

draft (proposed)

## Context

PRD-001 требует «5 selected models» для smoke run — конкретный список не зафиксирован, оставлен на RFC stage. Выбор моделей определяет:
- Cost (от ~$1 до ~$15 за smoke run в зависимости от mix'а)
- Provider диверситет (если все 5 от Anthropic — нет judge panel diversity в Phase 3)
- Stack-evaluation thesis test (если все 5 — premium closed, не показываем «cheap + scaffolding > expensive raw»)
- Reproducibility (open-weight модели stable через checkpoints; closed APIs могут drift)

Выбор замораживается в manifest при run start (per SPEC-001 model_pins).

## Decision Drivers

- **Vendor diversity** для judge panels (PRD-002): минимум 3 vendor families (Anthropic, OpenAI, Google) чтобы судьи могли быть из разных origins.
- **Price tier coverage**: представить range $0.05/Mtoken (cheapest) до $15/Mtoken (premium) — чтобы Pareto frontier (PRD-004) имел meaningful spread.
- **Open vs closed**: тест POLLMEVALS thesis требует ≥2 open-weight моделей с реальным scaffolding потенциалом.
- **Provider stability**: Cerebras/Runpod — это новые провайдеры (2024-2026), нужно валидировать их в smoke перед commitment в weekly run.
- **OpenRouter as unified API**: per RFC-001 архитектура — всё через OpenRouter для cost-attribution simplicity (избегаем 5 разных API clients).
- **Anti-contamination**: per EVID-002 (MTEB) и EVID-003 (LM Harness) — модели, обученные на популярных public datasets, искажают результаты. Выбираем модели с pretrain-data документацией.

## Considered Options

### Option A: All-premium-closed (Claude Sonnet 4.6, GPT-5, Gemini 3 Pro, Claude Opus 4, GPT-5 Pro)

- **Pros**: Самая высокая baseline quality; vendor diversity для judges (3 families); reliable APIs.
- **Cons**: Cost ~$15-25 за smoke (избыточно для proof-of-pipeline); НЕ тестирует POLLMEVALS thesis (где cheap+scaffolding?); 0 open-weight models = leaderboard будет одностронним.
- **Estimated cost**: $20.

### Option B: All-cheap-mix (Gemini 3 Flash, GPT-5 mini, Claude Haiku 4.5, Qwen 3 14B, Llama 4 70B)

- **Pros**: Самая дешёвая (~$3 total); хорошее open/closed mix (3/2); все 5 — production-realistic для cost-conscious users.
- **Cons**: Нет «premium reference» — невозможно показать "cheap+scaffolding catches up с премиумом"; vendor diversity слабее (Claude Haiku и Sonnet — одна family).
- **Estimated cost**: $3.

### Option C: Balanced 5-model lineup — **CHOSEN**

| Slot | Model | Tier | Provider route | Why |
|---|---|---|---|---|
| Premium closed | Claude Sonnet 4.6 | High closed | `openrouter/anthropic/claude-sonnet-4-6` | Mainline reference; user already uses for Claude Code workflow; well-documented capabilities |
| Mid closed | GPT-5 mini | Mid closed | `openrouter/openai/gpt-5-mini` | Cost-effective OpenAI baseline; 3-vendor diversity for judges; widely used in production |
| Cheap closed | Gemini 3 Flash | Cheap closed | `openrouter/google/gemini-3-flash` | Cheapest large-context closed (Jan 2026); calibration for cost-frontier visualization |
| Open-weight fast | Qwen 3 14B | Open fast | `openrouter/cerebras/qwen-3-14b` | Cerebras hardware — extreme inference speed; tests "cheap open beats expensive closed" thesis |
| Open-weight large | Llama 4 70B | Open large | `openrouter/runpod/llama-4-70b` | Self-hosted reference; validates `hosted_vllm/` Inspect AI provider (EVID-004); represents enterprise self-host case |

- **Pros**: Покрывает цены $0.05 to $15/Mtoken; 3 vendor families (Anthropic, OpenAI, Google) для judge diversity; 2 open-weight models тестируют POLLMEVALS thesis; validates new providers (Cerebras, Runpod) до commitment в weekly.
- **Cons**: Чуть дороже Option B (~$5); один provider route может не работать в момент smoke (mitigation через FR-009 failed evals).
- **Estimated cost**: $5-8.

### Option D: 7-model lineup (extra Claude Opus 4 + extra Mistral)

- **Pros**: Больше data points.
- **Cons**: Smoke = 7 × 3 × 3 = 63 evals (+40% от 45 plan); cost $8-12; не нужен для proof-of-pipeline; больше rate-limit pressure для concurrency=3.
- **Decision**: Rejected. Сохраняем 5 для smoke; extras в weekly.

## Decision Outcome

**Chosen: Option C — Balanced 5-model lineup**

Frozen lineup для smoke v0.1:

```yaml
# stacks/raw-llm/stack.yaml + manifest.model_pins
models:
  - id: claude-sonnet-4-6
    provider_route: openrouter/anthropic/claude-sonnet-4-6
    tier: premium-closed

  - id: gpt-5-mini
    provider_route: openrouter/openai/gpt-5-mini
    tier: mid-closed

  - id: gemini-3-flash
    provider_route: openrouter/google/gemini-3-flash
    tier: cheap-closed

  - id: qwen-3-14b-cerebras
    provider_route: openrouter/cerebras/qwen-3-14b
    tier: open-fast

  - id: llama-4-70b-runpod
    provider_route: openrouter/runpod/llama-4-70b
    tier: open-large
```

**Pre-flight requirement** (per RFC-001 § Pre-flight check): перед запуском smoke выполнить 1 prompt против каждого provider_route'а. Если model X недоступна → 2 опции:
1. Отложить smoke до восстановления (если single failure)
2. Запустить в degraded mode с 4 models если провайдер down > 24h (mark в manifest status=degraded)

**Reproducibility note**: если closed-API модель silently апдейтится между smoke and weekly run, это будет detected через drift в weekly Δ (separate concern, to be addressed in ADR for PRD-003), НЕ через smoke reproduce (per ADR-002).

## Consequences

### Positive
- ✅ 3-vendor diversity (Anthropic, OpenAI, Google) готова к judge panels в Phase 3 без перевыбора моделей
- ✅ 2 open-weight models тестируют POLLMEVALS «cheap + scaffolding» thesis с первого smoke
- ✅ Cost spread $0.05 to $15/Mtoken даст visible Pareto frontier на leaderboard (PRD-004)
- ✅ Validates Cerebras и Runpod в low-stakes окружении до commitment в weekly
- ✅ Все 5 через single OpenRouter API — simplifies cost-attribution layer (RFC-001 § Cost)

### Negative
- ❌ Hard dependency на OpenRouter availability — если OpenRouter упадёт в момент smoke, run blocked. Mitigation: pre-flight check + manual fallback to direct vendor APIs (degraded mode)
- ❌ Llama 4 70B на Runpod — single GPU bottleneck, может быть slowest и triggert most failures. ADR-001 (concurrency=3) частично mitigates
- ❌ Lineup pinned для smoke — изменение моделей между smoke и weekly run = different manifest, different baseline. ОK для smoke proof-of-pipeline, но PRD-003 weekly должна re-evaluate model selection separately

### Neutral
- Этот lineup для **smoke only**. Weekly run (PRD-003) может расширить до 7-10 models — decision deferred to ADR for PRD-003
- Future model additions (Mistral, Cohere, Yi) — через отдельный ADR в weekly cadence, не через silent change в smoke
- Если pricing OpenRouter изменится для одной из моделей >2× между smoke и first weekly run — это flag для drift detection, не для re-selection

## Invariants

For this decision to remain valid, ALL of the following must stay true:

- The `SMOKE_MODELS` list in `apps/eval-core-py/src/orchestrator/grid_runner.py` must match the five `provider_route` values defined in this ADR exactly. Any divergence means the manifest's `model_pins` will not reflect the chosen lineup — a direct violation of run reproducibility (SPEC-001 § model_pins, ADR-0002).
- All five models are routed through **OpenRouter** (prefix `openrouter/`). Direct-vendor routes (e.g., `anthropic/claude-sonnet-4-6` without the `openrouter/` prefix) bypass unified cost-attribution and must not be used without a new ADR.
- The lineup contains exactly **3 closed-API models** (Anthropic, OpenAI, Google) and **2 open-weight models** (Cerebras-hosted Qwen, Runpod-hosted Llama) — this balance is load-bearing for the POLLMEVALS thesis test and for PRD-002 judge-panel vendor diversity.
- A **pre-flight check** (one prompt per provider_route) must execute before every smoke run invocation. Skipping the pre-flight and running a degraded 4-model grid without updating `manifest.status = "degraded"` violates the manifest contract (SPEC-001).
- Model selection for the **weekly run (PRD-003) is a separate decision** — this ADR governs smoke only. Any expansion of `SMOKE_MODELS` beyond these 5 entries requires a new ADR, not a silent edit to `grid_runner.py`.

## Rollback Plan

If this decision is reversed (e.g., Cerebras or Runpod are unavailable at smoke time, or cost estimates prove significantly wrong):

1. **Single provider failure (degraded mode)**: If one provider_route is down at smoke time, invoke `make smoke-run -- --degraded` which sets `manifest.status = "degraded"` and proceeds with 4 models. Update `SMOKE_MODELS` in `grid_runner.py` to remove the failing route. No new ADR needed for degraded-mode execution — it is pre-approved in the Decision Outcome above.
2. **Replace one model slot**: If a model must be permanently swapped (e.g., Runpod vLLM unavailable for >1 week), create a new forgeplan evidence artifact (`evidence_type: measurement`) documenting the failure, then update `SMOKE_MODELS` in `grid_runner.py` and the `models` block in `stacks/raw-llm/stack.yaml`. Create a new ADR superseding this one — do not silently edit.
3. **Revert to Option B (all-cheap)**: If cost overruns make the balanced lineup too expensive, replace the three closed models with cheaper tiers. This is a semantic change to the lineup requiring a new ADR. The weekly run decision is unaffected.
4. **Full lineup change**: Replace `SMOKE_MODELS` constant in `grid_runner.py`; update `stacks/raw-llm/stack.yaml` `base_model_slug`; update manifest schema `model_pins` block; create new ADR superseding this one; record EVID with the cost/availability evidence that drove the change.

## Affected Files

Files directly constrained by this model lineup decision:

- `apps/eval-core-py/src/orchestrator/grid_runner.py` — `SMOKE_MODELS` list (lines 335–341) must match this ADR's five `provider_route` strings exactly; `make_smoke_grid_spec()` factory uses this list
- `stacks/raw-llm/stack.yaml` — `base_model_slug: configurable` and `execution.command: litellm` confirm the stack is model-agnostic; the five model slugs are injected at run time via manifest `model_pins`
- `evals/tasks/be_01_jwt_auth/task.yaml`, `evals/tasks/fe_01_multistep_form/task.yaml`, `evals/tasks/doc_01_cli_readme/task.yaml` — task specs must be compatible with all 5 provider routes (no model-specific prompt engineering in smoke tasks)
- `packages/contracts/` — JSON Schema for `RunManifest.model_pins` must accommodate all 5 provider_route strings; schema validation fires at run-start before any LLM calls
- `docs/04-runbook/12-first-smoke-run-playbook.md` — references the 5-model lineup; must be kept in sync if lineup changes
- `Makefile` — `make smoke-run` and `make demo-run` targets use the model list via `grid_runner.py`; `make demo-run` currently uses fixtures, not live routes, but the route names must still match for manifest validation

## Compliance

- Соответствует PRD-001 § Models (5 selected)
- Соответствует RFC-001 § Model selection table
- Соответствует EPIC-001 outcome #3 (Pareto frontier — нужен cost spread)
- Совместимо с EVID-004 (Inspect AI `openrouter/provider/model` format)
- Снижает риск ER-1 EPIC-001 (vendor diversity для judges от Phase 3)

## Links

- PRD-001 — parent
- RFC-001 § Model selection table — implementation reference
- EPIC-001 — Phase 1 deliverable
- EVID-002 (MTEB contamination) — anti-contamination considerations
- EVID-004 (Inspect AI provider routing) — provider_route format
- Future ADR for PRD-003 — weekly run model selection (extend or revise this lineup)




