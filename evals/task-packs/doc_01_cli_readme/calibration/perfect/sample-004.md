<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); perfect/sample-004 — reference-style, specification voice with synopsis grammar -->
# pollmevals fetch-task — Reference

> Reference documentation for `pollmevals fetch-task` version 0.1.x.
> Conformance to this document is enforced by the
> `--json` schema and the test suite in `apps/cli/tests/`.

## Overview

```
NAME
    pollmevals-fetch-task — POLLMEVALS task-pack CLI

SYNOPSIS
    pollmevals fetch-task <subcommand> [options]

SUBCOMMANDS
    list      List task packs from the catalog.
    show      Print one task pack's metadata.
    validate  Validate a task pack against the bundled JSON Schema.
    run       Execute a task pack against a Stack inside the sandbox.

CONFORMANCE
    The wire format of every `--json` output is governed by
    `apps/cli/schema/fetch-task-cli.schema.json` and is breaking-change
    safe within a major version (semver).
```

## Installation

### Static binary

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

Installs `pollmevals-fetch-task` to `/usr/local/bin` after SHA-256
verification against the GitHub release.

### Homebrew

```sh
brew install pollmevals/tap/fetch-task
```

### Docker

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
```

The image is `gcr.io/distroless/static`-based; entry point is
`/pollmevals-fetch-task`.

## Quick start

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

Conformant output for the fourth command:

```
ok  be_01 / raw-llm / seed=42
    artefacts → ./artifacts/run-2026-05-26T14-22-08Z-be01-rawllm/
    exit 0
```

## Commands

### list

```
SYNOPSIS
    pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]

OPTIONS
    --category   one of: backend | frontend | docs | review
    --difficulty one of: easy | medium | hard
    --json       emit JSON conforming to `list-result.schema.json`

EXIT CODES
    0   success
    2   network failure
    3   authentication failure

EXAMPLE
    $ pollmevals fetch-task list --category backend
    ID      VERSION  DIFFICULTY  TITLE
    be_01   1.0      medium      JWT auth middleware with refresh rotation
```

### show

```
SYNOPSIS
    pollmevals fetch-task show <task-id> [--version <ver>] [--json]

OPTIONS
    --version   semver string; default `latest`
    --json      emit JSON conforming to `show-result.schema.json`

EXIT CODES
    0   success
    4   task not found
    5   version not found

EXAMPLE
    $ pollmevals fetch-task show be_01 --version 1.0
    id:        be_01
    slug:      jwt-auth-middleware-with-refresh
    version:   1.0
    category:  backend
    difficulty: medium
```

### validate

```
SYNOPSIS
    pollmevals fetch-task validate <path-or-id> [--strict]

OPTIONS
    --strict   additionally enforce calibration quorum (≥5 samples per band)

EXIT CODES
    0   valid
    6   schema violation
    7   quorum failure (only returned when --strict is set)

EXAMPLE
    $ pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth --strict
    schema:      ok
    calibration: ok (perfect=5, good=5, mediocre=5, poor=5, broken=5)
```

### run

```
SYNOPSIS
    pollmevals fetch-task run <task-id> --stack <stack-slug> [--seed <int>]
                                        [--out <dir>] [--dry-run]

OPTIONS
    --stack     required; slug from `stacks/<slug>/stack.yaml`
    --seed      integer; default random
    --out       artefact directory; default `./artifacts/`
    --dry-run   validate inputs and print the planned invocation only

EXIT CODES
    0   success
    8   stack not found
    9   sandbox error
    10  evaluator reported a low-scoring but well-formed candidate

EXAMPLE
    $ pollmevals fetch-task run be_01 --stack claude-code-basic --seed 42 --dry-run
    plan:
      task:   be_01 @ 1.0
      stack:  claude-code-basic
      image:  ghcr.io/pollmevals/eval-ts:0.1.0
      seed:   42
      out:    ./artifacts/
```

## Configuration

### Precedence

```
HIGHEST  →  CLI flag
            environment variable
            config file (--config <path> or default location)
LOWEST   →  compiled-in default
```

### Config file

Default path: `$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`.

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir:   ~/.cache/pollmevals
log_level:   info
api_token:   ""
```

### Environment

| Variable | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |

## Troubleshooting

```
EXIT  COMMAND   SYMPTOM                              REMEDY
2     list      "catalog unreachable"                curl -fsS $POLLMEVALS_CATALOG_URL/health; check egress 443
3     show      "401 Unauthorized"                   regenerate POLLMEVALS_API_TOKEN and re-export
6     validate  "schema violation at <pointer>"      re-run with POLLMEVALS_LOG_LEVEL=debug to print the JSON Pointer
9     run       "sandbox unavailable"                docker version; docker pull ghcr.io/pollmevals/eval-ts:0.1.0
```

## Contributing

Repository: `https://github.com/pollmevals/fetch-task`. See
`CONTRIBUTING.md` for branch conventions, required smoke
(`moon run :test`), and the rule that the `--json` wire schema is
preserved across minor versions.

## Licence

MIT. Full text in `LICENSE`.
