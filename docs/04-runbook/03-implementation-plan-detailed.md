# 07 — Implementation Plan

## Phase 0 — Documentation and contracts

Deliverables:

- final repo tree;
- task schema;
- stack schema;
- run manifest schema;
- artifact schema;
- methodology v0.1;
- task authoring guide;
- first 3 task specs.

Exit criteria:

- task YAML validates;
- stack YAML validates;
- demo run manifest can be produced;
- documentation explains how to reproduce.

## Phase 1 — Deterministic smoke pipeline

Scope:

- 3 tasks: `be_01`, `fe_01`, `doc_01`;
- 5 models;
- 1 stack: `raw-llm`;
- 3 seeds;
- automatic metrics only;
- no judge panel yet.

Work items:

1. Implement LiteLLM call wrapper.
2. Implement task loader.
3. Implement prompt renderer.
4. Implement raw output artifact writer.
5. Implement evaluator sandbox for TypeScript tasks.
6. Implement documentation task evaluator.
7. Implement score aggregation.
8. Create `run manifest` and content hash.

Exit criteria:

- one command produces a complete run;
- all artifacts are content-hashed;
- run is reproducible from manifest;
- failures are stored, not hidden.

## Phase 2 — Judge panel

Scope:

- blind normalization;
- self-exclusion;
- 3 judges minimum;
- calibration set;
- median scoring;
- inter-judge agreement.

Exit criteria:

- calibration deviation is published;
- judge disagreement is measured;
- final score includes judge components only where needed.

## Phase 3 — Scaffolding ablation

Scope:

- L0 raw LLM;
- L1 system prompt;
- L2 tools;
- L3 skills;
- L4 file memory;
- L5 vector memory;
- L7 validator loop;
- 2–3 thick tasks.

Exit criteria:

- quality lift is measured per layer;
- cost overhead is measured;
- latency overhead is measured;
- at least one public post proves or disproves the key hypothesis.

## Phase 4 — Public product

Scope:

- `/methodology`;
- `/runs/[hash]`;
- `/leaderboards`;
- `/models/[slug]`;
- `/tasks/[slug]`;
- `/compare`.

Exit criteria:

- public data is understandable;
- raw artifacts are downloadable where safe;
- scoring methodology is transparent;
- run page can be cited.

## Phase 5 — Community and monetization

Only after traction:

- proposals;
- voting;
- API keys;
- datasets;
- sponsored disclosures;
- custom eval service.
