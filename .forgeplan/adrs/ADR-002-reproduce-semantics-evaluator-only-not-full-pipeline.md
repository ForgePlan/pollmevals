---
depth: standard
id: ADR-002
kind: adr
last_modified_at: 2026-05-24T10:18:44.224372+00:00
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

## Invariants

For this decision to remain valid, ALL of the following must stay true:

- `make reproduce` (implemented in `infra/scripts/reproduce-local-run.sh`) NEVER invokes any LLM API call — it reads only from `artifacts/` (local) or `r2://runs/{run_hash}/` (production). Any code path that calls `litellm.completion()` or `inspect_ai.eval()` inside the reproduce script violates this invariant.
- `artifact_refs` in every published `EvalRow` carry SHA256-pinned URIs for `raw_output` — the reproducer depends on content addressing, not mutable paths. If the artifact storage schema changes (SPEC-001), the sha256 field must be preserved.
- Deterministic fields in `evaluator_json` are explicitly enumerated and frozen per methodology version (v0.1.0 in `docs/02-methodology/`). Transient fields (`timestamp`, `eval_uuid`, token-level IDs) are excluded from the diff. This exclusion list must be documented in `docs/04-runbook/` and enforced in the reproduce script before the first smoke run.
- The reproduce outcome proves only **evaluator determinism**, not LLM determinism. Any documentation, README, or runbook that claims reproduce proves end-to-end determinism is incorrect and must be corrected before publishing.
- LLM drift detection (week-over-week Δ on baseline tasks) is a **separate concern** from reproduce and must never be conflated with SC-2 in PRD-001 wording.

## Rollback Plan

If this decision is reversed (e.g., a future LLM API genuinely guarantees byte-equal output and full-pipeline reproduce becomes meaningful):

1. **Update SC-2 wording in PRD-001** to explicitly include LLM re-call in the reproduce contract. This requires a new forgeplan evidence artifact (`evidence_type: measurement`) proving the specific model+provider combination is byte-equal across N runs.
2. **Add `--full` flag to `infra/scripts/reproduce-local-run.sh`**: extend the script to accept `--full` flag that re-calls the LLM via `litellm` using the pinned `model_id`, `prompt`, and `seed` from the manifest. Gate with `--yes` confirmation to prevent accidental cost spend.
3. **Update SPEC-001** manifest schema to add `reproduce_mode: "evaluator-only" | "full-pipeline"` field so runs are self-describing.
4. **Create a new ADR** superseding this one, linking the measurement EVID and explaining the changed LLM-API guarantee.
5. **Do NOT silently change `make reproduce` behaviour** without the above steps — any change without a new ADR violates the audit trail requirement (docs/adr/0002-run-immutability.md).

## Affected Files

Files directly implementing or constrained by this decision:

- `infra/scripts/reproduce-local-run.sh` — primary reproduce entrypoint; must never invoke LLM APIs; currently a stub (`python -m pollmevals_eval_core.demo_run ...`) — full implementation in Phase 2B
- `apps/eval-core-py/src/orchestrator/eval_caller.py` — `EvalRequest` / `EvalResult` dataclasses carry the fields reproduce reads (`eval_id`, `model_id`, `task_id`, `seed`, artifact URIs)
- `apps/eval-core-py/src/orchestrator/journal.py` — `JournalWriter` appends `EvalRow` records that reproduce reads back via `JournalPath`; the `manifest.journal.ndjson` file is the input source for the reproducer
- `packages/db/migrations/` — `evals` table `artifact_refs` JSONB column stores sha256-pinned URIs; schema must preserve this field across migrations
- `packages/contracts/` — JSON Schema for `EvalRow` / `ArtifactRef` / `EvalArtifactRefs` types; `raw_output` URI field is load-bearing for reproduce
- `docs/02-methodology/` — frozen v0.1.0 methodology defines the "deterministic fields" exclusion list for evaluator_json diff
- `docs/04-runbook/12-first-smoke-run-playbook.md` — references reproduce semantics; must be updated to reflect evaluator-only scope before smoke run
- `Makefile` — `make reproduce` target; must never add `--full` flag without a new ADR

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


