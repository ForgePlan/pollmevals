---
depth: standard
id: EVID-047
kind: evidence
last_modified_at: 2026-06-01T20:16:16.813669+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-002
  relation: informs
- target: ADR-005
  relation: informs
- target: PRD-002
  relation: informs
status: active
title: 'Live-run: judge panel score()→α-gate end-to-end on real models (doc_01, 3 judges) + 3 wiring fixes + cap/parser robustness'
---

# EVID-047: Live-run — judge panel end-to-end on real models

| Field | Value |
|-------|-------|
| Status | Draft |
| Created | 2026-06-01 |
| Valid Until | 2026-09-01 |
| Target | RFC-002 (judge panel implementation) + ADR-005 (α-gate publication decision) |

## Structured Fields

evidence_type: measurement
verdict: supports
congruence_level: 3

## Measurement

First end-to-end live execution of the judge panel against real models (the
`score()` path had only ever run under mocked unit tests). Reproducer:
`apps/eval-core-py/scripts/judge_live_smoke.py` (cost-bounded manual smoke, NOT
a pytest test).

- Conditions: LiteLLM proxy at `localhost:4000`; 3 judges
  `claude-sonnet-4-6-judge` / `gpt-5-mini-judge` / `gemini-3-flash` (anthropic /
  openai / google families); candidate model `meta-llama/llama-3.3-70b-instruct`
  (distinct family → no self-judging); task `doc_01_cli_readme`; candidate output
  = a real "good"-band README.
- Measured: per-judge rubric `total_score` + criteria count, `tokens_in/out`,
  `latency_ms`, `cost_usd` (G6); panel `aggregate()` Krippendorff α + CI + status
  (α-gate / G1); calibration `_score_calibration_sample` on perfect+broken (G2);
  identification `_score_identification_sample` on one probe sample (G2).
- Two passes: (1) initial run with env workarounds → full pipeline; (2) re-run
  after wiring fixes with NO workarounds → turnkey verification.

## Result

Run 1 (full pipeline, env pre-wired):

| judge | total | criteria | tok_in/out | latency | cost |
|---|---|---|---|---|---|
| gemini-3-flash | 9.00 | 5 | 2569/158 | 29.2 s | $0.0101 |
| gpt-5-mini-judge | 0.00 | 1 (degraded) | 2439/768 | 23.5 s | $0.0188 |
| claude-sonnet-4-6-judge | 7.30 | 5 | 2719/451 | 10.5 s | $0.0149 |

- **α-gate (ADR-005):** `aggregate()` returned a REAL non-degenerate
  Krippendorff `α = 0.187` (`alpha_ci_lower = 0.187`), `judge_status = OK`,
  `n_judges_used = 3`. The gate correctly evaluates `< 0.70` → would refuse
  publication. Success criterion met: a real non-degenerate α, accepted or
  refused — not "α >= 0.70 actually holds".
- **G6 (cost accounting):** all judges report non-zero tokens + latency + cost;
  judge cost flows into `GridRunner._invoke_judge_panel` running total.
- **G2 (calibration + probe):** calibration `perfect = 8.60 > broken = 1.30`
  (correct ordering); probe `anthropic-001 → guess "anthropic"` (path works).

Five operational findings (the mocked unit tests had hidden three integration
assumptions; all fixed in commit `76a49e4`):

1. proxy-auth key — `api_key_env` defaulted to the OpenRouter UPSTREAM key
   (`sk-or-v1...`), rejected by the LiteLLM proxy (401). Proxy authenticates
   clients with `LITELLM_MASTER_KEY`. → default changed to the proxy key.
2. env-before-`get_model` — `_make_judge_models()` built the OpenAI client and
   read `OPENAI_API_KEY` at construction, before `_run_judge_task` wired the env.
   → pass `base_url`/`api_key` directly to `get_model`.
3. `eval_async` top-level model — required even though the forwarding solver
   never calls it. → pass a pre-resolved judge model as `model=`.
4. `_parse_rubric_scores` — now extracts the outermost `{...}` before parsing
   (handles markdown fences / surrounding prose).
5. rubric token cap 768 → 2048 — `gpt-5-mini` (a reasoning model) exhausted 768
   on reasoning tokens and returned an empty completion → degraded to
   `{'overall': 0.0}` (the degraded row above), which dragged α down. 2048 gives
   reasoning judges room for reasoning + JSON.

Run 2 (turnkey, no env workarounds): reached the live OpenRouter API with no
pre-wiring → fixes 1-3 CONFIRMED. The only failure was an OpenRouter HTTP 402
(downstream of all wiring): the project key is at `total_credits: 0`
(`total_usage: $0.152`, monthly budget exhausted) — a funding issue, not code.

Offline gate after fixes: ruff + ruff format + mypy --strict (30 files) clean;
624 passed, 1 skipped.

## Interpretation

The judge panel works end-to-end on real models: `score() -> aggregate()`
produces a genuine non-degenerate Krippendorff α and the publication gate
(ADR-005) evaluates it correctly. G1 (per-criterion scoring), G2
(calibration/probe paths), and G6 (per-judge cost) are all exercised live. The
three wiring fixes make `score()` turnkey (validated: run 2 reached the live API
with no env workarounds). This SUPPORTS RFC-002 (implementation) and ADR-005
(α-gate decision is validated and can be activated).

Open item (does NOT block ADR-005; does gate a clean RFC-002 "operational"
claim): a single funded re-run of the full strong panel where all 3 judges emit
complete 5-criterion JSON has not yet been observed — run 1 had `gpt-5-mini`
degrade (now addressed by the cap → 2048 fix, itself UNVALIDATED) and runs 2/3
were blocked by the depleted OpenRouter key. Judge tier for that re-run is
decided: balanced panel (sonnet / gpt-5-mini / gemini-flash). The low α = 0.187
in run 1 is partly an artifact of the degraded judge, not pure disagreement, so
no inference about real inter-judge agreement should be drawn from this run.

## Congruence Level Justification

CL3 (same-context, penalty 0.0): this is a direct live execution of the exact
`apps/eval-core-py/src/orchestrator/judge_panel.py` code that RFC-002 specifies
and ADR-005 decides, on a real project task (`doc_01_cli_readme`) through the
production LiteLLM-proxy path — not an analogue, benchmark, or external report.

## Related Artifacts

| Artifact | Relation |
|----------|----------|
| RFC-002 | informs |
| ADR-005 | informs |
| PRD-002 | informs |



