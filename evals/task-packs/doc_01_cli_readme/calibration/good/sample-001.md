<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); good/sample-001 — all sections present but one flag name is wrong (--cat instead of --category) consistently -->
# pollmevals fetch-task

## Overview

A CLI for working with POLLMEVALS task packs. It lists what the catalog
has, shows a single pack's metadata, validates a pack against the
bundled schema, and runs a pack against a Stack inside the evaluator
sandbox.

## Installation

```sh
# static binary
curl -fsSL https://get.pollmevals.dev/fetch-task | sh

# Homebrew
brew install pollmevals/tap/fetch-task

# Docker
docker pull ghcr.io/pollmevals/fetch-task:latest
```

Verify:

```sh
pollmevals fetch-task --version
```

## Quick start

```sh
pollmevals fetch-task list --cat backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

## Commands

### list

```
pollmevals fetch-task list [--cat <category>] [--difficulty <level>] [--json]
```

Flags: `--cat` (one of `backend`, `frontend`, `docs`, `review`);
`--difficulty` (one of `easy`, `medium`, `hard`); `--json` emits
machine-readable output.

Exit codes: `0` success — `2` network failure — `3` auth failure.

```
$ pollmevals fetch-task list --cat backend
ID      VERSION  DIFFICULTY  TITLE
be_01   1.0      medium      JWT auth middleware with refresh rotation
```

### show

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

`--version` defaults to `latest`. `--json` emits machine output.

Exit codes: `0` ok — `4` task not found — `5` version not found.

```
$ pollmevals fetch-task show be_01
id:        be_01
slug:      jwt-auth-middleware-with-refresh
version:   1.0
category:  backend
```

### validate

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

`--strict` requires ≥5 calibration samples per band.

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>]
                                    [--out <dir>] [--dry-run]
```

`--stack` is required. `--seed` defaults to a random int. `--out`
defaults to `./artifacts/`. `--dry-run` prints the plan and exits.

Exit codes: `0` success — `8` stack not found — `9` sandbox error —
`10` evaluator reported a low-scoring candidate.

```
$ pollmevals fetch-task run be_01 --stack claude-code-basic --seed 42 --dry-run
plan: be_01@1.0 stack=claude-code-basic seed=42 out=./artifacts/
```

## Configuration

Precedence (highest first): CLI flag → environment variable → config
file → compiled-in default. Default config file path:
`$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir:   ~/.cache/pollmevals
log_level:   info
api_token:   ""
```

| Variable | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | override catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

## Troubleshooting

- `exit 2` after `list` — catalog unreachable. Try
  `curl -fsS $POLLMEVALS_CATALOG_URL/health`.
- `exit 3` after `show` — auth failure. Regenerate
  `POLLMEVALS_API_TOKEN`.
- `exit 6` after `validate` — schema violation. Re-run with
  `POLLMEVALS_LOG_LEVEL=debug`.
- `exit 9` after `run` — sandbox error. `docker version`;
  `docker pull ghcr.io/pollmevals/eval-ts:0.1.0`.

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. See
`CONTRIBUTING.md`. Required pre-commit: `moon run :test`.

## Licence

MIT. See `LICENSE`.
