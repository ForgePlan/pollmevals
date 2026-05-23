---
depth: standard
id: ADR-002
kind: adr
last_modified_at: 2026-05-23T19:26:08.778769+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-001
  relation: refines
status: active
title: reproduce semantics — evaluator-only, not full-pipeline
---

# ADR-002: reproduce semantics — evaluator-only, not full-pipeline

## Status

draft (proposed)

## Context

PRD-001 SC-2 требует: «Скоринг детерминистичен → score variance при reproduce = 0 на deterministic полях». Это критерий публикации smoke run и базис доверия к leaderboard.

Существует **фундаментальная неоднозначность** в слове «reproduce»:

| Interpretation A: Evaluator-only | Interpretation B: Full-pipeline |
|---|---|
| `reproduce` загружает cached raw_output, прогоняет evaluator → diff evaluator_json | `reproduce` re-call LLM с тем же model+seed+prompt → новый raw_output → evaluator → diff |
| Доказывает: evaluator детерминирован для same input | Доказывает: вся pipeline (LLM API включая) детерминирована |
| Реалистично: 100% achievable | Реалистично: невозможно — LLM API недетерминирован даже с seed |

Без явного решения первый же `make reproduce` упадёт (Interpretation B) или будет интерпретирован неконсистентно между разработчиками.

ADI-разбор PRD-001 (`forgeplan reason`) явно выделил это как риск, требующий ADR. Hypothesis H2 утверждала, что «архитектура LLM nondeterminism сломает SC-2», и evidence_needed предложила: «запустить reproduce дважды для одного промпта, чтобы проверить»  — что именно и есть exposed ambiguity.

## Decision Drivers

- **Reality check**: LLM API (Claude, GPT, Gemini) НЕ гарантируют byte-equal output даже с seed — провайдеры могут silently апдейтить, batch'и в floats накапливают rounding, temperature=0 не панацея. Это конфирмировано HELM (EVID-001) и LM Harness (EVID-003) — оба используют cached output для reproduce.
- **What SC-2 actually buys us**: если evaluator детерминирован, это доказывает (а) absence of bugs в evaluator logic, (б) absence of accidental state в evaluator process (random seeds, system time, env vars). Это полезное доказательство.
- **What full-pipeline reproduce would buy us** (если бы было реалистично): доказательство стабильности LLM API. Это **отдельный** интересный вопрос, но он покрывается через 3 seeds внутри одного run (variance) и через drift detection в weekly cadence (Δ vs previous run).
- **Prior art**: HELM `scenario_state.json`, LM Harness `--use_cache` SQLite — оба выбрали Interpretation A. Это de-facto industry standard для serious eval platforms (EVID-001, EVID-003).
- **Reproducer cost**: Interpretation B re-calls 45 LLM evals на каждый reproduce → дополнительные $5-50 за прогон + ~30 min wall clock. Interpretation A — 0 LLM cost, < 1 минута wall clock.

## Considered Options

### Option A: Evaluator-only reproduce

```bash
make reproduce HASH=<run_hash> EVAL_ID=<eval_id>
# → reads manifest, loads raw_output from artifact_refs (sha256-pinned)
# → invokes evaluator(raw_output, gold) → new evaluator_json
# → diff against original evaluator_json on deterministic fields
# → exit 0 if diff == 0, exit 2 otherwise
```

- **Pros**: Реализуемо; matches HELM/LM Harness convention; быстро; дёшево; чётко формулирует ЧТО proves.
- **Cons**: НЕ proves stability LLM API (но это и не задача reproduce'а — это задача drift detection).

### Option B: Full-pipeline reproduce (re-call LLM)

- **Pros**: Доказывает end-to-end consistency.
- **Cons**: Невозможно в принципе — LLM API недетерминирован. SC-2 окажется constantly failing. Cost prohibitive.

### Option C: Hybrid — evaluator-only по умолчанию, optional `--full-pipeline` flag

```bash
make reproduce HASH=X EVAL_ID=Y           # default: Option A
make reproduce HASH=X EVAL_ID=Y --full    # Option B as opt-in diagnostic
```

- **Pros**: Best of both — main path работает; diagnostic-mode available для investigation drift.
- **Cons**: Doubles surface area; `--full` будет редко использоваться (cost prohibitive); maintenance overhead.

## Decision Outcome

**Chosen: Option A — Evaluator-only reproduce**

`make reproduce` НИКОГДА не re-calls LLM. Работает исключительно с cached raw_output (sha256-pinned в artifact_refs).

Rationale:
1. **Industry-aligned**: HELM и LM Harness — оба major eval platforms — используют этот pattern (EVID-001, EVID-003).
2. **Реально доказуемо**: 0% chance, что Option B когда-либо даст diff = 0 → SC-2 будет constantly failing.
3. **Cost-efficient**: $0 для каждого reproduce, < 1 минута.
4. **Чётко формулирует claim**: «evaluator детерминирован», not «LLM детерминирован».
5. **Орthogonal к drift detection** (которая covered through 3 seeds + weekly Δ).

Option C отвергнут — `--full` flag в реальности никогда не будет работать (по причинам Option B), это false advertising.

**Wording для documentation и PRD-001 SC-2 needs to be clarified**: «Reproducing one eval from manifest yields byte-equal evaluator_json on deterministic fields (excluding timestamps, token UUIDs, и любых других transient ID)».

## Consequences

### Positive
- ✅ SC-2 measurably achievable: 100% target reachable на первом smoke run
- ✅ Reproducer fast (<1 min) и cheap ($0) — низкий friction для разработчиков и methodology reviewer'ов
- ✅ Чёткое разделение concerns: reproduce = evaluator determinism, drift = LLM stability
- ✅ Aligns с EVID-001 (HELM `scenario_state.json`) и EVID-003 (LM Harness `--use_cache`)
- ✅ ADR-0002 (run immutability) и этот ADR rein-force each other — cached raw_output IS the immutable artifact

### Negative
- ❌ Не получает evidence про LLM stability через reproduce — нужны **отдельные measurements**: variance через 3 seeds, drift через weekly Δ
- ❌ User-expectation management: «reproduce» в общем lay-meaning может включать LLM re-call — нужна documentation что это НЕ делает
- ❌ Если evaluator имеет hidden nondeterminism (например, `dict` iteration order до Python 3.7 fix), он будет caught — но это и есть полезная функция

### Neutral
- PRD-001 SC-2 wording must be refined в next revision (clarify "deterministic fields" exclusion list)
- Future ADR may add `--full-pipeline` flag если когда-нибудь LLM APIs guarantee реальный определителизм (unlikely, but possible с reasoning-tier models или specialized eval endpoints)

## Compliance

- Соответствует PRD-001 SC-2 (with refined wording)
- Соответствует ADR-0002 (run immutability — raw_output is the immutable evidence)
- Соответствует RFC-001 § Reproduce semantics
- Diverges from naive "reproduce = re-run everything" interpretation — необходимо документировать в `docs/04-runbook/` postmortem template

## Links

- PRD-001 SC-2 — refined wording dependency
- RFC-001 — implementation lives there
- EVID-001 (HELM `scenario_state.json` precedent)
- EVID-003 (LM Harness `--use_cache` precedent)
- ADR-0002 legacy (run immutability — foundation)
- Future Note or ADR: drift detection methodology (separate concern from reproduce)





