# DOC-01 — CLI README

## Task type

documentation task

## Purpose

This folder documents the intended full task pack for `doc_01_cli_readme`. The source YAML spec is available in `evals/tasks/doc_01_cli_readme/task.yaml`.

## Required final files

```text
task-packs/doc_01_cli_readme/
  README.md
  prompt.md
  task.yaml
  gold/
    solution file
    evaluator file
    calibration variants
```

## Current state in this documentation archive

This documentation pack defines the task context, expected structure, scoring intent and implementation checklist. The executable gold/test files must be implemented in the main repository before this task can enter the active benchmark pool.

## Quality gate before activation

- gold solution passes;
- evaluator runs in clean sandbox;
- broken calibration scores low;
- good calibration scores high;
- task has no external network dependency;
- task runtime is bounded;
- license/provenance are clear.
