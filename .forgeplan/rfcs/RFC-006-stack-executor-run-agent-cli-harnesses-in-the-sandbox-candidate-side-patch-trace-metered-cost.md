---
depth: standard
id: RFC-006
kind: rfc
last_modified_at: 2026-06-01T23:17:48.052668+00:00
last_modified_by: claude-code/2.1.156
links:
- target: RFC-005
  relation: informs
- target: PRD-006
  relation: informs
status: draft
title: Stack executor — run agent-CLI harnesses in the sandbox (candidate side) → patch + trace + metered cost
---

# RFC-006: Stack executor — run agent-CLI harnesses in the sandbox

## Summary

A `StackExecutor` that, given a stack adapter (`stack.yaml`) + a task (prompt +
repository snapshot), invokes the declared **agent CLI inside a network-isolated
Docker sandbox**, routes the CLI's model calls through the **LiteLLM proxy** (so
we choose the model AND meter every token), and captures the produced **patch +
trace + cost**. This is the candidate-side half for non-`raw-llm` stacks. It
turns the 2026-06-02 feasibility spikes (7 CLIs proven headless via the proxy)
into the production executor.

## Motivation

POLLMEVALS evaluates STACKS (model + harness + scaffolding), not raw models.
`raw-llm` (L0) runs today via `InspectEvalCaller` (model completion). The 11
CLI-harness stacks (aider, claude-code-basic, codex, opencode, goose, openhands,
hermes, cline, pi, forgeplan-framework) need a DIFFERENT candidate path: run the
CLI. Without this executor, the whole "model × harness" thesis is unmeasured.

## Architecture — the two-half sandbox

The eval pipeline has two sandboxed halves, complementary, both in Docker:

- **Half A — candidate (THIS RFC):** run the harness CLI → produce a patch.
- **Half B — evaluator (#24 + `evaluators/sandbox/`):** run the produced code →
  scores (vitest/pytest/lint). Partially built; #24 unblocked fe_01 e2e (3
  defects surfaced).

The executor produces the patch that Half B then scores. **No conflict with #24.**

## Proposed design (module breakdown)

- **`StackExecutor`** (new `apps/eval-core-py/src/orchestrator/stack_executor.py`):
  reads the `StackPin` (stack.yaml) → builds a sandbox container from an image
  that has the CLI pre-installed → mounts the repo snapshot at `/workspace` →
  injects the per-CLI proxy config → runs `execution.command + args` with the
  task prompt → enforces `limits` (wall-clock, tool-calls; tokens via the proxy
  cap) → captures `git diff` (patch) + the CLI trace + cost → returns an
  EvalResult-shaped object.
- **Per-CLI proxy adapter** — a map `agent_cli` → proven recipe (already codified
  in each `stack.yaml` comment + memory research-cli-harness-execution):
  - codex: `CODEX_HOME` config.toml `[model_providers.litellm] wire_api=responses`
  - claude-code: `ANTHROPIC_BASE_URL` (native/compatible model)
  - aider / goose / openhands: env (`OPENAI_API_BASE` / `OPENAI_HOST` / `LLM_BASE_URL`)
  - opencode: `opencode.json` provider; hermes: `config.yaml custom_providers`
- **Sandbox image**: base image with the agent CLIs installed. Built + cached per
  CLI (versioned).
- **GridRunner dispatch**: pick executor by stack — `raw-llm` → `InspectEvalCaller`;
  CLI stacks → `StackExecutor`. Then Half B evaluators run on the patch.
- **Cost metering**: all model calls traverse the proxy → metered per-call; the
  executor reads the proxy's per-run spend (judge-side pattern already does this).

## Sandbox networking — the crux

`network=none` for isolation, BUT the CLI must reach the LiteLLM proxy. Solution:
a controlled bridge that allows ONLY the proxy host:port — no general egress.
This keeps reproducibility + blocks data-exfil while letting the harness call
models. (Open question: implement via a sidecar proxy in the container network
vs a host-gateway firewall rule.)

## Risks

- Per-CLI fragility (e.g. claude-code breaks on some non-native models — use
  native/compatible pairings per the matrix). Mitigation: the proven-recipe map +
  a per-stack smoke before any scored run.
- Sandbox networking (proxy-only bridge) — security-sensitive; gate via review.
- Cost: real model calls × harness steps (multi-turn) → expensive. Mitigation:
  per-stack `limits` + the budget gate + small `k`.
- Non-determinism: harnesses vary run-to-run. Mitigation: seeds + the
  pass@k / pass^k reliability metrics (ADR-013) make variance a first-class output,
  not a bug.
- Image maintenance: CLIs update frequently → pin versions in the image.

## Test plan

- Unit: `StackExecutor` with a mock/fake CLI (no Docker, no network) — invocation
  building, limit enforcement, patch capture, error paths.
- Integration: one stack × trivial task locally (the 2026-06-02 spikes are the
  feasibility evidence; promote one to a test).
- Live (cost-checkpointed): the first-slice run below.

## First slice

**`aider × be_01_jwt_auth`** (aider = simplest, model-agnostic, already proven):
StackExecutor runs aider in the sandbox on a chosen model → patch → apply → Half
B evaluators (vitest, per #24's Linux-deps fix) → score + judges → the **first
real "model × harness" number**. Then widen to codex/opencode + more tasks.

## Alternatives considered

- Run CLIs on the host (no sandbox) — rejected: isolation/security/reproducibility.
- Reimplement each harness's logic — rejected: we must evaluate the REAL harness.
- Support only model-agnostic CLIs — partial: start there (aider/goose/openhands),
  add vendor-tuned (codex/claude-code/opencode/hermes) via their proven configs.

## Related Artifacts

| Artifact | Relation |
|----------|----------|
| RFC-005 | informs |
| PRD-006 | informs |
| NOTE-011 | informs |



