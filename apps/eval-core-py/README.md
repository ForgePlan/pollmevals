# pollmevals-eval-core

Python evaluation orchestrator for POLLMEVALS — the open evidence layer for choosing production LLM stacks.

## What this package does

`eval-core-py` is a thin wrapper around [Inspect AI](https://inspect.ai) that adds three capabilities not present in upstream:

1. **Hard run immutability** — SHA256 content-addressing, `chmod 0444` on publish, R2 object-lock (v0.2+).
2. **Per-evaluation cost attribution** — pricing snapshot taken at run start multiplied by token counts per evaluation row.
3. **Leaderboard hygiene** — Krippendorff alpha calculation, contamination flags (PRD-002).

The orchestrator does NOT reimplement Inspect's Task/Solver/Scorer/epochs — it invokes `inspect_ai.eval()` programmatically and projects Inspect's `EvalLog` into the POLLMEVALS manifest schema (SPEC-001).

## Package layout

```
src/
  contracts/      # Pydantic v2 models matching SPEC-001 (EvalRow, Manifest, etc.)
  orchestrator/   # Core modules: eval_caller, grid_runner, cost, journal, manifest, ...
  inspect_tasks/  # @task functions — one per (stack x task) combination
  evaluators/     # Automatic evaluators for be_01, fe_01, doc_01
tests/
  conftest.py     # Shared fixtures (no LLM calls — deterministic)
```

## How to run tests

```bash
# From repo root
moon run eval-core-py:test

# Directly (requires uv sync first)
cd apps/eval-core-py
uv sync --extra dev
uv run pytest tests/ -v
```

## How to run lint / typecheck

```bash
moon run eval-core-py:lint       # ruff + mypy --strict
moon run eval-core-py:typecheck  # mypy --strict only
```

## Relation to RFC-001

This package implements RFC-001 (v0.1 smoke run — implementation plan, orchestrator on Inspect AI).
The smoke run is a 45-row grid: 5 models x 3 tasks x 3 seeds, raw-llm stack, automatic metrics only,
budget under $50, region eu-central.

Entry points:
- `make smoke-run` — full run (Phase 2B, not yet wired)
- `make reproduce HASH=<x> EVAL_ID=<y>` — evaluator-only reproduce (Phase 2C)
- `make resume HASH=<x>` — crash recovery (Phase 2A wave 5)

See `docs/04-runbook/12-first-smoke-run-playbook.md` for the end-to-end playbook.
