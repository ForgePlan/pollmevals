---
name: Bug
about: Behavior that deviates from a PRD success criterion or NFR
title: "[BUG] <one-line symptom>"
labels: type/fix
assignees: ''
---

## Symptom

What happened. Include log line, error class, or screenshot.

## Expected (per PRD / SPEC / ADR)

Reference the contract this bug violates:
- PRD: `prd-<slug>` SC-N or FR-N
- SPEC: `spec-<slug>` AC-N
- ADR: `adr-<slug>` (decision being broken)

## Reproduction

1. `make smoke-run RUN_TYPE=smoke`
2. Observe …
3. Expected: SC-N pass; Actual: …

## Environment

- Branch / commit: `main@<sha>`
- Python: `uv run python --version`
- Node: `node --version`
- LiteLLM proxy version: …
- Inspect AI version (per `pyproject.toml` pin): …

## Methodology version

`v0.1.0` (frozen). If bug is in a methodology-frozen contract, this needs an ADR not a bugfix.

## Run hash (if applicable)

`sha256:...` from manifest.json — links failed eval to a specific immutable artifact.

## Acceptance criteria for fix

- [ ] Regression test added in `apps/eval-core-py/tests/`
- [ ] Fix doesn't violate any [red line](../../CLAUDE.md#-red-lines)
- [ ] New EVID artifact links the fix to the affected PRD/SPEC/RFC
