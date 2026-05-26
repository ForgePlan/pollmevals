<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); poor/sample-001 — Commands section missing entirely AND Installation section missing AND tool name flips between `pollmevals fetch-task`, `pollmevals-cli`, and `pmctl` -->
# pollmevals fetch-task

## Overview

`pollmevals-cli` is a command-line tool for the POLLMEVALS benchmark.
It interacts with a remote catalog of task packs, validates them
locally, and runs them against a Stack. The catalog lives at
`https://catalog.pollmevals.dev`.

## Quick start

Once installed, you can list available task packs, inspect them, and
run them against a Stack. The full reference of subcommands is
maintained inside the binary — pass `--help` to any subcommand to see
its flags.

```sh
pmctl --help
pollmevals-cli list --help
pmctl run --help
```

## Configuration

The tool reads configuration from CLI flags, then environment
variables, then a YAML config file at
`$XDG_CONFIG_HOME/pollmevals/fetch-task.yaml`, then compiled-in
defaults. Supported environment variables include
`POLLMEVALS_CATALOG_URL`, `POLLMEVALS_API_TOKEN`,
`POLLMEVALS_CACHE_DIR`, and `POLLMEVALS_LOG_LEVEL`.

## Troubleshooting

If a command fails, re-run it with `POLLMEVALS_LOG_LEVEL=debug` and
inspect the stderr trace. Common categories of failure include catalog
unreachability, authentication errors, schema violations, and sandbox
problems with Docker. Each surfaces a distinct non-zero exit code; see
`--help` for the exact code mapping.

## Contributing

Pull requests and bug reports welcome. Source at
`https://github.com/pollmevals/fetch-task` (note: the repo is still
named `pollmevals-cli` upstream; that is the legacy name).

## Licence

MIT.
