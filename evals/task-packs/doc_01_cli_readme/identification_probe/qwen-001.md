<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/qwen-001 — plain description-first style, combined flag+exit-code tables, moderate length -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` is a command-line tool that fetches evaluation
task packs from the POLLMEVALS catalog, validates them against the bundled
JSON Schema (Draft 2020-12), and runs them inside a sandboxed evaluator.

The tool is available as:

- A standalone static binary
- A Homebrew formula via `pollmevals/tap`
- A Docker image at `ghcr.io/pollmevals/fetch-task`

The catalog is served at `https://catalog.pollmevals.dev` by default.
Override the URL using the `POLLMEVALS_CATALOG_URL` environment variable
or the config file.

## Installation

```bash
# Static binary (Linux and macOS)
curl -fsSL https://get.pollmevals.dev/fetch-task | sh

# Homebrew
brew install pollmevals/tap/fetch-task

# Docker
docker pull ghcr.io/pollmevals/fetch-task:latest
```

Verify the install:

```bash
pollmevals fetch-task --version
```

## Quick start

```bash
# 1. Discover available tasks
pollmevals fetch-task list --category backend

# 2. Inspect a task
pollmevals fetch-task show be_01_jwt_auth

# 3. Run the task
pollmevals fetch-task run be_01_jwt_auth \
  --stack claude-code-basic \
  --out ./artifacts/
```

## Commands

### list

List task packs from the catalog. Supports filtering by category and
difficulty. Use `--json` for machine-readable output.

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

| Flag | Description |
|---|---|
| `--category <cat>` | Category filter. Accepted values: `backend`, `frontend`, `docs`, `review`. |
| `--difficulty <level>` | Difficulty filter. Accepted values: `easy`, `medium`, `hard`. |
| `--json` | Print results as newline-delimited JSON. |

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | Network failure — could not reach catalog |
| 3 | Auth failure — token missing or invalid |

Example:

```bash
pollmevals fetch-task list --category backend --difficulty hard
```

### show

Display metadata for a single task pack.

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

| Flag | Default | Description |
|---|---|---|
| `--version <ver>` | `latest` | The task version to show. |
| `--json` | — | Output as JSON. |

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 4 | Task ID not found |
| 5 | Specified version not found |

Example:

```bash
pollmevals fetch-task show doc_01_cli_readme
pollmevals fetch-task show doc_01_cli_readme --version 1.0 --json
```

### validate

Validate a task pack against the bundled schema. Accepts a local
directory path or a remote task ID.

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

| Flag | Description |
|---|---|
| `--strict` | Additionally require ≥5 samples per calibration band (quorum check). |

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Valid |
| 6 | Schema violation |
| 7 | Quorum failure (strict mode only) |

Example:

```bash
pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth
pollmevals fetch-task validate doc_01_cli_readme --strict
```

### run

Pull a task pack and run it in the sandbox evaluator against the
specified stack. Artefacts are written to the output directory.

```
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

| Flag | Default | Description |
|---|---|---|
| `--stack <stack-slug>` | *(required)* | Stack slug to evaluate against. |
| `--seed <int>` | — | Seed value for deterministic runs. |
| `--out <dir>` | `./artifacts/` | Directory to write output artefacts. |
| `--dry-run` | — | Print the planned invocation without running. |

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 8 | Stack not found |
| 9 | Sandbox infrastructure error |
| 10 | Evaluator-reported failure (infrastructure succeeded; candidate output flagged) |

Example:

```bash
pollmevals fetch-task run fe_01_multistep_form \
  --stack forgeplan-framework \
  --seed 5 \
  --out ./out/

# Preview without executing
pollmevals fetch-task run be_01_jwt_auth --stack raw-llm --dry-run
```

## Configuration

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | Catalog base URL. |
| `POLLMEVALS_API_TOKEN` | unset | Bearer token for authenticated access. |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | Local cache directory for downloaded packs. |
| `POLLMEVALS_NO_COLOR` | unset | Disable ANSI colour when set. |
| `POLLMEVALS_LOG_LEVEL` | `info` | Log level: `debug`, `info`, `warn`, or `error`. |

### Config file

Default path: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

Use `--config <path>` to specify a different file.

Precedence (highest first): CLI flag → environment variable → config
file → compiled-in default.

```yaml
catalog_url: https://catalog.pollmevals.dev
log_level: info
cache_dir: ~/.cache/pollmevals
```

## Troubleshooting

**Exit 2 — network failure**

The tool could not reach the catalog. Test connectivity:

```bash
curl -sf https://catalog.pollmevals.dev/healthz && echo "ok"
```

For environments with HTTP proxies, set `HTTPS_PROXY` or override
`POLLMEVALS_CATALOG_URL` with a reachable mirror.

**Exit 3 — auth failure**

Check that the token is set and not expired:

```bash
export POLLMEVALS_API_TOKEN=pv_live_<token>
pollmevals fetch-task list
```

**Exit 9 — sandbox failure**

Verify Docker is running and the image is available locally:

```bash
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit 6 — schema violation**

Run with debug logging to identify the offending field:

```bash
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
```

## Contributing

Refer to [CONTRIBUTING.md](CONTRIBUTING.md) for the development
workflow, commit conventions, and PR requirements.

## Licence

MIT. See [LICENSE](LICENSE) for the full text.
