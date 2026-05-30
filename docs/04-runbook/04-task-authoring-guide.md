# 08 — Task Authoring Guide

## Goal

A POLLMEVALS task must be a reproducible, versioned, discriminative evaluation unit.

It must answer:

> Can this stack solve this realistic task under fixed constraints?

## Required task files

Each task should eventually have this structure:

```text
evals/tasks/{task_slug}/
  task.yaml
  prompt.md
  README.md
  gold/
    solution.*
    tests.*
    evaluator.sh
    package.json or pyproject.toml
    tsconfig.json if TypeScript
    calibration/
      perfect.*
      good.*
      mediocre.*
      poor.*
      broken.*
```

## Required metadata

`task.yaml` must include:

- `id`;
- `slug`;
- `version`;
- `category`;
- `difficulty`;
- `language`;
- `description`;
- `prompt_template`;
- `gold_solution_uri`;
- `test_path_uri` or evaluator reference;
- `evaluator_commands`;
- `success_criteria`;
- `weight_components`;
- `expected_tokens_in`;
- `expected_tokens_out`;
- `expected_wall_clock_seconds`;
- `calibration_set`;
- `license`;
- `real_world_source`.

## Task quality gates

Before a task enters active pool:

| Gate | Required condition |
|---|---|
| Gold validity | gold solution passes its own tests |
| Broken discrimination | broken calibration fails or scores near 0 |
| Medium discrimination | mediocre sample scores between poor and good |
| Runtime bound | evaluator p95 runtime stays within limit |
| Scoring bound | score never exceeds 10 or drops below 0 |
| License | source is original or permissioned |
| Contamination | unique phrases/code are not publicly indexed |
| Reproducibility | task can run in clean sandbox |
| Judge calibration | judge rank correlation with expected samples is acceptable |

## Category-specific requirements

### Coding tasks

Must include:

- executable tests;
- typecheck where applicable;
- lint or complexity check;
- clear input/output contract;
- no network dependency;
- deterministic seed where randomness exists.

### Documentation tasks

Must include:

- gold reference document;
- rubric;
- expected sections;
- factual constraints;
- scoring criteria;
- examples of good/medium/bad outputs.

### Code review tasks

Must include:

- diff or repository snapshot;
- ground truth bug list;
- severity labels;
- location matching policy;
- precision/recall scoring.

## Prompt authoring — closed-loop constraint (mandatory)

Every `prompt_template` **must** instruct the model to operate in closed-loop mode:

> The model must not ask follow-up or clarifying questions. It must choose all
> technical and architectural details itself, using only the information provided
> in the prompt. Anything not explicitly specified is the model's choice to make.

This constraint is non-negotiable. POLLMEVALS measures the **stack** (model +
scaffolding), not the operator. An evaluation that stalls waiting for
clarification produces no output, scores zero, and wastes a judge-panel call.

**Implementation** — include a line such as the following near the end of every
`prompt_template`, before any output-format instruction:

```
Do not ask clarifying questions. If any detail is unspecified, choose
the most idiomatic approach and proceed. Output only the requested artifact.
```

The three existing reference tasks (`be_01`, `fe_01`, `doc_01`) satisfy this
constraint via the closing line "Output only the code for solution.ts. No prose,
no markdown fences." — an equivalent closed-loop instruction. New tasks must
include an explicit equivalent.

## Versioning rule

Changing prompt, tests, evaluator, scoring weights or gold solution creates a new task version.

Do not edit old task versions in place after they have been used in a public run.
