# Build & test config

Multi-language monorepo with **Moon** as the build orchestrator.

## Toolchains

| Language | Package manager | Test framework | Lint/format |
|---|---|---|---|
| TypeScript | pnpm (Corepack) | Vitest | ESLint + Prettier |
| Python | uv | pytest | ruff (format + check), mypy --strict |
| (Rust — future) | cargo | cargo test | rustfmt + clippy |

## Top-level commands (Moon)

```bash
# Install all dependencies (runs across all projects)
pnpm install && uv sync

# Run a task across all projects
moon run :build       # build every project that declares a build task
moon run :test        # run every project's test suite
moon run :lint        # lint + typecheck every project
moon run :format      # format every project

# Inspect Moon workspace
moon query projects   # list all projects
moon ci               # run CI-equivalent task graph
```

## Per-project commands

```bash
# Python eval orchestrator
moon run eval-core-py:test
uv run -- pytest apps/eval-core-py/tests/   # direct without Moon

# Hono API
moon run api:dev          # start dev server on :8787
moon run api:test

# Next.js site
moon run site:dev         # start dev server on :3000
moon run site:test

# Contracts package (JSON Schema validation + TS types)
moon run contracts:check
```

## Make targets (high-level orchestration)

```bash
make demo-run         # local smoke run (no external LLM, uses fixtures)
make docker-up        # bring up NATS, Redis, Postgres, LiteLLM proxy
make docker-down
make api-dev          # = moon run api:dev
make site-dev         # = moon run site:dev
make validate-tasks   # python infra/scripts/validate-task-specs.py
make reproduce        # bash infra/scripts/reproduce-local-run.sh
make format-tree      # find . -maxdepth 3 -type f | sort
```

## Smoke test (before commit)

Run **all three**, not just the happy path:

```bash
moon run :build      # ← must complete with no warnings
moon run :test       # ← all suites green
moon run :lint       # ← 0 errors, warnings reviewed
```

## Pre-commit hook

Not yet configured. When set up:

- `pnpm format` + `pnpm lint` for staged TS/JS files.
- `uv run ruff format` + `uv run ruff check` for staged Python files.
- `forgeplan validate <id>` for any staged `.forgeplan/*.md`.

Until then — run smoke test manually before commit. Don't use `git commit --no-verify` once the hook lands (red-line).

## CI

GitHub Actions — not yet configured. Planned:

- `.github/workflows/ci.yml` — `moon ci` on every PR.
- `.github/workflows/eval-weekly.yml` — Monday 03:00 UTC trigger for weekly run.

## Env vars

See `.env.example` at repo root for the full list. Required for any non-mock run:

- `OPENROUTER_API_KEY` — for cloud models (Claude, GPT, Gemini, etc.)
- `LITELLM_MASTER_KEY` — for the LiteLLM proxy
- `DATABASE_URL` — Postgres connection
- `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` — Cloudflare R2 for artifact storage (production only)
