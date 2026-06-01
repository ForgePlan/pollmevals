<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/meta-llama-001 — compact sections, inline code emphasis, no table headers for small flag sets -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` is a tool for fetching, validating, and running
POLLMEVALS evaluation task packs. It communicates with a central catalog
to list and download packs, validates them against the bundled JSON Schema
(Draft 2020-12), and runs them in a sandboxed environment.

Catalog: `https://catalog.pollmevals.dev` (override via env or config).

Distribution: static binary, Homebrew tap (`pollmevals/tap`), Docker
image (`ghcr.io/pollmevals/fetch-task`).

## Installation

**Binary**

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

Verify:

```bash
pollmevals fetch-task --version
```

## Quick start

```bash
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01_jwt_auth
pollmevals fetch-task run be_01_jwt_auth --stack claude-code-basic --out ./out/
```

## Commands

### list

List task packs from the catalog.

```bash
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

Flags:
- `--category` — filter: `backend`, `frontend`, `docs`, `review`
- `--difficulty` — filter: `easy`, `medium`, `hard`
- `--json` — output as newline-delimited JSON

Exit codes: 0 success, 2 network failure, 3 auth failure

```bash
pollmevals fetch-task list --category docs --difficulty easy
```

### show

Show metadata for a single task pack.

```bash
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

Flags:
- `--version` — version to retrieve (default: `latest`)
- `--json` — JSON output

Exit codes: 0 success, 4 task not found, 5 version not found

```bash
pollmevals fetch-task show be_01_jwt_auth
pollmevals fetch-task show be_01_jwt_auth --version 1.0 --json
```

### validate

Validate a task pack against the bundled schema.

```bash
pollmevals fetch-task validate <path-or-id> [--strict]
```

Flags:
- `--strict` — also check calibration-band quorum (≥5 samples per band)

Exit codes: 0 valid, 6 schema violation, 7 quorum failure

```bash
pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth
pollmevals fetch-task validate be_01_jwt_auth --strict
```

### run

Pull and run a task pack in the sandbox evaluator.

```bash
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

Flags:
- `--stack` — stack slug to evaluate against **(required)**
- `--seed` — random seed
- `--out` — artefact output directory (default: `./artifacts/`)
- `--dry-run` — print planned invocation, do not run

Exit codes: 0 success, 8 stack not found, 9 sandbox error,
10 evaluator failure (not an infra error — sandbox ran OK, candidate
output scored below threshold)

```bash
pollmevals fetch-task run be_01_jwt_auth \
  --stack forgeplan-framework \
  --seed 12 \
  --out ./results/

pollmevals fetch-task run be_01_jwt_auth --stack raw-llm --dry-run
```

## Configuration

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | Catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | Bearer auth token |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | Local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | Disable ANSI colour if set |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

### Config file

Location: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

Override path: `--config <path>`

Precedence (highest first): CLI flag → env var → config file → default

```yaml
catalog_url: https://catalog.pollmevals.dev
log_level: warn
```

## Troubleshooting

**Exit 2 — network failure**

Test catalog connectivity:

```bash
curl -sf https://catalog.pollmevals.dev/healthz && echo ok
```

If behind a proxy, set `HTTPS_PROXY` or override `POLLMEVALS_CATALOG_URL`.

**Exit 3 — auth failure**

Set your API token:

```bash
export POLLMEVALS_API_TOKEN=pv_live_yourtoken
pollmevals fetch-task list
```

**Exit 9 — sandbox failure**

Check that Docker is running:

```bash
docker info
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit 6 — schema violation**

Enable debug logging to see which field fails:

```bash
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and PR conventions.

## Licence

MIT — see [LICENSE](LICENSE).
