<!-- source: own-authored 2026-06-01 by gogocat (license: MIT); identification_probe/openai-002 — lean prose, synopsis-first subcommand layout, light use of horizontal rules -->
# pollmevals fetch-task

## Overview

`pollmevals fetch-task` is a CLI for working with POLLMEVALS evaluation
task packs. Use it to browse the catalog, validate task pack structure,
and run packs through the sandboxed evaluator.

Distribution: static binary, Homebrew (`pollmevals/tap`), Docker
(`ghcr.io/pollmevals/fetch-task`).

Catalog: `https://catalog.pollmevals.dev` (configurable via
`POLLMEVALS_CATALOG_URL`).

## Installation

Binary:

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
pollmevals fetch-task --version
```

Homebrew:

```sh
brew install pollmevals/tap/fetch-task
```

Docker:

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
```

## Quick start

```sh
# Find something to run
pollmevals fetch-task list --category backend --difficulty easy

# Inspect it
pollmevals fetch-task show be_01_jwt_auth

# Run it
pollmevals fetch-task run be_01_jwt_auth \
  --stack claude-code-basic \
  --out ./run-001/
```

## Commands

### list

Browse available task packs.

**Synopsis:**

```
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

**Flags:**

- `--category <cat>` — `backend` | `frontend` | `docs` | `review`
- `--difficulty <level>` — `easy` | `medium` | `hard`
- `--json` — newline-delimited JSON output

**Exit codes:** 0 success / 2 network failure / 3 auth failure

```sh
pollmevals fetch-task list --json | jq '.slug'
```

---

### show

Display task metadata.

**Synopsis:**

```
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

**Flags:**

- `--version <ver>` — version to fetch (default: `latest`)
- `--json` — emit JSON

**Exit codes:** 0 / 4 not found / 5 version not found

```sh
pollmevals fetch-task show fe_01_multistep_form --version 1.0
```

---

### validate

Validate a task pack against the bundled JSON Schema.

**Synopsis:**

```
pollmevals fetch-task validate <path-or-id> [--strict]
```

**Flags:**

- `--strict` — require ≥5 calibration samples per band

**Exit codes:** 0 valid / 6 schema violation / 7 quorum failure

```sh
pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
pollmevals fetch-task validate doc_01_cli_readme --strict
```

---

### run

Run a task pack through the evaluator.

**Synopsis:**

```
pollmevals fetch-task run <task-id> --stack <stack-slug> \
  [--seed <int>] [--out <dir>] [--dry-run]
```

**Flags:**

- `--stack <stack-slug>` — stack to use *(required)*
- `--seed <int>` — randomness seed
- `--out <dir>` — artefact directory (default `./artifacts/`)
- `--dry-run` — print plan, skip execution

**Exit codes:** 0 / 8 stack missing / 9 sandbox failure / 10 evaluator failure

Note: exit 10 means the evaluator ran to completion and flagged a
low-quality submission. It is not an infrastructure error.

```sh
pollmevals fetch-task run doc_01_cli_readme \
  --stack forgeplan-framework \
  --seed 2025 \
  --out ./results/

# Dry run first
pollmevals fetch-task run doc_01_cli_readme --stack raw-llm --dry-run
```

## Configuration

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | Remote catalog URL |
| `POLLMEVALS_API_TOKEN` | unset | Auth token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | Local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | Disable ANSI colour when set |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

### Config file

Default: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`

Override with `--config <path>`.

Precedence (highest first): CLI flag → env var → config file → built-in default.

```yaml
catalog_url: https://catalog.pollmevals.dev
log_level: warn
cache_dir: /data/pv-cache
```

## Troubleshooting

**Exit 2 — cannot reach catalog**

```sh
curl -sf https://catalog.pollmevals.dev/healthz && echo ok
```

If blocked by a firewall or proxy, set `HTTPS_PROXY` or override the
catalog URL.

**Exit 3 — authentication rejected**

```sh
export POLLMEVALS_API_TOKEN=<your_token>
pollmevals fetch-task list
```

**Exit 9 — sandbox failed to start**

```sh
docker info          # daemon running?
docker pull ghcr.io/pollmevals/fetch-task:latest
```

**Exit 6 — schema violation**

```sh
POLLMEVALS_LOG_LEVEL=debug \
  pollmevals fetch-task validate ./evals/task-packs/doc_01_cli_readme
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit conventions and the PR
workflow.

## Licence

MIT. Full text in [LICENSE](LICENSE).
