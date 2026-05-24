---
depth: standard
id: NOTE-005
kind: note
last_modified_at: 2026-05-24T22:40:09.308614+00:00
last_modified_by: claude-code/2.1.150
links:
- target: EPIC-001
  relation: informs
- target: NOTE-004
  relation: refines
status: draft
title: POLLMEVALS Vision Map — dd.md ↔ forgeplan artifact coverage matrix
---

# NOTE-005: POLLMEVALS Vision Map — dd.md ↔ forgeplan artifact coverage matrix

## Purpose

`docs/old/dd.md` — это **исходное TЗ** проекта (1785 lines), полная переписка от идеи до product spec. Это **what we promised to build**. Этот NOTE даёт **single-file index** проверки покрытия:

- Что из dd.md уже **зафиксировано** в forgeplan (с указанием artifact ID)
- Что из dd.md **частично** покрыто (с конкретным gap)
- Что из dd.md **НЕ покрыто** ни одним artifact (с предложенным slot'ом для будущего)

**How to use**: open этот NOTE FIRST когда задаёшься вопросом "а у нас это есть?" or "что не сделано из dd.md?" before reading individual artifacts. Updated после каждого major artifact change.

---

## Section A — Vision + methodology (концепция scaffolding evaluation)

| dd.md theme | Status | Artifact |
|---|---|---|
| POLLMEVALS — оценка **полных стеков** (модель + agent CLI + skills + память + validator) не голых моделей | ✅ | EPIC-001 + NOTE-004 + `docs/01-vision/00-executive-vision.md` (frozen v0.1.0) |
| L0→L8 scaffolding ladder | ✅ | `CONTEXT.md` Domain glossary + NOTE-004 Section 1 |
| Дешёвая модель + обвязка vs дорогая голая модель = thesis | ✅ | EPIC-001 + `docs/01-vision/00-executive-vision.md` "first proof must be scaffolding ablation" |
| 5-фазный factorial design (Фаза 1 baseline → Фаза 5 Pareto) | ✅ | NOTE-004 Section 6 (research phases) + `docs/old/pollmevals-research 2/03-experiment-design.md` (seed) |
| Series of 5 blog posts (How we measure → Bare LLM vs scaffolding → Memory → Validator → Stacks) | 🟡 | NOTE-004 mentions; **no dedicated PRD** для blog series — это marketing artefact, OK не tracked в forgeplan |

## Section B — Tools chain (inference + observability)

| dd.md theme | Status | Artifact |
|---|---|---|
| Inspect AI как eval engine | ✅ | EVID-004 (prior art) + RFC-001 (orchestrator) + `InspectEvalCaller` real impl (commit 9e668db) + EVID-023 (H1 spike proves list-of-scorers) |
| LiteLLM gateway + Postgres spend logs + virtual keys | ✅ | EVID-020 (bootstrap) + `infra/litellm-config.yaml` + commit b9ebb1f + commit 5d4b432 (cost_per_token API swap, Library-first) |
| Cerebras + Runpod + OpenRouter под одной крышей LiteLLM | 🟡 | ADR-003 — OpenRouter routes wired (5 моделей); **Cerebras + Runpod routes NOT yet added** к `infra/litellm-config.yaml`. Gap: extend config + test. |
| OTel/Grafana/Loki/Tempo observability | ✅ | NOTE-003 + Phase 2B/2C commits (b9ebb1f + 0e494f6) — **дополнение к dd.md**, не было в исходном spec |
| Cost tracking + automatic pricing snapshots | ✅ | `_make_pricing_snapshot` via `litellm.cost_per_token()` (commit 5d4b432) + `_FALLBACK_PRICING_PER_MTOKEN` для unknown models |

## Section C — Skoring methodology (automatic + LLM judges)

| dd.md theme | Status | Artifact |
|---|---|---|
| Composite scoring formulas: correctness + coverage + complexity + lint + type + pattern (coding); structural_completeness + factual + clarity + actionability + consistency (doc) | ✅ | `docs/02-methodology/scoring.md` v0.1.0 frozen |
| **Extended metrics** (docstring coverage, profiling, dep selection, vulnerability scan) | ✅ | NOTE-004 Section 5 (catalogued + canonical libraries) |
| Panel of LLM judges с rotation, no self-judging, blind labels, median, calibration | ✅ | PRD-002 (Q1-Q5 decisions) + RFC-002 5 Slices + ADR-005 (median + CI gate rationale) + `docs/02-methodology/judge-policy.md` |
| Judge bias mitigation (self-enhancement, position, length, verbosity, authority, sycophancy, anchor, halo, calibration drift) | ✅ | `docs/02-methodology/judge-policy.md` (frozen Bias mitigations table) + PRD-002 sections |
| Calibration set (5 quality levels × 3 tasks × 10 samples = 150 samples per session) + identification probe (150 samples, accuracy ≤ 30%) | ✅ | PRD-002 Q4 + Q5 + RFC-002 Slice D + ADR-005 invariants |
| Inter-judge agreement Krippendorff α ≥ 0.70 + bootstrap CI lower-bound publication gate | ✅ | ADR-005 + PRD-002 SC-1 + RFC-002 Slice C |
| Cohen's d, multi-seed runs, pre-registration | 🟡 | **Multi-seed = ✅** (3 seeds в smoke run done, EVID-024); **Cohen's d effect size = ❌** not formalized в any artifact; **pre-registration = ❌** not formalized |

## Section D — Tasks library (20 production-ready)

| dd.md theme | Status | Artifact |
|---|---|---|
| 20 задач: 4 BE + 3 FE + 2 FS + 2 DB + 2 DevOps + 3 Docs + 2 Tests + 2 Review + 1 Refactor + 1 Refactor-other | 🟡 | **3/20** реализовано в `evals/task-packs/` (be_01_jwt_auth + fe_01_multistep_form + doc_01_cli_readme); **17 задач missing** |
| Каждая задача: gold solution + automated evaluator + ≥3 numerical metrics + <5 min wall-clock | 🟡 | Для 3 existing — gold + evaluator stubbed; **real automated evaluator (vitest/tsc/c8) для coding tasks = Phase 2D Slice 2 scope (NOT done)** |
| TypeScript/Node.js основной + Python для DevOps + SQL для DB | 🟡 | be_01/fe_01 — TS; doc_01 — markdown; **Python + SQL tasks NOT in repo** |
| Versioned tasks (slug + version) | ✅ | SPEC-001 TaskPin contract + `docs/02-methodology/task-lifecycle.md` |
| Gold solutions origins: SWE-Lancer (1488 real Upwork), DevBench (1800 telemetry), BigCodeBench (1140 functions) | 🟡 | dd.md рекомендует — **no dedicated artifact** acknowledging это; references только в NOTE-004 |

**Gap to close**: PRD-006 (или NOTE-006) "Tasks catalog expansion v0.1 — Phase 1 20-task roadmap". Specify which 17 tasks + acceptance criteria + gold source.

## Section E — Models lineup (14 cloud + local)

| dd.md theme | Status | Artifact |
|---|---|---|
| 8 cloud: Claude Opus 4.7 + Sonnet 4.6, GPT-5 + GPT-5-mini, Gemini 2.5 Pro + Flash, Grok 4, DeepSeek V3.5 | 🟡 | ADR-003 — **5/8** wired (Sonnet 4.6, GPT-5 mini, Gemini 3 Flash); **3 missing**: Opus, GPT-5 full, Gemini 2.5 Pro, Grok 4, DeepSeek V3.5 |
| 6 local через Cerebras: Llama 3.3 70B, Qwen3 32B, GLM-4.7, gpt-oss-120B; через Runpod: Qwen 2.5 72B; Mac local: Qwen 2.5 14B | 🟡 | **2/6** wired (Qwen 3 14B, Llama 3.3 70B через OpenRouter, не через Cerebras direct); **4 missing**: Cerebras routes + Runpod 72B + Mac local |
| Per-model provider routing (Cerebras cheap+fast, Runpod for big open-weight, OpenRouter for closed) | 🟡 | ADR-003 Decision Outcome documents intent; **Cerebras + Runpod routes NOT yet added** to litellm-config.yaml |

**Gap to close**: ADR-006 (или extend ADR-003) "Phase 1 14-model adoption — Cerebras + Runpod routing + cost matrix"

## Section F — Eval pipeline (14 шагов)

| dd.md step | Status | Artifact |
|---|---|---|
| 1. Cron trigger в понедельник 03:00 UTC | 🟡 | PRD-003 draft mentions; **no Cron file** (e.g. `.github/workflows/weekly-eval.yml` not created) |
| 2. Snapshot state (model + tool versions) | ✅ | SPEC-001 Manifest (model_pins/stack_pins/task_pins + version_tag) |
| 3. 4 region workers поднимаются | ❌ | **NO artifact** для geo workers; not in any PRD/RFC |
| 4. Worker'ы прогоняют матрицу (models × tasks × 5 seeds) | ✅ | RFC-001 § Concurrency + EVID-017 + commit b9ebb1f + Phase 2B coda 45/45 (EVID-024) |
| 5. Raw outputs → S3 content-hash | 🟡 | EVID-024 confirmed local disk persistence (mode 0o444); **R2/S3 upload NOT yet** — only local `artifacts/` |
| 6. Automatic metrics (pytest, eslint, radon) | 🟡 | Phase 2D Slice 1 — 3 evaluators wraps live (lint/complexity/secret_scan); **Slice 2 vitest/tsc/c8 в sandbox = NOT done** |
| 7. Anonymization pipeline | 🟡 | `docs/04-runbook/07-judge-panel.md` lists normalization steps; **no impl** code yet |
| 8. Judge panel × all evals, randomized order, blind labels | 🟡 | Slice A (skeleton) + Slice B (score dispatch) done; **Slice C (aggregate) + D (calibration) + E (GridRunner integration) = NOT done** |
| 9. Aggregation: median + α + bootstrap CI | 🟡 | ADR-005 + RFC-002 Slice C scoped; **NOT implemented** |
| 10. Drift detection (compare с prev week) | ❌ | **NO artifact** — neither PRD-003 nor PRD-004 mention currently |
| 11. Calibration check (golden set) | 🟡 | PRD-002 SC-3 (calibration MAD ≤ 1.5) + RFC-002 Slice D; **NOT implemented** |
| 12. DB update atomically | ✅ | EVID-013 (atomic manifest state machine writer) + ADR-002 immutability |
| 13. Cache invalidation + leaderboard rebuild | ❌ | **NO artifact** — это часть PRD-004 frontend MVP scope |
| 14. Public announcement (blog + Twitter + Telegram + RSS) | ❌ | **NO artifact** — это marketing scope, OK не tracked |

## Section G — Sites pages (Next.js 15 frontend)

| dd.md page | Status | Artifact |
|---|---|---|
| `/leaderboards` (3 tabs: by Model, by Stack, by Task class) | 🟡 | PRD-004 draft mentions; **not built** |
| `/models/[slug]` (radar + history + latency by region + best stacks) | ❌ | PRD-004 не упоминает в detail |
| `/stacks/[slug]` (best models for this stack + cost-quality vs bare) | ❌ | PRD-004 не упоминает |
| `/tasks/[slug]` (description + gold + evaluator + history) | ❌ | PRD-004 не упоминает |
| `/compare` (side-by-side до 4 моделей/стеков + shareable URL) | ❌ | PRD-004 не упоминает |
| `/runs/[hash]` (reproducibility proof page) | ❌ | PRD-004 не упоминает; partial — manifest есть на disk |
| `/methodology` (полная methodology + versioned) | 🟡 | `docs/02-methodology/` exists в repo; **not published site** |
| `/judges` (judge list + calibration scores + inter-judge matrix) | ❌ | PRD-004 не упоминает |
| `/calibration` (golden set + judge scores per task) | ❌ | PRD-004 не упоминает |
| `/scoring` (formulas documentation) | 🟡 | `docs/02-methodology/scoring.md` exists; **not published** |
| `/blog` (weekly updates + long-form posts) | ❌ | **NO artifact** — это marketing |
| `/vote` (community voting GitHub OAuth) | ❌ | **NO artifact** |
| `/propose-{model\|task\|stack}` (submission forms) | ❌ | **NO artifact** |
| `/api` (public OpenAPI docs + auth + rate limits) | ❌ | **NO artifact** |
| `/datasets` (bulk download Parquet/CSV) | ❌ | **NO artifact** |
| `/status` (cron health + last/next run + worker uptime) | ❌ | **NO artifact** |
| `/pricing` (Tier 0/1/2) | ❌ | **NO artifact** |
| `/changelog` (methodology + model + task changes + RSS) | ❌ | **NO artifact** |

**Gap to close**: extend **PRD-004** body с full sitemap + per-page acceptance criteria, OR create **SPEC-002 "POLLMEVALS site architecture v0.1"**

## Section H — Data model

| dd.md table | Status | Artifact |
|---|---|---|
| `models` | ✅ | `packages/db/migrations/0001_initial.sql` + SPEC-001 ModelPin |
| `model_providers` | ✅ | `0001_initial.sql` |
| `stacks` | ✅ | `0001_initial.sql` + SPEC-001 StackPin + stacks/*/stack.yaml (9 stacks) |
| `tasks` | ✅ | `0001_initial.sql` + SPEC-001 TaskPin + evals/task-packs/ (3 tasks) |
| `runs` | ✅ | SPEC-001 RunHash + ADR-002 immutability + EVID-024 |
| `evals` | ✅ | SPEC-001 EvalRow + EVID-016 (GridRunner) + EVID-017 |
| `judgments` | 🟡 | `apps/eval-core-py/src/contracts/judge.py` (Slice A) — Pydantic model; **DB table NOT in migration 0001** |
| `calibration_runs` | ❌ | **NO Pydantic model, NO DB table** |
| `votes` | ❌ | **NO model/table** — community feature, Phase 4+ |

**Gap to close**: migration `0002_judges_calibration_votes.sql` для extending DB schema.

## Section I — Reliability, immutability, anti-gaming

| dd.md theme | Status | Artifact |
|---|---|---|
| Reproducibility (all prompts + versions + seeds pinned, raw outputs immutable) | ✅ | ADR-002 + SPEC-001 + EVID-024 (mode 0o444 verified) |
| Task versioning (slug + version, old evals stay valid) | ✅ | SPEC-001 + `docs/02-methodology/task-lifecycle.md` |
| **Model drift detection** (Δ > 2σ → alert + public note) | ❌ | **NO artifact** — PRD-003 ambient mention only |
| **Contamination detection** (Google search for task hashes) | ❌ | **NO artifact** |
| **Anti-gaming held-out set** (20% private tasks, monthly rotation) | ❌ | **NO artifact** |
| Code execution safety (Docker no-network, RAM/CPU limit, 60s timeout, read-only fs) | 🟡 | `docs/02-methodology/security-sandbox.md` (frozen) + stacks/*/sandbox spec; **NO sandbox runner impl** in apps/eval-core-py/ |
| Calibration set (10 known-score samples per task category) | 🟡 | PRD-002 Q4 + RFC-002 Slice D; **NOT implemented** |
| Pre-registration (hypotheses в git before run) | ❌ | **NO artifact / NO process** |

**Gaps to close**: NOTE-006 "Anti-gaming + drift + contamination program" + extend PRD-003 (или create PRD-007 dedicated)

## Section J — Privacy, legal, disclosure

| dd.md theme | Status | Artifact |
|---|---|---|
| License: dataset CC BY-SA 4.0, code MIT | 🟡 | repo has `LICENSE` (likely MIT — verify); **dataset license NOT specified** |
| GDPR compliance для community accounts (right to deletion) | ❌ | **NO artifact** — community Phase v0.3+ |
| Disclosure policy для sponsored evals (badge + dedicated page) | ❌ | **NO artifact** — Tier 3 v1.0 scope |
| ToS vendor check (некоторые запрещают benchmark publication) | ❌ | **NO artifact** — operational check not formalized |
| IP authors of tasks (если basis from production code, нужна permission) | ❌ | **NO artifact** |
| Disclosure of conflicts (Eli ведёт ForgePlan; ForgePlan stack evaluated рядом с конкурентами) | ❌ | **NO artifact** — должен быть public statement |

**Gap to close**: NOTE-007 "POLLMEVALS legal + disclosure policy v0.1"

## Section K — Onboarding flows (new model/stack/task)

| dd.md step | Status | Artifact |
|---|---|---|
| 1. Proposal form (`/propose-model` with YAML спека) | ❌ | **NO frontend, NO artifact** |
| 2. Auto-check (endpoint reachable + ping + tokens counter + pricing match + slug unique) | ❌ | **NO artifact** |
| 3. Community vote (X votes за 7 days; fast-track для critical flagships) | ❌ | **NO artifact** |
| 4. Manual review (duplicate check + ToS check + 10 sanity prompts) | ❌ | **NO artifact** |
| 5. Calibration run (mini-grid: 5 cal + 3 regular) | 🟡 | RFC-002 Slice D mentions calibration; **process NOT formalized** |
| 6. LiteLLM config update + version tag pin | 🟡 | Manual process; **automation NOT artifact** |
| 7. Public announcement в `/changelog` + RSS | ❌ | **NO artifact** |

**Gap to close**: RFC-003 "Artifact onboarding workflow v0.1 (model/stack/task proposal → review → publication)"

## Section L — Geo-aware metrics (4 регионов)

| dd.md theme | Status | Artifact |
|---|---|---|
| 4 docker workers в US-East, EU-Central, APAC, SA | ❌ | **NO PRD/RFC** |
| TTFT measurement per region | ❌ | OTel can capture (NOTE-003) но **region attribution NOT wired** |
| `evals.region` column + frontend filter | 🟡 | SPEC-001 has `region` field (defaulted "eu-central"); **multi-region NOT exercised** |
| World heatmap latency + geo-IP detection | ❌ | **NO artifact** — Phase 4 frontend |

**Gap to close**: PRD-006 "Geo-aware latency v0.2 — 4-region workers" (defer to v0.2 per dd.md roadmap)

## Section M — Open questions (tactical)

| dd.md question | Status | Action needed |
|---|---|---|
| Где брать gold solutions для 17 missing tasks? | ❌ | Decision: написать самим (~150ч) OR взять SWE-Lancer subset OR hire freelancers ($5-10k). **TBD discussion.** |
| Кто пишет evaluator scripts (40-80ч)? | ❌ | Solo if Phase 2D coder agents handle it via Library-first |
| Юридическая структура (LLC/Ltd) | ❌ | Phase v1.0+ when commercialization starts |
| Domain pollmevals.com registration | ❌ | **HIGH PRIORITY — register сейчас** (per dd.md open Q#4) |
| Brand check (Google "pollmevals" + trademark) | ❌ | Quick action |
| Open-source repo org `github.com/pollmevals/{core,tasks,site,litellm-config}` | 🟡 | Currently single repo `ForgePlan/pollmevals`. **Decision: split or stay monorepo** |
| TypeScript/Node.js as основной стек | ✅ | Confirmed в `docs/01-vision/00-executive-vision.md` + ADR-001 (concurrency for Python orchestrator) |

## Section N — Roadmap fidelity

| dd.md milestone | Status | Mapping |
|---|---|---|
| **MVP (3-4 мес)**: Phase 1 only + basic site + 1 weekly run (14 models × 20 tasks) от Frankfurt | 🟡 | Infrastructure 90% done; **content (17 tasks + 9 models) + frontend = pending** |
| **v0.2 (5-6 мес)**: Geo workers + scaffolding stacks (Фаза 2) + Compare page + Public datasets | ❌ | Stacks catalog ready (9 stacks); geo + ablation runs + compare = pending |
| **v0.3 (7-9 мес)**: Community vote + Public API + Tier 1 pricing | ❌ | Phase 4-5 in our infra plan |
| **v1.0 (10-12 мес)**: Validator loop (Фаза 3) + full ablation series Фазы 2-5 weekly | ❌ | Distant scope |
| **v2.0 (год+)**: Enterprise white-label + multilingual + sponsored evals protocol | ❌ | Out of v0.x scope per existing Non-goals в CLAUDE.md |

---

## Summary — overall coverage

| Block | Coverage | Notes |
|---|---|---|
| A — Vision/methodology | **100%** | Full alignment dd.md vs frozen v0.1.0 + EPIC-001 |
| B — Tools chain | **80%** | Inspect + LiteLLM + OTel done; Cerebras/Runpod routes pending |
| C — Skoring methodology | **70%** | Formulas frozen + judge methodology designed; impl partial |
| D — Tasks library | **15%** | 3/20 tasks; **biggest content gap** |
| E — Models lineup | **36%** | 5/14 models wired |
| F — Eval pipeline 14 steps | **57%** (8/14 done) | Steps 3 (geo), 10 (drift), 13 (cache), 14 (announce) — pending |
| G — Sites pages | **5%** | Almost nothing built; methodology lives в repo docs |
| H — Data model | **78%** (7/9 tables) | Judgments + calibration_runs + votes missing |
| I — Reliability/anti-gaming | **40%** | Reproducibility solid; drift/contamination/anti-gaming = ❌ |
| J — Privacy/legal | **10%** | License OK; disclosure/GDPR/ToS = ❌ |
| K — Onboarding flows | **5%** | RFC-003 needed |
| L — Geo-aware metrics | **5%** | SPEC-001 has region field; impl = ❌ |
| M — Open questions | **20%** | Stack lang ✅; gold/domain/legal/repo split TBD |
| N — Roadmap fidelity | **40%** (MVP partial) | Infra 90%; content + frontend pending |

**Overall coverage MVP (dd.md scope): ~45-55%** (infra core полностью, content + frontend + advanced features pending)

---

## Identified gaps — proposed artifact slots

Прямые gaps which нужно создать как future artifacts (когда дойдут руки):

| Gap | Predicted artifact | Scope |
|---|---|---|
| 17 missing tasks roadmap | **NOTE-006** или **PRD-006** "Tasks catalog expansion v0.1" | List 17 missing tasks + gold source choice (own vs SWE-Lancer) + Phase 2D evaluator dependency |
| 9 missing models adoption | **ADR-006** "Phase 1 14-model adoption: Cerebras + Runpod routes + cost matrix" | LiteLLM config additions + pricing snapshot updates |
| Drift detection + alerting | extend **PRD-003** body OR new **PRD-007** | Δ > 2σ trigger logic + alert channel + public note format |
| Contamination + anti-gaming | new **NOTE-007** | Periodic hash search + 20% held-out task rotation policy |
| Legal/disclosure/conflicts | new **NOTE-008** | License + GDPR + sponsored eval disclosure + ForgePlan conflict |
| Onboarding workflow | new **RFC-003** | propose-model/task/stack flow + manual review + calibration run |
| Geo-aware workers | extend **PRD-003** body OR new **PRD-008** | 4-region docker workers + region routing |
| Frontend sitemap | extend **PRD-004** body OR new **SPEC-002** | Full 18-page sitemap per dd.md + acceptance criteria |
| Migration `0002_judges_calibration_votes` | DB migration file (not forgeplan artifact) | Add 3 missing tables |

## How to keep this NOTE current

- Update Section N (roadmap fidelity) when any phase milestone hits
- Update Section coverage % when any major artifact lands
- When user asks "что из dd.md покрыто?" — open this NOTE first
- When orchestrator considers spawning agent для feature — verify here first что gap не закрыт уже в существующем artifact

This NOTE is **the single SOURCE OF TRUTH** for dd.md ↔ forgeplan coverage. Cite NOTE-005 in any future review of project state.

---

## Cross-references

- All forgeplan artifacts (42 total): use `mcp__forgeplan__forgeplan_list` для swieżej snapshot
- Source TЗ: `docs/old/dd.md` (1785 lines, read-only)
- Vision canonical: `docs/01-vision/00-executive-vision.md`
- Methodology canonical: `docs/02-methodology/` (FROZEN v0.1.0)
- Extended vision catalog: NOTE-004
- File RAG entry point: `INDEX.md` (root) + `docs/INDEX.md`
- CLAUDE.md Library-first rule: `CLAUDE.md` § Library-first



