# Execution shape — swe_002 (wtforms__wtforms-614)

**Status: CATALOGUE entry (not yet runnable).**

## Why this is not runnable today

This pack was ingested from `nebius/SWE-rebench-V2`. Unlike the single-file reference task `be_01_jwt_auth` (one `solution.ts` graded by a Dockerised vitest run), a SWE-rebench instance is a **repository-level** task:

  - it needs a full checkout of `wtforms/wtforms` at base commit `848d28d67e45cda7a06c4c8ed2768e6a8cb1c016`;
  - it runs inside the prebuilt Docker image `docker.io/swerebenchv2/wtforms-wtforms:614-848d28d`;
  - the gold fix is a multi-file diff applied to that working tree;
  - correctness is decided by a test command (`pytest --no-header -rA --tb=line --color=no -p no:cacheprovider -W ignore::DeprecationWarning tests/test_fields.py tests/test_validators.py tests/test_widgets.py`) parsing FAIL_TO_PASS / PASS_TO_PASS results.

Our current executor only does **single-file** submissions, so this pack is a catalogue entry: the prompt, gold patch, test patch, and expectations are stored verbatim and become runnable once the executor supports repo-based tasks (checkout at base_commit + image pull + apply test patch + run test_cmd + parse).

## What is stored here

| File | Contents |
|---|---|
| `gold/gold.patch` | reference fix (the `patch` field) — verbatim |
| `gold/test.patch` | the test diff (the `test_patch` field) — verbatim |
| `gold/expectations.json` | FAIL_TO_PASS + PASS_TO_PASS test name lists |
| `task.yaml` | metadata, source provenance, candidate prompt |
| `rubric.yaml` | bugfix judge rubric (correctness gated by the test grid) |

## Provenance / licensing caveat

Dataset license: **CC-BY-4.0** (per-instance code license: **BSD-3-Clause**, recorded in `task.yaml`). NOTE: ADR-007's Tier-2 import allowlist (MIT / Apache-2.0 / BSD) and eligible-source list do **not** yet cover SWE-rebench-V2 or CC-BY-4.0. These packs are flagged `sourcing: hybrid` (Tier-2) but staged catalogue-only; promotion to a scored run needs an ADR-007 amendment plus the G4 contamination gate.
