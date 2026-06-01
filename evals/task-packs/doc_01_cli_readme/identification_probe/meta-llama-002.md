<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/meta-llama-002 — explicit h3 subsections for flags and exit codes, sentence-per-paragraph style -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` retrieves POLLMEVALS evaluation task packs from a
remote catalog and runs them against configured model stacks inside a
sandboxed evaluator. It bundles JSON Schema Draft 2020-12 for local
validation without a network round-trip.

Packages: static binary, Homebrew tap, Docker image.

Default catalog: `https://catalog.pollmevals.dev`.

## Installation

Install via the convenience script:

```bash
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

Or use Homebrew:

```bash
brew install pollmevals/tap/fetch-task
```

Or pull the container image:

```bash
docker pull ghcr.io/pollmevals/fetch-task:latest
```

Confirm the installation:

```bash
pollmevals fetch-task --version
```

## Quick start

Run through the basic lifecycle in four commands:

```bash
# List what is available
pollmevals fetch-task list --category backend

# Inspect a task
pollmevals fetch-task show be_01_jwt_auth

# Validate a local pack
pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth

# Execute and collect results
pollmevals fetch-task run be_01_jwt_auth \
  --stack claude-code-basic \
  --out ./artifacts/
```

## Commands

### list

Retrieves the list of task packs available in the catalog.

**Syntax:**

```bash
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

**Flags:**

| Flag | Description |
|---|---|
| `--category <cat>` | Filter to `backend`, `frontend`, `docs`, or `review`. |
| `--difficulty <level>` | Filter to `easy`, `medium`, or `hard`. |
| `--json` | Newline-delimited JSON output. |

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Success. |
| 2 | Network failure. |
| 3 | Authentication failure. |

**Example:**

```bash
pollmevals fetch-task list --category frontend --json
```

### show

Shows the metadata of a task pack. When `--version` is not given,
the latest version is returned.

**Syntax:**

```bash
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

**Flags:**

| Flag | Default | Description |
|---|---|---|
| `--version <ver>` | `latest` | The version string to retrieve. |
| `--json` | — | Emit JSON output. |

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Success. |
| 4 | Task not found. |
| 5 | Version not found. |

**Example:**

```bash
pollmevals fetch-task show doc_01_cli_readme --version 1.1
```

### validate

Validates a task pack against the bundled JSON Schema. The argument can
be a path to a local directory or a remote task ID.

**Syntax:**

```bash
pollmevals fetch-task validate <path-or-id> [--strict]
```

**Flags:**

| Flag | Description |
|---|---|
| `--strict` | Enforce calibration-band quorum (≥5 samples per band). |

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Valid. |
| 6 | Schema violation. |
| 7 | Quorum failure (strict mode only). |

**Example:**

```bash
pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme --strict
```

### run

Pulls a task pack from the catalog, mounts it into the sandbox evaluator,
and runs the configured Stack against it.

**Syntax:**

```bash
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

**Flags:**

| Flag | Default | Description |
|---|---|---|
| `--stack <stack-slug>` | *(required)* | Stack identifier to evaluate against. |
| `--seed <int>` | — | Random seed for reproducibility. |
| `--out <dir>` | `./artifacts/` | Output directory for artefacts. |
| `--dry-run` | — | Print the planned invocation without running it. |

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Success. |
| 8 | Stack not found. |
| 9 | Sandbox error. |
| 10 | Evaluator failure (infrastructure succeeded; output scored below threshold). |

**Example:**

```bash
pollmevals fetch-task run fe_01_multistep_form \
  --stack forgeplan-framework \
  --seed 3 \
  --out ./out/
```

## Configuration

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | Catalog base URL. |
| `POLLMEVALS_API_TOKEN` | unset | Bearer token for private catalogs. |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | Local cache for task packs. |
| `POLLMEVALS_NO_COLOR` | unset | Disable colour output if set. |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug`, `info`, `warn`, or `error`. |

### Config file

The default config path is `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`.
Specify an alternate location with `--config`.

Precedence (highest wins): CLI flag → env var → config file → default.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir: /tmp/pv
log_level: info
```

## Troubleshooting

**Exit 2 — network failure**

The catalog is unreachable. Check connectivity:

```bash
curl -sf https://catalog.pollmevals.dev/healthz
```

Use `HTTPS_PROXY` or override `POLLMEVALS_CATALOG_URL` for proxy
environments.

**Exit 3 — auth failure**

Set a valid API token:

```bash
export POLLMEVALS_API_TOKEN=pv_live_yourtoken
pollmevals fetch-task list
```

**Exit 9 — sandbox error**

Check Docker is running and the image is current:

```bash
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit 6 — schema violation**

Run at debug level to identify the bad field:

```bash
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT. See [LICENSE](LICENSE).
