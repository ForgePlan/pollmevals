<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); good/sample-003 — all sections present but `POLLMEVALS_LOG_LEVEL` default is documented as `warn` instead of `info` (one env-var default wrong) -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` retrieves POLLMEVALS task packs from the catalog,
validates them against a bundled JSON Schema (Draft 2020-12), and runs
them against a Stack inside a sandboxed evaluator. Single static binary,
Homebrew tap, Docker image.

## Installation

**Static binary**:

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

**Homebrew**:

```sh
brew install pollmevals/tap/fetch-task
```

**Docker**:

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
docker run --rm ghcr.io/pollmevals/fetch-task --version
```

## Quick start

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

## Commands

### list

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Categories: `backend`, `frontend`, `docs`, `review`. Difficulty:
`easy`, `medium`, `hard`. `--json` for machine output.

Exit codes: `0` ok — `2` network failure — `3` auth failure.

```
$ pollmevals fetch-task list --category backend
ID      VERSION  DIFFICULTY  TITLE
be_01   1.0      medium      JWT auth middleware with refresh rotation
```

### show

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

`--version` defaults to `latest`. `--json` for machine output.

Exit codes: `0` ok — `4` task not found — `5` version not found.

```
$ pollmevals fetch-task show be_01
id:        be_01
slug:      jwt-auth-middleware-with-refresh
version:   1.0
```

### validate

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

`--strict` enforces calibration quorum (≥5 samples per band).

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>]
                                    [--out <dir>] [--dry-run]
```

`--stack` is required. `--seed` defaults to random. `--out` defaults to
`./artifacts/`. `--dry-run` validates and prints the plan only.

Exit codes: `0` ok — `8` stack not found — `9` sandbox error —
`10` evaluator reported a low-scoring but well-formed candidate.

```
$ pollmevals fetch-task run be_01 --stack claude-code-basic --seed 42 --dry-run
plan:
  task:   be_01 @ 1.0
  stack:  claude-code-basic
  image:  ghcr.io/pollmevals/eval-ts:0.1.0
  seed:   42
  out:    ./artifacts/
```

## Configuration

Precedence (highest first): CLI flag → environment variable → config
file → compiled-in default. Default config path:
`$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir:   ~/.cache/pollmevals
log_level:   info
api_token:   ""
```

| Name | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | override catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `warn` | `debug` / `info` / `warn` / `error` |

## Troubleshooting

| Exit | Subcommand | Symptom | Fix |
|---|---|---|---|
| 2 | `list` | catalog unreachable | `curl -fsS $POLLMEVALS_CATALOG_URL/health`; check egress 443 |
| 3 | `show` | 401 from catalog | regenerate `POLLMEVALS_API_TOKEN` |
| 6 | `validate` | schema violation | re-run with `POLLMEVALS_LOG_LEVEL=debug` |
| 9 | `run` | sandbox unavailable | `docker version`; `docker pull ghcr.io/pollmevals/eval-ts:0.1.0` |

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. Read
`CONTRIBUTING.md`. Required pre-commit: `moon run :test`.

## Licence

MIT. See `LICENSE`.
