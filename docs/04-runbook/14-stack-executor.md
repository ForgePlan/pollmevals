# 14 — Stack Executor (Half A: harness → patch)

How to run a **real** `harness × model × task` evaluation: drive an agent-CLI
harness (aider, …) against a task inside an isolated sandbox, capture the
produced **patch + trace + metered cost**, then score it.

Built per **RFC-006**. Complements the existing pieces:

- `05-stack-adapter-guide.md` — the `stack.yaml` adapter this reads.
- `09-sandbox-security.md` — the frozen sandbox policy (Half B side).
- `07-judge-panel.md` + `08-scoring-contract.md` — how the patch is scored.

---

## The two-half sandbox

```
Half A — candidate (this doc):  harness CLI  ──►  patch
         StackExecutor + DockerHarnessLauncher (src/orchestrator/stack_executor.py)

Half B — evaluator:             produced code ──►  scores
         evaluators/ + evaluators/sandbox/runner.py  (+ judge panel)

Bridge:  StackExecResult ──► EvalResult   (src/orchestrator/stack_scoring.py)
```

`raw-llm` (L0, `execution.mode: direct_completion`) stays on `InspectEvalCaller`.
Every `repository_patch` stack (aider, claude-code, codex, …) runs through the
**StackExecutor**.

---

## Network model — the bastion (RFC-006 decision A)

The harness must reach the LiteLLM proxy (to pick the model + meter every token)
but must NOT reach anything else (no un-metered egress, no data exfil).

Solution: a Docker **`internal`** network `pollmevals-sandbox` (no external
route). The proxy is attached to it as the **only reachable host** (a bastion);
it also stays on the default net to reach OpenRouter. The harness joins ONLY
`pollmevals-sandbox`.

```
[ harness container ] ──(pollmevals-sandbox, internal)──► [ litellm-proxy ] ──(default)──► OpenRouter
        │                                                                                       
        └── no route to anything else (DNS for the open internet fails)                         
```

Consequences:
- No `NET_ADMIN` / iptables needed → `cap_drop ALL` holds.
- Portable Linux / macOS / CI (pure Docker topology, not firewall rules).
- In-sandbox the proxy is addressed by **container name** (`http://pollmevals-litellm-proxy:4000`),
  NOT `localhost` — the internal net has no host route.

---

## One-time setup

```bash
make stack-up            # Postgres + NATS + LiteLLM proxy (healthy)
make sandbox-net-up      # create pollmevals-sandbox + attach the proxy (idempotent;
                         # for an already-running stack — no recreate needed)
make harness-image-aider # build pollmevals-harness-aider:0.1.0 (python+aider+git)
```

`make stack-up` also creates `pollmevals-sandbox` declaratively (it is in
`infra/docker-compose.litellm.yml`); `sandbox-net-up` is the imperative path for
a stack that is already up.

Verify the bastion (no spend):

```bash
# reaches the proxy (expect 200)
docker run --rm --network pollmevals-sandbox pollmevals-harness-aider:0.1.0 \
  python -c "import urllib.request; print(urllib.request.urlopen('http://pollmevals-litellm-proxy:4000/health/liveliness',timeout=8).status)"
# cannot reach the internet (expect DNS failure)
docker run --rm --network pollmevals-sandbox pollmevals-harness-aider:0.1.0 \
  python -c "import urllib.request; urllib.request.urlopen('https://example.com',timeout=6)"
```

---

## Running it

All scripts are spend-gated (`--confirm-spend`) and require `LITELLM_MASTER_KEY`
in `.env` (the proxy key — NOT the upstream provider key).

### Plumbing check (\$0 — no model call)

```bash
uv run --project apps/eval-core-py python \
  apps/eval-core-py/scripts/stack_exec_live_smoke.py --plumbing
```

Runs a no-model command in the sandbox and asserts the launcher captures the
git diff. Use this to debug Docker / mount / network issues before spending.

### Half A only — harness → patch (≈ \$0.001)

```bash
uv run --project apps/eval-core-py python \
  apps/eval-core-py/scripts/stack_exec_live_smoke.py --confirm-spend
```

### Full chain — harness → patch → judge → scored number (≈ \$0.07)

```bash
uv run --project apps/eval-core-py python \
  apps/eval-core-py/scripts/stack_score_live_smoke.py --confirm-spend
```

Run from the **repo root** (the judge panel resolves `evals/task-packs/<task>/rubric.yaml`
via cwd; the score script also `chdir`s to the repo root defensively).

---

## How patch capture works

The harness command is run as a **clean argv list** (no shell), so the
multi-line task prompt needs no quoting. The patch is captured **host-side** with
git, robust to whether the harness auto-commits:

1. before the run: `git init` (if needed) + commit the snapshot AS GIVEN → base SHA
2. run the harness container (writable `/workspace` bind on the bastion net)
3. after: `git add -A && git diff --cached <base>` → the unified patch
   (committed + working-tree + new files), with harness bookkeeping
   (`.aider*`, `.gitignore`) filtered out by the scoring bridge

Token/cost: best-effort from the harness self-report for now; the proxy is the
metered source of truth for reconciliation (a Phase-4 follow-up).

---

## Scoring path (be_01 caveat)

The bridge (`stack_scoring.exec_result_to_eval_result`) writes the candidate's
changed source files as the `raw_output` artifact, then the judge panel scores
it against the task rubric.

**Use the judge panel for be_01, not the deterministic evaluators** — the be_01
deterministic evaluators score-INVERT (broken > perfect, EVID-027). Judged
subjective scoring is also POLLMEVALS' edge. `doc_01` is judge-only by design;
`fe_01` has working dynamic evaluators (post-#24).

---

## Known defects / follow-ups

- **gpt-5-mini judge truncates** its rubric JSON at the 2048 `max_tokens` cap on
  a 7-criterion coding rubric → parse-fail → 0.0 fallback, which drags the panel
  median + Krippendorff α. Fix is `reasoning_effort` (cap reasoning tokens), NOT
  raising the cap (EVID-023: the cap is bounded by the OpenRouter HTTP-402
  pre-reservation hazard). Until then, read the per-judge scores, not just the
  median.
- **Proxy-metered cost reconciliation** — replace the best-effort harness
  self-report with a proxy `/spend` query (harness-agnostic).
- **GridRunner dispatch-by-stack** — route CLI stacks to StackExecutor inside
  GridRunner so a full grid run emits real Board data (RFC-006 Phase 4b).
- **More harnesses** — codex / claude-code / goose / openhands recipes are
  registered but pending their per-stack smoke (`_PENDING_RECIPES`, Phase 5).

---

## First real numbers (2026-06-02)

| stack | task | result | cost |
|---|---|---|---|
| aider × qwen-3-14b | be_01 | patch: 208-line Express JWT middleware, `status=ok` | \$0.00063 |
| aider × qwen-3-14b | be_01 | judged: claude 5.27 · gemini 7.33 · gpt-5-mini 0.00\* | \$0.070 |

\* gpt-5-mini truncation defect (above); trustworthy 2-judge signal ≈ 6.3.
