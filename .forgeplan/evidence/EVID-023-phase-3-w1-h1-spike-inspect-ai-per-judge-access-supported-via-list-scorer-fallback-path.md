---
depth: standard
id: EVID-023
kind: evidence
last_modified_at: 2026-05-24T19:41:40.825570+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-002
  relation: informs
- target: PRD-002
  relation: informs
status: draft
title: Phase 3 W1 H1 spike — Inspect AI per-judge access SUPPORTED via list-scorer fallback path
---

# EVID-023: Phase 3 W1 H1 spike — Inspect AI per-judge access SUPPORTED via list-scorer fallback path

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: test

## Context

Phase 3 Week 1 H1 spike per RFC-002 Slice B. Question: does Inspect AI's judge panel architecture expose per-judge `Score` objects individually (PRD-002 Q1, RFC-002 Slice B), or only an aggregated majority-vote result (refutation → ADR-006 pivot)?

Spike script: `infra/scripts/inspect_ai_h1_spike.py`. 1 sample (candidate: `gemini-3-flash`), 2 judges (`claude-sonnet-4-6-judge`, `gpt-5-mini-judge`) routed via LiteLLM proxy with `OPENROUTER_API_KEY_JUDGE` billing isolation per RFC-002 NFR-005.

Result: H1 **SUPPORTED** via fallback path. Per-judge access confirmed; RFC-002 Slice B proceeds as drafted with documented adjustments.

## ADI cycle

### Abduction — hypotheses (≥3)

- **H1**: Inspect AI's `multi_scorer(scorers=[...], reducer=...)` exposes per-judge Score objects in `sample.scores` as a dict, NOT only the reduced aggregate.
- **H2**: `multi_scorer()` returns only the reduced aggregate Score (majority-vote / mean / median); per-judge data is internal and inaccessible from outside the scorer.
- **H3**: `multi_scorer()` is broken or non-functional in the installed version; the only working path is passing a list of scorers directly to `Task(scorer=[...])`, which itself may or may not expose per-judge data.

### Deduction — observable predictions

- **H1 prediction**: `sample.scores` is `dict` with N entries (one per judge), each value is a `Score` object with distinct `explanation` text from that judge.
- **H2 prediction**: `sample.scores` is a single `Score` object OR a dict with exactly 1 entry corresponding to the reducer output. Per-judge data not accessible via documented API.
- **H3 prediction**: `multi_scorer()` raises a runtime error (registry / closure / signature mismatch) when used in `Task(scorer=multi_scorer(...))`. The list-of-scorers path produces `sample.scores` as dict with auto-assigned scorer names.

### Induction — evidence per prediction

Observed in spike run (commit `<see commit>`, `inspect_ai==0.3.46`, 2026-05-24 22:40:11+03:00 → 22:40:23+03:00):

| Prediction | Observed | Status |
|---|---|---|
| H1: dict with N=2 entries (one per judge) | `type(sample.scores) == dict`, len == 2, keys `['model_graded_qa', 'model_graded_qa1']`, each a `Score` object with distinct judge explanation | **CONFIRMED for fallback path** (list-of-scorers, NOT `multi_scorer()`) |
| H1 via documented `multi_scorer()` path | `multi_scorer()` returns unregistered closure; runtime crash `Object score does not have registry info` when used in `Task(scorer=...)` | **REFUTED for documented path** |
| H3: list-of-scorers path works; auto-assigned scorer names | Confirmed — Inspect AI assigns `'model_graded_qa'` to first scorer and appends incrementing suffix `'model_graded_qa1'`, `'model_graded_qa2'`, ... | CONFIRMED |
| Bonus prediction: judge `max_tokens` defaults to model native max (65k for Claude Sonnet) → can exhaust OpenRouter monthly budget | First run failed with HTTP 402 "requested up to 65536 tokens, can only afford 2537". Fix: `get_model(judge, config=GenerateConfig(max_tokens=512))`. Then run succeeded. | CONFIRMED (production hazard) |

Token usage from the successful run (single sample):

| Model | Input | Output | Total |
|---|---|---|---|
| `openai/gemini-3-flash` (candidate) | 17 | 1 | 18 |
| `openai/claude-sonnet-4-6-judge` | 249 | 57 | 306 |
| `openai/gpt-5-mini-judge` | 217 | 379 | 596 |
| **Total** | 483 | 437 | 920 |

Both judges scored `value='C'` (correct grading). Per-judge `explanation` text confirmed distinct (Claude vs GPT-5 mini wording differed).

### Surviving hypothesis

**H1 holds via the list-of-scorers fallback path documented in RFC-002 Slice B**. Documented `multi_scorer()` API is broken in `inspect_ai==0.3.46`. The fallback (pass a list to `Task(scorer=[...])`) is what production code must use, with explicit per-judge `get_model(config=GenerateConfig(max_tokens=N))` to cap output and avoid OpenRouter monthly-budget exhaustion.

H2 (only-aggregate behavior) refuted: 2 distinct judge Score objects accessible.
H3 (`multi_scorer()` is broken) confirmed as upstream issue; will require upstream report to UK AISI / inspect-ai repo.

## Trust Calculus per claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| `sample.scores` is dict with N entries when N scorers passed as list to `Task(scorer=[...])` | 9 | 9 | 9 | 27/27 | Empirically observed; deterministic API behaviour. |
| `multi_scorer()` is broken in `inspect_ai==0.3.46` ("Object score does not have registry info") | 8 | 8 | 8 | 24/27 | Reproduced in spike script comments; full stack trace captured in `/tmp/h1_spike_output.txt`. Worth an upstream bug report. |
| Per-judge `Score.value` and `Score.explanation` are individually distinct (no leakage between judges) | 9 | 9 | 8 | 26/27 | Confirmed in single sample; recommend wider replication in Phase 3 calibration. |
| Judge `max_tokens` default = model native max (production hazard) | 9 | 8 | 9 | 26/27 | Reproduced via HTTP 402; fix verified. |
| Inspect AI auto-assigns scorer names (`model_graded_qa`, `model_graded_qa1`, ...) | 8 | 8 | 8 | 24/27 | Empirically observed; production code should use explicit `Scorer.named(...)` or index by position. |

All claims sum ≥ 12 (NOTE-002 minimum threshold).

## Conclusions

- **Surviving hypothesis**: H1 via fallback path.
- **Decision strength**: 90% (single sample; broader replication = follow-up in Phase 3 calibration EVID).
- **ADR-006 status**: **NOT NEEDED for the dispatch path**. The original assumption "use `multi_scorer()`" is REFUTED for `inspect_ai==0.3.46`, but the fallback path (list of scorers) DOES expose per-judge access. RFC-002 Slice B's documented fallback path is the correct production approach. RFC-002 Slice B body already mentions this fallback as the "H3 path"; should be promoted from fallback to primary in a Slice B revision.
- **Follow-up actions**:
  1. **RFC-002 Slice B amendment** — promote list-of-scorers from fallback to primary path; downgrade `multi_scorer()` to "upstream broken, do not use until fixed".
  2. **Phase 3 implementation MUST cap judge `max_tokens`** — explicit `get_model(model, config=GenerateConfig(max_tokens=N))` in `JudgePanel.__init__`. Without this, any OpenRouter key with monthly budget less than ~5¢ per judge call will 402.
  3. **Upstream bug report** to `https://github.com/UKGovernmentBEIS/inspect_ai` describing `multi_scorer` registry issue with reproducer.
  4. **Scorer-name convention** — Phase 3 implementation should use explicit `Scorer.named("judge_<model_family>")` instead of relying on auto-assigned `model_graded_qa{N}` names (better debuggability + traces).
- **Phase 3 gate**: **READY**. Slice A coder dispatch can proceed.

## Artifact links

- `informs RFC-002` (parent, auto-linked via parent_id on creation)
- Will be linked `informs PRD-002` post-creation (Q1 verification)

## Reproducer

```bash
# Pre-requisites
make stack-up        # LiteLLM proxy + Postgres + NATS
# .env must have OPENROUTER_API_KEY_JUDGE + LITELLM_MASTER_KEY

# Run
uv run --project apps/eval-core-py python infra/scripts/inspect_ai_h1_spike.py

# Expected output (abridged)
# VERDICT: per_judge_scores_accessible = True
# H1 (RFC-002 Slice B assumption): SUPPORTED
```

Full successful run log: `/tmp/h1_spike_output_v2.txt` (local; not committed).

## Environment

- `inspect_ai==0.3.46`
- LiteLLM proxy on `http://localhost:4000` (commit `b9ebb1f` infra)
- Judge routes added in `infra/litellm-config.yaml` (uncommitted at observation time; included in same commit as this EVID)
- Candidate model: `openrouter/google/gemini-3-flash-preview` via `gemini-3-flash` proxy route
- Judges: `openrouter/anthropic/claude-sonnet-4.6` and `openrouter/openai/gpt-5-mini` via `*-judge` proxy routes with `OPENROUTER_API_KEY_JUDGE` billing isolation
- Date: 2026-05-24, commit `<post-commit SHA in same change>`


