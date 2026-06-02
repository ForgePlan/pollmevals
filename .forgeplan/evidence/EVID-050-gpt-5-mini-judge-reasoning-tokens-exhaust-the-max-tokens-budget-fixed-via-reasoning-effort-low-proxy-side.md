---
depth: standard
id: EVID-050
kind: evidence
last_modified_at: 2026-06-02T19:33:57.908876+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-006
  relation: informs
status: active
title: 'gpt-5-mini judge: reasoning_tokens exhaust the max_tokens budget — fixed via reasoning_effort=low (proxy-side)'
---

## Summary

The gpt-5-mini judge returned a false 0.0 on the first real scored run (EVID-049),
dragging the panel median + Krippendorff α. Root-caused live: gpt-5-mini is a
reasoning model that spends `reasoning_tokens` against the `max_tokens` budget —
at the default effort it burned all 2048 on reasoning and returned EMPTY content.
Fixed proxy-side with `reasoning_effort: low`.

## Structured Fields

- **verdict**: PASS
- **congruence_level**: CL3 (same context — the judge scoring path used by the executor)
- **evidence_type**: incident_diagnosis

## Diagnosis (direct gpt-5-mini calls via the proxy, be_01 7-criterion rubric)

| mode (max_tokens=2048) | finish_reason | reasoning_tokens | content | parse |
|---|---|---|---|---|
| default | `length` | 1856–2048 | empty / truncated | FAIL |
| `response_format=json_object` | `length` | 2048 | empty | FAIL |
| **`reasoning_effort=low`** | **`stop`** | **640–704** | **full valid JSON** | **OK** |

The decisive signal was `completion_tokens_details.reasoning_tokens == max_tokens`
with `finish_reason="length"` and `content len 0` — the model never emitted the
answer. JSON mode did NOT help (reasoning still ate the budget). Raising the cap
would not reliably help either (reasoning scales to fill it).

## Fix

`reasoning_effort: low` on the `gpt-5-mini-judge` alias in
`infra/litellm-config.yaml`. Bounds reasoning (~640 tok) so the full rubric JSON
fits, and the call is cheaper ($0.0019 vs $0.0043). This is the remedy EVID-023
predicted ("cap reasoning, do not raise the token cap" — OpenRouter pre-reserves
`max_tokens × price`, an HTTP-402 hazard). It lives PROXY-side because inspect_ai
0.3.46 `GenerateConfig` exposes no `reasoning_effort` / `extra_body` passthrough.
Scoped to the JUDGE alias only; candidate gpt-5 use is unaffected.

## Validation

After the fix + proxy restart, the panel's exact request path (no
`reasoning_effort` in the request) returns `finish_reason="stop"` + valid
parseable JSON: `{correctness:9.0, security_posture:10.0, error_handling:7.0,
type_safety:7.5, code_clarity:9.5, test_alignment:10.0}`. gpt-5-mini is now a
real third vote instead of a false 0.0.

## Follow-up (separate, noted in the commit)

A parse-failure should map to DEGRADED (the judge is a non-voter), not a false
0.0 — defense-in-depth so ANY future judge garbage can never pollute the median.

## Artifacts

- Fix: `infra/litellm-config.yaml` (commit ba476fa)
- Diagnostic tool: `apps/eval-core-py/scripts/diagnose_judge_json.py`
- Branch: `fix/judge-json-robustness`


