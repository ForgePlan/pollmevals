# 18 — Agent Handoff Brief

## Mission

Build POLLMEVALS as a reproducible evaluation system for production LLM stacks.

The first milestone is not a beautiful website. The first milestone is a trustworthy smoke run that produces immutable artifacts and a reproducible manifest.

## Non-negotiables

- Do not edit completed run results in place.
- Do not compare task versions as if they are the same.
- Do not let a model judge itself.
- Do not hide failed evals.
- Do not publish a leaderboard without methodology.
- Do not make paid/sponsored features before disclosure policy exists.
- Do not run untrusted code outside sandbox.

## Build order

1. Contracts.
2. Task specs.
3. Gold/evaluator files.
4. LiteLLM wrapper.
5. Raw run execution.
6. Artifact persistence.
7. Automatic scoring.
8. Manifest generation.
9. Reproduction script.
10. Judge panel.
11. Site pages.
12. API/datasets.

## First concrete implementation target

Create executable `be_01_jwt_auth` task pack:

- TypeScript Express middleware prompt;
- gold solution;
- Vitest tests;
- ESLint complexity check;
- TypeScript strict check;
- evaluator shell script;
- five calibration implementations.

Then run:

```text
3 tasks × 5 models × 3 seeds × 1 stack × 1 region = 45 evals
```

No judge panel in the first deterministic smoke.

## Definition of done for v0.1

A new engineer can clone the repository, set `.env`, run one command and produce a local run manifest with artifacts.
