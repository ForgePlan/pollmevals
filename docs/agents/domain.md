# Domain glossary

Quick reference for agents working on POLLMEVALS. For the full domain model see `docs/03-architecture/02-domain-model.md` and `CONTEXT.md`.

## Core entities

| Term | Meaning |
|---|---|
| **Model** | LLM identity (`claude-sonnet`, `qwen-2.5-14b-local`, `gpt-5`) + version tag. |
| **ModelProvider** | Where the model is hosted (OpenRouter, Cerebras, Runpod vLLM, Ollama, direct API) + pricing snapshot at run time. |
| **Stack** | A composition: base model + agent CLI + scaffolding layers (L0–L8). The unit POLLMEVALS evaluates. |
| **Task** | A versioned eval task: prompt template + gold solution + evaluator + calibration set + scoring weights. |
| **Run** | An immutable snapshot of one evaluation pass: hash, models/tasks/stacks/methodology versions frozen, set of evals. |
| **Eval** | One execution: `(model, stack, task, seed, region) → output`. Has automatic metrics + judge scores. |
| **Artifact** | Content-addressed output: raw_output, normalized_output, stdout, stderr, evaluator_json, trace_json, judge_reasoning. Stored at `r2://runs/{hash}/evals/{eval_id}/...`. |
| **Judgment** | One judge model's score on one normalised submission (rubric JSON + total score). |
| **JudgePanel** | The set of judges scoring a given eval — minimum 3, ideally from different families, never includes the eval's own model. |
| **CalibrationRun** | Performance of a judge on known-score samples (perfect/good/mediocre/poor/broken) to detect drift. |
| **MethodologyVersion** | Versioned bundle: scoring weights + judge policy + task lifecycle. Every Run references one. |
| **EvidencePack** | Forgeplan evidence artifact with structured fields (verdict, congruence_level, evidence_type). Drives R_eff. |

## Scaffolding ladder (L0–L8)

| Level | What |
|---|---|
| L0 | bare LLM (raw completion, no system prompt) |
| L1 | system prompt (role, persona, context priming) |
| L2 | tools (function calling, MCP) |
| L3 | skills (Anthropic Skills, AGENTS.md, Cursor rules — reusable instructions) |
| L4 | file memory (CLAUDE.md, scratchpad files) |
| L5 | vector memory (mem0, Hindsight, Letta, Zep) |
| L6 | subagents / multi-agent (Claude Code subagents, AutoGen, CrewAI) |
| L7 | validator loop (test-run-fix, AlphaCodium, Reflexion) |
| L8 | domain framework (ForgePlan, OpenSpec, voltagent) |

## Scoring (key formulas)

| Task type | Formula |
|---|---|
| Coding | `0.40 × correctness + 0.15 × coverage + 0.10 × complexity + 0.10 × lint + 0.10 × type_safety + 0.15 × pattern_match` |
| Frontend | `0.35 × correctness + 0.20 × accessibility + 0.15 × coverage + 0.10 × type_safety + 0.10 × ux_states + 0.10 × pattern_match` |
| Documentation | mean of 5 equal-weight judge criteria: structural_completeness, factual_accuracy, clarity, actionability, consistency |
| Review | `0.40 × recall + 0.30 × precision + 0.20 × severity_match + 0.10 × fix_quality` |

All normalised to 0–10. Aggregation: median per criterion (not mean), bootstrap 95% CI, never hide variance.

## Judge policy (must-knows)

1. **Model never judges itself.** No exceptions.
2. **Minimum 3 judges.** Prefer different vendor families.
3. **Median scoring**, not mean (robust to outliers).
4. **Blind labels + anonymised submissions** — judges shouldn't be able to ID the candidate.
5. **Calibration**: each judge runs known-score samples before production scoring.
6. **Publication threshold**: Krippendorff α ≥ 0.70, calibration MAD ≤ 1.5, model-ID probe accuracy ≤ 30%.

## Run lifecycle (immutability — ADR-0002)

`created → executing → evaluating → judging → aggregating → published`

After `published`:
- raw outputs, scores, manifest **never edited in place**
- errors found later → new run + `supersedes` link, original kept as historical record
- artifacts content-addressed (SHA256 in filename)

## Forgeplan terms (general — not POLLMEVALS-specific)

| Term | Meaning |
|---|---|
| **R_eff** | Effective reliability of an artifact. `R_eff = min(evidence_scores)` — weakest link, never average. |
| **Congruence Level (CL)** | How close an evidence is to the artifact's context. CL3 = same context (penalty 0.0), CL0 = opposed (penalty 0.9). |
| **ADI** | Abduction → Deduction → Induction reasoning cycle. Mandatory at Deep+ depth. |
| **Depth** | Tactical / Standard / Deep / Critical — drives how many artifact kinds are required for a task. |
| **Slug + assigned number** | Two-layer artifact ID. Slug (`prd-auth-system`) is canonical and immutable. Display number (`PRD-074`) is assigned by CI on merge. Before merge use slug only in `Refs:`. |
