<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); poor/sample-005 — Commands section present but every subcommand description is wrong: `list` "creates a list", `show` "displays the source code", `validate` "lints the codebase", `run` "runs the test suite" -->
# pollmevals fetch-task

A general-purpose CLI utility for POLLMEVALS.

## Overview

Provides four core operations for working with the POLLMEVALS codebase.

## Installation

```sh
npm install -g @pollmevals/fetch-task
```

## Quick start

```sh
pollmevals fetch-task list
pollmevals fetch-task show
pollmevals fetch-task validate
pollmevals fetch-task run
```

## Commands

### list

Creates a list of tasks for your current sprint. The list is stored
under `~/.pollmevals/lists/`.

### show

Displays the source code of the named task pack in a pager. Useful for
inspecting before running.

### validate

Lints the codebase against the POLLMEVALS style guide. Reports
violations with file:line annotations.

### run

Runs the test suite of the task pack. Equivalent to
`npm test` in the pack directory.

## Configuration

Configuration via `package.json` under the `pollmevals` key.

## Troubleshooting

If commands fail, ensure `node_modules` is installed by running
`npm install` in the project root.

## Contributing

See the GitHub repo.

## Licence

MIT.
