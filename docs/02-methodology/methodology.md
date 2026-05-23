# Methodology v0.1.0

## Principle

POLLMEVALS evaluates production LLM stacks, not isolated models.

## Scaffolding ladder

| Level | Name | Meaning |
|---|---|---|
| L0 | Bare LLM | direct model call without structured system prompt |
| L1 | System prompt | role, constraints, output contract |
| L2 | Tools | function calling, MCP tools, repository access tools |
| L3 | Skills | reusable task-specific instructions or skill packs |
| L4 | File memory | CLAUDE.md, AGENTS.md, repo-local memory, scratchpad |
| L5 | Vector memory | semantic memory: mem0, Zep, Letta, custom retriever |
| L6 | Subagents | delegated agents, specialist workers |
| L7 | Validator loop | test-run-fix, reflection, verifier, retry policy |
| L8 | Domain framework | ForgePlan, OpenSpec, domain-specific harness |

## Scoring model

The final score is task-type dependent. Objective code tasks combine automatic metrics and judge panel scoring. Documentation and architecture tasks rely more on calibrated judges.

## Publication rules

1. No result is public without a run manifest.
2. No run is changed after completion.
3. No judge scores itself or its model family when avoidable.
4. Median scoring is used for judge panel aggregation.
5. Confidence intervals are reported for aggregate results.
6. Negative findings are published when differences are not meaningful.
