<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); poor/sample-002 — hallucinated subcommands (`init`, `sync`, `audit`) that are not in the contract; real subcommands absent -->
# pollmevals fetch-task

## Overview

A command-line interface for the POLLMEVALS task catalog. Provides
initialisation, synchronisation, auditing, and reporting for local
copies of the benchmark.

## Installation

```sh
brew install pollmevals/tap/fetch-task
```

## Quick start

```sh
pollmevals fetch-task init
pollmevals fetch-task sync
pollmevals fetch-task audit
pollmevals fetch-task report --format html
```

## Commands

### init

Initialises a local POLLMEVALS workspace under `~/.pollmevals/` with a
config file, an empty cache directory, and a default identity.

```sh
pollmevals fetch-task init [--force]
```

### sync

Synchronises the local cache with the remote catalog. Pulls new task
packs and prunes ones removed upstream.

```sh
pollmevals fetch-task sync [--prune] [--dry-run]
```

### audit

Audits the local cache for tampered or out-of-date packs.

```sh
pollmevals fetch-task audit
```

### report

Generates an HTML or JSON report of the local cache state and recent
runs.

```sh
pollmevals fetch-task report [--format <html|json>]
```

## Configuration

A YAML config file under `~/.pollmevals/config.yaml`. No environment
variables are read.

## Troubleshooting

Run `pollmevals fetch-task audit --verbose` for diagnostics.

## Contributing

PRs welcome.

## Licence

MIT.
