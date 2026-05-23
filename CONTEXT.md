# CONTEXT.md — Ubiquitous Language

Domain terminology for POLLMEVALS. This file is the **source of truth** for what each term means. When in doubt, link here.

Auto-loaded by Claude Code via `@CONTEXT.md` import in `CLAUDE.md`.

---

## Project mission

POLLMEVALS is an **open evidence layer for choosing production LLM stacks**. It evaluates not raw models, but **complete scaffolding stacks**: model + agent CLI + tools + skills + memory + validator loops, with cost, latency, reproducibility, and judge agreement.

**Thesis**: a cheap model with the right scaffolding often beats an expensive one without it, at a fraction of the price. Goal — prove it with numbers.

---

## Core domain (in dependency order)

### Model

An LLM identity (e.g. `claude-sonnet`, `qwen-2.5-14b-local`, `gpt-5`) plus a version tag. Same model from different providers (e.g. Claude via Anthropic API vs. OpenRouter) counts as **same model**; the provider is captured separately.

### ModelProvider

Where a model is hosted. POLLMEVALS supports:
- **Cloud APIs**: OpenRouter (aggregator), direct vendor APIs (Anthropic, OpenAI, Google, xAI)
- **Open-weight fast**: Cerebras
- **Self-hosted**: Runpod vLLM
- **Local**: Ollama (development / smoke runs)

A `ModelProvider` row carries a **pricing snapshot** taken at run-execution time. Pricing drift is captured by repeating the snapshot on each Run.

### Stack

A composition that wraps a base Model. Specified by a YAML adapter (`stacks/<slug>/stack.yaml`) declaring which scaffolding layers L0–L8 are present + the execution contract (input/output, sandbox needs, limits).

Three reference stacks:
- `raw-llm` — L0 only (bare LLM, no scaffolding)
- `claude-code-basic` — L1 + L2 (system prompt + tools, Claude Code CLI)
- `forgeplan-framework` — L3+L4+L6+L7+L8 (skills + file memory + subagents + validator + ForgePlan framework)

A Stack is the **unit POLLMEVALS evaluates**.

### Task

A versioned evaluation task. Each `Task` has:
- `slug` + `version` (semver-ish; bumping version creates a new immutable task)
- category (`backend`, `frontend`, `docs`, `review`, …)
- difficulty (`easy`, `medium`, `hard`)
- prompt template (what the model sees)
- gold solution (the canonical correct answer — kept private once task goes public)
- evaluator (script that scores the model's output against gold)
- calibration set (perfect / good / mediocre / poor / broken examples for judge calibration)
- scoring weights (`weight_components` map)

Three reference tasks in v0.1:
- `be_01_jwt_auth` — JWT auth middleware in Express (TypeScript)
- `fe_01_multistep_form` — accessible multi-step form (React)
- `doc_01_cli_readme` — README for a CLI tool (Markdown)

### Run

An immutable snapshot of one evaluation pass. Carries:
- `run_hash` (content-addressed, includes all input snapshots)
- `run_type` (`smoke`, `weekly`, `flagship_triggered`, `calibration`, `ablation`)
- frozen models, tasks, stacks, methodology version
- set of `evals` (the actual results)
- aggregate cost + token totals

**Immutability rule (ADR-0002)**: once a Run is `published`, none of its data is edited in place. Errors → new Run + `supersedes` link.

### Eval

One execution within a Run: `(model, stack, task, seed, region) → output`. Contains:
- raw output (URI to R2)
- normalised output (after stripping greetings, signatures)
- automatic metrics (test pass rate, lint errors, complexity, …)
- judge scores (from JudgePanel)
- final_score (0–10, normalised, weighted)
- TTFT + total latency + tokens in/out + cost

### Artifact

Any content-addressed output of an Eval. Categories:
- `raw_output` — what the model produced verbatim
- `normalized_output` — after normalisation pipeline
- `stdout` / `stderr` — from sandbox execution
- `evaluator_json` — structured metrics output
- `trace_json` — tool calls, file mutations (for Stacks with L2+ scaffolding)
- `judge_reasoning` — judge model's chain-of-thought (for audit)

Naming: `r2://runs/{run_hash}/evals/{eval_id}/{type}-{sha256}.{ext}`

### Judgment

One judge model's score on one normalised submission. Carries:
- judge_model_id (which LLM did the judging)
- judge_order (randomised position to mitigate position bias)
- rubric_version
- rubric_scores_json (per-criterion scores)
- total_score (0–10)
- agreement_with_consensus (this judgment's deviation from panel median)

### JudgePanel

The set of judges scoring a given Eval. Rules:
- Minimum 3, ideally 5
- Different model families (Claude + GPT + Gemini + open-weight)
- **Never includes the eval's own model** (self-judging is the cardinal sin)
- Blind labels — judge doesn't know which model produced the output
- Median scoring across panel

### CalibrationRun

A judge's performance on known-score samples. Detects:
- Mean absolute deviation from expected score
- Rank correlation with expected order
- Length bias (over-rewards verbose answers?)
- Self-enhancement (would the judge score its own family higher?)

Threshold for publication: MAD ≤ 1.5 on 0–10 scale.

### MethodologyVersion

Versioned bundle of rules: scoring weights + judge policy + task lifecycle policy. Every Run references one. **Frozen** for v0.1.0 in `docs/02-methodology/`.

Methodology changes go through an ADR + new MethodologyVersion. Old Runs remain bound to their MethodologyVersion forever.

---

## Composite / quality terms

### Quality metric: Krippendorff α

Inter-judge agreement metric. Range 0–1. **Threshold for publication: ≥ 0.70.**

### Quality metric: Bootstrap 95% CI

Always reported alongside means and medians. Never publish a delta unless the CIs don't overlap.

### Pareto frontier

A Stack `A` dominates Stack `B` if `A` has both higher-or-equal quality **and** lower-or-equal cost. The set of non-dominated Stacks is the Pareto frontier — the only honest way to compare cost-vs-quality tradeoffs.

### Drift detection

For closed-API models (Claude, GPT, Gemini), the vendor may silently update the model. Drift detection compares this week's score on baseline tasks vs. last week's. Delta > 2σ → public alert.

### Contamination

A Task is **contaminated** if it (or near-paraphrases) appears in any model's training data. Monthly check: search GitHub + Stack Overflow + public datasets for prompt fragments. Compromised Tasks are retired and replaced.

---

## Forgeplan terms (cross-project)

These apply to all forgeplan-aware projects, not just POLLMEVALS:

| Term | Meaning |
|---|---|
| **R_eff** | Effective reliability of an artifact. `R_eff = min(evidence_scores)` — weakest link, never average. Active artifact with no evidence linked → R_eff = 0.0 by definition. |
| **Congruence Level (CL)** | How close an evidence is to the artifact's context. CL3 (same context) → penalty 0.0; CL2 → 0.1; CL1 → 0.4; CL0 (opposed) → 0.9. |
| **ADI** | Abduction → Deduction → Induction reasoning cycle. Mandatory at Deep+ depth. |
| **Depth** | Tactical / Standard / Deep / Critical — drives how many artifact kinds a task requires. |
| **Slug** | Canonical artifact ID (`prd-auth-system`). Immutable. Use this in `Refs:` before merge. |
| **Assigned number** | Display ID (`PRD-074`). Assigned by CI on merge to default branch. Write-once. |

---

## Anti-glossary (what these are NOT)

| Term | Common misuse | Actual meaning |
|---|---|---|
| **Model** | "GPT-5 on OpenRouter is a different model" | No — same Model, different ModelProvider. |
| **Stack** | "Just the agent CLI" | No — Stack includes base Model + all L0–L8 scaffolding decisions. |
| **Run** | "One inference call" | No — a Run is the full pass over many evals. One inference = one Eval (or a step inside one). |
| **Judge** | "A human grader" | No — POLLMEVALS judges are LLMs. Humans only appear in calibration v2.0. |
| **Score** | "The number" | No — always a distribution (median + CI). Single numbers without CI are misleading. |
| **Cost** | "What the model API charged" | No — total cost includes judge calls (5× per eval typically), retries, and aggregator overhead. |
