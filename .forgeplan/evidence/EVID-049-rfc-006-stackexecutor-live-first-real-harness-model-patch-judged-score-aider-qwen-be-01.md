---
depth: standard
id: EVID-049
kind: evidence
last_modified_at: 2026-06-02T18:31:17.801906+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-006
  relation: informs
status: active
title: 'RFC-006 StackExecutor live: first real harness×model patch + judged score (aider×qwen×be_01)'
---

## Summary

RFC-006 StackExecutor (Half A: harness → patch) is implemented and validated
end-to-end on real money. The candidate pipeline produces a real
`harness × model × task` patch with metered cost, and the Half A→B bridge feeds
it to the judge panel for a real score.

## Structured Fields

- **verdict**: PASS
- **congruence_level**: CL3 (same context — this is RFC-006's own implementation, verified directly against its acceptance criteria)
- **evidence_type**: live_integration_run

## What was verified (2026-06-02)

1. **Network decision A (bastion) — proven, $0.** A container on the Docker
   `internal` net `pollmevals-sandbox` reaches the LiteLLM proxy (HTTP 200) but
   NOT the internet (DNS resolution fails). No un-metered egress; `cap_drop ALL`
   holds (no NET_ADMIN needed).
2. **Half A plumbing — proven, $0.** `DockerHarnessLauncher` runs a no-model
   command in the sandbox, writes to the writable `/workspace` bind, and
   host-side git captures the diff (`--plumbing` check). Surfaced + fixed a
   `DOCKER_HOST` discovery bug before any spend (cheap-signal-before-dear).
3. **First real patch — aider × qwen-3-14b × be_01.** `status=ok`, a 208-line
   real Express JWT auth middleware written to `solution.ts`, `cost=$0.000626`
   (metered via the proxy), in 1400 / out 2200 tokens, ~55s.
4. **First scored number — same stack, judged.** Half A→B bridge → judge panel
   (inversion-free; the be_01 deterministic evaluators invert per EVID-027):
   claude-sonnet 5.27 · gemini-3-flash 7.33 · gpt-5-mini 0.00\* · total $0.070.
   Panel median 5.27/10; trustworthy 2-judge signal ≈ 6.3.

## Defect surfaced

\* **gpt-5-mini judge truncates** its rubric JSON at the 2048 `max_tokens` cap on
the be_01 7-criterion coding rubric → JSON parse-fail → 0.0 fallback, which
drags the panel median + Krippendorff α (α went negative). Fix is
`reasoning_effort` (cap reasoning tokens), NOT raising the cap — EVID-023 bounds
the cap by the OpenRouter HTTP-402 pre-reservation hazard. Tracked as judge
follow-up; does not block the executor.

## Artifacts

- Code: `apps/eval-core-py/src/orchestrator/stack_executor.py`, `stack_scoring.py`
- Image: `pollmevals-harness-aider:0.1.0` (aider-chat 0.86.2)
- Smokes: `scripts/stack_exec_live_smoke.py`, `scripts/stack_score_live_smoke.py`
- Runbook: `docs/04-runbook/14-stack-executor.md`
- Branches: `feat/stack-executor-rfc006` (Phases 1-3, PR #39), `feat/stack-scoring-rfc006` (Phase 4a)


