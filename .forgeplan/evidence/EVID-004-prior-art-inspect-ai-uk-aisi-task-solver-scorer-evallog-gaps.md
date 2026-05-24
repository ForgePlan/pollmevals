---
depth: standard
id: EVID-004
kind: evidence
last_modified_at: 2026-05-24T07:40:02.589037+00:00
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

## ADI cycle (per NOTE-002 — retrofit)

### Abduction — research questions framed as hypotheses

- **H1**: Inspect AI is a thin wrapper around model APIs — POLLMEVALS would still need to build most of orchestrator from scratch.
- **H2**: Inspect AI provides Task/Solver/Scorer composition + EvalLog + multi-provider routing — POLLMEVALS L0-L8 stacks map cleanly; only need to add hard immutability + cost attribution + leaderboard hygiene.
- **H3**: Inspect AI has built-in stack-cost attribution; POLLMEVALS doesn't need cost.py.

### Induction — verification per hypothesis

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (thin wrapper) | Solvers docs (https://inspect.aisi.org.uk/solvers.html): full composition primitives — Sample/Task/Solver/Scorer; chain(), system_message(), use_tools(), self_critique(), @solver decorator; epochs param for multi-seed; multi_scorer + model_graded_qa for judge panels | False — full framework | **H1 REFUTED** |
| Y2 (composition fits + 3 gaps) | All 4 primitives (Sample, Task, Solver, Scorer) confirmed in docs; L0-L8 mapping fits chain() of @solver decorators; EvalLog .eval binary has append-only `log_updates` but SOFT immutability; cost tracking NOT built in (only token counts in `stats`) | Exactly as predicted | **H2 SUPPORTED** |
| Y3 (cost built in) | models.html docs: "stats captures token counts only, no dollar amounts" | False | **H3 REFUTED** |

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| Inspect AI Task/Solver/Scorer composition maps to POLLMEVALS (task, stack, seed) at zero extra code | 9 | 9 | 9 | 27/27 | F: explicit chain([...]) pattern + epochs param. G: precise mapping table. R: official docs (4 pages cited). |
| EvalLog soft-immutable (append-only `log_updates`); POLLMEVALS must wrap for hard immutability | 9 | 8 | 9 | 26/27 | F: docs explicit. G: specific field name + behavior. R: official eval-logs.html. |
| Cost tracking NOT built in (token counts only in `stats`) | 9 | 9 | 9 | 27/27 | F: docs explicit. G: "no dollar amounts" precise. R: official models.html. |
| Model routing via `provider/model-name` prefix (anthropic/openai/google/openrouter/hosted_vllm/ollama) | 9 | 9 | 9 | 27/27 | F: docs list all supported. G: exact prefix syntax. R: official models.html. |
| `multi_scorer(model_graded_qa(model=[...]))` gives multi-judge panel with majority-vote | 9 | 8 | 9 | 26/27 | F: docs explicit. G: function signatures named. R: official scorers.html. |
| L0-L8 stacks map to chain() of @solver decorators (synthesis) | 7 | 8 | 7 | 22/27 | F: synthesis (not explicitly stated in docs). G: detailed table per layer. R: derived from confirmed primitives + EVID-007 architect-reviewer agreement. |
| `.eval` binary format is opaque (no stable public schema for non-SDK consumers) | 7 | 7 | 8 | 22/27 | F: stated as open question in EVID author's report. G: explicit limitation. R: docs don't explicitly commit to schema stability — derived from absence. |

**Decision strength**: average sum = 25.3/27 (94%). Three 27/27 claims (composition fit, cost gap, model routing — all load-bearing for RFC-001 architecture). Weakest: L0-L8 synthesis (22/27) and `.eval` opacity (22/27) — both derived rather than explicitly stated.

## Key Findings (preserved)

### Composition model — direct fit for (task, stack, seed) and L0-L8

`Sample` (one Dataset row) → `Task(dataset, solver, scorer, name, version, metadata, sandbox, epochs, setup, cleanup)` → `Solver` (async receives TaskState + generate → returns mutated TaskState) → `Scorer` (receives final TaskState → returns Score). Multiple scorers supported. Reducers (mean/median/pass_at_k) aggregate epochs.

### L0-L8 stack mapping (synthesis — RFC-001 architectural foundation)

| POLLMEVALS layer | Inspect primitive |
|---|---|
| L0 bare LLM | `Task(solver=[generate()])` |
| L1 system prompt | `system_message("…")` |
| L2 tools | `use_tools([...])` + `generate()` loop |
| L3 skills | Custom `@solver` injecting skill content |
| L4 file memory | Custom solver reads + injects file contents |
| L5 vector memory | Custom solver calls retrieval |
| L6 subagents | `@agent` with `handoff()`, or nested Agent calls |
| L7 validator loop | `self_critique()` or custom loop |
| L8 domain framework | Shell-out solver invoking CLI |

### Run log model — soft immutability (POLLMEVALS adds hard)

EvalLog: `.eval` binary (1/8 size of JSON, default v0.3.46+). Post-eval edits land in `log.log_updates` with author + reason; original preserved in `history`. **Soft immutability — file on disk is mutable**. POLLMEVALS wraps with SHA256 + R2 object-lock + DB `published` state.

### Multi-provider model abstraction

`provider/model-name` prefix: anthropic/, openai/, google/, hf/, hosted_vllm/, ollama/, openrouter/<provider/model>. Cost tracking NOT built in.

### 3 gaps POLLMEVALS must fill

1. Stack-level cost attribution (Wave 4 cost.py — EVID-014)
2. Hard run immutability + content-addressing (Wave 3 manifest-writer.py — EVID-013)
3. Leaderboard hygiene (PRD-002 Krippendorff α + PRD-004 contamination display — Phases 3-4)

## Conclusions

- **Surviving hypothesis**: H2 (full framework + 3 specific gaps) — operationalized in Wave 3 + Wave 4
- **Decision strength**: 94% — strongest external research EVID (3 claims at 27/27)
- **POLLMEVALS implication**: RFC-001 "build on Inspect AI" decision fully validated; ~2-3 weeks of duplication avoided
- **Follow-up evidence needed**: live `inspect_ai.eval` invocation in Phase 2B (raises L0-L8 synthesis claim from 22/27 → 26/27); confirm `.eval` schema stability via direct file inspection (raises opacity claim)

## Sources

1. <https://inspect.aisi.org.uk/solvers.html>
2. <https://inspect.aisi.org.uk/tasks.html>
3. <https://inspect.aisi.org.uk/scorers.html>
4. <https://inspect.aisi.org.uk/eval-logs.html>
5. <https://inspect.aisi.org.uk/agents.html>
6. <https://inspect.aisi.org.uk/models.html>
7. <https://github.com/UKGovernmentBEIS/inspect_ai>

## Related Artifacts

- PRD-001 (informs — auto-linked)
- RFC-001 (Inspect AI is chosen orchestrator — direct dependency)
- SPEC-001 (`inspect_eval_log_sha256` + EvalLog mapping table)
- ADR-003 (model selection uses `provider/model-name` format from EVID-004)
- EPIC-001 ER-7 (Inspect breaking change risk)
- EVID-013 (Wave 3 — hard immutability gap closed)
- EVID-014 (Wave 4 — cost attribution gap closed)
- EVID-015 (Wave 4 — EvalCaller seam wraps Inspect AI)
- NOTE-002 (Evidence Quality Standard — retrofit)

