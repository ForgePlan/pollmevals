---
depth: standard
id: NOTE-004
kind: note
last_modified_at: 2026-05-24T20:41:50.538073+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-002
  relation: informs
- target: RFC-002
  relation: informs
- target: PRD-001
  relation: informs
status: draft
title: Expanded vision catalog — agent CLIs, memory variants, context tools, indexing tools, extended metrics
---

# NOTE-004: Expanded vision catalog — agent CLIs, memory variants, context tools, indexing tools, extended metrics

## Context

2026-05-24 session pivot: user re-affirmed that POLLMEVALS должен evaluate **полную экосистему** scaffolding, не только 3 starter stacks (raw-llm, claude-code-basic, forgeplan-framework). Эта заметка фиксирует расширенный каталог, который future Phase 3/4 implementations используют для построения stacks/, evaluators, и leaderboard tracks.

Связь с existing docs:
- `docs/01-vision/00-executive-vision.md`: "first proof must be Phase 2 scaffolding ablation" + "How much does each layer L0 → L8 add"
- `docs/old/pollmevals-research 2/03-experiment-design.md`: 5-фазный fractional factorial design (~470 прогонов). Эта NOTE — операционализация полной vision, частично уже captured в old research.
- `docs/02-methodology/scoring.md`: текущие 6 метрик для coding (correctness, coverage, complexity, lint, type-safety, judge_pattern). Эта NOTE дополняет ещё 4 dimensions.

Status: durable reference. NOTE = micro-decision (90-day TTL) — продлевается по relevance ; промотируется в PRD/RFC когда implementation начинается.

## Section 1 — Agent CLI catalog (extended Phase 4 = "CLI agents")

Текущий stack каталог (`stacks/`) имеет 3 starter. Полный список для POLLMEVALS v0.2+:

| Slug | Vendor | Layers default | Source | Notes |
|---|---|---|---|---|
| **claude-code** | Anthropic | L1+L2 | `claude-code` CLI | + L3 skills + L4 file mem + L6 agents опционально |
| **codex** | OpenAI | L1+L2 | новый OpenAI Codex CLI | competitor к claude-code |
| **aider** | OSS | L1+L2+L4 | github.com/Aider-AI/aider | git-aware, repo-map built-in |
| **gemini-cli** | Google | L1+L2 | `gemini` CLI | Google's new agent CLI |
| **cursor-cli** | Anysphere | L1+L2 | Cursor headless mode | если supports non-interactive |
| **cline** | OSS | L1+L2 | github.com/cline/cline | VSCode/CLI hybrid |
| **cody** | Sourcegraph | L1+L2 | Cody CLI | enterprise context |
| **pi** | OSS | L1+L2+L3+L4 | pi.dev — "minimal terminal coding harness" | tree-structured session, auto-compaction memory. **NO** built-in subagents/validator (only via extensions). |
| **hermes** | Nous Research | L1+L2+L3+L4+L5+L6+L7 | hermes-agent.nousresearch.com | persistent multi-platform agent. Auto-generated skills, isolated subagents, 5 sandbox backends (local/Docker/SSH/Singularity/Modal). |
| **openhands** | OSS | L1+L2+L6 | github.com/All-Hands-AI/OpenHands | ex-OpenDevin, multi-agent built-in |
| **plandex** | OSS | L1+L2+L7 | github.com/plandex-ai/plandex | validator loops built-in |
| **goose** | Block | L1+L2+L3 | github.com/block/goose | extension marketplace, MCP integration |
| **forgeplan-framework** | ForgePlan | L1+L2+L3+L4+L6+L7+L8 | forgeplan CLI | наш собственный — full ladder |

### CLI sub-axes (test variations on same base CLI)

Для **claude-code** specifically — natural ablation:
- `claude-code` (L1+L2 only — system prompt + tools)
- `claude-code + skills` (+L3 — Anthropic Skills marketplace)
- `claude-code + claude.md` (+L4 file memory — CLAUDE.md auto-loaded)
- `claude-code + hindsight` (+L5 vector memory — наш Hindsight MCP)
- `claude-code + subagents` (+L6 — Agent tool with multiple subagents)
- `claude-code + plan-mode` (+L7 partial — plan-mode hook)
- `claude-code + forgeplan` (+L8 framework — forgeplan MCP active)

## Section 2 — Memory variants (axis для тестов)

| Slug | Layer | Source | Notes |
|---|---|---|---|
| **none** | — | — | baseline |
| **file-claude-md** | L4 | static markdown | always-loaded context |
| **file-agents-md** | L4 | AGENTS.md convention | OpenAI Codex / general |
| **mem0** | L5 | mem0.ai | vector memory с auto-classification |
| **letta-memgpt** | L5 | github.com/letta-ai/letta (ex-MemGPT) | hierarchical memory (working/archival/recall) |
| **zep** | L5 | getzep.com | temporal session memory с knowledge graph |
| **hindsight** | L5 | github.com/Anthropic/hindsight (наш!) | semantic recall + mental models + reflect |
| **graphrag** | L5+ | Microsoft GraphRAG / GoT (Graph of Thoughts) | graph-structured retrieval |
| **raflo** | L5+ | RAFLOW retrieval framework | retrieval-flow pipelines |
| **lightrag** | L5+ | github.com/HKUDS/LightRAG | lightweight graph RAG |

## Section 3 — Context tools axis (MCP servers + similar)

Ortho dimension — test **с** конкретным context tool **vs без**:

| Tool | What it provides | Test as axis |
|---|---|---|
| **context7** | live docs lookup (React/Next.js/Prisma/etc.) | + vs −: качество кода когда модель имеет доступ к real-time docs |
| **playwright-mcp** | browser automation context | для frontend tasks |
| **filesystem-mcp** | filesystem access | repo-aware tasks |
| **git-mcp** | git operations | review tasks |

Ablation: `claude-code` × `[context7=yes, context7=no]` — измеряем uplift от MCP docs tool.

## Section 4 — Codebase indexing tools (Serena-class)

Codebase **understanding** axis — different approaches к building repo context:

| Tool | Approach | Source |
|---|---|---|
| **serena** | LSP-based semantic indexing | github.com/oraios/serena |
| **aider-repo-map** | tree-sitter + LSP, dynamic repo map | built into aider |
| **sourcegraph** | enterprise code intelligence (Cody backend) | sourcegraph.com |
| **cody-context** | Sourcegraph context API | Cody CLI |
| **continue-codebase** | local-first indexing | github.com/continuedev/continue |
| **chroma-codebase** | vector embeddings of files | various |
| **claude-code-skill-find-skills** | naive skill-based lookup | Anthropic Skills "find-skills" |
| **mcp-codebase-summary** | LLM-summarised codebase index | various MCP servers |

Ablation: same agent CLI × `[no-index, serena, aider-repo-map, sourcegraph]` — измеряем impact индексирования на качество.

## Section 5 — Extended metrics dimensions

Текущий scoring.md имеет 6 метрик для coding tasks. Добавляем 4 dimensions для полной evaluation:

### Existing (from `docs/02-methodology/scoring.md`)

| Метрика | Weight (coding) | Tool |
|---|---|---|
| correctness | 0.40 | vitest / jest / pytest |
| test_coverage | 0.15 | coverage.py / c8 / vitest --coverage |
| complexity_score | 0.10 | radon (Py) / eslint --max-complexity (TS) / lizard |
| lint_score | 0.10 | ruff (Py) / eslint (TS) |
| type_safety_score | 0.10 | mypy --strict (Py) / tsc --strict (TS) |
| judge_panel_pattern_score | 0.15 | LLM judges per rubric (SOLID + style) |

### NEW (added per 2026-05-24 vision expansion)

| Метрика | Tool | Notes |
|---|---|---|
| **docstring_coverage** | interrogate (Py) / jsdoc-checker (TS) / pydocstyle | % public APIs с docstrings/JSDoc |
| **profile_score** | cProfile (Py) / clinic.js (TS) / pyinstrument | basic perf check, p95 latency under load |
| **dep_selection_quality** | bundle-phobia (TS) / pypistats (Py) / manual LLM rubric | did the model pick reasonable, well-maintained deps? |
| **vulnerability_scan_score** | npm audit / pip-audit / cargo audit / semgrep --config p/security / trivy | CVE-free, no high/critical findings |

### Adjusted weight proposal (v0.2 methodology)

Reweight to accommodate new dimensions (preserves correctness dominance):

```
final_score_01 =
  0.30 * correctness                ← reduced from 0.40
  + 0.10 * test_coverage           ← reduced from 0.15
  + 0.07 * docstring_coverage      ← NEW
  + 0.08 * complexity_score        ← reduced from 0.10
  + 0.08 * lint_score              ← reduced from 0.10
  + 0.08 * type_safety_score       ← reduced from 0.10
  + 0.07 * profile_score           ← NEW
  + 0.05 * dep_selection_quality   ← NEW
  + 0.07 * vulnerability_scan_score ← NEW
  + 0.10 * judge_panel_pattern_score ← reduced from 0.15
```

**Это proposal** — формальное изменение требует ADR (frozen methodology change). Не делается в этой NOTE; здесь зафиксирована direction.

## Section 6 — Phase numbering disambiguation

**Critical**: docs/ research использует "Фаза 1-5" (experiment phases), а codebase использует "Phase 0-5" (infrastructure phases). Это **разные оси**:

| Codebase "Phase N" | Что это | Research "Фаза N" | Что это |
|---|---|---|---|
| Phase 0 | Documentation + research | — | — |
| Phase 1 | 20 forgeplan artifacts + GitHub setup | — | — |
| Phase 2A | Python orchestrator foundation | — | — |
| Phase 2B | Docker stack + LiteLLM + LGTM | — | — |
| Phase 2C | OTel instrumentation | — | — |
| Phase 2B coda | First real smoke run (45 evals) | **Фаза 1** | 14 моделей × 20 задач baseline radar |
| Phase 2D | Real evaluators (cyclomatic + coverage + lint + extended metrics) | — | — |
| Phase 3 | Judges layer (PRD-002 + RFC-002) | **Фаза 2** | Scaffolding ablation L0→L6 on 1 model |
| — | — | **Фаза 3** | Memory variants comparison |
| Phase 4 | Weekly cron + leaderboard | **Фаза 4** | CLI agent comparison (Claude Code, Codex, Gemini, Hermes, Pi) |
| Phase 5 | Release pipeline | **Фаза 5** | Pareto cost vs quality |

**How to apply**: When discussing "Phase N", prefix as either "infra-phase N" or "research-phase N" if context ambiguous.

## Section 7 — Suggested execution timeline (revised after 2026-05-24)

```
Now (infra-phase 2B coda)
  → fix smoke bugs (cost + determinism per ADR-002)
  → full 45-eval smoke на raw-llm × 5 models = pipeline validation

Next session (infra-phase 2D + research-Фаза 1 minimal)
  → implement real evaluators (cyclomatic, coverage, lint, type) + extended metrics stubs
  → expand stacks/ catalog: add YAMLs для aider, codex, gemini-cli, pi, hermes (5 stacks)
  → expand evals/task-packs/: 3 → 5 (add be_02, fe_02 as quick wins)

Sessions +2..+4 (infra-phase 3 + research-Фаза 2)
  → judges layer (PRD-002 Slices B-E implementation)
  → run scaffolding ablation (research-Фаза 2): 1 model × 8 stack variants × 3 tasks × 3 seeds = 72 evals
  → first ablation EVID with median uplift per layer

Sessions +5..+7 (research-Фаза 3 + research-Фаза 4)
  → memory variants comparison (research-Фаза 3): 1 model × 6 memory types × 3 tasks
  → CLI agents comparison (research-Фаза 4): claude-code, codex, aider, openhands, hermes, pi on same task

Sessions +8..+10 (infra-phase 4 + research-Фаза 5)
  → weekly cron + leaderboard frontend
  → Pareto frontier publication (research-Фаза 5)
```

## Section 8 — User-mentioned dimensions (zachvachuk for reference)

Verbatim list of dimensions user established in 2026-05-24 session, all captured above:

1. ✅ "claude код чистый, затем клод код и скиллы, затем клод код и агенты, затем клод код и память" — covered в Section 1 sub-axes
2. ✅ "цикломатика, сложность, чистота, покрытие тестами, линтинг, форматинг" — Section 5 existing metrics
3. ✅ "SOLID и другие стандарты" — covered judge_panel_pattern_score (existing) + dep_selection_quality (new)
4. ✅ "codex, aider, gemini, pi, hermes" — Section 1 catalog
5. ✅ "разную память — gas town, raflo" — Section 2 memory variants (gas town = GoT/Graph of Thoughts, raflo = RAFLOW)
6. ✅ "покрытие документации в коде" — Section 5 NEW docstring_coverage
7. ✅ "профилирование" — Section 5 NEW profile_score
8. ✅ "как написан код хорошо и как применены подходы" — judge_panel_pattern_score (existing)
9. ✅ "подборка библиотек" — Section 5 NEW dep_selection_quality
10. ✅ "проверка библиотек на уязвимости" — Section 5 NEW vulnerability_scan_score
11. ✅ "тест с context7 и без него" — Section 3 context tools axis
12. ✅ "serena и другие шутки которые индексируют" — Section 4 codebase indexing tools

## Section 9 — Cross-references

- **PRD-001**: smoke run goal (5 models × 3 tasks × 3 seeds raw-llm) — pipeline validation, не full ablation
- **PRD-002**: judges layer — required для всех research-фаз (3, 4, 5)
- **PRD-003..005**: drafts, не expanded — eventual targets: PRD-003 weekly cadence ↔ research-фаза 5
- **RFC-002**: judges implementation — orthogonal to this NOTE; both feed Phase 3+ work
- **SPEC-001**: manifest contract — extended metrics ADD fields; SPEC-001 may need v1.1.0 для new metrics
- **ADR-003**: 5-model lineup — compatible with extended catalog (adds models incrementally)
- **ADR-005** (draft): median + CI gate — extends to extended metrics too (same aggregation rules)
- **EVID-019** (smoke OpenRouter), **EVID-020** (Phase 2B bootstrap), **EVID-023** (H1 spike) — все compatible
- **NOTE-002**: evidence quality standard — applies к future EVIDs from extended runs
- **NOTE-003**: observability — already in place для tracking multi-stack runs

## Section 10 — Status + lifecycle

- Status: **draft** initially. Activate когда (a) at least 3 stack additions implemented в stacks/ AND (b) at least 1 extended metric reduced to working evaluator.
- TTL: 90 days default; renew at activation. Will be superseded by formal **PRD-006 "expanded stacks + extended metrics methodology"** if vision crystallizes into product spec.
- Owner: gogocat (solo maintainer per user_profile memory).

## How to use this NOTE

- **Future Phase 3+ implementations**: cite NOTE-004 как source-of-truth для stack/memory/tool/metric catalog. Don't re-derive.
- **Future PRD-006 author**: this NOTE is the seed. Promote to PRD when 5+ stacks implemented и extended metrics design proves viable.
- **Future ADR for methodology v0.2**: Section 5 proposed reweighted formula is starting point. Empirical validation за first ablation EVID required before adoption.






