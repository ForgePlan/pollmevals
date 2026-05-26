<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); mediocre/sample-003 — all sections present but the `run` subcommand is factually wrong throughout: invented `--profile` and `--retries` flags, wrong exit code mapping, no `--dry-run` -->
# pollmevals fetch-task

## Overview

POLLMEVALS task-pack CLI. Lists, shows, validates, and runs task packs
from the catalog at `https://catalog.pollmevals.dev`.

## Installation

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh   # binary
brew install pollmevals/tap/fetch-task                  # Homebrew
docker pull ghcr.io/pollmevals/fetch-task:latest        # Docker
```

## Quick start

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --profile fast --retries 2
```

## Commands

### list

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Categories: `backend`, `frontend`, `docs`, `review`. Difficulty: `easy`,
`medium`, `hard`.

Exit codes: `0` ok — `2` network — `3` auth.

### show

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

`--version` defaults to `latest`.

Exit codes: `0` ok — `4` task not found — `5` version not found.

### validate

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--profile <p>]
                                    [--retries <n>] [--out <dir>]
```

`--stack` is required. `--profile` selects one of `fast` / `accurate` /
`debug` (default `accurate`). `--retries` controls how many times the
evaluator restarts on a sandbox failure (default `1`). `--out` defaults
to `./artifacts/`.

Exit codes:

- `0` success
- `1` general failure
- `2` invalid arguments
- `3` evaluator timeout

```
$ pollmevals fetch-task run be_01 --stack raw-llm --profile fast
running be_01 against raw-llm (profile=fast retries=1)
```

## Configuration

Precedence (highest first): CLI flag → environment variable → config
file → compiled-in default. Default config path:
`$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`.

| Name | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

## Troubleshooting

- `exit 2` from `list` → catalog unreachable; check egress 443.
- `exit 3` from `show` → 401 from the catalog; regenerate the API token.
- `exit 6` from `validate` → schema violation; re-run with
  `POLLMEVALS_LOG_LEVEL=debug`.
- `exit 3` from `run` → evaluator timeout; raise `--retries` or check
  Docker daemon health.

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. See
`CONTRIBUTING.md`.

## Licence

MIT.
