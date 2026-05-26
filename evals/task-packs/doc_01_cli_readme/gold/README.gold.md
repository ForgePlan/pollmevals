<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); gold/README.gold.md — reference README at expected score 9.0-10.0 -->
# `pollmevals fetch-task`

Retrieve, validate, and run POLLMEVALS evaluation task packs from the
command line.

## Overview

`pollmevals fetch-task` is a single-binary CLI that talks to the
POLLMEVALS catalog at `https://catalog.pollmevals.dev`, downloads task
packs into a local cache, validates them against a bundled JSON Schema
(Draft 2020-12), and runs them against a configured Stack inside a
sandboxed evaluator. It is the front door for everyone who reproduces a
published Run, develops a new task pack locally, or wires the benchmark
into CI.

The tool is read-mostly. It writes only inside its cache directory
(`$XDG_CACHE_HOME/pollmevals` by default) and the `--out` directory you
pass to `run`. It never modifies your shell environment or the catalog.

## Installation

Three supported delivery channels. Pick one.

### Static binary

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

The script verifies a SHA-256 checksum against the GitHub release and
installs to `/usr/local/bin/pollmevals-fetch-task`.

### Homebrew

```sh
brew install pollmevals/tap/fetch-task
```

### Docker

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
docker run --rm ghcr.io/pollmevals/fetch-task --version
```

Verify the install:

```sh
$ pollmevals fetch-task --version
pollmevals fetch-task 0.1.0
```

## Quick start

List the available backend tasks, inspect one, validate the local copy,
and run it against the `raw-llm` stack:

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

Expected after `run`:

```
ok   be_01 / raw-llm / seed=42
     artefacts → ./artifacts/run-2026-05-26T14-22-08Z-be01-rawllm/
     exit 0
```

## Commands

### `list`

List task packs visible to the configured catalog.

```sh
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--category` | `backend` \| `frontend` \| `docs` \| `review` | all | filter by category |
| `--difficulty` | `easy` \| `medium` \| `hard` | all | filter by difficulty |
| `--json` | bool | false | emit machine-readable JSON instead of a table |

Example:

```sh
$ pollmevals fetch-task list --category docs
ID       VERSION  DIFFICULTY  TITLE
doc_01   1.0      easy        README for the pollmevals fetch-task CLI
```

Exit codes: `0` success — `2` network failure — `3` auth failure.

### `show`

Print one task pack's metadata.

```sh
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--version` | semver string | `latest` | pin to a specific task version |
| `--json` | bool | false | emit machine-readable JSON instead of a table |

Example:

```sh
$ pollmevals fetch-task show be_01 --version 1.0
id:          be_01
slug:        jwt-auth-middleware-with-refresh
version:     1.0
category:    backend
difficulty:  medium
language:    typescript
sourcing:    own
```

Exit codes: `0` success — `4` task not found — `5` version not found.

### `validate`

Validate a local task-pack directory or a remote task ID against the
bundled schema.

```sh
pollmevals fetch-task validate <path-or-id> [--strict]
```

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--strict` | bool | false | additionally enforce calibration quorum (≥5 samples per band) |

Example:

```sh
$ pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth --strict
schema:      ok
calibration: ok (perfect=5, good=5, mediocre=5, poor=5, broken=5)
```

Exit codes: `0` valid — `6` schema violation — `7` quorum failure (only
returned when `--strict` is on).

### `run`

Pull the task pack, mount it into the evaluator sandbox, run the named
Stack against it, and write artefacts.

```sh
pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>] [--out <dir>] [--dry-run]
```

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--stack` | string (required) | — | Stack slug from `stacks/` (e.g. `raw-llm`, `claude-code-basic`) |
| `--seed` | int | random | RNG seed; required for reproducibility runs |
| `--out` | path | `./artifacts/` | where to write evaluator artefacts |
| `--dry-run` | bool | false | validate inputs and print the planned invocation; do not execute |

Example:

```sh
$ pollmevals fetch-task run be_01 --stack claude-code-basic --seed 42 --dry-run
plan:
  task:   be_01 @ 1.0
  stack:  claude-code-basic
  image:  ghcr.io/pollmevals/eval-ts:0.1.0
  seed:   42
  out:    ./artifacts/
  (dry-run — nothing executed)
```

Exit codes: `0` success — `8` stack not found — `9` sandbox error
(image pull, mount, process supervision) — `10` evaluator reported a
low-scoring but well-formed candidate (the wrapper itself succeeded; the
exit code only signals that the produced output did not pass the
evaluator's quality bar).

## Configuration

Configuration sources, highest priority wins:

1. CLI flag
2. Environment variable
3. Config file (`--config <path>` or default location)
4. Compiled-in default

### Config file

Default path: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`. Override
with `--config <path>` on any subcommand.

```yaml
# $XDG_CONFIG_HOME/pollmevals/fetch-task.yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir:   ~/.cache/pollmevals
log_level:   info
api_token:   ""           # leave empty for public catalogs
```

### Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | override the catalog base URL | `https://catalog.pollmevals.dev` |
| `POLLMEVALS_API_TOKEN` | bearer token for private catalogs | unset |
| `POLLMEVALS_CACHE_DIR` | local cache for downloaded packs | `$XDG_CACHE_HOME/pollmevals` |
| `POLLMEVALS_NO_COLOR` | disable ANSI colour in stderr output | unset |
| `POLLMEVALS_LOG_LEVEL` | `debug` \| `info` \| `warn` \| `error` | `info` |

## Troubleshooting

### `exit 2` — network failure on `list` / `show`

The catalog at `POLLMEVALS_CATALOG_URL` is unreachable. Check connectivity
with `curl -fsS $POLLMEVALS_CATALOG_URL/health`. On a private network,
verify the firewall allows egress on 443 to the catalog host.

### `exit 3` — auth failure on `list` / `show`

The catalog returned 401. Either `POLLMEVALS_API_TOKEN` is unset for a
private catalog, or the token has expired. Regenerate from the catalog
web UI and re-export:

```sh
export POLLMEVALS_API_TOKEN=<new-token>
```

### `exit 6` — schema violation on `validate`

The task pack's `task.yaml` does not satisfy the bundled JSON Schema. Run
with `POLLMEVALS_LOG_LEVEL=debug` to see the failing JSON Pointer and the
offending value:

```sh
POLLMEVALS_LOG_LEVEL=debug pollmevals fetch-task validate <path>
```

### `exit 9` — sandbox error on `run`

Docker is not running, or the evaluator image cannot be pulled. Verify
with `docker version` and `docker pull ghcr.io/pollmevals/eval-ts:0.1.0`.
On rootless setups, ensure your user is in the `docker` group or use a
rootless-compatible runtime (Podman with `DOCKER_HOST=unix://...`).

## Contributing

Source lives at <https://github.com/pollmevals/fetch-task>. Read
`CONTRIBUTING.md` first — it covers branch conventions, the required
`moon run :test` smoke before PR, and how to add a new subcommand without
breaking the JSON output schema. All PRs require one passing CI run and
one reviewer.

## Licence

MIT. See `LICENSE` in the repository root.
