<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/openai-003 — flat reference style, code-heavy, inline exit-code annotations -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` is the CLI for POLLMEVALS task pack management.
It connects to a remote catalog, validates pack structure against a
bundled JSON Schema (Draft 2020-12), and runs packs in a sandboxed
evaluator.

- **Binary name:** `pollmevals-fetch-task` (entry point: `pollmevals fetch-task`)
- **Catalog:** `https://catalog.pollmevals.dev`
- **Schema:** JSON Schema Draft 2020-12, embedded in the binary
- **Config:** `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

## Installation

```sh
# Static binary
curl -fsSL https://get.pollmevals.dev/fetch-task | sh

# Homebrew
brew install pollmevals/tap/fetch-task

# Docker
docker pull ghcr.io/pollmevals/fetch-task:latest

# Check version
pollmevals fetch-task --version
```

## Quick start

```sh
# List backend tasks
pollmevals fetch-task list --category backend

# Show details for a task
pollmevals fetch-task show be_01_jwt_auth

# Run a task with the basic Claude Code stack
pollmevals fetch-task run be_01_jwt_auth \
  --stack claude-code-basic \
  --seed 42 \
  --out ./artifacts/
```

## Commands

### list

List task packs from the catalog.

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Flags:

| Flag | Values | Notes |
|---|---|---|
| `--category <cat>` | `backend` `frontend` `docs` `review` | Optional filter |
| `--difficulty <level>` | `easy` `medium` `hard` | Optional filter |
| `--json` | — | NDJSON output |

Exit codes: **0** success · **2** network failure · **3** auth failure

```sh
pollmevals fetch-task list --category docs --difficulty easy --json
```

### show

Show metadata for a task pack.

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

Flags:

| Flag | Default | Notes |
|---|---|---|
| `--version <ver>` | `latest` | — |
| `--json` | — | JSON output |

Exit codes: **0** success · **4** task not found · **5** version not found

```sh
pollmevals fetch-task show fe_01_multistep_form --json
```

### validate

Validate a task pack against the bundled schema.

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

Flags:

| Flag | Notes |
|---|---|
| `--strict` | Enforce ≥5 samples per calibration band |

Exit codes: **0** valid · **6** schema violation · **7** quorum failure

```sh
pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth
pollmevals fetch-task validate doc_01_cli_readme --strict
```

### run

Run a task pack through the evaluator.

```
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

Flags:

| Flag | Default | Notes |
|---|---|---|
| `--stack <stack-slug>` | *(required)* | Stack to evaluate against |
| `--seed <int>` | — | Reproducibility seed |
| `--out <dir>` | `./artifacts/` | Artefact output path |
| `--dry-run` | — | Print invocation, skip execution |

Exit codes: **0** success · **8** stack not found · **9** sandbox error ·
**10** evaluator failure (not an infra error)

```sh
pollmevals fetch-task run fe_01_multistep_form \
  --stack raw-llm \
  --seed 0 \
  --out ./out/fe/

# Preview without running
pollmevals fetch-task run be_01_jwt_auth \
  --stack forgeplan-framework \
  --dry-run
```

## Configuration

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | Catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | Bearer auth token |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | Pack cache root |
| `POLLMEVALS_NO_COLOR` | unset | Suppress ANSI colour if set |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

### Config file

Location: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

Specify an alternate path with `--config <path>`.

Precedence: CLI > env > config file > compiled default.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir: /tmp/pv
log_level: debug
```

## Troubleshooting

**Exit 2 — network failure**

```sh
curl -I https://catalog.pollmevals.dev/healthz
```

Use `HTTPS_PROXY` or override `POLLMEVALS_CATALOG_URL` if behind a
restricted network.

**Exit 3 — auth failure**

```sh
export POLLMEVALS_API_TOKEN=pv_live_...
pollmevals fetch-task list
```

**Exit 9 — sandbox startup failure**

```sh
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit 6 — schema violation**

```sh
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate <path-or-id>
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — [LICENSE](LICENSE).
