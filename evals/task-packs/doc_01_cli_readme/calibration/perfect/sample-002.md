<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); perfect/sample-002 — tutorial-style, numbered step voice with running example carried through every section -->
# pollmevals fetch-task

A command-line tool for working with POLLMEVALS evaluation task packs.
The rest of this README walks one full task — `be_01` — through every
subcommand. Each example continues from the previous one.

## Overview

Three things this tool does:

1. Lists task packs the catalog at
   `https://catalog.pollmevals.dev` exposes to you.
2. Validates a task pack (local directory or remote ID) against the
   bundled JSON Schema (Draft 2020-12).
3. Runs a task pack against a configured Stack inside a sandboxed
   evaluator and writes artefacts to disk.

It does no background work. It writes only to its cache and to the
directory you pass via `--out`.

## Installation

Step 1 — pick a channel.

The static binary installer runs against the GitHub release and verifies
SHA-256 before installing to `/usr/local/bin`:

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

The Homebrew formula pins the same release:

```sh
brew install pollmevals/tap/fetch-task
```

The Docker image is the same binary in a `gcr.io/distroless/static` base:

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
alias pollmevals-fetch-task='docker run --rm -v "$PWD:/work" -w /work ghcr.io/pollmevals/fetch-task'
```

Step 2 — verify.

```sh
pollmevals fetch-task --version
# pollmevals fetch-task 0.1.0
```

## Quick start

Run these four commands in order. They take ~90 seconds end-to-end.

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

After the last command:

```
ok  be_01 / raw-llm / seed=42
    artefacts → ./artifacts/run-2026-05-26T14-22-08Z-be01-rawllm/
    exit 0
```

## Commands

### list

Step 1 in the workflow — discover what's in the catalog.

```sh
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Flags:

- `--category` — one of `backend`, `frontend`, `docs`, `review`.
- `--difficulty` — one of `easy`, `medium`, `hard`.
- `--json` — emit machine-readable output instead of the human table.

Example:

```sh
$ pollmevals fetch-task list --category backend --difficulty medium
ID      VERSION  DIFFICULTY  TITLE
be_01   1.0      medium      JWT auth middleware with refresh rotation
```

Exit codes: `0` success — `2` network failure — `3` auth failure.

### show

Step 2 — confirm the metadata of the task you're about to use.

```sh
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

Flags:

- `--version` — defaults to `latest`. Use a semver string like `1.0` to
  pin.
- `--json` — emit machine-readable output.

Example:

```sh
$ pollmevals fetch-task show be_01 --version 1.0
id:          be_01
slug:        jwt-auth-middleware-with-refresh
version:     1.0
category:    backend
difficulty:  medium
sourcing:    own
```

Exit codes: `0` success — `4` task not found — `5` version not found.

### validate

Step 3 — confirm the pack is structurally sound before running it.

```sh
pollmevals fetch-task validate <path-or-id> [--strict]
```

Flag:

- `--strict` — additionally require ≥5 calibration samples per band
  (`perfect`, `good`, `mediocre`, `poor`, `broken`).

Example:

```sh
$ pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth --strict
schema:      ok
calibration: ok (perfect=5, good=5, mediocre=5, poor=5, broken=5)
```

Exit codes: `0` valid — `6` schema violation — `7` quorum failure.

### run

Step 4 — execute the task against a Stack and persist artefacts.

```sh
pollmevals fetch-task run <task-id> --stack <stack-slug> \
                                    [--seed <int>] [--out <dir>] [--dry-run]
```

Flags:

- `--stack` (required) — slug from `stacks/`, e.g. `raw-llm`,
  `claude-code-basic`, `forgeplan-framework`.
- `--seed` — RNG seed for the candidate model. Defaults to a random
  64-bit integer; set explicitly for reproducibility.
- `--out` — artefact directory. Defaults to `./artifacts/`.
- `--dry-run` — print the plan, do not execute.

Example:

```sh
$ pollmevals fetch-task run be_01 --stack claude-code-basic --seed 42 --dry-run
plan:
  task:   be_01 @ 1.0
  stack:  claude-code-basic
  image:  ghcr.io/pollmevals/eval-ts:0.1.0
  seed:   42
  out:    ./artifacts/
```

Exit codes: `0` success — `8` stack not found — `9` sandbox error —
`10` evaluator reported a low-scoring but well-formed candidate (the
wrapper itself succeeded).

## Configuration

Sources, highest priority first:

1. CLI flag
2. Environment variable
3. Config file (`--config <path>`, or the default location)
4. Compiled-in default

Default config path: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir:   ~/.cache/pollmevals
log_level:   info
api_token:   ""
```

Environment variables:

| Name | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

## Troubleshooting

**`exit 2` after `list` — "catalog unreachable".** The catalog host is
not responding. Confirm with `curl -fsS $POLLMEVALS_CATALOG_URL/health`.
On a corporate network, ensure egress 443 is open to the catalog host.

**`exit 3` after `show` — 401 from the catalog.** Your
`POLLMEVALS_API_TOKEN` is unset or expired. Regenerate from the catalog
web UI:

```sh
export POLLMEVALS_API_TOKEN=<new-token>
```

**`exit 6` after `validate` — schema violation.** Re-run with
`POLLMEVALS_LOG_LEVEL=debug` to print the failing JSON Pointer and the
offending value.

**`exit 9` after `run` — sandbox error.** Docker is not available, or
the evaluator image cannot be pulled. Run `docker version` and `docker
pull ghcr.io/pollmevals/eval-ts:0.1.0` to confirm.

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. Read
`CONTRIBUTING.md` first — it documents the branch naming convention,
required smoke tests, and the rule that any subcommand change must
preserve the existing `--json` schema.

## Licence

MIT. See `LICENSE`.
