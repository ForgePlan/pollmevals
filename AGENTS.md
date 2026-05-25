# AGENTS.md — pollmevals

> Universal manifest for any AI coding agent working in this repo (Claude Code, Cursor, Codex, Aider, Cline, etc.). Tool-specific extensions live in their own files: `CLAUDE.md` for Claude Code, `.cursorrules` for Cursor, etc. Don't duplicate this content there — import or link.

POLLMEVALS — open evaluation platform for full LLM **stacks** (model + agent CLI + skills + memory + validator), not just raw models. Goal: prove with numbers that a cheap model with the right scaffolding often beats an expensive one without it.

Language: code/identifiers/commits in **English** (Conventional Commits). Russian acceptable in commit body when it adds clarity.

**Status**: v0.0 pre-launch — documentation + contracts ready, no executable code yet. Next: smoke run (3 tasks × 5 models × 3 seeds = 45 evals) per `docs/04-runbook/12-first-smoke-run-playbook.md`.

**Stack**: monorepo (TypeScript product plane + Python eval plane, future Rust sandbox) · pnpm + uv · Vitest + pytest · Moon (workspace) · Node 22+ / Python 3.12+.

---

## 🔴 Red lines (irreversible — require explicit "yes" in current session)

- **Destructive git** (`push --force`, `reset --hard`, branch/tag deletion, `rebase -i` on shared history) — only after explicit confirmation. Full rules → [`guides/GIT-FLOW-GUIDE.ru.md`](guides/GIT-FLOW-GUIDE.ru.md) §7.
- **No secrets in git** — `.env`, tokens, API keys, certificates. Run `git status` before `git add`. `.forgeplan/config.yaml` must use `api_key_env: VAR_NAME`, never literal `api_key: "sk-..."`. If a literal key landed: rewrite, **revoke the leaked key**, force-push only the fix commit (with confirmation).
- **No bypass of branch protection** — `main` merges only via PR. No direct push.
- **No `forgeplan` artifact direct edits** — `.forgeplan/{prds,rfcs,adrs,specs,epics,evidence,problems,solutions,refresh,notes,memory}/*.md` and `.forgeplan/state/*.yaml` are managed by the CLI/MCP only. Use `forgeplan update`/`new`/`link`/`activate`/`deprecate`. Direct edit is OK only for non-forgeplan markdown (READMEs, this file, src code).
- **No mutation of completed run results** (ADR-0002 immutability) — `evals[].final_score`, `artifacts/runs/<hash>/*` and DB rows for completed `runs` are write-once. Errors → new run + `supersedes` link.
- **No long/expensive operations** (deploy, DB migrations, mass network/LLM calls, weekly run trigger) without explicit confirmation. Weekly eval run = $100-200 in inference.
- **No rewriting other people's history** — if `git log` shows commits not yours in a range, no `rebase`/`amend`/`reset` over it.

---

## Build & test (smoke before commit)

```bash
pnpm install && uv sync          # install (TS + Python)
moon run :build                  # build all projects
moon run :test                   # test all projects
moon run :lint                   # lint / typecheck all projects
```

Run the **full** check (build + test + lint), not the happy path only. Per-project shortcuts → `docs/agents/build-config.md`.

---

## Git workflow (short — full guide in `guides/GIT-FLOW-GUIDE.ru.md`)

- **Branches**: `feat/*` / `fix/*` / `chore/*` / `docs/*` → `dev` (or default branch) → `main`. No direct commits to `main`.
- **Commits** — Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`). Body imperative, _why_ over _what_. Reference artifacts: `Refs: prd-<slug>` (before merge) or `Refs: PRD-NNN` (after merge).
- **PR titles** — Conventional Commits + artifact ID where applicable: `feat(scope): add OAuth2 (PRD-042)`.
- **Merge strategy** — merge commit (preserves history). Squash only for noisy WIP branches when explicitly requested.
- **No `git add .` / `git add -A`** — stage specific files. Prevents accidentally committing `.env`, lockfile drift, or stray editor files.
- **No `--no-verify`** — fix the underlying issue, never bypass hooks.

Safety table (full version → `guides/GIT-FLOW-GUIDE.ru.md` §7.1):

| Command | Why dangerous | Safe alternative |
|---|---|---|
| `git reset --hard` | destroys uncommitted work | `git stash` or `git branch backup/...` first |
| `git push --force` | rewrites remote history | `--force-with-lease` + own feature branch only |
| `git branch -D <name>` | deletes unmerged | `git branch -d` (refuses if unmerged) |
| `git clean -fd` | nukes untracked | `git clean -n` (dry-run) first |
| `git commit --amend` after push | rewrites published | new commit `fix: ...` |
| `rm -rf .git` | destroys history | never |

---

## Code conventions

- **Naming**: files `kebab-case`, identifiers `camelCase` (TS) / `snake_case` (Python), types/classes `PascalCase`.
- **Comments**: only where _why_ isn't obvious. No "added for #123" — that belongs in the commit message.
- **Tests**: every public function gets at least a happy-path test plus edge cases that matter for callers.
- **Errors**: validate at boundaries (user input, external APIs). Trust internal code — don't add defensive checks for impossible states.
- **No premature abstraction**: three similar lines beat a wrong abstraction. Wait until you have three real call sites before extracting.

### TypeScript (apps/api, apps/site, packages/contracts)

- Strict mode on (`strict: true`). No `any` — use `unknown` + narrowing. No `as` casts unless verified at a system boundary. `!` non-null assertions only after a guard expression.

### Python (apps/eval-core-py)

- Type hints on all public APIs. Pydantic models at boundaries. `mypy --strict` clean before commit. `ruff format` + `ruff check`.

---

## Library-first (mandatory)

> 🔴 **Don't write your own from scratch if a library exists.** Before implementing any component — evaluator, metric, linter, scanner, parser, formatter, retry logic, queue, cache, validator, etc. — search for an existing solution **first**.

**Pipeline for every "I'll implement X":**

1. **Library lookup first** (Context7 / npm / PyPI / WebSearch). Find a battle-tested option.
2. **Pin version + cite source.** `radon>=6,<7`, not `radon`. Mention in commit: `feat: cyclomatic eval via radon>=6.0`.
3. **Wrap, don't replace.** If the library API doesn't fit perfectly — thin adapter under a Protocol seam (e.g. `EvalCaller`-style). Don't rewrite functionality.
4. **Custom code only when:** library missing / abandoned (>2yr no commit) / incompatible license / trivially wrappable (<20 lines).

**Canonical libraries for POLLMEVALS metrics** (full table in NOTE-004 §5):

| Metric | Library |
|---|---|
| cyclomatic | `radon` (Py), `lizard` (multi), `eslint --max-complexity` (TS) |
| coverage | `coverage` (Py), `c8` (Node), `vitest --coverage` |
| lint | `ruff` (Py), `eslint` (TS), `clippy` (Rust) |
| type safety | `mypy --strict` (Py), `tsc --strict` (TS) |
| security | `bandit`, `semgrep`, `trivy`, `pip-audit`, `npm audit`, `gitleaks` |
| docstring | `interrogate` (Py), `jsdoc-coverage` (TS) |
| profiling | `cProfile` + `pyinstrument` (Py), `clinic.js` (Node) |
| α agreement | `krippendorff` (PyPI) |
| async retry | `tenacity` (Py), `p-retry` (Node) — NOT manual catch+sleep |
| HTTP | `httpx` (Py), `axios`/`undici` (Node) |
| validation | `pydantic` v2 (Py), `zod` (TS) |
| LLM eval | Inspect AI (Py, per EVID-004) |

**Anti-patterns to refuse:**

- "I'll write my own cyclomatic counter — only 50 lines" → **NO**, use `radon`/`lizard`.
- "Custom retry decorator with exponential backoff" → **NO**, use `tenacity` / `p-retry`.
- "Hand-rolled YAML parser" → **NO**, use `ruamel.yaml` or `PyYAML`.
- "My own Krippendorff α impl" → **NO**, use the `krippendorff` PyPI package.
- "Hardcoded model pricing dict" → **NO**, use `litellm.cost_per_token()`.

**Exception**: domain-specific orchestration (GridRunner, JudgePanel, JournalWriter manifest immutability) — our uniqueness, custom code justified. Even there — use library primitives inside (httpx, asyncio, pydantic).

---

## AI-agent rules (non-interactive / autorun)

- Default to **non-destructive** operations. When unsure, list intended changes and ask once.
- Refuse red-line actions above, surface the rule.
- When `forgeplan health` reports stubs/orphans/duplicates — note them, don't auto-fix unless that's the explicit task.
- Match scope to request: a bug fix doesn't need surrounding cleanup; one-shot operations don't need helpers.
- Don't write feature flags, backwards-compat shims, or "for future use" abstractions unless asked.
- **Terminology precision**: don't sprinkle specialised terms ("hexagonal", "monadic", "idempotent", "bounded context") unless you can map the meaning to current context. Plain words first; cross-reference official term only if sure.
- **Methodology is frozen** (`docs/02-methodology/` v0.1.0) — changes go through ADR, not direct edits.

---

## Smoke test (before PR)

1. `moon run :build` — clean build, no warnings.
2. `moon run :test` — all tests pass.
3. `moon run :lint` — no lint errors.
4. `forgeplan health` — no new orphans/stubs/duplicates.
5. `git status` — only intended files staged; no `.env`, no editor files, no lockfile drift.
6. `git diff --stat origin/main..HEAD` — diff matches PR scope claim.

If any step fails, fix it. Never `--no-verify` the pre-commit hook.

---

## Storage layout

`.forgeplan/` mixes tracked artifacts (source of truth) with derived / runtime state. Full setup contract → `plugins/fpl-skills/skills/bootstrap/resources/guides/FORGEPLAN-SETUP.md` (read for the complete reference).

```
.forgeplan/                      ← managed by CLI/MCP, mostly tracked
├── prds/                        ← TRACKED — product requirements
├── rfcs/                        ← TRACKED — architecture proposals
├── adrs/                        ← TRACKED — decisions (with valid_until TTL)
├── specs/                       ← TRACKED — API / data-model contracts
├── epics/                       ← TRACKED — groupings of PRD[]/RFC[]
├── evidence/                    ← TRACKED — measurements / tests / audits
├── problems/                    ← TRACKED — problem cards
├── solutions/                   ← TRACKED — solution portfolios
├── refresh/                     ← TRACKED — re-evaluation of stale ADRs
├── notes/                       ← TRACKED — micro-decisions (90-day TTL)
├── memory/                      ← TRACKED — typed memory (fact/convention/constraint/observation/procedure)
├── state/                       ← TRACKED — lifecycle state machine YAML (one per artifact)
├── config.yaml                  ← TRACKED — project config (uses api_key_env, never literal keys)
├── .gitignore                   ← TRACKED — lists what NOT to track
│
├── lance/                       ← ❌ gitignored — LanceDB vector index (rebuild via `forgeplan scan-import`)
├── .fastembed_cache/            ← ❌ gitignored — bge-m3 model cache (~600 MB)
├── logs/                        ← ❌ gitignored — local audit/ops logs
├── .lock                        ← ❌ gitignored — runtime mutex
├── session.yaml                 ← ❌ gitignored — per-machine focus / claim TTLs (NOT shared)
├── trash/                       ← ❌ gitignored — soft-deleted artifacts
└── discovery/                   ← ❌ gitignored — ephemeral research findings

apps/
├── eval-core-py/                ← Python eval orchestrator (Inspect AI, LiteLLM wrapper)
├── api/                         ← Hono TypeScript API
└── site/                        ← Next.js 15 public site

packages/
├── contracts/                   ← JSON Schemas + TypeScript types
└── db/migrations/               ← SQL migrations (8 tables)

evals/{tasks,task-packs,rubrics,calibration}/
stacks/                          ← stack adapter specs
data/                            ← sample JSON
infra/scripts/                   ← validate-task-specs.py, reproduce-local-run.sh

docs/
├── 00-research/                 ← original research (read-only archive)
├── 01-vision/                   ← vision, requirements, business
├── 02-methodology/              ← FROZEN v0.1.0 (judge-policy, scoring, sandbox)
├── 03-architecture/             ← system architecture, stack, domain
├── 04-runbook/                  ← implementation plan, ops, smoke playbook
├── adr/                         ← project ADRs (ADR-0001 hybrid stack, ADR-0002 immutability)
├── visuals/                     ← HTML/SVG diagrams
└── agents/                      ← per-project metadata read by fpl-skills

CONTEXT.md                       ← ubiquitous language / domain glossary
.env                             ← ❌ gitignored — actual secrets
MASTER.md                        ← linear 151 KB doc, all-in-one navigation
INDEX.md                         ← file index + migration map
```

### Secrets — 12-factor pattern

`.forgeplan/config.yaml` is **tracked** but contains only the **name** of the env var holding the API key, never the key itself:

```yaml
llm:
  provider: gemini
  model: gemini-2.0-flash-thinking-exp-01-21
  api_key_env: GEMINI_API_KEY    # ← env var NAME, not the key
  max_tokens: 8192

embedding:
  model: bge-m3
```

The actual key (`GEMINI_API_KEY=AIza...`) lives in `.env` (gitignored), `~/.zshrc`, or CI secrets. Forgeplan reads it from process env at runtime.

**Pre-commit check** — confirm no literal key slipped into `config.yaml`:

```bash
! grep -qE 'api_key:\s*["'"'"']?(sk-|AIza|ant-)[A-Za-z0-9_-]{20,}' .forgeplan/config.yaml \
  && echo "✅ clean" || echo "❌ literal API key — revoke + rewrite to api_key_env"
```

If a literal key was committed: `git rm --cached`, rewrite to `api_key_env`, **revoke the leaked key** (it's already in git history), commit the fix.

### Env var overrides

`FORGEPLAN_LLM_PROVIDER`, `FORGEPLAN_LLM_MODEL`, `FORGEPLAN_LLM_BASE_URL`, `FORGEPLAN_LLM_MAX_TOKENS`, `FORGEPLAN_LLM_API_KEY_ENV`, `FORGEPLAN_EMBEDDING_MODEL`, `FORGEPLAN_STORAGE_DRIVER`, `FORGEPLAN_STORAGE_PATH`, `FORGEPLAN_MEMORY_DRIVER`.

Priority: env > config.yaml > built-in default.

### Fresh clone protocol

```bash
git clone <repo>
cd pollmevals
forgeplan init -y                    # creates lance/, .fastembed_cache/, etc.
forgeplan scan-import                # rebuilds vector index from markdown
set -a && source .env && set +a      # load secrets (or `direnv allow`)
pnpm install && uv sync              # install all dependencies (TS + Python)
forgeplan health                     # verify clean state
```

---

## File RAG — where to look when in doubt

| Question | File / artifact |
|---|---|
| **What we're building as product + CJM (5 stages × 4 personas) + 18 site pages + API contracts** | `forgeplan get SPEC-002` |
| **What's done vs missing from dd.md? Coverage matrix** | `forgeplan get NOTE-005` |
| Full catalogue: stacks / memory / tools / metrics dimensions | `forgeplan get NOTE-004` |
| Anti-gaming + contamination + drift policy | `forgeplan get NOTE-006` |
| Original 1785-line TЗ | `docs/old/dd.md` (read-only seed) |
| Repo file system map | `INDEX.md` (root) |
| Docs map | `docs/INDEX.md` |
| Full artifact list | `forgeplan list` / `forgeplan health` |
| Domain glossary | `CONTEXT.md` |

### Per-artifact responsibility map

| Artifact | Owns |
|---|---|
| **EPIC-001** | v0.1 launch — overall epic ownership, R_eff source-of-truth for project health |
| **PRD-001** | Smoke run base — first 45-eval grid contract (3 tasks × 5 models × 3 seeds on raw-llm) |
| **PRD-002** | Judge panel methodology — Q1-Q5 decisions (multi_scorer + median + CI gate + degraded + ID probe) |
| **PRD-003** | Weekly cadence (draft) — operational reliability, cron, alerting |
| **PRD-004** | Public leaderboard MVP (draft) — refined by SPEC-002 |
| **PRD-005** | Release pipeline (draft) — assigned_number bot + sync workflow |
| **PRD-006** | Tasks catalog expansion — 17 missing tasks roadmap (Waves 1+2+3) |
| **RFC-001** | Orchestrator implementation plan on Inspect AI |
| **RFC-002** | Judge panel layer implementation (5 Slices A-E) |
| **ADR-001** | Concurrency model (semaphore + per-provider rate awareness) |
| **ADR-002** | Reproduce semantics — evaluator-only (cached raw_output, never re-fire LLM) |
| **ADR-003** | 5-model smoke lineup + provider routing |
| **ADR-004** | MoleculerPy as distributed orchestrator (Phase 3+) |
| **ADR-005** | Judge score aggregation — median reducer + bootstrap CI lower-bound gate |
| **ADR-006** | Phase 1 14-model adoption (Cerebras + Runpod routes + cost matrix) |
| **SPEC-001** | Manifest + EvalRow + ArtifactRef contracts |
| **SPEC-002** | Product spec + CJM + 18 site pages + API contracts (refines PRD-004) |
| **NOTE-001** | Crash recovery (append-only journal + atomic rename) |
| **NOTE-002** | Evidence Quality Standard — ADI cycle + Trust Calculus per EVID (mandatory) |
| **NOTE-003** | Observability stack seed (LGTM choice for PRD-003+) |
| **NOTE-004** | Expanded vision catalog (12 stacks + 9 memory + 4 context + 8 indexing + 10 metrics) |
| **NOTE-005** | dd.md ↔ artifacts coverage matrix |
| **NOTE-006** | Anti-gaming + contamination program (3 pillars + 3 policy decisions) |
| **EVID-001..024** | Per-EVID specifics: prior art audits, Wave EVIDs, smoke run measurements |

### Triage table (3-second look-up)

```
Question                                       →  Open
─────────────────────────────────────────────────────────────────────
"What are we building as product?"             →  SPEC-002 (CJM + pages + API)
"What's left to build?"                        →  NOTE-005 (gap matrix)
"Which stacks do we test?"                     →  NOTE-004 §1
"Which models in lineup?"                      →  ADR-003 (smoke 5) + ADR-006 (full 14)
"How do we score quality / cost?"              →  docs/02-methodology/scoring.md (frozen)
"How does the panel of judges work?"           →  PRD-002 + RFC-002 + ADR-005
"How do we defend against gaming?"             →  NOTE-006
"What's the manifest format?"                  →  SPEC-001
"How to reproduce a run?"                      →  ADR-002 + Makefile reproduce target
"What does a specific site page hit?"          →  SPEC-002 § "API Contracts"
```

---

## Expanded vision (NOTE-004 canonical)

POLLMEVALS evaluates **whole scaffolding stacks**, not isolated models. The full catalog of agent CLIs (Claude Code, Codex, Aider, Gemini CLI, Cursor, Cline, Pi, Hermes, OpenHands, Plandex, Goose, forgeplan-framework), memory variants (file CLAUDE.md/AGENTS.md, mem0, Letta, Zep, Hindsight, GraphRAG, RAFLOW), context tools (Context7 axis), codebase indexing (Serena, Aider repo-map, Sourcegraph, Cody), and extended metrics dimensions (6 existing + 4 new — docstring_coverage, profile_score, dep_selection_quality, vulnerability_scan_score) is captured in `NOTE-004`.

**Cite NOTE-004, don't repeat the catalog in new artifacts.** `forgeplan get NOTE-004` is the source of truth. Promote to PRD-006 when 5+ stacks implemented + extended metrics design proven viable.

**Phase numbering disambiguation** (NOTE-004 §6): codebase uses "Phase 0-5" (infra phases — what to build), research uses "Фаза 1-5" (experiment phases — what to measure). They are **different axes** — always be explicit which one you mean.

---

## References

- `forgeplan` CLI — installed at `/opt/homebrew/bin/forgeplan` (v0.32.1). `brew install ForgePlan/tap/forgeplan` or `cargo install --git https://github.com/ForgePlan/forgeplan forgeplan-cli`.
- Project decisions — `.forgeplan/adrs/` (open `*.md` for context; mutate via CLI/MCP only) + `docs/adr/` (ADR-0001 hybrid stack, ADR-0002 run immutability).
- Methodology canon — `docs/02-methodology/` (frozen v0.1.0). Source of truth for scoring formulas, judge policy, sandbox specs.
- Implementation playbook — `docs/04-runbook/12-first-smoke-run-playbook.md`. Start here for the v0.1 smoke run.
- Master doc — `MASTER.md` (151 KB, linear). Use `docs/{01..04}/` subfolders for targeted reading.

---

## Non-goals (recency-zone — hard "no", not "maybe later")

- **No human eval** in v0.1 — automatic metrics + LLM judges only.
- **No paid API** until methodology has 2+ public runs with α ≥ 0.70.
- **No sponsored evals** in v0.x — disclosure policy lands in v1.0.
- **No public community proposal flow** until v1.0 — adding model/stack/task requires maintainer review.
- **No enterprise white-label** in v0.x.
- **No Rust rewrite** of orchestrator before eval protocol stabilises (per ADR-0001).
- **No multilingual tasks** in v0.x — English only.

---

## Where to look next

- [`CLAUDE.md`](CLAUDE.md) — Claude Code-specific extensions: session start protocol, forgeplan MCP tooling, fpl-skills slash commands, subagent packs, Hindsight memory, `.claude/` settings.
- [`CONTEXT.md`](CONTEXT.md) — domain glossary (ubiquitous language).
- [`guides/GIT-FLOW-GUIDE.ru.md`](guides/GIT-FLOW-GUIDE.ru.md) — full Git Flow + safety rules.
- [`guides/CLAUDE-MD-GUIDE.ru.md`](guides/CLAUDE-MD-GUIDE.ru.md) — how to keep this file and `CLAUDE.md` healthy (U-curve, cry-wolf, dilution).
- `docs/agents/{issue-tracker,build-config,paths,domain}.md` — per-area metadata.
