<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/qwen-002 — section intro sentences, description-list style for env vars, varied subcommand layout -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` is the POLLMEVALS CLI for task pack management. It
allows you to browse the catalog, download and validate task packs, and
run them through a sandboxed evaluator against your chosen model stack.

The binary bundles the JSON Schema (Draft 2020-12) used for validation, so
schema checks work offline. Running tasks (`run`) requires Docker to start
the sandbox evaluator container.

**Endpoints and distribution:**

- Catalog: `https://catalog.pollmevals.dev`
- Binary: `pollmevals-fetch-task`, entry via `pollmevals fetch-task`
- Homebrew: `brew install pollmevals/tap/fetch-task`
- Docker: `ghcr.io/pollmevals/fetch-task:latest`

## Installation

Download and install the binary:

```bash
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

Using Homebrew:

```bash
brew install pollmevals/tap/fetch-task
```

Using Docker:

```bash
docker pull ghcr.io/pollmevals/fetch-task:latest
```

Check the version:

```bash
pollmevals fetch-task --version
```

## Quick start

A minimal workflow:

```bash
# Find a task
pollmevals fetch-task list --category docs

# Inspect it
pollmevals fetch-task show doc_01_cli_readme

# Run it
pollmevals fetch-task run doc_01_cli_readme \
  --stack claude-code-basic \
  --out ./artifacts/
```

## Commands

### list

Browse task packs in the catalog. Optional filters narrow results by
category or difficulty. `--json` outputs records suitable for piping
into `jq` or other tools.

**Usage:**

```bash
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

**Flags:**

`--category <cat>` — restrict to one of `backend`, `frontend`, `docs`, `review`

`--difficulty <level>` — restrict to one of `easy`, `medium`, `hard`

`--json` — emit newline-delimited JSON (one object per task)

**Exit codes:** 0 success, 2 network failure, 3 auth failure

**Example:**

```bash
pollmevals fetch-task list --category docs --json | jq '.id'
```

### show

Retrieve metadata for one task pack by ID.

**Usage:**

```bash
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

**Flags:**

`--version <ver>` — version to retrieve (default: `latest`)

`--json` — JSON output

**Exit codes:** 0 success, 4 task not found, 5 version not found

**Example:**

```bash
pollmevals fetch-task show doc_01_cli_readme
pollmevals fetch-task show doc_01_cli_readme --version 1.0
```

### validate

Validate a task pack against the bundled schema. Supply a local directory
path or a remote task ID.

**Usage:**

```bash
pollmevals fetch-task validate <path-or-id> [--strict]
```

**Flags:**

`--strict` — also enforce that each calibration band has at least 5 samples

**Exit codes:** 0 valid, 6 schema violation, 7 quorum failure

**Examples:**

```bash
# Local directory
pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme

# Remote task, strict quorum
pollmevals fetch-task validate doc_01_cli_readme --strict
```

### run

Execute a task pack in the sandbox evaluator. The `--stack` flag is
required. Artefacts land in `--out`.

**Usage:**

```bash
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

**Flags:**

`--stack <stack-slug>` — stack to evaluate against **(required)**

`--seed <int>` — seed for reproducibility

`--out <dir>` — output directory (default: `./artifacts/`)

`--dry-run` — print the planned invocation, do not execute

**Exit codes:**

- 0: success
- 8: stack not found
- 9: sandbox infrastructure failure
- 10: evaluator-reported failure (sandbox ran OK; output below threshold)

**Example:**

```bash
pollmevals fetch-task run doc_01_cli_readme \
  --stack forgeplan-framework \
  --seed 99 \
  --out ./results/doc_01/

# Preview only
pollmevals fetch-task run doc_01_cli_readme \
  --stack raw-llm \
  --dry-run
```

## Configuration

### Environment variables

`POLLMEVALS_CATALOG_URL`
: Override the catalog base URL.
: Default: `https://catalog.pollmevals.dev`

`POLLMEVALS_API_TOKEN`
: Bearer token for private catalog access.
: Default: unset

`POLLMEVALS_CACHE_DIR`
: Local directory for cached task packs.
: Default: `$XDG_CACHE_HOME/pollmevals`

`POLLMEVALS_NO_COLOR`
: Disable ANSI colour output when set to any value.
: Default: unset

`POLLMEVALS_LOG_LEVEL`
: Log verbosity. One of `debug`, `info`, `warn`, `error`.
: Default: `info`

### Config file

Default location: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

Pass `--config <path>` to use a different file.

Precedence (highest first): CLI flag → env var → config file → compiled-in default.

```yaml
catalog_url: https://catalog.pollmevals.dev
log_level: warn
cache_dir: ~/.local/share/pollmevals/cache
```

## Troubleshooting

**Exit 2 — network failure**

The catalog endpoint is unreachable. Test directly:

```bash
curl -sf https://catalog.pollmevals.dev/healthz && echo "reachable"
```

If a proxy is required, set `HTTPS_PROXY` or override
`POLLMEVALS_CATALOG_URL` with a mirror that is reachable from your
environment.

**Exit 3 — auth failure**

Your API token is missing or expired. Set it in the environment:

```bash
export POLLMEVALS_API_TOKEN=pv_live_yourtoken
pollmevals fetch-task list
```

**Exit 9 — sandbox error**

The evaluator container failed to start. Confirm the Docker daemon is
running and the image is present:

```bash
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit 6 — schema violation**

Increase log verbosity to trace the failing field:

```bash
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, the
branching model, and the pull-request checklist.

## Licence

MIT. See [LICENSE](LICENSE).
