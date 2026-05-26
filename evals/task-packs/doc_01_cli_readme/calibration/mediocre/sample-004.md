<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); mediocre/sample-004 — Quick start AND Troubleshooting both missing AND `run` documents an invented `--parallel <N>` flag with a parallel-execution example -->
# pollmevals fetch-task

## Overview

A command-line tool for working with POLLMEVALS task packs. It talks to
the catalog at `https://catalog.pollmevals.dev`, validates packs against
the bundled JSON Schema (Draft 2020-12), and runs them against a Stack
inside the evaluator sandbox.

## Installation

Static binary:

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

## Commands

### list

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Categories: `backend`, `frontend`, `docs`, `review`. Difficulty:
`easy`, `medium`, `hard`. `--json` for machine output.

Exit codes: `0` success — `2` network failure — `3` auth failure.

### show

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

`--version` defaults to `latest`. `--json` for machine output.

Exit codes: `0` ok — `4` task not found — `5` version not found.

### validate

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

`--strict` enforces calibration quorum (≥5 samples per band).

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>]
                                    [--out <dir>] [--parallel <N>] [--dry-run]
```

`--stack` required. `--seed` random by default. `--out` default
`./artifacts/`. `--parallel <N>` runs N evaluator workers concurrently
(default `1`, max `16`). `--dry-run` prints plan only.

```
$ pollmevals fetch-task run be_01 --stack raw-llm --parallel 4 --seed 42
fan-out: 4 workers
[w0] ok  be_01 / raw-llm / seed=42
[w1] ok  be_01 / raw-llm / seed=43
[w2] ok  be_01 / raw-llm / seed=44
[w3] ok  be_01 / raw-llm / seed=45
```

Exit codes: `0` ok — `8` stack not found — `9` sandbox error —
`10` evaluator reported a low-scoring candidate.

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

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. See
`CONTRIBUTING.md`. Required pre-commit: `moon run :test`.

## Licence

MIT.
