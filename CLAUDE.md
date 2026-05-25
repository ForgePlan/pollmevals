# CLAUDE.md — pollmevals (Claude Code extensions)

> Universal rules — red lines, build/test, git workflow, code conventions, library-first, smoke test, non-goals, storage layout, file RAG, per-artifact responsibility map — live in [`AGENTS.md`](AGENTS.md). Read that first; it's tool-agnostic and applies to every AI coding agent (Claude Code, Cursor, Codex, Aider, Cline). **This file adds Claude Code-specific extensions only**: session start protocol, forgeplan MCP tooling, fpl-skills slash commands, subagent packs, Hindsight memory, `.claude/` settings.

<!-- U-curve attention: primacy zone (session start, MCP tooling) in lines 1-80, reference zone (tables, packs, slash commands) in 80-200, recency zone (memory, references) in 200-end. Keep total ≤ 300 lines. See guides/CLAUDE-MD-GUIDE.ru.md for the rationale. -->

---

## Session start

Run in parallel at the start of a session — three sources of truth, never one:

```bash
forgeplan health                       # active artifacts, blind spots, stubs
git status && git log --oneline -5     # local state and recent direction
ls .forgeplan/adrs/                    # decisions in force
```

**Don't read at start** (open only when relevant):

- Lockfiles (`pnpm-lock.yaml` / `uv.lock`) — only during dependency debugging.
- Generated artifacts (`dist/`, `target/`, `build/`, `.moon/cache/`, `artifacts/`).
- Full `CHANGELOG` / git history beyond the last 10–15 commits.
- `MASTER.md` (151 KB linear doc) — open by section, not "just in case". Use `docs/{01..04}/*` instead.

**Re-warm triggers** (mid-session top-ups):

- Switching to a new package/area → read its `moon.yml` and module `README.md`.
- Touching release/CI flow → read `.github/workflows/` and Moon task config.
- Touching forgeplan artifacts → read the latest `forgeplan get <ID>` output, not the file.
- Touching evals/scoring → read `docs/02-methodology/scoring.md` + `docs/04-runbook/08-scoring-contract.md`.
- Touching judge logic → read `docs/02-methodology/judge-policy.md` + `docs/04-runbook/07-judge-panel.md`.

**Sufficiency criterion**: you can name (a) the active feature/PRD in flight, (b) the build/test command for the area you're touching, (c) the most recent ADR that applies. If you can't — re-warm before acting.

`MEMORY.md` is auto-loaded every turn — no explicit `memory_recall` needed for the index. Call `memory_recall` only for records beyond what's already in scope.

---

## Forgeplan — Claude Code tooling

Concepts (depth, lifecycle, R_eff math, EvidencePack structured fields, slug + assigned number, validator aliases) live in [`AGENTS.md`](AGENTS.md). This section covers **how Claude Code invokes forgeplan**: prefer MCP, fall back to CLI.

**Tool selection** — if the deferred-tools list contains `mcp__forgeplan__*` tools (forgeplan MCP server wired in `.mcp.json` and reachable), **prefer MCP** over shell. MCP returns typed dicts and includes a `_next_action` field on every response — relay that to your reports. If MCP tools are absent, fall back to shell `forgeplan` CLI. If neither works (`command -v forgeplan` fails), warn once at session start and proceed without artifact ops.

**Phases**: `OBSERVE → ROUTE → SHAPE → BUILD → PROVE → SHIP`.

| Phase | MCP tool | CLI fallback |
|---|---|---|
| Observe | `forgeplan_health` | `forgeplan health` |
| Route | (none — CLI only) | `forgeplan route "<task>"` |
| Shape | `forgeplan_new`, `forgeplan_validate` | `forgeplan new <kind>`, `forgeplan validate <id>` |
| Reason (ADI) | `forgeplan_reason` | `forgeplan reason <id>` |
| Prove | `forgeplan_new kind=evidence`, `forgeplan_link`, `forgeplan_score` | `forgeplan new evidence`, `forgeplan link`, `forgeplan score` |
| Ship | `forgeplan_activate`, then `gh pr create` | `forgeplan activate <id>`, then `gh pr create` |

**Hint protocol** — every `forgeplan` output ends with one marker. Execute verbatim, don't paraphrase:

| Marker | Meaning |
|---|---|
| `Next: <command>` | Run as-is for the next step. |
| `Or: <command>` | Use only if `Next:` blocks. |
| `Wait: <condition>` | Retry after condition holds. |
| `Done.` | Step complete; move on. |
| `Fix: <command>` | Error remediation, paired with `Error:`. |

MCP consumers read `_next_action`. CLI `--json` puts the hint on stderr (bare array on stdout for jq compat).

**Standard flow** (end-to-end, Standard depth):

```bash
forgeplan health                                   # observe
forgeplan route "implement <feature description>"  # decide depth
forgeplan new prd "<title>"                        # shape
$EDITOR .forgeplan/prds/PRD-NNN-*.md               # fill MUST sections
forgeplan validate PRD-NNN                         # 0 MUST errors
forgeplan reason PRD-NNN                           # ADI (Standard+)
# ...write code + tests...
forgeplan new evidence "PRD-NNN: <verification>"
$EDITOR .forgeplan/evidence/EVID-MMM-*.md          # fill ## Structured Fields!
forgeplan link EVID-MMM PRD-NNN --relation informs
forgeplan score PRD-NNN                            # R_eff > 0?
forgeplan activate PRD-NNN                         # draft → active
gh pr create --base main                           # PR body: "Refs: prd-<slug>"
```

**Multi-agent (`dispatch → claim → release`)** — when 2–5 sub-agents work in the same workspace:

```bash
forgeplan dispatch --agents N --json   # planner: conflict-free buckets
forgeplan claim <id> --agent <name> --ttl-minutes 30
# ...work...
forgeplan release <id>
forgeplan claims                       # who's holding what right now
```

`dispatch` returns a plan; the **main thread / orchestrator** spawns workers via `Agent({subagent_type, prompt})` — multiple `Agent` blocks in one message run in parallel. `SendMessage` is **not** a spawner; it only addresses already-running processes.

**Non-interactive hygiene**: always invoke `forgeplan init -y` (no interactive prompt). After every spawned `Agent({…})`, the orchestrator owns the writeback to `forgeplan` (claim/release, evidence linking) — sub-agents must not call `forgeplan activate` directly unless the orchestrator explicitly delegated it.

This is enforcement, not recommendation. Skipping leaves the artifact graph empty — `forgeplan_health` will flag orphans / missing evidence / stale stubs.

---

## Permission zones (Forge Mode)

| Zone | What | Mode | Examples |
|---|---|---|---|
| 🟢 Green | read-only, build, test, `forgeplan` | auto-allow | `moon run :test`, `forgeplan health`, `git status` |
| 🟡 Yellow | files, `git add`/`commit` | acceptEdits | `Write`, `Edit`, `git commit` |
| 🔴 Red | irreversible | **block via hook** | `git push --force`, `rm -rf /`, weekly run trigger, `DROP TABLE` |

A `.claude/settings.json` PreToolUse hook returns exit code 2 on `forgeplan delete/reset/destroy` without `--yes`. Whitelist exceptions in `.claude/settings.local.json`. `/fpl-init` installed the default safety hook on bootstrap.

---

## Agent teams (when to delegate)

Spawn sub-agents instead of doing the work in the main thread when:

- **Independent investigations**: research, code search, log analysis. Multiple `Agent` calls in one message run in parallel.
- **Wave-based execution** (`/sprint`): each wave's tasks are claimed by separate agents with `addBlockedBy` declaring inter-wave deps.
- **Adversarial review** (`/audit`): minimum 4 reviewers (logic, architecture, types, security) — must find issues, 0 findings = re-review.
- **Long-running work** with checkpoints — `/do` (interactive) or `/autorun` (overnight).

Agent packs ship subagent types ready to use:

| Pack | What it gives |
|---|---|
| `agents-core` | 11 baseline subagents — debugger, code-reviewer, planner, tester, researcher… |
| `agents-domain` | 11 stack specialists — typescript-pro, golang-pro, nextjs, fullstack… |
| `agents-pro` | 21 expert agents — security, architecture, prompt engineering, ML… |
| `agents-github` | 7 GitHub agents — PR/issue/release/workflow management |
| `agents-sparc` | 5 SPARC-methodology agents — Specification → Pseudocode → Architecture → Refinement → Completion |

Install only the packs you actually use. `/audit`, `/sprint`, `/research` will pick up whichever packs are present.

---

## fpl-skills — slash commands

| Command | Use case |
|---|---|
| `/restore` | Start of a new session — recover context from git + memory. |
| `/briefing` | Daily — open tasks, mentions, today's focus from your tracker. |
| `/research <topic>` | Unfamiliar area, gap analysis, "what do we already have on X". |
| `/refine <plan>` | Plan is rough — sharpen terminology, surface contradictions, lazy-create CONTEXT.md/ADRs. |
| `/rfc create` | Formalise a refined plan into a structured RFC. |
| `/sprint <feature>` | Multi-wave implementation with strict file ownership. |
| `/audit` | Multi-expert review (≥4 reviewers — logic, architecture, types, security). |
| `/diagnose <bug>` | Hard / non-deterministic / performance bug — 6-phase debug loop. |
| `/autorun <task>` | Overnight or unattended runs (no approval pauses). |
| `/do <task>` | Interactive variant of /autorun (pauses at checkpoints). |
| `/setup` | (Re-)run the docs/agents/ wizard when project structure changes. |

`/fpl-init` already ran on this project — that's why you're seeing this CLAUDE.md.

---

## Project context (auto-loaded via @import)

@docs/agents/issue-tracker.md
@docs/agents/build-config.md
@docs/agents/paths.md
@docs/agents/domain.md
@CONTEXT.md

These files are written by `/setup`. Edit them when project structure changes — fpl-skills picks up changes automatically.

---

## Long-term memory (Hindsight MCP)

Project bank: **`pollmevals`** (declared in `.mcp.json`). Three hooks run automatically:

- **`UserPromptSubmit`** — before every user prompt, `recall` is called and relevant memories are appended to the message as additional context.
- **`Stop`** — after every assistant response, transcript is saved once every N turns.
- **`SessionEnd`** — forces a final retain when the session closes.

**Don't call `memory_recall` reflexively** — it's already happening. Manual `memory_retain` only for **non-obvious** findings: a hard-won lesson, a sticky decision, an explicit user correction. Use the shape: rule → **Why:** → **How to apply:**.

Full guidance: [`~/.claude/rules/hindsight.md`](~/.claude/rules/hindsight.md).

---

## Unified workflow (Forgeplan × Tracker × Memory)

Three systems, three concerns:

- **Forgeplan** = WHAT to do and WHY (artifacts, quality, evidence).
- **Tracker** (Orchestra / GitHub Issues / Linear / Jira / local TODO) = WHO does it and WHEN.
- **Memory** (Hindsight MCP / `MEMORY.md`) = context between sessions.

Synchronisation rules:

1. New artifact created → matching task in your tracker (if available).
2. `forgeplan activate <id>` → mark the tracker task Done.
3. PR merged → update tracker + retain non-obvious decisions in long-term memory.
4. Tracker offline → record what to sync in `TODO.md` and reconcile later.

Task naming convention in the tracker: `[ARTIFACT-ID] description` when an artifact exists; plain description + tags otherwise.

---

## See also

- [`AGENTS.md`](AGENTS.md) — universal manifest (red lines, build/test, git workflow, code conventions, library-first, storage layout, file RAG, per-artifact responsibility map, references).
- [`CONTEXT.md`](CONTEXT.md) — domain glossary (ubiquitous language).
- [`guides/CLAUDE-MD-GUIDE.ru.md`](guides/CLAUDE-MD-GUIDE.ru.md) — why this file is structured the way it is (U-curve attention, ≤ 7 red lines, primacy/reference/recency zones).
- [`guides/GIT-FLOW-GUIDE.ru.md`](guides/GIT-FLOW-GUIDE.ru.md) — full Git Flow + safety rules.
- `docs/agents/{issue-tracker,build-config,paths,domain}.md` — auto-loaded per-area metadata.
