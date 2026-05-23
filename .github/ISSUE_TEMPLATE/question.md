---
name: Question / Discussion
about: Methodology clarification, design discussion, or research question
title: "[Q] <topic>"
labels: question
assignees: ''
---

## Context

What you're trying to understand or decide.

## Background you've already checked

- [ ] `docs/02-methodology/` (frozen v0.1.0)
- [ ] `docs/04-runbook/` (operational playbooks)
- [ ] `.forgeplan/{prds,rfcs,adrs,specs,evidence}/` (artifact graph — try `forgeplan search "<query>"`)
- [ ] `docs/adr/{0001,0002}` (legacy ADRs — hybrid stack + run immutability)

## Specific question

Be precise. Example: *"PRD-001 SC-2 says reproduce yields byte-equal evaluator_json. Does this include LLM determinism, or only evaluator determinism on cached raw_output?"*

(Answer for above: see ADR-002 — evaluator-only.)

## Trade-offs (if a decision)

- Option A: …
- Option B: …
- Constraints: …

## What outcome would satisfy this question?

- New ADR
- Update to existing ADR (`forgeplan_supersede`)
- New Note (90-day TTL, less formal)
- Update to PRD/SPEC/RFC wording
- Just confirmation in this thread
