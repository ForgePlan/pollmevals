<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); prompt — candidate-facing brief for doc_01_cli_readme -->
# Prompt — `pollmevals fetch-task` README

> The canonical prompt lives in [`task.yaml`](./task.yaml) under
> `prompt_template`. The renderer in `apps/eval-core-py/` reads that field
> and ships it to the candidate model verbatim. This file is the
> human-readable mirror of the same prompt, plus authoring notes that the
> judge and the candidate never see.

---

## Brief (what the candidate sees)

You are writing the `README.md` for a command-line tool called
`pollmevals fetch-task`. The tool retrieves POLLMEVALS evaluation task
packs from a remote catalog, validates them against the local schema, and
runs them inside a sandboxed evaluator. It ships as a single static
binary, a Homebrew tap (`pollmevals/tap`), and a Docker image
(`ghcr.io/pollmevals/fetch-task`).

### Tool contract

```
Binary name:      pollmevals-fetch-task   (entry point: `pollmevals fetch-task`)
Catalog endpoint: https://catalog.pollmevals.dev   (override with POLLMEVALS_CATALOG_URL)
Schema:           JSON Schema Draft 2020-12, bundled in the binary
Config file:      $XDG_CONFIG_HOME/pollmevals/fetch-task.yaml   (override with --config)
Auth:             optional POLLMEVALS_API_TOKEN for private catalogs
```

### Subcommands

| Subcommand | Flags | Exit codes |
|---|---|---|
| `list` | `--category <cat>` `--difficulty <level>` `--json` | 0 ok / 2 network / 3 auth |
| `show <task-id>` | `--version <ver>` (default `latest`) `--json` | 0 ok / 4 task not found / 5 version not found |
| `validate <path-or-id>` | `--strict` | 0 valid / 6 schema violation / 7 quorum failure |
| `run <task-id>` | `--stack <stack-slug>` `--seed <int>` `--out <dir>` `--dry-run` | 0 ok / 8 stack not found / 9 sandbox error / 10 evaluator-reported failure |

Categories: `backend`, `frontend`, `docs`, `review`.
Difficulty levels: `easy`, `medium`, `hard`.

Exit code 10 means the evaluator finished but flagged a low-quality
candidate output — the wrapper itself succeeded. Sandbox + infra failures
are 9; 10 is only for the evaluator's own verdict.

### Environment variables

| Name | Purpose | Default |
|---|---|---|
| `POLLMEVALS_CATALOG_URL` | override catalog base URL | `https://catalog.pollmevals.dev` |
| `POLLMEVALS_API_TOKEN` | bearer token for private catalogs | unset |
| `POLLMEVALS_CACHE_DIR` | local cache for downloaded packs | `$XDG_CACHE_HOME/pollmevals` |
| `POLLMEVALS_NO_COLOR` | disable ANSI colour in stderr output | unset |
| `POLLMEVALS_LOG_LEVEL` | `debug` / `info` / `warn` / `error` | `info` |

### Config precedence (highest wins)

1. CLI flag
2. Environment variable
3. Config file (`--config` or default path)
4. Compiled-in default

### Output

Write a single Markdown file with the following eight top-level sections,
in this exact order:

1. Overview
2. Installation
3. Quick start
4. Commands
5. Configuration
6. Troubleshooting
7. Contributing
8. Licence

Use level-2 headings for sections, level-3 for each subcommand inside
**Commands**. Use code blocks for all shell invocations and config
snippets. Keep examples self-contained — paste-and-run.

Output only the Markdown source for the README. No prose around it. No
triple-backtick fence wrapping the whole document.

---

## Authoring notes (NOT shown to the candidate or the judge)

- The candidate never sees `gold/README.gold.md`, `rubric.yaml`, or any
  calibration sample.
- The judge sees the candidate output + `rubric.yaml` only. The judge does
  not see the gold README either — comparison is against the rubric
  anchors, not against gold (gold is for our calibration loop).
- Prompt rendering strips any candidate prose outside fenced code blocks
  before scoring (normalisation pipeline, NOTE-007).
- Do not change the contract without bumping `task.yaml#version` and
  filing a new ADR — every closed Run is bound to the prompt it was
  evaluated against (ADR-0002 immutability).
