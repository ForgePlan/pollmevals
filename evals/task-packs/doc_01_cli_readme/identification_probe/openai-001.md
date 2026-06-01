<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/openai-001 — direct imperative headers, minimal prose, terse inline tables -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` fetches POLLMEVALS evaluation task packs from a
remote catalog, validates them against a bundled JSON Schema (Draft
2020-12), and runs them in an isolated sandbox. Ships as a static binary,
Homebrew formula, and Docker image.

Default catalog: `https://catalog.pollmevals.dev`. Set
`POLLMEVALS_CATALOG_URL` to use a different endpoint.

## Installation

```sh
# Binary
curl -fsSL https://get.pollmevals.dev/fetch-task | sh

# Homebrew
brew install pollmevals/tap/fetch-task

# Docker
docker pull ghcr.io/pollmevals/fetch-task:latest
```

Confirm:

```sh
pollmevals fetch-task --version
```

## Quick start

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01_jwt_auth
pollmevals fetch-task run be_01_jwt_auth --stack claude-code-basic --out ./artifacts/
```

## Commands

### list

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

| Flag | Description |
|---|---|
| `--category` | `backend`, `frontend`, `docs`, `review` |
| `--difficulty` | `easy`, `medium`, `hard` |
| `--json` | Output newline-delimited JSON |

Exit codes: 0 ok, 2 network error, 3 auth error

```sh
pollmevals fetch-task list --category docs
```

### show

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

| Flag | Default | Description |
|---|---|---|
| `--version` | `latest` | Task version |
| `--json` | — | JSON output |

Exit codes: 0 ok, 4 not found, 5 version not found

```sh
pollmevals fetch-task show doc_01_cli_readme
pollmevals fetch-task show doc_01_cli_readme --version 1.1 --json
```

### validate

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

| Flag | Description |
|---|---|
| `--strict` | Enforce calibration-band quorum (≥5 samples per band) |

Exit codes: 0 valid, 6 schema error, 7 quorum error

```sh
pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth
pollmevals fetch-task validate be_01_jwt_auth --strict
```

### run

```
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

| Flag | Default | Description |
|---|---|---|
| `--stack` | required | Stack slug |
| `--seed` | — | RNG seed |
| `--out` | `./artifacts/` | Output directory |
| `--dry-run` | — | Print plan, do not execute |

Exit codes: 0 ok, 8 stack not found, 9 sandbox error, 10 evaluator failure

```sh
pollmevals fetch-task run be_01_jwt_auth \
  --stack forgeplan-framework \
  --seed 1 \
  --out ./out/

# Dry run
pollmevals fetch-task run be_01_jwt_auth --stack raw-llm --dry-run
```

## Configuration

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | Catalog endpoint |
| `POLLMEVALS_API_TOKEN` | unset | Bearer token |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | Pack cache directory |
| `POLLMEVALS_NO_COLOR` | unset | Disable colour output if set |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

### Config file

Path: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml` (override with `--config`)

Precedence: CLI flag > env var > config file > compiled default

```yaml
catalog_url: https://catalog.pollmevals.dev
log_level: warn
cache_dir: ~/.cache/pollmevals
```

## Troubleshooting

**Exit 2 — network failure**

The catalog is unreachable. Test connectivity:

```sh
curl -I https://catalog.pollmevals.dev/healthz
```

Set `HTTPS_PROXY` if behind a proxy, or override `POLLMEVALS_CATALOG_URL`.

**Exit 3 — auth failure**

Provide or refresh your API token:

```sh
export POLLMEVALS_API_TOKEN=pv_live_yourtoken
```

**Exit 9 — sandbox error**

Docker is not running or the image is missing:

```sh
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit 6 — schema violation**

Enable debug logging:

```sh
POLLMEVALS_LOG_LEVEL=debug pollmevals fetch-task validate ./path/to/pack
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).
