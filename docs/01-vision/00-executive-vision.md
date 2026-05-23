# 00 — Executive vision

## One-sentence vision

POLLMEVALS is an evidence-based evaluation platform for choosing production LLM stacks, not just ranking raw models.

## Product thesis

Most LLM leaderboards compare isolated models. Production teams do not buy isolated models; they operate stacks: a model behind a gateway, wrapped in an agent CLI, tools, skills, memory, repository context, validator loops, observability, cost controls and region-specific latency constraints.

POLLMEVALS exists to answer this practical question:

> For task class X, budget Y and region Z, which LLM stack is the best operational choice?

## Core promise

- Evaluate complete stacks: model + CLI + tools + skills + memory + validator + framework.
- Publish raw outputs, prompts, seeds, versions, cost and reproducibility manifests.
- Use calibrated LLM judge panels for subjective parts and automatic evaluators for objective parts.
- Show cost-quality Pareto instead of one-dimensional rank.
- Track silent model drift over time.

## The first proof

The first public proof must be Phase 2 scaffolding ablation, because Phase 1 raw model comparison is not enough to define a new category.

Phase 2 asks:

> How much does each layer L0 → L8 add on a fixed hard task?

This is the point where POLLMEVALS becomes defensible.
