---
depth: standard
id: EVID-004
kind: evidence
last_modified_at: 2026-05-23T19:30:01.983815+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: RFC-001
  relation: informs
- target: SPEC-001
  relation: informs
- target: ADR-003
  relation: informs
- target: ADR-001
  relation: informs
status: active
title: 'prior art: Inspect AI (UK AISI) — Task/Solver/Scorer + EvalLog gaps'
---

# EVID-004: Inspect AI (UK AISI) — Task/Solver/Scorer + EvalLog gaps

## Structured Fields

verdict: supports
congruence_level: 2
evidence_type: audit

## Summary

Critical prior art review of Inspect AI (UK AI Safety Institute framework, github.com/UKGovernmentBEIS/inspect_ai, active 2024-2026). POLLMEVALS plans to USE Inspect AI as the underlying orchestrator (per RFC-001), so this is the most architecturally important reference. Validates the full POLLMEVALS architecture and surfaces 3 specific gaps POLLMEVALS must fill on top.

## Key Findings

### Composition model — direct fit for POLLMEVALS (task, stack, seed) and L0-L8

The four primitives compose in one direction:

- **`Sample`** — one row from `Dataset`: `{input, target, metadata, choices, id}`.
- **`Task`** — recipe: `Task(dataset, solver, scorer, name, version, metadata, sandbox, epochs, setup, cleanup)`. `solver` accepts a list which Inspect auto-wraps in `chain()`.
- **`Solver`** — `async def solve(state: TaskState, generate: Generate) -> TaskState`. Receives full `TaskState`, returns mutated copy.
- **`Scorer`** — receives final `TaskState`; returns `Score`. Multiple scorers per Task supported. Reducers (`mean`, `median`, `pass_at_k`) aggregate across `epochs`.

Built-in solvers: `generate()`, `system_message()`, `prompt_template()`, `chain_of_thought()`, `use_tools()`, `self_critique()`, `multiple_choice()`. Custom solvers use `@solver` decorator.

Sources: <https://inspect.aisi.org.uk/solvers.html>, <https://inspect.aisi.org.uk/tasks.html>, <https://inspect.aisi.org.uk/scorers.html>.

### L0–L8 stack mapping (synthesis — RFC-001 architectural foundation)

| POLLMEVALS layer | Inspect primitive |
|---|---|
| L0 bare LLM | `Task(solver=[generate()])` |
| L1 system prompt | `system_message("…")` solver |
| L2 tools | `use_tools([...])` + `generate()` loop |
| L3 skills | Custom `@solver` injecting skill content into prompt |
| L4 file memory | Custom solver reads + injects file contents |
| L5 vector memory | Custom solver calls external retrieval |
| L6 subagents | `@agent` with `handoff()`, or nested Agent calls |
| L7 validator loop | `self_critique()` or custom loop |
| L8 domain framework | Shell-out solver that invokes CLI (`forgeplan eval`) |

A POLLMEVALS stack YAML maps directly to `chain([...])` of solver instances. `epochs=3` handles 3-seed requirement without extra code.

### Run log model — soft immutability, POLLMEVALS must enforce hard

Inspect writes one `EvalLog` per `eval()` call. Format: `.eval` binary (1/8 size of JSON, default since v0.3.46) or `.json`. Schema fields: `version`, `status`, `eval` (task + model + timestamps), `plan` (solver list + gen config), `results`, `stats`, `samples`, `tags/metadata`, `log_updates`.

**Append-only edit history**: post-eval edits land in `log.log_updates` with author + reason provenance. Original scores preserved in `history` field — not overwritten. **This is soft immutability** — the file on disk is mutable.

`inspect log export-config` extracts run config to YAML/JSON; `inspect eval --run-config <file>` re-runs it.

Source: <https://inspect.aisi.org.uk/eval-logs.html>.

**POLLMEVALS gap to fill**: SHA256-hash the `.eval` file after completion, store as `run_hash`, move to content-addressed storage (R2), set DB row to `published`. This is SPEC-001 `inspect_eval_log_sha256` + manifest `published` terminal state.

### Multi-provider model abstraction — direct compatibility

Model IDs use `provider/model-name` prefix routing:

| Provider | Example ID |
|---|---|
| Anthropic | `anthropic/claude-sonnet-4-0` |
| OpenAI | `openai/gpt-4o-mini` |
| Google | `google/gemini-2.5-pro` |
| HuggingFace | `hf/openai-community/gpt2` |
| vLLM (self-hosted) | `hosted_vllm/<served-model-name>` |
| Ollama | `ollama/<model-name>` |
| OpenRouter | `openrouter/<provider/model>` |

Cost tracking is **NOT built in** — `stats` captures token counts only, no dollar amounts.

Source: <https://inspect.aisi.org.uk/models.html>.

**POLLMEVALS gap to fill**: `pricing_snapshot × token_count → cost_usd` computed by POLLMEVALS orchestrator (RFC-001 § Cost attribution layer).

### What POLLMEVALS can borrow directly (high-value)

- **`Task(dataset, solver=chain([...]), scorer=[...], epochs=3)`** — maps cleanly to `(task, stack, seed)`. `epochs` handles 3-seed at zero code.
- **`model_graded_qa(model=[...])` + `multi_scorer()`** — multi-judge panel out of the box. Set `model=["anthropic/...", "openai/...", "google/..."]` for 3-judge panel; swap mean reducer for median (per EVID-001 divergence).
- **`inspect log export-config` / `--run-config`** — use as run-manifest format. Store emitted YAML alongside SHA256-addressed `.eval` log.
- **`read_eval_log(header_only=True)`** — fast manifest scanning for leaderboard aggregation.
- **`task_with()`** — override task solver at eval time without touching task source; enables stack-substitution pattern.
- **`hosted_vllm/` prefix** — zero-config for self-hosted Qwen, Llama on Runpod (ADR-003 model selection).

### What POLLMEVALS must add (3 gaps)

1. **Stack-level cost attribution** — Inspect captures token counts, not dollars. POLLMEVALS pricing-snapshot layer fills this (RFC-001).
2. **Hard run immutability + content-addressing** — Inspect's append-only `log_updates` is soft. POLLMEVALS SHA256 + R2 object-lock + DB `published` state.
3. **Leaderboard hygiene** — Inspect has no built-in mechanism for task contamination checks, model-ID probe testing (publication gate: probe accuracy ≤ 30%), or Krippendorff α calculation. POLLMEVALS aggregation pipeline does these (PRD-002, PRD-004).

## Implications for POLLMEVALS

1. **RFC-001 "build on Inspect AI" decision is fully validated.** L0-L8 maps cleanly, Inspect gives polished Task/Solver/Scorer/multi_scorer, saves 2-3 weeks of duplicating effort.
2. **SPEC-001 must include `inspect_ai_version` pin and `inspect_eval_log_sha256`** as version pinning fields.
3. **ER-7 risk in EPIC-001 (Inspect breaking changes)** is real but low — exact version pin in `pyproject.toml` mitigates.
4. **3 gaps POLLMEVALS fills (cost, hard immutability, leaderboard hygiene) define our value-add** — they should be highlighted in v0.1 launch positioning.

## Sources

1. <https://inspect.aisi.org.uk/solvers.html> — Solver contract and composition
2. <https://inspect.aisi.org.uk/tasks.html> — Task constructor, epochs, sandbox, task_with()
3. <https://inspect.aisi.org.uk/scorers.html> — Scorers, multi_scorer(), reducers, model_graded_qa
4. <https://inspect.aisi.org.uk/eval-logs.html> — EvalLog schema, log_updates, export-config
5. <https://inspect.aisi.org.uk/agents.html> — @agent, handoff(), as_tool(), generate_loop
6. <https://inspect.aisi.org.uk/models.html> — provider/model-name routing
7. <https://github.com/UKGovernmentBEIS/inspect_ai> — canonical source repo

## Confidence

🟢 High — four canonical doc pages fetched from inspect.aisi.org.uk (the live authoritative domain). All three design questions answered from primary sources. L0-L8 mapping is 🟡 (derived, not stated explicitly in docs) but grounded in confirmed primitives.

## Open Questions

- Does Inspect's `.eval` binary format expose a stable public schema for parsing without the Python SDK? (Matters for R2-stored artifact inspection from non-Python consumers, e.g. apps/site SSG.)
- What exact fields does `eval.eval` carry for the model spec — is full generation config (temperature, top_p, max_tokens) captured?
- Does `hosted_vllm/` provider support streaming token counts for per-request cost attribution?

## Related Artifacts

- PRD-001 (informs — auto-linked)
- RFC-001 (Inspect AI is the chosen orchestrator — direct dependency)
- SPEC-001 (`inspect_eval_log_sha256` + Inspect EvalLog mapping)
- ADR-003 (model selection uses Inspect `provider/model-name` format)
- EPIC-001 ER-7 (Inspect breaking change risk)






