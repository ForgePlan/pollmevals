<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/google-002 — task-list quick start, verbose type annotations in tables, note blocks for nuanced exit codes -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` manages POLLMEVALS evaluation task packs. It
communicates with a remote catalog to list, inspect, and download packs,
validates them against a schema bundled inside the binary (JSON Schema
Draft 2020-12), and runs them in an isolated sandbox evaluator.

| Property | Value |
|---|---|
| Binary name | `pollmevals-fetch-task` |
| Entry point | `pollmevals fetch-task` |
| Default catalog | `https://catalog.pollmevals.dev` |
| Config file | `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml` |
| Distribution | static binary, Homebrew tap, Docker image |

## Installation

**Static binary**

```bash
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

**Homebrew**

```bash
brew install pollmevals/tap/fetch-task
```

**Docker**

```bash
docker pull ghcr.io/pollmevals/fetch-task:latest
```

Run the image by mounting the working directory:

```bash
docker run --rm \
  -v "$PWD:/workspace" -w /workspace \
  ghcr.io/pollmevals/fetch-task:latest \
  list --category backend
```

**Verify installation**

```bash
pollmevals fetch-task --version
```

## Quick start

Complete workflow — list, inspect, validate, then run:

1. List backend tasks:

   ```bash
   pollmevals fetch-task list --category backend
   ```

2. Inspect a task:

   ```bash
   pollmevals fetch-task show be_01_jwt_auth
   ```

3. Validate a local pack:

   ```bash
   pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth
   ```

4. Run the task and save artefacts:

   ```bash
   pollmevals fetch-task run be_01_jwt_auth \
     --stack claude-code-basic \
     --seed 0 \
     --out ./artifacts/be_01/
   ```

## Commands

### list

Retrieves the list of available task packs from the catalog.

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

**Flags**

| Flag | Type | Description |
|---|---|---|
| `--category <cat>` | `string` | Limit results to one category. Values: `backend`, `frontend`, `docs`, `review`. |
| `--difficulty <level>` | `string` | Limit results to one difficulty. Values: `easy`, `medium`, `hard`. |
| `--json` | `bool` | Emit newline-delimited JSON, one record per task. |

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Success. |
| `2` | Network failure. |
| `3` | Authentication failure. |

```bash
pollmevals fetch-task list --category docs --json
```

### show

Retrieves metadata for a specific task pack.

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

**Flags**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--version <ver>` | `string` | `latest` | Version string to retrieve. |
| `--json` | `bool` | — | Emit JSON output. |

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Success. |
| `4` | Task ID not found in catalog. |
| `5` | Task found, but specified version does not exist. |

```bash
pollmevals fetch-task show doc_01_cli_readme
pollmevals fetch-task show doc_01_cli_readme --version 1.1 --json
```

### validate

Validates a task pack against the bundled JSON Schema. The argument may
be a local directory path or a remote task ID.

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

**Flags**

| Flag | Type | Description |
|---|---|---|
| `--strict` | `bool` | Additionally enforce that each calibration band contains at least 5 samples. |

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Pack is valid. |
| `6` | One or more schema violations found. |
| `7` | Calibration-band quorum not met (`--strict` only). |

```bash
pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
pollmevals fetch-task validate doc_01_cli_readme --strict
```

### run

Runs a task pack through the sandbox evaluator using the named Stack.

```
pollmevals fetch-task run <task-id> --stack <stack-slug> [OPTIONS]
```

**Flags**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--stack <stack-slug>` | `string` | *(required)* | Stack identifier. |
| `--seed <int>` | `integer` | — | RNG seed for reproducibility. |
| `--out <dir>` | `path` | `./artifacts/` | Destination for output artefacts. |
| `--dry-run` | `bool` | — | Print the planned invocation without executing. |

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Success. |
| `8` | Stack not found. |
| `9` | Sandbox infrastructure failure. |
| `10` | Evaluator-reported failure. The sandbox ran successfully; the candidate output did not meet quality thresholds. Not an infrastructure error. |

```bash
pollmevals fetch-task run doc_01_cli_readme \
  --stack forgeplan-framework \
  --seed 77 \
  --out ./out/

# Preview without executing
pollmevals fetch-task run doc_01_cli_readme \
  --stack raw-llm \
  --dry-run
```

## Configuration

### Environment variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `URL` | `https://catalog.pollmevals.dev` | Base URL for the task catalog. |
| `POLLMEVALS_API_TOKEN` | `string` | *(unset)* | Bearer token for private catalog access. |
| `POLLMEVALS_CACHE_DIR` | `path` | `$XDG_CACHE_HOME/pollmevals` | Local directory for cached task packs. |
| `POLLMEVALS_NO_COLOR` | `any` | *(unset)* | Disable ANSI colour output when set to any value. |
| `POLLMEVALS_LOG_LEVEL` | `enum` | `info` | Logging verbosity. One of `debug`, `info`, `warn`, `error`. |

### Config file

**Default location:** `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

Specify an alternate path with `--config <path>`.

**Precedence (highest first):**

1. CLI flag
2. Environment variable
3. Config file
4. Compiled-in default

```yaml
# fetch-task.yaml
catalog_url: https://catalog.pollmevals.dev
log_level: warn
cache_dir: ~/.cache/pollmevals
```

## Troubleshooting

**Exit 2 — network failure**

Test connectivity to the catalog:

```bash
curl -sf https://catalog.pollmevals.dev/healthz && echo "reachable"
```

For restricted networks, configure an HTTP proxy via `HTTPS_PROXY` or
set `POLLMEVALS_CATALOG_URL` to an accessible mirror.

**Exit 3 — authentication failure**

Ensure the API token is exported and has not expired:

```bash
export POLLMEVALS_API_TOKEN=pv_live_<token>
pollmevals fetch-task list
```

**Exit 9 — sandbox infrastructure failure**

Verify the Docker daemon is running and the image is available:

```bash
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit 6 — schema violation**

Increase log verbosity to identify the failing field:

```bash
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate <path-or-id>
```

## Contributing

Development setup, branch naming, and the pull-request checklist are in
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT. See [LICENSE](LICENSE) for the full license text.
