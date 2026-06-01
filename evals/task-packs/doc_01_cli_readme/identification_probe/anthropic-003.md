<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/anthropic-003 — bold concept labels, bullet-list flag presentation, callout-style notes -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` is a command-line utility for retrieving POLLMEVALS
evaluation task packs from a remote catalog, validating them against a
bundled JSON Schema, and executing them inside a sandboxed evaluator. The
binary bundles the schema and the evaluator harness — no separate install
step is needed for local schema validation.

**Catalog endpoint:** `https://catalog.pollmevals.dev`
Override with `POLLMEVALS_CATALOG_URL` for private or mirror deployments.

**Auth:** Pass `POLLMEVALS_API_TOKEN` as a bearer token when the catalog
requires authentication. Public catalog access does not require a token.

## Installation

**Via install script**

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

**Via Homebrew**

```sh
brew install pollmevals/tap/fetch-task
```

**Via Docker**

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Verify**

```sh
pollmevals fetch-task --version
```

## Quick start

```sh
# Browse available tasks
pollmevals fetch-task list --category backend

# Inspect a task
pollmevals fetch-task show be_01_jwt_auth

# Run the task, collecting artefacts in ./artifacts/
pollmevals fetch-task run be_01_jwt_auth \
  --stack claude-code-basic \
  --out ./artifacts/
```

## Commands

### list

Enumerate task packs from the catalog with optional filters.

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Flags:

- `--category <cat>` — one of `backend`, `frontend`, `docs`, `review`
- `--difficulty <level>` — one of `easy`, `medium`, `hard`
- `--json` — emit newline-delimited JSON instead of tabular output

Exit codes:

- `0` — success
- `2` — network failure (catalog unreachable)
- `3` — auth failure (token rejected or missing)

```sh
pollmevals fetch-task list --category review --json
```

### show

Display full metadata for a single task pack. Versions default to
`latest` unless overridden.

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

Flags:

- `--version <ver>` — version string; defaults to `latest`
- `--json` — emit JSON

Exit codes:

- `0` — success
- `4` — task ID not found in catalog
- `5` — task found, but the requested version does not exist

```sh
pollmevals fetch-task show doc_01_cli_readme --json
pollmevals fetch-task show doc_01_cli_readme --version 1.0
```

### validate

Check a task pack against the bundled JSON Schema. Accepts a local
directory path or a remote task ID.

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

Flags:

- `--strict` — additionally check that each calibration band contains at
  least 5 samples (quorum check)

Exit codes:

- `0` — valid
- `6` — schema violation
- `7` — quorum failure (only triggered by `--strict`)

```sh
# Local directory
pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth

# Remote, with quorum check
pollmevals fetch-task validate be_01_jwt_auth --strict
```

### run

Pull a task pack, start the sandbox evaluator, and run the specified
Stack against it. Artefacts are written to the output directory.

```
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

Flags:

- `--stack <stack-slug>` — **(required)** the Stack to evaluate against
- `--seed <int>` — random seed for reproducibility across runs
- `--out <dir>` — artefact output directory; defaults to `./artifacts/`
- `--dry-run` — print the planned invocation without executing

Exit codes:

- `0` — success
- `8` — stack slug not found
- `9` — sandbox infrastructure failure (container error)
- `10` — evaluator-reported failure (sandbox succeeded; candidate output
  was below threshold — not an infrastructure error)

```sh
# Full run with seed
pollmevals fetch-task run fe_01_multistep_form \
  --stack forgeplan-framework \
  --seed 100 \
  --out ./out/fe/

# Dry run to inspect planned invocation
pollmevals fetch-task run be_01_jwt_auth --stack raw-llm --dry-run
```

## Configuration

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | Catalog base URL |
| `POLLMEVALS_API_TOKEN` | *(unset)* | Bearer token for private catalog access |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | Directory for locally cached task packs |
| `POLLMEVALS_NO_COLOR` | *(unset)* | Set to any value to suppress ANSI colour in stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | Log verbosity: `debug`, `info`, `warn`, `error` |

### Config file

Default location: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

Override with `--config <path>` on any subcommand.

Precedence (highest wins): CLI flag → env var → config file →
compiled-in default.

```yaml
catalog_url: https://catalog.pollmevals.dev
log_level: info
cache_dir: /var/cache/pollmevals
```

## Troubleshooting

**Network failure (exit 2)**

Verify catalog reachability. If behind a proxy, configure it via
`HTTPS_PROXY`:

```sh
curl -sf https://catalog.pollmevals.dev/healthz
# Expected: HTTP 200
```

**Auth failure (exit 3)**

Confirm the token value and that it has not expired:

```sh
export POLLMEVALS_API_TOKEN=pv_live_xxxxx
pollmevals fetch-task list
```

**Sandbox error (exit 9)**

Check Docker daemon status and image availability:

```sh
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Schema violation (exit 6)**

Enable debug logging to see the full violation path:

```sh
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, branch
naming conventions, and the review checklist.

## Licence

MIT. See [`LICENSE`](LICENSE).
