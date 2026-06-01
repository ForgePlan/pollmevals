<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/anthropic-001 — moderate verbosity, structured prose, grouped concept boundaries -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` retrieves POLLMEVALS evaluation task packs from a
remote catalog, validates them against the bundled JSON Schema (Draft
2020-12), and runs them inside a sandboxed evaluator. The tool ships as a
single static binary, a Homebrew tap, and a Docker image. It does not
require a running daemon or background service.

The catalog endpoint defaults to `https://catalog.pollmevals.dev`. Private
or mirror catalogs are supported by setting `POLLMEVALS_CATALOG_URL`.

## Installation

**Static binary (Linux / macOS)**

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

Verify the installation:

```sh
pollmevals fetch-task --version
```

**Homebrew**

```sh
brew install pollmevals/tap/fetch-task
```

**Docker**

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
```

To invoke via Docker, mount your working directory:

```sh
docker run --rm -v "$PWD:/work" -w /work \
  ghcr.io/pollmevals/fetch-task:latest list --category backend
```

## Quick start

Fetch the task list, inspect a single task, and run it against a stack:

```sh
# 1. List tasks in the backend category
pollmevals fetch-task list --category backend

# 2. Inspect a specific task
pollmevals fetch-task show be_01_jwt_auth

# 3. Run against a stack, writing artefacts to ./out/
pollmevals fetch-task run be_01_jwt_auth \
  --stack claude-code-basic \
  --out ./out/
```

## Commands

### list

Lists task packs available in the catalog.

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

| Flag | Description |
|---|---|
| `--category <cat>` | Filter by category: `backend`, `frontend`, `docs`, `review` |
| `--difficulty <level>` | Filter by difficulty: `easy`, `medium`, `hard` |
| `--json` | Emit newline-delimited JSON records instead of tabular output |

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | Network failure |
| 3 | Authentication failure |

Example:

```sh
pollmevals fetch-task list --category docs --difficulty easy
```

### show

Prints metadata for a single task pack.

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

| Flag | Description |
|---|---|
| `--version <ver>` | Specific version to retrieve; defaults to `latest` |
| `--json` | Emit JSON instead of formatted output |

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 4 | Task not found |
| 5 | Requested version not found |

Example:

```sh
pollmevals fetch-task show doc_01_cli_readme --version 1.1 --json
```

### validate

Validates a local task pack directory or a remote task ID against the
bundled JSON Schema.

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

| Flag | Description |
|---|---|
| `--strict` | Also enforce calibration-band sample-count quorum (≥5 per band) |

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Valid |
| 6 | Schema violation |
| 7 | Quorum failure (only possible with `--strict`) |

Example:

```sh
# Validate a local directory
pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme

# Validate a remote task with strict quorum check
pollmevals fetch-task validate be_01_jwt_auth --strict
```

### run

Pulls a task pack, mounts it into the sandbox evaluator, and executes the
configured Stack against it.

```
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

| Flag | Description |
|---|---|
| `--stack <stack-slug>` | **(required)** Stack identifier to evaluate against |
| `--seed <int>` | Random seed for reproducibility |
| `--out <dir>` | Output directory for artefacts (default: `./artifacts/`) |
| `--dry-run` | Validate inputs and print the planned invocation; do not execute |

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 8 | Stack not found |
| 9 | Sandbox infrastructure error |
| 10 | Evaluator-reported failure (infrastructure succeeded; candidate output low-quality) |

Example:

```sh
pollmevals fetch-task run fe_01_multistep_form \
  --stack forgeplan-framework \
  --seed 42 \
  --out ./run-output/
```

Dry run:

```sh
pollmevals fetch-task run be_01_jwt_auth --stack raw-llm --dry-run
```

## Configuration

### Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | Override catalog base URL | `https://catalog.pollmevals.dev` |
| `POLLMEVALS_API_TOKEN` | Bearer token for private or authenticated catalogs | unset |
| `POLLMEVALS_CACHE_DIR` | Local cache directory for downloaded task packs | `$XDG_CACHE_HOME/pollmevals` |
| `POLLMEVALS_NO_COLOR` | Set to any non-empty value to disable ANSI colour in stderr | unset |
| `POLLMEVALS_LOG_LEVEL` | Log verbosity: `debug`, `info`, `warn`, or `error` | `info` |

### Config file

The config file is read from `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`
by default. Override the path with `--config <path>`.

Precedence (highest wins): CLI flag → env var → config file →
compiled-in default.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir: /tmp/pv-cache
log_level: warn
```

## Troubleshooting

**Exit code 2 — network failure**

Check that `https://catalog.pollmevals.dev` is reachable from your
environment:

```sh
curl -I https://catalog.pollmevals.dev/healthz
```

If behind a proxy, set `HTTPS_PROXY` or point `POLLMEVALS_CATALOG_URL`
at an accessible mirror.

**Exit code 3 — authentication failure**

Set or refresh your token:

```sh
export POLLMEVALS_API_TOKEN=pv_live_yourtoken
pollmevals fetch-task list
```

**Exit code 9 — sandbox error**

Ensure Docker is running and the image is accessible:

```sh
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit code 6 — schema violation during validate**

Run with `POLLMEVALS_LOG_LEVEL=debug` to see the full validation path:

```sh
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for branch conventions, commit
message format, and the pull-request checklist.

## Licence

MIT. See [`LICENSE`](LICENSE) for the full text.
