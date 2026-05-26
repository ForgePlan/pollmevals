<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); perfect/sample-003 — FAQ-style, every heading is a question; complete and accurate -->
# pollmevals fetch-task

## Overview

### What is this tool?

`pollmevals fetch-task` is a CLI that retrieves POLLMEVALS evaluation
task packs from the catalog at `https://catalog.pollmevals.dev`,
validates them against the bundled JSON Schema (Draft 2020-12), and runs
them inside a sandboxed evaluator. It ships as a single static binary, a
Homebrew tap, and a Docker image.

### What does it not do?

It does not modify the catalog. It does not edit your task packs. It
does not run anything outside its own cache directory and the `--out`
path you give to `run`.

## Installation

### How do I install the static binary?

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

The installer verifies a SHA-256 checksum against the GitHub release
before placing `pollmevals-fetch-task` in `/usr/local/bin`.

### Is there a Homebrew formula?

```sh
brew install pollmevals/tap/fetch-task
```

### Is there a Docker image?

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
docker run --rm ghcr.io/pollmevals/fetch-task --version
```

### How do I verify the install?

```sh
$ pollmevals fetch-task --version
pollmevals fetch-task 0.1.0
```

## Quick start

### What's the shortest end-to-end smoke?

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

The fourth command prints:

```
ok  be_01 / raw-llm / seed=42
    artefacts → ./artifacts/run-2026-05-26T14-22-08Z-be01-rawllm/
    exit 0
```

## Commands

### What does `list` do?

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Returns the task packs visible to your catalog. `--category` is one of
`backend`, `frontend`, `docs`, `review`. `--difficulty` is one of
`easy`, `medium`, `hard`. `--json` emits machine output.

Exit codes: `0` ok — `2` network failure — `3` auth failure.

```
$ pollmevals fetch-task list --category docs
ID      VERSION  DIFFICULTY  TITLE
doc_01  1.0      easy        README for the pollmevals fetch-task CLI
```

### What does `show` do?

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

Prints one task pack's metadata. `--version` defaults to `latest`;
`--json` emits machine output.

Exit codes: `0` ok — `4` task not found — `5` version not found.

```
$ pollmevals fetch-task show be_01 --version 1.0
id:          be_01
slug:        jwt-auth-middleware-with-refresh
version:     1.0
category:    backend
```

### What does `validate` do?

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

Validates a local task-pack directory or a remote task ID against the
bundled schema. `--strict` adds the calibration quorum check (≥5
samples per band).

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

```
$ pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth --strict
schema:      ok
calibration: ok (perfect=5, good=5, mediocre=5, poor=5, broken=5)
```

### What does `run` do?

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>]
                                    [--out <dir>] [--dry-run]
```

Pulls the task pack, mounts it into the evaluator sandbox, executes the
named Stack against it, writes artefacts to `--out` (default
`./artifacts/`). `--seed` controls model RNG; `--dry-run` prints the
plan without executing.

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

### Where does config come from?

Precedence, highest first: CLI flag → environment variable → config
file → compiled-in default.

### Where does the config file live?

Default: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`. Override with
`--config <path>`.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir:   ~/.cache/pollmevals
log_level:   info
api_token:   ""
```

### Which environment variables exist?

| Name | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | override catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

## Troubleshooting

### Why does `list` exit 2?

Network failure. Run `curl -fsS $POLLMEVALS_CATALOG_URL/health`. On a
corporate network, confirm egress 443 to the catalog host.

### Why does `show` exit 3?

`POLLMEVALS_API_TOKEN` is unset or expired. Regenerate from the catalog
web UI and re-export:

```sh
export POLLMEVALS_API_TOKEN=<new-token>
```

### Why does `validate` exit 6?

The task pack does not satisfy the bundled JSON Schema. Re-run with
`POLLMEVALS_LOG_LEVEL=debug` to print the failing JSON Pointer.

### Why does `run` exit 9?

Docker is not running or the evaluator image cannot be pulled. Confirm
with `docker version` and `docker pull ghcr.io/pollmevals/eval-ts:0.1.0`.

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. Read
`CONTRIBUTING.md` first — it covers branch conventions, required
`moon run :test` smoke before PR, and the rule that any subcommand
change preserves the existing `--json` schema.

## Licence

MIT. See `LICENSE`.
