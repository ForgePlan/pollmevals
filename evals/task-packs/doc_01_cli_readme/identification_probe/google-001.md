<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/google-001 — layered headings, spec-style parameter tables with type columns -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` is a command-line tool that retrieves evaluation
task packs from the POLLMEVALS catalog, validates them against the bundled
JSON Schema (Draft 2020-12), and executes them inside a sandboxed
evaluator. The tool is packaged as a standalone static binary, a Homebrew
formula, and a container image.

**Catalog URL:** `https://catalog.pollmevals.dev`
(configurable — see [Configuration](#configuration))

**Schema validation** uses JSON Schema Draft 2020-12 embedded in the
binary. No network access is required for local schema checks.

## Installation

The tool supports three distribution channels:

**Static binary**

```shell
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

**Homebrew**

```shell
brew install pollmevals/tap/fetch-task
```

**Docker**

```shell
docker pull ghcr.io/pollmevals/fetch-task:latest
```

After installation, verify the binary:

```shell
pollmevals fetch-task --version
```

## Quick start

The following sequence lists available tasks, inspects one, and runs it:

```shell
# Step 1: browse the catalog
pollmevals fetch-task list --category backend

# Step 2: read task metadata
pollmevals fetch-task show be_01_jwt_auth

# Step 3: execute against a stack
pollmevals fetch-task run be_01_jwt_auth \
  --stack claude-code-basic \
  --out ./artifacts/
```

## Commands

### list

Lists task packs available in the catalog. Results can be filtered by
category and difficulty, and optionally emitted as newline-delimited JSON.

**Syntax**

```
pollmevals fetch-task list [OPTIONS]
```

**Options**

| Option | Type | Description |
|---|---|---|
| `--category <cat>` | string | Filter by category. One of: `backend`, `frontend`, `docs`, `review`. |
| `--difficulty <level>` | string | Filter by difficulty. One of: `easy`, `medium`, `hard`. |
| `--json` | flag | Emit newline-delimited JSON records. |

**Exit codes**

| Code | Description |
|---|---|
| 0 | Success. |
| 2 | Network failure — catalog unreachable. |
| 3 | Authentication failure — token absent or rejected. |

**Example**

```shell
pollmevals fetch-task list --category backend --difficulty easy
```

### show

Prints the metadata of a single task pack. Use `--version` to retrieve a
specific version; if omitted, the latest version is returned.

**Syntax**

```
pollmevals fetch-task show <task-id> [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
|---|---|---|---|
| `--version <ver>` | string | `latest` | The task version to retrieve. |
| `--json` | flag | — | Emit JSON output. |

**Exit codes**

| Code | Description |
|---|---|
| 0 | Success. |
| 4 | Task not found. |
| 5 | Requested version not found. |

**Example**

```shell
pollmevals fetch-task show doc_01_cli_readme --version 1.1 --json
```

### validate

Validates a task pack against the JSON Schema embedded in the binary.
Accepts either a local directory path or a remote task ID (fetched from
the catalog for validation).

**Syntax**

```
pollmevals fetch-task validate <path-or-id> [OPTIONS]
```

**Options**

| Option | Type | Description |
|---|---|---|
| `--strict` | flag | Also enforce calibration-band sample-count quorum (minimum 5 samples per band). |

**Exit codes**

| Code | Description |
|---|---|
| 0 | Pack is valid. |
| 6 | Schema violation detected. |
| 7 | Quorum failure (`--strict` only). |

**Example**

```shell
# Validate a local directory
pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme

# Validate a remote task with strict quorum enforcement
pollmevals fetch-task validate doc_01_cli_readme --strict
```

### run

Pulls a task pack from the catalog, mounts it into the sandbox evaluator
container, and runs the specified Stack against it. Artefacts are written
to the output directory.

**Syntax**

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
|---|---|---|---|
| `--stack <stack-slug>` | string | *(required)* | The Stack identifier to evaluate against. |
| `--seed <int>` | integer | — | Random seed for reproducibility. |
| `--out <dir>` | path | `./artifacts/` | Directory to write output artefacts. |
| `--dry-run` | flag | — | Validate inputs and print the planned invocation without executing. |

**Exit codes**

| Code | Description |
|---|---|
| 0 | Success. |
| 8 | Stack not found. |
| 9 | Sandbox infrastructure error. |
| 10 | Evaluator-reported failure. The sandbox ran to completion; the candidate output was flagged as low-quality. This is not an infrastructure error. |

**Example**

```shell
pollmevals fetch-task run fe_01_multistep_form \
  --stack forgeplan-framework \
  --seed 42 \
  --out ./results/

# Dry run to preview the invocation
pollmevals fetch-task run be_01_jwt_auth --stack raw-llm --dry-run
```

## Configuration

### Environment variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `POLLMEVALS_CATALOG_URL` | URL | `https://catalog.pollmevals.dev` | Override the catalog base URL. |
| `POLLMEVALS_API_TOKEN` | string | *(unset)* | Bearer token for authenticated catalog access. |
| `POLLMEVALS_CACHE_DIR` | path | `$XDG_CACHE_HOME/pollmevals` | Local cache directory for downloaded task packs. |
| `POLLMEVALS_NO_COLOR` | any | *(unset)* | When set, disables ANSI colour in stderr output. |
| `POLLMEVALS_LOG_LEVEL` | enum | `info` | Log verbosity. One of: `debug`, `info`, `warn`, `error`. |

### Config file

**Default path:** `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

Override with `--config <path>`.

**Precedence** (highest wins):

1. CLI flag
2. Environment variable
3. Config file
4. Compiled-in default

**Example config:**

```yaml
catalog_url: https://catalog.pollmevals.dev
log_level: warn
cache_dir: /var/cache/pollmevals
```

## Troubleshooting

**Exit code 2 — network failure**

Confirm the catalog endpoint is reachable:

```shell
curl -sf https://catalog.pollmevals.dev/healthz && echo "ok"
```

If your network uses an HTTP proxy, set the `HTTPS_PROXY` environment
variable, or override `POLLMEVALS_CATALOG_URL` with a mirror URL.

**Exit code 3 — authentication failure**

Set the API token and retry:

```shell
export POLLMEVALS_API_TOKEN=pv_live_<token>
pollmevals fetch-task list
```

Confirm the token is valid and has not expired in the POLLMEVALS dashboard.

**Exit code 9 — sandbox error**

The evaluator container failed to start. Check the Docker daemon:

```shell
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit code 6 — schema violation**

Enable debug-level logging to identify the offending field:

```shell
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup,
branching model, and pull-request checklist.

## Licence

MIT. See [LICENSE](LICENSE).
