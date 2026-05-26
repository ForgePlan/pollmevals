<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); perfect/sample-005 — narrative engineer's-notes voice; prose paragraphs that still carry every required fact -->
# pollmevals fetch-task

A small CLI that does four useful things with POLLMEVALS task packs:
lists what the catalog has, shows the metadata for one, validates a
pack against the bundled schema, and runs the pack against a Stack
inside the evaluator sandbox.

## Overview

The catalog lives at `https://catalog.pollmevals.dev` by default
(override with `POLLMEVALS_CATALOG_URL`), and the schema is JSON Schema
Draft 2020-12, compiled into the binary so there is nothing to fetch
before validation works. The tool ships as a single static binary, a
Homebrew formula in the `pollmevals/tap` repository, and a Docker image
at `ghcr.io/pollmevals/fetch-task`. It writes only inside its cache
(`$XDG_CACHE_HOME/pollmevals` by default) and inside the `--out`
directory you give to `run` — nothing else on the filesystem changes.

## Installation

The static binary is the typical install. The one-liner verifies a
SHA-256 against the GitHub release before placing the executable:

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
```

If you prefer Homebrew, tap and install:

```sh
brew install pollmevals/tap/fetch-task
```

If you would rather containerise, pull the image. It is a distroless
build, so the entry point is the binary itself:

```sh
docker pull ghcr.io/pollmevals/fetch-task:latest
docker run --rm ghcr.io/pollmevals/fetch-task --version
```

Confirm the install with `pollmevals fetch-task --version`; you should
see `pollmevals fetch-task 0.1.0`.

## Quick start

The shortest path to a green smoke run is four commands. Run them in
order; the last one completes in about ninety seconds against the
`raw-llm` stack:

```sh
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

When the fourth command finishes you should see:

```
ok  be_01 / raw-llm / seed=42
    artefacts → ./artifacts/run-2026-05-26T14-22-08Z-be01-rawllm/
    exit 0
```

## Commands

### list

`list` walks the catalog and prints the task packs you can see. It is
the safest subcommand to start with because it talks only to the
catalog and writes nothing locally.

```sh
pollmevals fetch-task list [--category <cat>] [--difficulty <level>] [--json]
```

`--category` accepts one of `backend`, `frontend`, `docs`, `review`.
`--difficulty` accepts one of `easy`, `medium`, `hard`. `--json`
switches the output from a human table to machine-readable JSON. A
typical invocation:

```sh
$ pollmevals fetch-task list --category backend
ID      VERSION  DIFFICULTY  TITLE
be_01   1.0      medium      JWT auth middleware with refresh rotation
```

Exit codes: `0` for success, `2` when the catalog is unreachable, `3`
when the catalog returned 401.

### show

`show` prints one task pack's metadata. The `--version` flag defaults
to `latest`; use a semver string to pin (`1.0`, `1.1`, etc).

```sh
pollmevals fetch-task show <task-id> [--version <ver>] [--json]
```

Example:

```sh
$ pollmevals fetch-task show be_01 --version 1.0
id:          be_01
slug:        jwt-auth-middleware-with-refresh
version:     1.0
category:    backend
difficulty:  medium
```

Exit codes: `0` on success, `4` when the task ID is not in the catalog,
`5` when the requested version of an existing task does not exist.

### validate

`validate` runs a local task-pack directory (or a remote ID, in which
case the pack is fetched into the cache first) against the bundled JSON
Schema. The `--strict` flag layers an extra check: the calibration
directory must contain at least five samples per band — `perfect`,
`good`, `mediocre`, `poor`, `broken`.

```sh
pollmevals fetch-task validate <path-or-id> [--strict]
```

Example output for a healthy pack:

```sh
$ pollmevals fetch-task validate ./evals/task-packs/be_01_jwt_auth --strict
schema:      ok
calibration: ok (perfect=5, good=5, mediocre=5, poor=5, broken=5)
```

Exit codes: `0` valid, `6` schema violation, `7` quorum failure (only
returned when `--strict` is on).

### run

`run` is the heavyweight subcommand. It pulls the task pack, mounts it
into the evaluator image (`ghcr.io/pollmevals/eval-ts:0.1.0` by
default), runs the named Stack against it, and writes artefacts to
`--out` (`./artifacts/` by default).

```sh
pollmevals fetch-task run <task-id> --stack <stack-slug> \
                                    [--seed <int>] [--out <dir>] [--dry-run]
```

`--stack` is required and accepts any slug from `stacks/<slug>/stack.yaml`
— `raw-llm`, `claude-code-basic`, `forgeplan-framework`. `--seed` fixes
the candidate model's RNG; without it the seed is randomised, which is
fine for exploratory runs and wrong for reproducibility. `--dry-run`
prints the plan and exits without touching the sandbox:

```sh
$ pollmevals fetch-task run be_01 --stack claude-code-basic --seed 42 --dry-run
plan:
  task:   be_01 @ 1.0
  stack:  claude-code-basic
  image:  ghcr.io/pollmevals/eval-ts:0.1.0
  seed:   42
  out:    ./artifacts/
```

Exit codes: `0` success, `8` when the Stack slug is not in `stacks/`,
`9` for any sandbox-level failure (image pull, mount, supervision), and
`10` when the evaluator finished but reported a low-quality candidate.
Note that `10` is the evaluator's verdict, not an infrastructure
problem — the wrapper itself succeeded.

## Configuration

Configuration sources, with the highest priority listed first: a CLI
flag wins, then an environment variable, then the config file (either
`--config <path>` or the default location), then the compiled-in
default. The default config file path is
`$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`. A typical config:

```yaml
catalog_url: https://catalog.pollmevals.dev
cache_dir:   ~/.cache/pollmevals
log_level:   info
api_token:   ""
```

The supported environment variables are:

| Variable | Default | Purpose |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | `https://catalog.pollmevals.dev` | catalog base URL |
| `POLLMEVALS_API_TOKEN` | unset | bearer token for private catalogs |
| `POLLMEVALS_CACHE_DIR` | `$XDG_CACHE_HOME/pollmevals` | local pack cache |
| `POLLMEVALS_NO_COLOR` | unset | disable ANSI colour on stderr |
| `POLLMEVALS_LOG_LEVEL` | `info` | one of `debug`, `info`, `warn`, `error` |

## Troubleshooting

The four exit codes you will see most often have specific remedies.

If `list` exits `2`, the catalog is unreachable. Confirm with
`curl -fsS $POLLMEVALS_CATALOG_URL/health`; on a corporate network
verify that egress on 443 to the catalog host is open.

If `show` exits `3`, the catalog returned 401. Your
`POLLMEVALS_API_TOKEN` is either unset (for a private catalog) or
expired. Regenerate the token from the catalog web UI and re-export
with `export POLLMEVALS_API_TOKEN=<new-token>`.

If `validate` exits `6`, the task pack does not satisfy the bundled
schema. Re-run with `POLLMEVALS_LOG_LEVEL=debug` to print the failing
JSON Pointer and the value at that pointer.

If `run` exits `9`, the evaluator sandbox is unavailable. Run
`docker version` and `docker pull ghcr.io/pollmevals/eval-ts:0.1.0` to
confirm Docker is up and the image is reachable.

## Contributing

Source lives at `https://github.com/pollmevals/fetch-task`. Read
`CONTRIBUTING.md` before opening a PR — it covers branch conventions,
the required `moon run :test` smoke test, and the rule that any change
to a subcommand's `--json` output must keep the existing wire schema
backwards compatible.

## Licence

MIT. The full text is in `LICENSE` at the repository root.
