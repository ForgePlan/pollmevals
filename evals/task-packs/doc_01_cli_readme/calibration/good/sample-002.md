<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); good/sample-002 — all sections present but `run` exit code 10 documented as "general failure" instead of evaluator-reported low quality (one factual slip) -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` is the POLLMEVALS task-pack CLI. It retrieves
task packs from the catalog at `https://catalog.pollmevals.dev`,
validates them against a bundled JSON Schema (Draft 2020-12), and runs
them against a Stack inside a sandboxed evaluator. Distribution: static
binary, Homebrew tap, Docker image.

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

Sanity check:

```sh
pollmevals fetch-task --version
# pollmevals fetch-task 0.1.0
```

## Quick start

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

The fourth command finishes in <2 minutes against `raw-llm`.

## Commands

### list

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Flags: `--category` (one of `backend`, `frontend`, `docs`, `review`);
`--difficulty` (one of `easy`, `medium`, `hard`); `--json`.

Exit codes: `0` ok — `2` network — `3` auth.

```
$ pollmevals fetch-task list --category backend
ID      VERSION  DIFFICULTY  TITLE
be_01   1.0      medium      JWT auth middleware with refresh rotation
```

### show

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

`--version` defaults to `latest`. `--json` switches to machine output.

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

`--strict` adds the calibration quorum check (≥5 samples per band).

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>]
                                    [--out <dir>] [--dry-run]
```

`--stack` is required. `--seed` defaults to random. `--out` defaults to
`./artifacts/`. `--dry-run` prints the plan only.

Exit codes:

- `0` success
- `8` stack not found
- `9` sandbox error
- `10` general failure

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
file → compiled-in default.

Default config path: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir:   ~/.cache/pollmevals
log_level:   info
api_token:   ""
```

Environment:

| Name | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | override catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

## Troubleshooting

**`exit 2` on `list`** — catalog unreachable. Run
`curl -fsS $POLLMEVALS_CATALOG_URL/health`; confirm egress 443.

**`exit 3` on `show`** — auth failure. Regenerate
`POLLMEVALS_API_TOKEN` from the catalog UI.

**`exit 6` on `validate`** — schema violation. Re-run with
`POLLMEVALS_LOG_LEVEL=debug` to print the JSON Pointer.

**`exit 9` on `run`** — sandbox unavailable. Confirm
`docker version` and `docker pull ghcr.io/pollmevals/eval-ts:0.1.0`.

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. Read
`CONTRIBUTING.md`. Required pre-commit: `moon run :test`.

## Licence

MIT. See `LICENSE`.
