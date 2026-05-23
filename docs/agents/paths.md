# Project paths

Canonical locations for the kinds of files agents look up most often.

## Forgeplan artifacts

| Kind | Path | Created by |
|---|---|---|
| PRD | `.forgeplan/prds/PRD-NNN-*.md` | `forgeplan new prd "<title>"` |
| RFC | `.forgeplan/rfcs/RFC-NNN-*.md` | `forgeplan new rfc "<title>"` |
| ADR | `.forgeplan/adrs/ADR-NNN-*.md` | `forgeplan new adr "<title>"` |
| Spec | `.forgeplan/specs/SPEC-NNN-*.md` | `forgeplan new spec "<title>"` |
| Epic | `.forgeplan/epics/EPIC-NNN-*.md` | `forgeplan new epic "<title>"` |
| Evidence | `.forgeplan/evidence/EVID-NNN-*.md` | `forgeplan new evidence "<desc>"` |
| Problem | `.forgeplan/problems/PROB-NNN-*.md` | `forgeplan new problem "<title>"` |
| Solution | `.forgeplan/solutions/SOLN-NNN-*.md` | `forgeplan new solution "<title>"` |
| Refresh | `.forgeplan/refresh/REFRESH-NNN-*.md` | `forgeplan new refresh "<title>"` |
| Note | `.forgeplan/notes/NOTE-NNN-*.md` | `forgeplan new note "<text>"` |

**Rule**: Never `Edit`/`Write` these directly. Always go through `forgeplan update`/`new`/`link` (or `mcp__forgeplan__forgeplan_*` MCP tools).

## Project-level ADRs (pre-forgeplan)

`docs/adr/` — ADRs that pre-date forgeplan onboarding:

- `docs/adr/0001-use-hybrid-stack.md` — TypeScript + Python hybrid
- `docs/adr/0002-run-immutability.md` — completed runs are write-once

When superseding or extending these, create a new ADR in `.forgeplan/adrs/` (managed by forgeplan) and link `supersedes` to the legacy one. Don't migrate the legacy files — leave them as historical record.

## Documentation

| Topic | Path |
|---|---|
| Master doc (linear, 151 KB) | `MASTER.md` |
| Original research (read-only archive) | `docs/00-research/` |
| Product vision + business | `docs/01-vision/` |
| **Frozen methodology v0.1.0** | `docs/02-methodology/` |
| System architecture | `docs/03-architecture/` |
| Implementation runbook | `docs/04-runbook/` |
| Visuals (HTML/SVG) | `docs/visuals/` |
| Per-project metadata for fpl-skills | `docs/agents/` |
| Project tree snapshot | `docs/PROJECT_TREE.md` |

## Code

| Area | Path |
|---|---|
| Python eval orchestrator | `apps/eval-core-py/` |
| Hono TypeScript API | `apps/api/` |
| Next.js public site | `apps/site/` |
| JSON Schemas + TS types | `packages/contracts/` |
| SQL migrations | `packages/db/migrations/` |

## Eval materials

| Kind | Path |
|---|---|
| Task specs (for execution) | `evals/tasks/<slug>/task.yaml` |
| Task packs (with prompt + gold) | `evals/task-packs/<slug>/` |
| Judge rubrics | `evals/rubrics/` |
| Calibration samples | `evals/calibration/` |
| Stack adapter specs | `stacks/<slug>/stack.yaml` |
| Sample JSON data | `data/` |

## Infrastructure

| File | Purpose |
|---|---|
| `Makefile` | top-level command shortcuts |
| `.env.example` | env var template |
| `infra/scripts/validate-task-specs.py` | task YAML validator |
| `infra/scripts/reproduce-local-run.sh` | reproducer for a run by hash |
| `.mcp.json` | MCP server config (currently: forgeplan) |
| `.claude/settings.json` | Claude Code per-project settings (incl. safety hook) |

## TODO file

`TODO.md` at repo root — local task list until a formal tracker is wired.

## Generated / gitignored (don't read at session start)

- `artifacts/` — local run outputs (gitignored)
- `node_modules/` — pnpm install output
- `.venv/` — uv environment (if using local venv mode)
- `dist/`, `build/`, `.next/`, `out/` — TS/JS build output
- `.moon/cache/` — Moon task cache
- `.forgeplan/lance/` — LanceDB vector index (rebuild via `forgeplan scan-import`)
- `.forgeplan/.fastembed_cache/` — bge-m3 model cache (~600 MB)
- `.forgeplan/logs/` — local audit logs
- `.forgeplan/session.yaml` — per-machine claim TTLs (not shared)
- `.forgeplan/trash/`, `.forgeplan/discovery/` — soft-delete + ephemeral
