# Imported benchmark task-packs — catalogue status

This directory's own-authored reference packs (`be_01_jwt_auth`, `fe_01_multistep_form`,
`doc_01_cli_readme`) are **Tier-1** (`sourcing: own`) and scored.

The 30 packs listed below were **imported from third-party benchmarks** to grow the
catalogue. They are all flagged `sourcing: hybrid` (ADR-007 Tier-2 — sourced-with-attribution)
and are **CATALOGUE-ONLY**: visible on the site's "what we evaluate" surface, but **not yet
runnable and not in any scored Run**. Each pack carries a `NOTE.md` with its execution shape
and per-source ADR-007 status.

## Why catalogue-only (two independent reasons)

1. **Executor support is missing.** Our StackExecutor (RFC-006) currently does *single-file*
   submissions graded by a fixed framework command (the `be_01` vitest path). The imports need
   runners that don't exist yet (see each pack's `NOTE.md`):
   - BigCodeBench → a **Python `unittest`/`pytest` runner** (closest to runnable).
   - LiveCodeBench → a **stdin/stdout harness** (feed `gold/tests.json` I/O pairs).
   - SWE-rebench → a **repo-checkout executor** (clone at `base_commit`, apply test patch, run `test_cmd`, parse FAIL_TO_PASS / PASS_TO_PASS).
2. **ADR-007 sourcing gates are open.** See the table below — two of the three sources are not
   on the ADR-007 Tier-2 allowlist, and **none** has passed the **G4 contamination gate** yet.

## Source matrix

| Source | Packs | Prefix | Dataset license | ADR-007 allowlist | G4 run | Gate before any SCORED use |
|---|---|---|---|---|---|---|
| **BigCodeBench** | 10 | `bcb-*` | Apache-2.0 | ✅ on allowlist (ADR-007 line 85) | ❌ | G4 only |
| **LiveCodeBench** (AtCoder 2025) | 10 | `lcb-atcoder-*` | MIT | ❌ off-allowlist (ADR lists *LiveBench*, a different benchmark) | ❌ | ADR-007 allowlist amendment **+** G4 |
| **SWE-rebench-V2** | 10 | `swe-*` | **CC-BY-4.0** (dataset) | ❌ off-allowlist **and** CC-BY is outside the Tier-2 license rule (MIT/Apache/BSD) | ❌ | ADR-007 allowlist **+ license-rule** amendment + per-instance handling + G4 |

### SWE-rebench per-instance code licenses

The dataset wrapper is CC-BY-4.0; the underlying repo code carries its own license, recorded in
each `task.yaml` provenance header. Mostly permissive, with two that need explicit handling:

| Pack | Repo code license |
|---|---|
| `swe-box-project-box-644`, `swe-bvanelli-actualpy-56`, `swe-elastic-synthetics-316`, `swe-webpack-contrib-copy-webpack-plugin-590` | MIT |
| `swe-crawler-commons-crawler-commons-227`, `swe-dtolnay-cxx-839`, `swe-gradleup-shadow-1448` | Apache-2.0 |
| `swe-wtforms-wtforms-614` | BSD-3-Clause |
| `swe-rust-bitcoin-rust-bitcoin-2255` | **CC0-1.0** (public domain — outside the MIT/Apache/BSD enumeration) |
| `swe-aio-libs-aiohttp-9047` | **custom** (needs manual license verification on GitHub) |

## The open decision (owner: maintainer)

Promoting any of these from catalogue to a **scored** Run requires an **ADR-007 amendment**
(ADR-007 line 88: "Adding a source requires updating this ADR"). The amendment must decide:

- Add **LiveCodeBench** (MIT) + **BigCodeBench** (already listed) explicitly to the allowlist.
- Whether/how to admit **SWE-rebench-V2** given its **CC-BY-4.0** dataset wrapper (broaden the
  license rule, or treat the per-instance code license as authoritative), plus the CC0 + custom
  instances.
- Re-affirm **G4 contamination gate** is BLOCKING for every imported sample regardless of tier.

Until that lands, these packs stay `sourcing: hybrid`, catalogue-only. Reproduce the import with
`apps/eval-core-py/scripts/ingest_{bigcodebench,livecodebench,swe_rebench}.py`.
