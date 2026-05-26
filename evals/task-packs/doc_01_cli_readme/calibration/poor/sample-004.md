<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); poor/sample-004 — documents a different tool (`pollmevals-doctor` diagnostics CLI) AND has no working code examples (empty fences, missing shell prompts) AND markdown is broken (unclosed code blocks, heading levels skipped, mismatched list markers) -->
# pollmevals-doctor

A diagnostic CLI for the POLLMEVALS benchmark. Inspects local
installations, checks Docker connectivity, and reports broken
dependencies.

#### Overview

`pollmevals-doctor` is a read-only health checker. It scans your
machine for the POLLMEVALS dependencies (Docker, Node, Python, uv,
Moon) and confirms each is at a supported version. It does not modify
anything.

## Installation

```
##### Quick start

```sh
```

##### Commands

#### check

Runs the full diagnostic suite. No example output is shown here —
inspect your own machine.

```
```

#### fix

Attempts to repair common issues — restarts the Docker daemon, clears
the Moon cache, prunes the local registry.

- runs in best-effort mode
* may require sudo
+ idempotent

## Configuration

No configuration. Reads `~/.docker/config.json` for Docker context only.

##### Troubleshooting

If `check` reports a missing dependency, install it via your platform's
package manager. If Docker is reported as `unreachable`, ensure the
daemon is running.

```sh
# (example omitted)

## Contributing

PRs welcome at `https://github.com/pollmevals/doctor`.

## Licence

MIT.
