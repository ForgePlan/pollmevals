<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); perfect/sample-001 — terse-formal Unix man-page voice; all sections present, exit codes tabulated, no filler -->
# pollmevals-fetch-task(1)

## Overview

Fetches POLLMEVALS task packs from a remote catalog, validates them
against the bundled JSON Schema (Draft 2020-12), and runs them inside
a sandboxed evaluator. Single static binary. No background daemon. No
mutation outside the cache and `--out` directories.

## Installation

| Channel | Command |
|---|---|
| Static binary | `curl -fsSL https://get.pollmevals.dev/fetch-task \| sh` |
| Homebrew | `brew install pollmevals/tap/fetch-task` |
| Docker | `docker pull ghcr.io/pollmevals/fetch-task:latest` |

Verify:

```sh
pollmevals fetch-task --version
# pollmevals fetch-task 0.1.0
```

## Quick start

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run  be_01 --stack raw-llm --seed 42 --out ./artifacts
```

Exit `0` on the full sequence indicates a clean smoke run.

## Commands

### list

```
pollmevals fetch-task list [--category CAT] [--difficulty LEVEL] [--json]
```

Flags: `--category` ∈ {backend, frontend, docs, review}; `--difficulty`
∈ {easy, medium, hard}; `--json` emits machine-readable output.

Exit codes: `0` ok — `2` network — `3` auth.

```
$ pollmevals fetch-task list --category docs --json
[{"id":"doc_01","version":"1.0","difficulty":"easy","title":"README for the pollmevals fetch-task CLI"}]
```

### show

```
pollmevals fetch-task show <task-id> [--version VER] [--json]
```

Flags: `--version` (default `latest`); `--json`.

Exit codes: `0` ok — `4` task not found — `5` version not found.

```
$ pollmevals fetch-task show be_01 --version 1.0
id=be_01 slug=jwt-auth-middleware-with-refresh category=backend
```

### validate

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

Flag: `--strict` adds calibration quorum check (≥5 samples per band).

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed INT]
                                    [--out DIR] [--dry-run]
```

Flags: `--stack` (required); `--seed` (default random); `--out` (default
`./artifacts/`); `--dry-run` prints the plan only.

Exit codes: `0` ok — `8` stack not found — `9` sandbox error —
`10` evaluator reported low quality.

```
$ pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --dry-run
plan: be_01@1.0 stack=raw-llm image=ghcr.io/pollmevals/eval-ts:0.1.0 seed=42
```

## Configuration

Precedence (highest first): CLI flag → environment → config file →
compiled-in default.

Config file path: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`. Override
with `--config <path>`.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir:   ~/.cache/pollmevals
log_level:   info
api_token:   ""
```

Environment variables:

| Name | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | pack cache directory |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | debug / info / warn / error |

## Troubleshooting

| Exit | Symptom | Fix |
|---|---|---|
| 2 | `list` returns "catalog unreachable" | `curl -fsS $POLLMEVALS_CATALOG_URL/health`; check egress 443 |
| 3 | `show` returns 401 | regenerate `POLLMEVALS_API_TOKEN` from the catalog UI |
| 6 | `validate` reports schema mismatch | re-run with `POLLMEVALS_LOG_LEVEL=debug` to print the JSON Pointer |
| 9 | `run` fails before evaluator starts | `docker version`; `docker pull ghcr.io/pollmevals/eval-ts:0.1.0` |

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. Read
`CONTRIBUTING.md` before opening a PR. Required pre-commit:
`moon run :test`. One reviewer per PR.

## Licence

MIT. See `LICENSE`.
