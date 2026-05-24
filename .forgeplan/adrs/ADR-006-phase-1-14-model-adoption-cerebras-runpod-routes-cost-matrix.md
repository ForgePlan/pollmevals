---
depth: standard
id: ADR-006
kind: adr
last_modified_at: 2026-05-24T22:59:46.161469+00:00
last_modified_by: claude-code/2.1.150
links:
- target: ADR-003
  relation: refines
- target: NOTE-005
  relation: informs
status: draft
title: Phase 1 14-model adoption — Cerebras + Runpod routes + cost matrix
---

# ADR-006: Phase 1 14-model adoption — Cerebras + Runpod routes + cost matrix

## Status

draft (proposed) — refines ADR-003

## Context

ADR-003 fixed the **v0.1 smoke** lineup at 5 models (Claude Sonnet 4.6, GPT-5 mini, Gemini 3 Flash, Qwen 3 14B, Llama 3.3 70B) — all 5 routed through OpenRouter (one via HF router for Qwen) for cost-attribution simplicity. Smoke pipeline proven 2026-05-24 (45/45 evals, $0.067, EVID-024).

NOTE-005 Section E identifies the **Phase 1 baseline radar gap**: `docs/old/dd.md` lines 832-844 + 869-886 specified **14 models across 3 providers** (Cerebras for fast open-weight, Runpod vLLM for big self-host, OpenRouter for closed APIs) for the weekly Phase 1 run (14 models × 20 tasks × 5 seeds). The smoke lineup of 5 satisfies pipeline validation but is insufficient for the Phase 1 baseline:

- **5/14 models** wired (Sonnet 4.6, GPT-5 mini, Gemini 3 Flash, Qwen 3 14B, Llama 3.3 70B)
- **9 models missing**: Claude Opus 4.7, GPT-5 (full), Gemini 2.5 Pro, Grok 4, DeepSeek V3.5, Qwen3 32B (Cerebras), GLM-4.7 (Cerebras), gpt-oss-120B (Cerebras), Qwen 2.5 72B (Runpod vLLM)
- **3 providers** required (current config = 2: OpenRouter + HF router); Cerebras direct + Runpod vLLM endpoints absent from `infra/litellm-config.yaml`

Forces:

- **Speed/cost frontier coverage**: dd.md thesis ("cheap+scaffolding beats expensive raw") requires the full price spread $0.05/Mtok (Cerebras Llama) → $75/Mtok (Claude Opus output) — currently flat at $0.10-15/Mtok range.
- **Provider redundancy**: closed-API silent drift (Claude/GPT/Gemini) is the #1 anti-gaming concern (NOTE-005 Section I); Cerebras open-weight provides independent reproducibility anchor (open weights + pinned version tag).
- **Cerebras free-tier 1M tokens/day**: zero-cost validation runs for smoke gating before paid weekly grid (estimated $30-80/week at 14×20×5 = 1400 evals).
- **Library-first**: per CLAUDE.md + commit 5d4b432, `litellm.cost_per_token()` is the source of truth for pricing — handles Cerebras/OpenRouter/Runpod uniformly; no hardcoded `_MODEL_PRICING` keys needed for new routes.
- **Routing diversity vs cost-attribution complexity**: 3 separate provider keys (`CEREBRAS_API_KEY`, `RUNPOD_VLLM_API_BASE`, `OPENROUTER_API_KEY`) raises ops burden but ADR-003's single-OpenRouter-key constraint is incompatible with dd.md's 14-model lineup.

Frozen v0.1.0 methodology (`docs/02-methodology/`) is unaffected — this ADR adds models, does not modify scoring formulas or judge policy. Manifest contract (SPEC-001 `model_pins`) already supports arbitrary `provider_route_id` strings.

## Decision Drivers

- **dd.md fidelity** — Phase 1 baseline must exercise full 14-model matrix to validate cost-quality Pareto (PRD-004 leaderboard goal).
- **Cerebras free-tier** — 1M tokens/day = ~50-80 free smoke evals on open-weight tier; reduces cost gate before Cerebras paid tier engagement.
- **Provider failure isolation** — if OpenRouter is degraded at run time (ADR-003 § Negative), 9 of 14 models still reachable via Cerebras + Runpod direct.
- **Self-host validation** — Runpod vLLM is the only path to Qwen 2.5 72B (not hosted by Cerebras as of 2026-05-25); validates `hosted_vllm/` Inspect AI provider path (EVID-004).
- **Cost ceiling discipline** — per-model pricing in manifest enforces NFR-001 $50 hard budget (cost.py); new providers must report token counts compatible with `litellm.completion_cost()`.
- **Routing flexibility for Llama 3.3 70B** — Cerebras serves Llama 3.3 70B at ~10-20× OpenRouter speed (1500-3000 tok/s vs 80-150 tok/s); dual-route allows Cerebras primary + OpenRouter fallback.

## Considered Options

### Option A: Three-provider split (CHOSEN)

Cerebras direct (4 routes) + Runpod vLLM (1 route) + OpenRouter (9 routes, includes Llama 3.3 70B fallback).

- **Pros**: Matches dd.md Phase 1 lineup exactly; Cerebras free-tier supports zero-cost smoke iteration; 10-20× speedup on open-weight; redundancy on Llama via dual-route; per-provider failure isolation.
- **Cons**: 3 API keys in `.env` (CEREBRAS_API_KEY, RUNPOD_VLLM_API_BASE+RUNPOD_VLLM_API_KEY, OPENROUTER_API_KEY); per-provider rate-limit + spend tracking complexity; Runpod GPU spin-up adds 2-5 min cold-start to first call.
- **Cost estimate**: $30-80 per weekly run (14 models × 20 tasks × 5 seeds = 1400 evals; ~70% mass on OpenRouter closed APIs at $0.50-15/Mtok output; Cerebras paid tier ~$0.10-0.50/Mtok open-weight; Runpod $3-6/run amortized over the 72B share).

### Option B: All-through-OpenRouter (uniform)

Route all 14 models via OpenRouter regardless of native provider.

- **Pros**: Single API key; single rate-limit surface; uniform pricing via OpenRouter; matches ADR-003 invariant ("All five models routed through OpenRouter").
- **Cons**: OpenRouter doesn't host Cerebras-only models (GLM-4.7, gpt-oss-120B not on OR as of EVID-019); ~5.5% OpenRouter markup over vendor-direct; loses Cerebras 10-20× speedup; loses Runpod self-host reproducibility anchor; loses free-tier validation path.
- **Verdict**: rejected — Cerebras-only models not available, breaks 14-model coverage.

### Option C: Direct vendor APIs (no OpenRouter)

Route closed APIs directly (Anthropic, OpenAI, Google, xAI, DeepSeek) + Cerebras direct + Runpod vLLM. 7 separate API keys.

- **Pros**: Saves 5.5% OpenRouter markup; direct vendor support for edge features (e.g., Anthropic prompt caching).
- **Cons**: 7 API keys to provision, rotate, and budget-cap separately; loses OpenRouter aggregated cost reporting; ADR-003 already standardized on OpenRouter for closed models — switching now requires new ADR + re-wiring 5 working routes; vendor-direct rate-limits stricter than OpenRouter pooled.
- **Verdict**: rejected — disrupts working smoke setup for marginal 5.5% savings; would require new ADR superseding ADR-003 (not refining).

## Decision Outcome

Chosen option: **Option A — Three-provider split**.

Justification: matches dd.md Phase 1 spec; preserves ADR-003 OpenRouter-for-closed pattern (refines, not supersedes); Cerebras free-tier provides essential zero-cost iteration loop for smoke validation before paid weekly run; Runpod is the only path to Qwen 2.5 72B; per-provider failure isolation reduces ADR-003 § Negative single-vendor risk. Per ADI synthesis on NOTE-005 (gemini-3.1-pro-preview, confidence High), this targets the documented 36% model-coverage gap without artifact bloat (one new ADR refining one existing ADR).

### Routing matrix — 14 models

| Model | Primary provider | Fallback | LiteLLM `model_name` alias | `litellm_params.model` (primary) | Env key |
|---|---|---|---|---|---|
| Claude Opus 4.7 | OpenRouter | — | `claude-opus-4-7` | `openrouter/anthropic/claude-opus-4.7` | `OPENROUTER_API_KEY` |
| Claude Sonnet 4.6 | OpenRouter | — | `claude-sonnet-4-6` (existing) | `openrouter/anthropic/claude-sonnet-4.6` | `OPENROUTER_API_KEY` |
| GPT-5 (full) | OpenRouter | — | `gpt-5` | `openrouter/openai/gpt-5` | `OPENROUTER_API_KEY` |
| GPT-5-mini | OpenRouter | — | `gpt-5-mini` (existing) | `openrouter/openai/gpt-5-mini` | `OPENROUTER_API_KEY` |
| Gemini 2.5 Pro | OpenRouter | — | `gemini-2-5-pro` | `openrouter/google/gemini-2.5-pro` | `OPENROUTER_API_KEY` |
| Gemini 3 Flash | OpenRouter | — | `gemini-3-flash` (existing) | `openrouter/google/gemini-3-flash-preview` | `OPENROUTER_API_KEY` |
| Grok 4 | OpenRouter | — | `grok-4` | `openrouter/x-ai/grok-4` | `OPENROUTER_API_KEY` |
| DeepSeek V3.5 | OpenRouter | — | `deepseek-v3-5` | `openrouter/deepseek/deepseek-v3.5` | `OPENROUTER_API_KEY` |
| Llama 3.3 70B | Cerebras | OpenRouter | `llama-3-3-70b` (existing — re-route to Cerebras primary) | `cerebras/llama3.3-70b` | `CEREBRAS_API_KEY` |
| Qwen3 32B | Cerebras | — | `qwen3-32b` | `cerebras/qwen-3-32b` | `CEREBRAS_API_KEY` |
| GLM-4.7 | Cerebras | — | `glm-4-7` | `cerebras/glm-4.7` | `CEREBRAS_API_KEY` |
| gpt-oss-120B | Cerebras | — | `gpt-oss-120b` | `cerebras/gpt-oss-120b` | `CEREBRAS_API_KEY` |
| Qwen 2.5 72B | Runpod vLLM | — | `qwen-2-5-72b` | `hosted_vllm/Qwen/Qwen2.5-72B-Instruct` (api_base = `RUNPOD_VLLM_API_BASE`) | `RUNPOD_VLLM_API_KEY` |
| Qwen 3 14B (smoke) | HF router | OpenRouter | `qwen-3-14b` (existing) | `openai/Qwen/Qwen3-14B` (api_base = `https://router.huggingface.co/v1`) | `HF_TOKEN` |

LiteLLM provider prefix syntax confirmed via Context7 (`/websites/litellm_ai`, 2026-05-25):

- `cerebras/<model>` with `api_key: os.environ/CEREBRAS_API_KEY` — Cerebras direct provider (LiteLLM provider id confirmed).
- `hosted_vllm/<model>` with `api_base: os.environ/RUNPOD_VLLM_API_BASE` + `api_key: os.environ/RUNPOD_VLLM_API_KEY` — OpenAI-compatible vLLM endpoint pattern.

### Smoke vs weekly scope split

- **Smoke (PRD-001, ADR-003)** — remains 5 models (`SMOKE_MODELS`); no change. Pipeline validation, not Pareto coverage.
- **Phase 1 weekly (PRD-003)** — full 14 models, new constant `WEEKLY_MODELS` in `grid_runner.py`. Grid = 14 × 20 × 5 = 1400 evals.
- Both lists are source-of-truth from this ADR; `_PROXY_ALIAS_TO_LITELLM_MODEL` mapping in `scripts/smoke_run.py` extends to 14 aliases (covers both smoke and weekly).

### Cost matrix (estimated per 1M output tokens — basis for budget caps)

| Model | $/Mtok output (est.) | Source / verification path |
|---|---|---|
| Claude Opus 4.7 | $75 | OpenRouter listing snapshot; verify via `litellm.cost_per_token()` at run time |
| Claude Sonnet 4.6 | $15 | OpenRouter; verified EVID-024 |
| GPT-5 (full) | $30 | OpenRouter listing; verify |
| GPT-5-mini | $0.60 | OpenRouter; verified EVID-024 |
| Gemini 2.5 Pro | $10 | OpenRouter; verify |
| Gemini 3 Flash | $0.30 | OpenRouter; verified EVID-024 |
| Grok 4 | $15 | OpenRouter listing; verify |
| DeepSeek V3.5 | $0.40 | OpenRouter listing; verify |
| Llama 3.3 70B (Cerebras paid) | $0.85 | Cerebras pricing page; verify |
| Qwen3 32B (Cerebras paid) | $0.60 | Cerebras pricing page; verify |
| GLM-4.7 (Cerebras paid) | TBD | Cerebras pricing page; verify at integration time |
| gpt-oss-120B (Cerebras paid) | $0.50 | Cerebras pricing page; verify |
| Qwen 2.5 72B (Runpod H100) | ~$3/hr GPU → est. $0.30-0.50/Mtok amortized | Runpod pricing page + token throughput measurement |
| Qwen 3 14B (HF router) | $0.10 | EVID-019 measured |

**All numbers verified at run time** by `litellm.cost_per_token()` (commit 5d4b432); table above is planning estimate only. Numbers marked TBD are filled in by EVID at first paid call.

## Consequences

### Positive

- 14-model Phase 1 baseline radar matches dd.md spec, unblocking PRD-003 weekly grid scope.
- Cerebras free-tier (1M tok/day) enables zero-cost smoke validation loop before paid weekly engagement.
- Provider failure isolation: single-vendor outage degrades at most 9/14 models (OpenRouter) or 4/14 (Cerebras) or 1/14 (Runpod), never blocks full grid.
- 10-20× faster open-weight inference via Cerebras (1500-3000 tok/s vs 80-150 tok/s OpenRouter) — lowers weekly run wall-clock.
- Pricing transparency: `litellm.cost_per_token()` resolves Cerebras and Runpod uniformly with OpenRouter (Library-first invariant 2026-05-25).
- Refines ADR-003 without breaking smoke (ADR-003 5-model lineup unchanged; only Llama route changed primary from OpenRouter → Cerebras with OpenRouter fallback).

### Negative

- Three API keys in operational rotation (`CEREBRAS_API_KEY`, `RUNPOD_VLLM_API_KEY`, `OPENROUTER_API_KEY`) — secret-management surface tripled.
- Per-provider rate-limit tracking required in orchestrator (ADR-001 semaphore-per-provider must add Cerebras + Runpod buckets).
- Runpod cold-start: 2-5 min GPU spin-up on first call after idle — first eval per worker on Qwen 2.5 72B slower.
- Cerebras free-tier exhaustion mid-run: if 1M tok/day cap hit during smoke, route silently fails (Cerebras returns 429); orchestrator must surface 429 as `error_class=rate_limit` and degrade-mode-defer per ADR-003 rollback pattern.
- Runpod endpoint URL hardcoded into `RUNPOD_VLLM_API_BASE` — if endpoint URL changes (Runpod pod restart), `.env` update required; not a config.yaml hot-reload.
- Cost matrix above is planning estimate; actual `litellm.cost_per_token()` numbers may drift up to 30% (per Trust Calculus below) before LiteLLM pricing table refreshes.

### Neutral

- Smoke `SMOKE_MODELS` unchanged; only weekly grid expands.
- Frozen v0.1.0 methodology unaffected (scoring + judge policy depend on model count, not provider mix).
- Judge panel diversity strengthens with 14 models — judges can be chosen from 5+ vendor families with no self-judging conflicts (PRD-002 SC-1).

## Invariants

For this decision to remain valid, ALL of the following must stay true:

- All 14 `model_name` aliases in `infra/litellm-config.yaml` exactly match the `_PROXY_ALIAS_TO_LITELLM_MODEL` mapping keys in `apps/eval-core-py/scripts/smoke_run.py`. Any divergence breaks alias resolution at run start.
- `WEEKLY_MODELS` constant in `apps/eval-core-py/src/orchestrator/grid_runner.py` lists exactly these 14 aliases. `SMOKE_MODELS` remains the 5-model subset per ADR-003.
- Cerebras free-tier (1M tokens/day) is used **only** for validation/smoke runs. Production weekly grid uses Cerebras paid tier — config flag `CEREBRAS_BILLING_MODE=paid` enforces in orchestrator.
- Per-model `provider_route_id` in `manifest.model_pins` reflects the route actually used at run time (Cerebras OR OpenRouter for Llama 3.3 70B fallback case), not the planned primary. Manifest immutability (ADR-002) requires the actual route, not the intent.
- `litellm.cost_per_token()` is the single source of truth for cost reconciliation per `_make_pricing_snapshot` (commit 5d4b432). No hardcoded prices in this ADR's cost matrix are loaded into runtime config.
- The 9 new routes do not alter ADR-003 smoke contract — `SMOKE_MODELS` stays 5, smoke runs deterministic per ADR-002.
- Llama 3.3 70B dual-route: Cerebras primary, OpenRouter fallback resolved at run start (one route active per run, recorded in manifest); not load-balanced mid-run.

## Rollback Plan

If this decision is reversed (Cerebras instability, Runpod cost overrun, ops complexity too high):

1. **Cerebras free-tier rate-limit hit during smoke**: drop to OpenRouter for the affected open-weight model. Update `litellm-config.yaml` route to OpenRouter prefix; remove from Cerebras `model_list` entries; no orchestrator code change. Record EVID with rate-limit incident details.
2. **Runpod vLLM unstable / endpoint flapping**: replace Qwen 2.5 72B with Llama 3.1 70B on Cerebras (similar 70B-class capacity). Update `WEEKLY_MODELS`, `litellm-config.yaml`, and create new EVID documenting the swap. Does not require new ADR — fallback pre-approved here.
3. **OpenRouter degraded for closed APIs**: switch to direct vendor APIs (Anthropic, OpenAI, Google, xAI). Requires 4 new env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `XAI_API_KEY`); requires new ADR superseding Option B of this ADR (Option C is the pre-rejected target, but trigger conditions differ).
4. **Cerebras paid pricing changes >2×**: weekly cost estimate drift triggers refresh — capture in EVID + update `cost matrix` table here via `forgeplan update`. If sustained, supersede this ADR with re-pricing decision.
5. **Full revert to 5-model**: if Phase 1 weekly is descoped, revert `WEEKLY_MODELS` to mirror `SMOKE_MODELS`; deprecate this ADR with `--reason "Phase 1 weekly grid descoped"`.

## Affected Files

Files directly constrained by this 14-model routing decision (this ADR documents the mapping; the orchestrator / next coder applies the config — no .yaml edits in this ADR session):

- `infra/litellm-config.yaml` — 9 new `model_list` entries (Opus 4.7, GPT-5 full, Gemini 2.5 Pro, Grok 4, DeepSeek V3.5, Qwen3 32B, GLM-4.7, gpt-oss-120B, Qwen 2.5 72B); 1 update (Llama 3.3 70B primary → Cerebras with OpenRouter fallback comment).
- `apps/eval-core-py/src/orchestrator/grid_runner.py` — new `WEEKLY_MODELS: list[str]` constant of 14 aliases; `SMOKE_MODELS` unchanged.
- `apps/eval-core-py/scripts/smoke_run.py` — `_PROXY_ALIAS_TO_LITELLM_MODEL` mapping extended to 14 entries.
- `.env.example` — add placeholders: `CEREBRAS_API_KEY=`, `RUNPOD_VLLM_API_BASE=` (e.g., `https://<pod-id>-8000.proxy.runpod.net/v1`), `RUNPOD_VLLM_API_KEY=`.
- `docs/02-methodology/judge-policy.md` — informational update: judge panel selectable from 14-model pool (no policy change; PRD-002 self-judging guard already covers).
- `apps/eval-core-py/src/orchestrator/cost.py` — verify `litellm.cost_per_token()` resolves new Cerebras + Runpod aliases; if any return None, extend `_FALLBACK_PRICING_PER_MTOKEN` only after EVID measurement (no planning estimates in fallback).
- `apps/eval-core-py/src/orchestrator/grid_runner.py` (ADR-001 semaphore section) — add `cerebras` and `runpod` semaphore buckets alongside existing `openrouter` and `hf` buckets.

## Trust Calculus per claim

Per NOTE-002 evidence quality standard, F-G-R scoring for load-bearing claims:

| Claim | F (Fact) | G (Generalization) | R (Replicability) | Sum | Source / Notes |
|---|:---:|:---:|:---:|---|---|
| Cerebras delivers 1500-3000 tok/s on open-weight models | 8 | 8 | 8 | 24/27 | Cerebras public benchmarks + Inference API docs; reproducible via direct API ping |
| Runpod vLLM H100 at $3/hr ≈ $0.30-0.50/Mtok amortized on Qwen 2.5 72B | 7 | 7 | 6 | 20/27 | Runpod pricing page + projected token throughput; not yet measured under POLLMEVALS load |
| OpenRouter markup ≈ 5.5% over vendor direct | 9 | 9 | 9 | 27/27 | OpenRouter public fee schedule; verifiable per-call via headers |
| `litellm.cost_per_token()` resolves Cerebras + Runpod aliases | 8 | 8 | 8 | 24/27 | LiteLLM provider docs (Context7 verified 2026-05-25); fallback path exists for unknown aliases |
| Per-Mtok cost matrix accurate within 30% drift before LiteLLM pricing refresh | 8 | 8 | 7 | 23/27 | `litellm.cost_per_token()` auto-updates per Library-first invariant (commit 5d4b432); `_FALLBACK_PRICING_PER_MTOKEN` covers unknown aliases |
| Cerebras free-tier = 1M tokens/day | 8 | 9 | 9 | 26/27 | Cerebras public terms; verifiable via dashboard quota |
| Qwen 2.5 72B not hosted by Cerebras as of 2026-05-25 | 7 | 7 | 8 | 22/27 | Cerebras model list inspection; subject to Cerebras catalog updates |

## Related Decisions

- ADR-003 — refined by this ADR (model lineup extended from 5 smoke → 14 weekly; ADR-003 5-model smoke contract unchanged).
- ADR-001 — concurrency model (semaphore-per-provider extended with Cerebras + Runpod buckets).
- ADR-002 — run immutability (manifest `provider_route_id` records actual route used; no in-place edits).
- ADR-005 — judge aggregation (judge panel diversity strengthened with 14 models in pool).
- NOTE-005 — Section E gap (informs this ADR; coverage matrix tracked here).
- NOTE-002 — evidence quality standard (F-G-R scoring used in Trust Calculus above).
- PRD-001 — smoke run (unchanged; this ADR does not modify smoke scope).
- PRD-003 — weekly cadence (this ADR scopes the model dimension; PRD-003 owns scheduling/cron).

## References

- `docs/old/dd.md` lines 832-844 + 869-886 — original 14-model lineup spec.
- `infra/litellm-config.yaml` — current 5-model config (to extend).
- `apps/eval-core-py/src/orchestrator/grid_runner.py:335-341` — `SMOKE_MODELS` constant.
- `apps/eval-core-py/scripts/smoke_run.py:_PROXY_ALIAS_TO_LITELLM_MODEL` — alias→LiteLLM mapping.
- Context7 LiteLLM docs (`/websites/litellm_ai`, 2026-05-25) — `cerebras/` and `hosted_vllm/` provider prefix syntax.
- EVID-019 — OpenRouter smoke (qwen-3-14b not on OR, HF router resolution).
- EVID-024 — first real smoke run (45/45 evals, $0.067; confirms `litellm.cost_per_token()` path).
- Commit 5d4b432 — Library-first cost API swap (`litellm.cost_per_token`).
- ADI synthesis on NOTE-005 (gemini-3.1-pro-preview, confidence High) — recommends consolidating model gap into single ADR refining ADR-003.

## Compliance

- Compatible with PRD-001 § Models (5 smoke unchanged).
- Compatible with RFC-001 § Model selection (extends via WEEKLY_MODELS).
- Compatible with EPIC-001 outcome #3 (Pareto frontier — full cost spread $0.10 to $75/Mtok delivered).
- Compatible with EVID-004 (Inspect AI `hosted_vllm/` provider routing format).
- Compatible with ADR-002 (manifest immutability — actual route recorded).
- Reduces EPIC-001 risk ER-1 (single-vendor dependency — now 3 vendors).
- Refines ADR-003 (does not supersede — smoke contract preserved).



