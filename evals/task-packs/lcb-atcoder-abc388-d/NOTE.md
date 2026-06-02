# Execution shape — coming-of-age-celebration

**Source**: `livecodebench/code_generation_lite` (release_v6, problems released 2025-01 onward (post-2024 cutoff)). License: MIT.

**Oracle**: the test cases in `gold/tests.json` (3 public + 40 private input/output pairs). LiveCodeBench ships **no reference solution** — the hidden tests are the sole objective oracle.

**Problem type**: stdin/stdout.

Self-contained stdin/stdout problem: the candidate writes a whole program that reads stdin and writes stdout. A test runner must pipe each test `input` into the program and diff its stdout against `output`.

## Runnable now?

**Needs a test-runner.** The current executor (see `be_01_jwt_auth`) does a single-file write + a framework test command (vitest/pytest against a fixed spec). These LCB problems instead need a generic **stdin/stdout harness** that feeds each `gold/tests.json` case to the candidate program and compares output. That harness does not exist in the executor yet, so these packs are **ingested-but-not-yet-runnable** until a `tests.json` runner is added.

They are *closer* to runnable than repo-based tasks (no git apply, no multi-file project, no dependency install — just a script + I/O pairs), so wiring the runner is a small, well-scoped follow-up.

## ADR-007 sourcing status

`sourcing: hybrid` (Tier-2 sourced-with-attribution). **Catalogue-only — not scored.**
Two ADR-007 gates are still open:

- **Allowlist**: LiveCodeBench is *not* on the ADR-007 Tier-2 eligible-source list
  (the ADR lists *LiveBench*, a different benchmark). Adding it requires an ADR-007
  amendment (ADR-007 line 88: "Adding a source requires updating this ADR").
- **G4 contamination gate**: not yet run. Problems are post-2024-cutoff (released
  2025-01+), so contamination risk is low, but the gate is still required before
  any scored use.

License (MIT) satisfies the Tier-2 license rule; a per-pack `LICENSE.md` is deferred
until the allowlist amendment lands.
