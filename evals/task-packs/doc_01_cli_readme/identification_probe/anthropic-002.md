<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/anthropic-002 — numbered steps in quick start, inline explanations adjacent to flag tables -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` downloads and validates POLLMEVALS evaluation task
packs from a centrally hosted catalog and runs them inside an isolated
sandbox evaluator. It is distributed as a self-contained static binary,
a Homebrew formula, and a Docker image — no runtime dependencies are
required beyond Docker for the `run` subcommand.

By default the tool connects to `https://catalog.pollmevals.dev`. The
catalog URL, authentication token, and local cache path can all be
overridden without recompiling.

## Installation

**Binary installer**

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

Verify the binary is on `PATH`:

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

## Quick start

1. List all available backend tasks:

   ```sh
   pollmevals fetch-task list --category backend
   ```

2. Inspect the JWT auth task:

   ```sh
   pollmevals fetch-task show be_01_jwt_auth
   ```

3. Validate a local task pack before submitting changes:

   ```sh
   pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth
   ```

4. Run the task with a specific stack:

   ```sh
   pollmevals fetch-task run be_01_jwt_auth \
     --stack claude-code-basic \
     --out ./out/
   ```

## Commands

### list

Queries the catalog for available task packs. Supports category and
difficulty filters, and can produce machine-readable JSON output.

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

| Flag | Values | Description |
|---|---|---|
| `--category` | `backend` `frontend` `docs` `review` | Narrow results to one category |
| `--difficulty` | `easy` `medium` `hard` | Narrow results to one difficulty level |
| `--json` | — | Emit newline-delimited JSON; one record per task |

Exit codes: `0` success · `2` network failure · `3` auth failure

```sh
pollmevals fetch-task list --category frontend --difficulty medium
```

### show

Retrieves and displays metadata for a single task pack.

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

| Flag | Default | Description |
|---|---|---|
| `--version` | `latest` | Specific version string to fetch |
| `--json` | — | Emit JSON instead of formatted text |

Exit codes: `0` success · `4` task not found · `5` version not found

```sh
pollmevals fetch-task show be_01_jwt_auth --version 1.0
```

### validate

Validates a task pack against the JSON Schema Draft 2020-12 bundled
inside the binary. Accepts either a local directory path or a remote
task ID.

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

| Flag | Description |
|---|---|
| `--strict` | Enforce calibration-band quorum: each band must have ≥5 samples |

Exit codes: `0` valid · `6` schema violation · `7` quorum failure

```sh
# Local path
pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme --strict

# Remote ID
pollmevals fetch-task validate doc_01_cli_readme
```

### run

Pulls the specified task pack from the catalog, mounts it into the
sandbox evaluator container, and runs the named Stack against it.

```
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

| Flag | Default | Description |
|---|---|---|
| `--stack` | *(required)* | Stack slug to evaluate against |
| `--seed` | — | Integer seed for reproducibility |
| `--out` | `./artifacts/` | Directory to write output artefacts |
| `--dry-run` | — | Print the planned invocation without executing |

Exit codes: `0` success · `8` stack not found · `9` sandbox error ·
`10` evaluator-reported failure

```sh
pollmevals fetch-task run doc_01_cli_readme \
  --stack forgeplan-framework \
  --seed 7 \
  --out ./artifacts/doc_01/
```

## Configuration

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | Catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | Bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | Local cache for downloaded packs |
| `POLLMEVALS_NO_COLOR` | unset | Disable ANSI colour when set to any value |
| `POLLMEVALS_LOG_LEVEL` | `info` | One of `debug`, `info`, `warn`, `error` |

### Config file

Default path: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

Override with `--config <path>`. The file is optional; omitting it uses
compiled-in defaults.

Precedence (highest wins): CLI flag → env var → config file →
compiled-in default.

```yaml
# fetch-task.yaml
catalog_url: https://catalog.internal.example.com
log_level: warn
cache_dir: ~/.cache/pollmevals
```

## Troubleshooting

**Exit code 2 — network failure**

Verify catalog reachability:

```sh
curl -sf https://catalog.pollmevals.dev/healthz && echo "reachable"
```

If behind a corporate proxy, set `HTTPS_PROXY` or point
`POLLMEVALS_CATALOG_URL` at an accessible mirror.

**Exit code 3 — auth failure**

Confirm the token is set correctly:

```sh
export POLLMEVALS_API_TOKEN=pv_live_<your-token>
pollmevals fetch-task list
```

**Exit code 9 — sandbox infrastructure error**

Confirm Docker is running and the image is present:

```sh
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit code 6 — schema violation**

Enable debug logging to see the full violation path:

```sh
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
```

## Contributing

Contribution guidelines, branch naming, and the PR checklist are in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

MIT. See [`LICENSE`](LICENSE).
