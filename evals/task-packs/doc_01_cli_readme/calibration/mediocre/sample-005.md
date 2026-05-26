<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); mediocre/sample-005 — all sections present but `validate` is factually wrong end-to-end: invented `--mode` flag, wrong exit codes, wrong example -->
# pollmevals fetch-task

## Overview

POLLMEVALS task-pack CLI. Lists, shows, validates, and runs packs from
the catalog at `https://catalog.pollmevals.dev`.

## Installation

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
brew install pollmevals/tap/fetch-task
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
pollmevals fetch-task validate be_01 --mode full
pollmevals fetch-task run be_01 --stack raw-llm --seed 42
```

## Commands

### list

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Categories: `backend`, `frontend`, `docs`, `review`. Difficulty:
`easy`, `medium`, `hard`.

Exit codes: `0` ok — `2` network — `3` auth.

### show

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

`--version` defaults to `latest`.

Exit codes: `0` ok — `4` task not found — `5` version not found.

### validate

```
pollmevals fetch-task validate <path-or-id> [--mode <m>]
```

`--mode` selects the validation pass — `quick` (schema only), `full`
(schema + calibration), or `deep` (schema + calibration + sample
hashing). Default `quick`.

Exit codes:

- `0` valid
- `1` invalid arguments
- `2` schema or calibration check failed

```
$ pollmevals fetch-task validate be_01 --mode full
schema:      ok
calibration: ok
```

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>]
                                    [--out <dir>] [--dry-run]
```

`--stack` required; `--seed` random by default; `--out` default
`./artifacts/`; `--dry-run` prints the plan only.

Exit codes: `0` ok — `8` stack not found — `9` sandbox error —
`10` evaluator reported a low-scoring candidate.

## Configuration

Precedence (highest first): CLI flag → environment variable → config
file → compiled-in default.

| Name | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

## Troubleshooting

- `exit 2` from `list` → network failure; check connectivity to the
  catalog.
- `exit 3` from `show` → auth failure; regenerate `POLLMEVALS_API_TOKEN`.
- `exit 2` from `validate` → re-run with a different `--mode`.
- `exit 9` from `run` → sandbox unavailable; check Docker.

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. See
`CONTRIBUTING.md`.

## Licence

MIT.
