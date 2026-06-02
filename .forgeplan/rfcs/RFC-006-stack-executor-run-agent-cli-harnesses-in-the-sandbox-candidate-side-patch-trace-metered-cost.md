---
depth: standard
id: RFC-006
kind: rfc
last_modified_at: 2026-06-02T12:41:03.121711+00:00
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
CLI. Without this executor, the whole "model × harness" thesis is unmeasured —
and the public leaderboard (PR #36) can only show illustrative data.

## Architecture — the two-half sandbox

The eval pipeline has two sandboxed halves, complementary, both in Docker:

- **Half A — candidate (THIS RFC):** run the harness CLI → produce a patch.
- **Half B — evaluator (#24 + `evaluators/sandbox/`):** run the produced code →
  scores (vitest/pytest/lint). BUILT (evaluators + sandbox/runner.py); #24
  unblocked fe_01 e2e (3 defects surfaced, EVID-033).

The executor produces the patch that Half B then scores. **No conflict with #24.**

## Recon status (2026-06-02 — what already exists)

- Docker UP (24.0.2). Half B evaluators + `evaluators/sandbox/runner.py` (docker-py)
  EXIST. Judges operational (#28, live α=0.358). be_01 pack has Dockerfile + gold
  + rubric. 7 CLI harnesses proven headless via the proxy. Leaderboard data layer
  (#35) + rich Board contract (apps/site/src/lib/board.ts) exist.
- **Only Half A (this RFC) is missing.** Docker is ready; build can be tested for real.

## Proposed design (module breakdown)

- **`StackExecutor`** (new `apps/eval-core-py/src/orchestrator/stack_executor.py`):
  reads the `StackPin` (stack.yaml) → builds a sandbox container from an image
  that has the CLI pre-installed → mounts the repo snapshot at `/workspace` →
  injects the per-CLI proxy config → runs `execution.command + args` with the
  task prompt → enforces `limits` (wall-clock, tool-calls; tokens via the proxy
  cap) → captures `git diff` (patch) + the CLI trace + cost → returns an
  EvalResult-shaped object. Protocol seam for mock unit tests (EVID-015 discipline).
- **Per-CLI proxy adapter** — a map `agent_cli` → proven recipe (codified in each
  `stack.yaml` comment + memory research-cli-harness-execution):
  - codex: `CODEX_HOME` config.toml `[model_providers.litellm] wire_api=responses`
  - claude-code: `ANTHROPIC_BASE_URL` (native/compatible model)
  - aider / goose / openhands: env (`OPENAI_API_BASE` / `OPENAI_HOST` / `LLM_BASE_URL`)
  - opencode: `opencode.json` provider; hermes: `config.yaml custom_providers`
- **Sandbox image**: base image with the agent CLIs installed. Built + cached per
  CLI (versioned).
- **GridRunner dispatch**: pick executor by stack — `raw-llm` → `InspectEvalCaller`;
  CLI stacks → `StackExecutor`. Then Half B evaluators run on the patch.
- **Cost metering**: all model calls traverse the proxy → metered per-call; reuse
  the judge-side cost pattern (`cost.compute_cost`).
- **Board emission**: extend `apps/eval-core-py/src/leaderboard/` to emit the rich
  Board shape (harness metadata from stack.yaml + per-task scores) the site renders,
  replacing `board.illustrative.json`.

## Sandbox networking — the crux

`network=none` for isolation, BUT the CLI must reach the LiteLLM proxy
(localhost:4000). Solution: a controlled bridge that allows ONLY the proxy
host:port — no general egress. Keeps reproducibility + blocks data-exfil while
letting the harness call models. (Open question: sidecar proxy in the container
net vs a host-gateway firewall rule.)

## Implementation Phases

Ordered, each independently shippable. Earlier phases need no extra spend beyond
the first-slice live run.

1. **Phase 1 — StackExecutor core (no Docker, mocked).** `stack_executor.py` +
   the per-CLI proxy-config builder + patch/trace/cost capture, with a Protocol
   seam so unit tests run without Docker or network. Gate: ruff + mypy --strict +
   unit tests. No spend.
2. **Phase 2 — Sandbox image + real single-harness run.** Build the CLI sandbox
   image (start: aider only); wire the network bridge (proxy-only); run `aider ×
   qwen × be_01` in the sandbox → capture a real patch. HUMAN cost checkpoint
   (~pennies). Validate the patch is a real git diff.
3. **Phase 3 — Wire Half A → Half B → score.** Apply the patch, run the be_01
   evaluators (Half B) + judges → the FIRST real (model × harness × task) score.
   CAVEAT: pick a task whose evaluators aren't inverted — be_01 evaluators
   score-INVERT (EVID-027); fe_01 had 3 defects (#24); doc_01 is judge-only (no
   code-exec). Resolve the be_01 inversion OR start with fe_01 (post-#24) OR
   doc_01. Deliberate choice required.
4. **Phase 4 — GridRunner dispatch-by-stack + Board emission.** Route CLI stacks
   to StackExecutor in GridRunner; extend the leaderboard aggregate to emit the
   real Board; point apps/site at real data (drop the illustrative flag for that run).
5. **Phase 5 — Widen.** Add codex/opencode/goose/openhands (proven recipes) +
   more models + fe_01/doc_01. Each new stack: per-stack smoke before a scored run.

## Invariants

- Run immutability (ADR-0002): a scored run is never edited in place.
- The harness is run AS-IS — never reimplement its logic (we evaluate the real harness).
- All model calls traverse the metered proxy — no un-metered egress (also the
  network-isolation security invariant).
- Non-determinism is reported (seeds + pass@k/pass^k, ADR-013), never hidden.

## Rollback Plan

StackExecutor is additive (new dispatch branch); `raw-llm` keeps using
InspectEvalCaller unchanged. To roll back: route all stacks to InspectEvalCaller
(raw-llm only) and keep the site on illustrative data. The sandbox image + bridge
are disposable. No published-run mutation (ADR-0002).

## Risks

- Per-CLI fragility (claude-code breaks on some non-native models — use
  native/compatible pairings per the matrix). Mitigation: proven-recipe map +
  per-stack smoke before any scored run.
- Sandbox networking (proxy-only bridge) — security-sensitive; gate via review.
- Cost: real model calls × harness steps (multi-turn) → expensive. Mitigation:
  per-stack `limits` + budget gate + small `k`.
- Evaluator correctness: be_01 evaluators are score-inverted (EVID-027) — must be
  fixed or avoided for the first objective-scored slice.
- Image maintenance: CLIs update frequently → pin versions.

## Test plan

- Unit: `StackExecutor` with a mock/fake CLI (no Docker, no network) — invocation
  building, limit enforcement, patch capture, error paths.
- Integration: one stack × trivial task locally (the 2026-06-02 spikes are the
  feasibility evidence; promote one to a test).
- Live (cost-checkpointed): the first-slice run (Phase 2-3).

## First slice

**`aider × qwen-3-14b × be_01_jwt_auth`** (aider = simplest, model-agnostic,
proven): StackExecutor runs aider in the sandbox on a chosen model → patch →
apply → Half B evaluators → score + judges → the **first real "model × harness"
number**. Then widen to codex/opencode + more tasks.

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

