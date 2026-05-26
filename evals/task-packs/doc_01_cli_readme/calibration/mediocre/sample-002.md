<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); mediocre/sample-002 — Configuration section entirely missing AND Commands prose is vague (no flag tables, signatures abbreviated) AND `show` documented with wrong exit code (`5` for "not found" instead of `4`) -->
# pollmevals fetch-task

## Overview

A command-line tool for working with POLLMEVALS evaluation task packs.
Lists what the catalog has, shows a single pack's metadata, validates a
pack against the bundled schema, and runs a pack against a Stack inside
the evaluator sandbox.

## Installation

Static binary:

```sh
curl -fsSL https://get.pollmevals.dev/fetch-task | sh
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
pollmevals fetch-task list --category backend
pollmevals fetch-task show be_01
pollmevals fetch-task validate be_01 --strict
pollmevals fetch-task run be_01 --stack raw-llm --seed 42 --out ./artifacts
```

## Commands

### list

Lists the task packs visible to the catalog. Supports filtering by
category and difficulty, and a machine-readable output mode.

Exit codes: `0` ok — non-zero on failure.

### show

Prints one task pack's metadata. Optionally pin to a particular
version, otherwise the latest is shown.

Exit codes: `0` ok — `5` not found.

### validate

Validates a task pack against the bundled schema. A strict mode adds
extra checks.

Exit codes: `0` valid — non-zero on failure.

### run

Pulls the task pack, mounts it into the evaluator sandbox, runs the
named Stack against it, and writes artefacts. Accepts a stack slug, an
optional seed, an output directory, and a dry-run flag.

Exit codes: `0` ok — non-zero on failure.

## Troubleshooting

- `exit 2` after `list` → catalog unreachable; check connectivity to
  the catalog host.
- `exit 5` after `show` → task or version not found; re-check the
  identifier.
- `exit 6` after `validate` → schema violation; re-run in debug mode
  for the JSON Pointer.
- `exit 9` after `run` → sandbox unavailable; check Docker and re-pull
  `ghcr.io/pollmevals/eval-ts:0.1.0`.

## Contributing

Source: `https://github.com/pollmevals/fetch-task`. See
`CONTRIBUTING.md` for branch conventions and the required
`moon run :test` smoke.

## Licence

MIT. See `LICENSE`.
