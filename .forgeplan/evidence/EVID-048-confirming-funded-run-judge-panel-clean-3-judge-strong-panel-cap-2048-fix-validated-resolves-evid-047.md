---
depth: standard
id: EVID-048
kind: evidence
last_modified_at: 2026-06-01T20:28:40.121013+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-002
  relation: informs
- target: ADR-005
  relation: informs
- target: PRD-002
  relation: informs
status: active
title: 'Confirming funded run: judge panel clean 3-judge α, strong panel, cap-2048 fix validated (resolves EVID-047)'
---

# EVID-048: Confirming funded run — clean strong-panel judge α

| Field | Value |
|-------|-------|
| Status | Draft |
| Created | 2026-06-01 |
| Valid Until | 2026-09-01 |
| Target | RFC-002 (judge implementation) + ADR-005 (α-gate decision) |

## Structured Fields

evidence_type: measurement
verdict: supports
congruence_level: 3

## Measurement

Funded re-run of `apps/eval-core-py/scripts/judge_live_smoke.py` after the
OpenRouter key was topped up (+$10; available ~$9.85). Resolves the open item
EVID-047 declared: a clean run of the full STRONG balanced panel where all three
judges emit complete 5-criterion JSON, validating the cap → 2048 fix. Same
conditions as EVID-047 (LiteLLM proxy, task `doc_01_cli_readme`, candidate
meta-llama, turnkey — no env workarounds), strong balanced panel
`claude-sonnet-4-6-judge` / `gpt-5-mini-judge` / `gemini-3-flash`.

## Result

| judge | total | criteria | tok_in/out | latency | cost |
|---|---|---|---|---|---|
| gpt-5-mini-judge | 7.30 | 5 | 2439/1314 | 17.5 s | $0.0270 |
| claude-sonnet-4-6-judge | 7.50 | 5 | 2719/411 | 10.8 s | $0.0143 |
| gemini-3-flash | 9.00 | 5 | 2569/148 | 1.9 s | $0.0099 |

- **cap-2048 fix VALIDATED:** `gpt-5-mini-judge` now emits a complete
  5-criterion rubric (total 7.30) using 1314 output tokens — reasoning + JSON
  both fit. In EVID-047 the same judge degraded to `{'overall': 0.0}` (1
  criterion) under the old 768 cap. No degraded judge this run.
- **clean α:** `aggregate()` → `α = 0.358` (`alpha_ci_lower = 0.358`),
  `judge_status = OK`, `n_judges_used = 3`. Higher and cleaner than EVID-047's
  0.187 (which was depressed by the degraded judge), now reflecting genuine
  per-criterion inter-judge agreement. Still < 0.70 publication threshold →
  the gate would correctly refuse, which is the honest/expected v0.1 state.
- **G2 unchanged-good:** calibration `perfect = 8.50 > broken = 1.30`; probe
  `anthropic-001 → "anthropic"`.

## Interpretation

Closes the EVID-047 open item. The judge panel is fully operational on real
models with a STRONG, family-diverse panel: turnkey wiring (no env workarounds),
all three judges produce complete per-criterion scores, a real non-degenerate α,
and the publication gate evaluates it correctly. The cap → 2048 fix for reasoning
judges is validated (gpt-5-mini emitted full JSON). Nothing further blocks
activating ADR-005 (α-gate decision) then RFC-002 (judge implementation).

## Congruence Level Justification

CL3 (same-context, penalty 0.0): direct live execution of the exact
`judge_panel.py` code RFC-002 specifies and ADR-005 decides, on the real
`doc_01_cli_readme` task through the production LiteLLM-proxy path.

## Related Artifacts

| Artifact | Relation |
|----------|----------|
| RFC-002 | informs |
| ADR-005 | informs |
| PRD-002 | informs |




