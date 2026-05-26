<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); good/sample-005 — all sections present; one slight ambiguity: the `run` subcommand's exit code 10 is mentioned but its meaning is conflated with `9` in the Troubleshooting block -->
# pollmevals fetch-task

## Overview

A single-binary CLI for POLLMEVALS task packs. Discovers packs from the
catalog at `https://catalog.pollmevals.dev`, validates them against the
bundled JSON Schema (Draft 2020-12), and runs them against a Stack
inside the evaluator sandbox.

## Installation

Static binary (recommended):

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

Homebrew:

```sh
brew install pollmevals/tap/fetch-task
```

Docker:

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
```

Verify:

```sh
pollmevals fetch-task --version
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

Filters: `--category` ∈ {`backend`, `frontend`, `docs`, `review`};
`--difficulty` ∈ {`easy`, `medium`, `hard`}. `--json` for machine
output.

Exit codes: `0` ok — `2` network — `3` auth.

### show

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

`--version` defaults to `latest`. `--json` switches to machine output.

Exit codes: `0` ok — `4` task not found — `5` version not found.

### validate

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

`--strict` adds calibration quorum (≥5 samples per band).

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>]
                                    [--out <dir>] [--dry-run]
```

`--stack` is required; `--seed` defaults to random; `--out` defaults to
`./artifacts/`; `--dry-run` prints the plan only.

Exit codes: `0` success — `8` stack not found — `9` sandbox error —
`10` evaluator reported a low-scoring candidate.

```
$ pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --dry-run
plan:
  task:   be_01 @ 1.0
  stack:  raw-llm
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
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

## Troubleshooting

- `exit 2` from `list` → catalog unreachable; check connectivity to
  `$POLLMEVALS_CATALOG_URL`.
- `exit 3` from `show` → catalog returned 401; regenerate
  `POLLMEVALS_API_TOKEN`.
- `exit 6` from `validate` → schema violation; re-run with
  `POLLMEVALS_LOG_LEVEL=debug` for the JSON Pointer.
- `exit 9` or `exit 10` from `run` → either the sandbox is unavailable
  or the evaluator could not complete; check `docker version` and
  re-pull `ghcr.io/pollmevals/eval-ts:0.1.0`.

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. Read
`CONTRIBUTING.md` first. Required pre-commit: `moon run :test`.

## Licence

MIT. See `LICENSE`.
