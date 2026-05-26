<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); mediocre/sample-001 — Troubleshooting section missing AND `list` uses wrong flag `--filter` instead of `--category` AND tool name flips between `pollmevals fetch-task`, `pmf-task`, and `fetcher` -->
# pollmevals fetch-task

## Overview

`pmf-task` is the POLLMEVALS command-line client. It talks to the
catalog at `https://catalog.pollmevals.dev`, downloads packs, and runs
them against a Stack inside the evaluator sandbox.

## Installation

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
brew install pollmevals/tap/fetch-task
docker pull ghcr.io/pollmevals/fetch-task:latest
```

After install you can invoke the binary as `pollmevals fetch-task`,
`pmf-task`, or via `fetcher` (the legacy shim).

## Quick start

```sh
fetcher list --filter backend
pollmevals fetch-task show be_01
pmf-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

## Commands

### list

```
pmf-task list [--filter <cat>] [--difficulty <level>] [--json]
```

`--filter` accepts one of `backend`, `frontend`, `docs`, `review` and
restricts output to that category. `--difficulty` accepts `easy`,
`medium`, `hard`. `--json` switches to machine output.

Exit codes: `0` ok — `2` network — `3` auth.

### show

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

`--version` defaults to `latest`. `--json` for machine output.

Exit codes: `0` ok — `4` task not found — `5` version not found.

### validate

```
fetcher validate <path-or-id> [--strict]
```

`--strict` adds the calibration quorum check.

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>]
                                    [--out <dir>] [--dry-run]
```

`--stack` required, `--seed` defaults random, `--out` defaults
`./artifacts/`, `--dry-run` prints plan only.

Exit codes: `0` ok — `8` stack not found — `9` sandbox error —
`10` evaluator reported a low-scoring candidate.

## Configuration

Precedence (highest first): CLI flag → environment variable → config
file → compiled-in default. Default config path:
`$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`.

| Name | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | override catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. Read
`CONTRIBUTING.md`.

## Licence

MIT.
