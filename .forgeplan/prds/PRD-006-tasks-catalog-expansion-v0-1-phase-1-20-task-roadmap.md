---
depth: standard
id: PRD-006
kind: prd
last_modified_at: 2026-05-24T22:59:51.681745+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: NOTE-005
  relation: refines
- target: NOTE-004
  relation: informs
status: draft
title: Tasks catalog expansion v0.1 — Phase 1 20-task roadmap
---

# PRD-006: Tasks catalog expansion v0.1 — Phase 1 20-task roadmap

## Executive Summary

### Vision

Закрыть biggest content gap POLLMEVALS v0.1: дореализовать **17 missing tasks** из 20-задачного каталога dd.md (research-Фаза 1), чтобы базовая радар-карта **14 моделей × 20 задач × 3 seeds = 840 evals** стала возможной. На сегодня готовы только 3/20 tasks (`be_01_jwt_auth`, `fe_01_multistep_form`, `doc_01_cli_readme`); без расширения каталога мы не сможем выйти на честный publication-grade baseline, а Phase 2D evaluators (real cyclomatic / coverage / lint / extended metrics из NOTE-004 Section 5) останутся без реалистичного task input.

### Problem / Motivation

NOTE-005 Section D однозначно фиксирует: **15% coverage** — 3 из 20 задач имеют `task.yaml + prompt + gold + evaluator`. Без full 20-task catalog:

1. **Baseline radar невозможен.** Phase 1 research design (dd.md lines 1227-1300) предписывает 20 задач для получения статистически значимых per-category средних. С 3 задачами grid даёт 14×3×3=126 evals; целевой 14×20×3=840 evals покрывает coding/frontend/fullstack/db/ops/tests/docs/review реалистичной выборкой.
2. **Phase 2D evaluators недогружены.** Real evaluators (vitest, c8, eslint, radon, mypy, pip-audit, npm audit, interrogate, cProfile per NOTE-004 Section 5) требуют tasks с настоящим test suite + lint config + dep manifest. `be_01` имеет минимальный stub — недостаточно для калибровки 9-метрической формулы NOTE-004 Section 5.
3. **Cost-quality Pareto frontier (Фаза 5) недоступен.** Сравнение Stack × Task без покрытия всех 9 категорий (BE/FE/FS/DB/Ops/Tests/Docs/Review/Refactor) даёт смещённый результат — модель сильная в backend выглядит универсальным лидером.
4. **Анти-contamination недотягивает.** dd.md рекомендует 20% held-out tasks (NOTE-005 Section I) — это 4 задачи в private holdout. На 3 task catalog режим невозможен.

**Impact**: без этого PRD цель v0.1 weekly run cadence (PRD-003) откладывается до Q3, ADR-006 14-model adoption бессмысленен в content vacuum, и frontend leaderboard (PRD-004) рисует радары на n=3 — несостоятельно для публикации.

### Target Users

| Персона | Описание | Ключевая боль |
|---|---|---|
| Maintainer (gogocat) | Solo author, executes weekly run | Не может предъявить честный baseline на 3 задачах |
| Engineering lead | Внешний читатель leaderboard | Нужно покрытие реальных рабочих сценариев (BE+FE+DB+Ops+Tests) |
| Researcher | Сравнивает scaffolding effect | Не может развести model-quality от task-narrowness в выборке |
| Model creator | Хочет видеть как его модель ranking | Радар на 3 категориях даёт незначимые различия |

### Differentiators

- **Каталог уже design-frozen** в dd.md lines 1239-1297 — не нужно отдельной discovery-фазы, есть user-validated список.
- **Source diversification**: гибрид own-authored gold + sourced из SWE-Lancer / DevBench / BigCodeBench с license attribution — снижает single-author bias (R-3 ниже).
- **17 tasks с реалистичным размером (≤200 LOC gold)** соответствует "small real task" профилю dd.md и Phase 2D evaluator constraints (≤5min wall-clock).
- **Stack lang policy frozen**: TypeScript/Node.js основной + Python (DevOps/data) + SQL (DB neutral) — устраняет ambiguity dd.md open Q (NOTE-005 Section M user already confirmed).

---

## Success Criteria

| ID | Criterion | Metric | Current | Target | How to Measure |
|----|-----------|--------|---------|--------|----------------|
| SC-1 | All 17 missing tasks materialized | task-pack completeness | 3/20 | 20/20 with `task.yaml + prompt.md + gold/ + evaluator/` | `find evals/task-packs -name task.yaml \| wc -l` = 20 |
| SC-2 | Each task has ≥3 numerical metrics | `weight_components` keys in task.yaml | n/a | ≥3 per task per scoring.md formulas | `yq '.weight_components \| keys \| length' evals/task-packs/*/task.yaml` all ≥ 3 |
| SC-3 | All 20 task specs validate | JSON Schema PASS rate | 3/3 PASS | 20/20 PASS via `make validate-tasks` | `make validate-tasks` exit code 0 |
| SC-4 | Gold solutions provided | gold/ directory presence + LOC bounds | 3/3 own-authored | 20/20 (own OR sourced w/ attribution); ≤200 LOC each | `wc -l evals/task-packs/*/gold/**` per-task ≤200; LICENSE.md per sourced |
| SC-5 | Stack language policy honored | task lang allocation | n/a | TS ≥12 / Python ≥3 / SQL ≥2 / Mixed allowed | count by `task.yaml: language:` field |
| SC-6 | At least 1 smoke run on new tasks | manifest published | 0 (only PRD-001 smoke on 3 tasks) | ≥1 manifest covering ≥10 new tasks | manifest exists in `artifacts/runs/<hash>/manifest.json` with ≥10 new task slugs |

---

## Product Scope

### MVP (In-Scope)

**17 tasks to author** (full list per dd.md lines 1239-1297 verbatim):

**Backend / API (4 tasks, TypeScript/Node.js)**
- `be_01_jwt_auth` — DONE (existing)
- `be_02_rest_post_users` — REST POST /users + Zod validation + email dedup + RFC 7807 errors
- `be_03_webhook_hmac` — Webhook handler with HMAC signature verification + idempotency key + replay-safe retry
- `be_04_cursor_pagination` — Cursor-based pagination for GET /posts with N+1 prevention

**Frontend (3 tasks, React + TypeScript)**
- `fe_01_multistep_form` — DONE (existing)
- `fe_02_debounced_search` — Debounced search input with loading/error/empty states + race-condition safety
- `fe_03_dnd_kanban` — Drag-and-drop kanban list with persistent order + optimistic UI

**Fullstack (2 tasks)**
- `fs_01_feature_flag` — Feature flag system: backend toggle endpoint + frontend hook + no-flicker UX
- `fs_02_resumable_upload` — File upload with resumable chunks (frontend + backend) + abort safety + integrity check

**Database (2 tasks, PostgreSQL)**
- `db_01_zero_downtime_migration` — Migration: split `users.address` into normalized table with zero-downtime strategy + rollback safety
- `db_02_query_optimization` — Optimize query doing full scan on 10M rows → use index, p95 latency ≤ gold × 1.2

**DevOps (2 tasks, Docker + GitHub Actions, Python tooling)**
- `ops_01_multistage_dockerfile` — Multi-stage Dockerfile for Node app: image size < 150MB, non-root user, healthcheck, Trivy scan clean
- `ops_02_github_actions_workflow` — GitHub Actions workflow: matrix tests, cache, deploy-on-tag, actionlint validates, no secret leaks

**Tests (2 tasks)**
- `tst_01_legacy_function_tests` — Write tests for legacy function (given function + spec): coverage ≥90%, mutation score ≥70%, no flaky
- `tst_02_testcontainers_integration` — Integration test for REST API with Testcontainers Postgres: isolation, <5s runtime

**Documentation (3 tasks)**
- `doc_01_cli_readme` — DONE (existing)
- `doc_02_adr_postgres_vs_mongodb` — ADR on "chose Postgres over MongoDB" with context + factual accuracy + judge ≥7

**Refactor / Review (3 tasks)**
- `rev_01_find_bugs_in_diff` — Find bugs in 5 PR diffs (each 1-3 bugs of varying severity): recall, precision, severity F1
- `ref_01_solid_refactor` — Refactor 200-line God-function per SOLID, preserve all tests, no API change, CC decreases
- `ref_02_n_plus_one_orm` — Mitigate N+1 query in ORM code, preserve contract, query count −50%, type-safe

**Total**: 20 tasks = 3 done + **17 to author**.

**Authoring deliverables per task** (all 17):
1. `evals/task-packs/<slug>/task.yaml` — slug, version, category, difficulty, language, prompt_ref, gold_ref, evaluator_ref, weight_components (≥3 numerical metrics per scoring.md)
2. `evals/task-packs/<slug>/prompt.md` — task description + input examples + acceptance criteria
3. `evals/task-packs/<slug>/gold/` — reference solution (own-authored MIT OR sourced with attribution to SWE-Lancer / DevBench / BigCodeBench), ≤200 LOC
4. `evals/task-packs/<slug>/evaluator/` — vitest config (TS) / pytest config (Python) / SQL probe script (DB) / Trivy + actionlint wrapper (Ops) / judge rubric JSON (Docs) — sufficient for Phase 2D `EvaluatorRunner` integration

**Prioritization** (per R-1 mitigation, to manage 136h authoring budget):
- **Wave 1 (highest impact, 7 tasks, ~56h)**: `be_02`, `be_03`, `tst_01`, `tst_02`, `doc_02`, `rev_01`, `ref_01` — these exercise the broadest Phase 2D evaluator set (vitest, c8, mutation testing, judge rubric, lint, complexity) and cover the categories most likely to differentiate models.
- **Wave 2 (medium impact, 6 tasks, ~48h)**: `be_04`, `fe_02`, `fe_03`, `db_01`, `db_02`, `ref_02` — fill BE/FE/DB depth, exercise N+1 and query-plan checks.
- **Wave 3 (longest authoring time, 4 tasks, ~32h)**: `fs_01`, `fs_02`, `ops_01`, `ops_02` — fullstack and devops require sandbox + harness setup; lowest unique signal per hour. Acceptable to defer to PRD-006a if R-1 materializes.

### Out of Scope

- **Real evaluator implementation** (vitest in sandbox with npm install, c8 coverage, mutation testing wiring, Trivy scan integration) — this is **Phase 2D Slice 2** scope (per NOTE-005 Section F step 6). PRD-006 authors the **inputs** (gold + evaluator config); Slice 2 wires the **execution**.
- **Task versioning workflow** (slug + version bumping policy) — already covered in SPEC-001 TaskPin + `docs/02-methodology/task-lifecycle.md`. PRD-006 uses `version: 1.0.0` baseline for all 17 new tasks.
- **Multilingual task descriptions** — English only v0.1 per CLAUDE.md Non-goals.
- **SWE-Lancer / DevBench batch import automation** — manual cherry-picking of ~5-7 tasks (30-40% of catalog) with attribution; full automated import deferred to v0.2.
- **Hire freelancers for gold authoring** — deferred to v0.2 if R-1 schedule slip materializes (NOTE-005 Section M open Q).
- **Held-out 20% private holdout set** — anti-gaming program (NOTE-005 Section I gap) is separate scope (NOTE-007 future). PRD-006 produces 20 public tasks; holdout rotation policy is downstream.
- **`/propose-task` community submission flow** — NOTE-005 Section K + future RFC-003 scope.
- **9-metric reweighted formula adoption** (NOTE-004 Section 5 v0.2 proposal) — methodology change requires separate ADR. PRD-006 produces tasks compatible with **current** scoring.md v0.1.0 weights; extended metrics live in `weight_components` as optional fields.

### Growth Vision

- **v0.1 (this PRD)**: 20 tasks, public, MIT/sourced. Smoke runs and weekly cron operate on this set.
- **v0.2**: +5-10 tasks from SWE-Lancer batch import; first holdout rotation (4 tasks moved to private set, 4 new tasks added to public).
- **v0.3**: community-proposed tasks via `/propose-task`; ad-hoc difficulty re-balancing based on per-task model variance.
- **v1.0**: 40+ task catalog with monthly rotation; multilingual subset (English + 1-2 additional).

---

## Functional Requirements

| ID | Category | Priority | Requirement | Journey |
|----|----------|----------|-------------|---------|
| FR-001 | Content | Must | Maintainer can find authored `task.yaml + prompt.md + gold/ + evaluator/` for each of 17 new task slugs under `evals/task-packs/<slug>/` | Journey 1 |
| FR-002 | Schema | Must | Each new `task.yaml` validates against the task-pack JSON Schema (same schema as existing 3) | Journey 1 |
| FR-003 | Metrics | Must | Each `task.yaml` declares `weight_components` with at least 3 numerical metric keys mapped to scoring.md formulas (correctness + ≥2 others appropriate for category) | Journey 1 |
| FR-004 | Provenance | Must | Each sourced gold solution carries `LICENSE.md` + `ATTRIBUTION.md` in its `gold/` directory with origin URL, original license, and adaptation notes | Journey 1 |
| FR-005 | Language policy | Must | Per `task.yaml: language:` field: `be_*` + `fe_*` + `fs_*` + `tst_*` use `typescript`; `ops_*` uses `python` (Docker tooling) OR `bash` (workflow YAML); `db_*` uses `sql` + optional `python` (psql probes); `doc_*` + `rev_*` + `ref_*` per task | Journey 1 |
| FR-006 | Evaluator config | Must | Each task's `evaluator/` contains a runnable config (vitest.config.ts / pytest.ini / sql probe / etc.) consumable by Phase 2D `EvaluatorRunner` — full execution wiring is out of scope, but the config must be syntactically valid for its tool | Journey 1 |
| FR-007 | Wave prioritization | Should | Maintainer can author tasks in 3 waves (7 + 6 + 4) with explicit dependency markers; Wave 1 tasks reference no later-wave gold solutions | Journey 1 |
| FR-008 | Smoke validation | Must | After all 20 tasks land, maintainer can trigger 1 smoke run covering ≥10 new tasks via the orchestrator (PRD-001 pattern) and the manifest validates | Journey 2 |
| FR-009 | Sourced attribution audit | Should | A `make audit-task-licenses` target (or equivalent script in `infra/scripts/`) confirms every sourced task carries valid LICENSE + ATTRIBUTION and reports any orphans | Journey 2 |
| FR-010 | Progressive landing | Should | Tasks can land individually as separate PRs (one per task or one per wave) without blocking other tasks; `make validate-tasks` partial PASS is informative, not blocking | Journey 1 |

---

## Non-Functional Requirements

| ID | Category | Requirement | Metric | Condition | Measurement |
|----|----------|-------------|--------|-----------|-------------|
| NFR-001 | Performance | Each task evaluation completes within wall-clock budget | ≤ 5 minutes wall-clock | per (model, task, seed) on weakest model in lineup | orchestrator timeout enforcement; per-task documented `expected_runtime_seconds` in `task.yaml` |
| NFR-002 | Gold size | Gold solution stays compact and reviewable | ≤ 200 LOC per gold/ directory | per task | `find evals/task-packs/<slug>/gold -type f \( -name '*.ts' -o -name '*.py' -o -name '*.sql' \) -exec wc -l {} +` |
| NFR-003 | Author budget | Per-task authoring time fits sustainable solo schedule | ≤ 8 hours per task (author + self-review + initial fixture) | sustained across all 17 | author journal entry per task; aggregate over wave check-points |
| NFR-004 | License compatibility | All gold solutions usable in MIT-licensed catalog | License compatible with MIT redistribution | per task (own → MIT; sourced → MIT/Apache-2/BSD with attribution) | `audit-task-licenses` script; manual review per sourced task |
| NFR-005 | Determinism (downstream) | Tasks must permit deterministic re-execution of evaluator on cached output (ADR-002 compatibility) | task evaluator script accepts cached raw_output and produces byte-equal evaluator_json on deterministic fields | per task | PRD-001 SC-2 reproducer must work on each new task once Phase 2D Slice 2 lands |
| NFR-006 | Scoring-formula compatibility | Each task's `weight_components` map onto frozen scoring.md v0.1.0 formulas without method change | weights sum to 1.0 ± 0.001; keys subset of scoring.md vocabulary | per task | `validate-task-specs.py` extension or manual review at PR time |

---

## User Journeys

### Journey 1: Maintainer authors a single task (e.g., `be_02_rest_post_users`)

**Цель**: за один sustained focus session добавить одну задачу с минимальным rework loop.

| Шаг | Действие пользователя | Ответ системы | FR coverage |
|-----|-----------------------|---------------|-------------|
| 1 | Reads dd.md row for `be_02` + scoring.md formula for backend tasks | static docs | — |
| 2 | Creates `evals/task-packs/be_02_rest_post_users/{task.yaml, prompt.md, gold/, evaluator/}` | filesystem ready | FR-001 |
| 3 | Writes `task.yaml` with `slug`, `version: 1.0.0`, `language: typescript`, `weight_components: {correctness: 0.4, type_safety: 0.2, lint: 0.2, coverage: 0.2}` | maintainer-authored | FR-002, FR-003, FR-005 |
| 4 | Writes `prompt.md` with API contract + Zod schema requirement + dedup logic + RFC 7807 error format examples | maintainer-authored | FR-001 |
| 5 | Authors gold solution (own, ≤200 LOC) OR cherry-picks from SWE-Lancer subset + adds `LICENSE.md` + `ATTRIBUTION.md` | maintainer-authored | FR-004, NFR-002, NFR-004 |
| 6 | Writes evaluator config (`vitest.config.ts` + happy-path + edge-case test file) | maintainer-authored | FR-006 |
| 7 | Runs `make validate-tasks` | exit 0 OR specific schema errors | FR-002 |
| 8 | Opens PR with `Refs: prd-tasks-catalog-expansion-v0-1-phase-1-20-task-roadmap, be_02` | landed independently | FR-010 |

**Результат**: one task added; CI green; PR mergeable without blocking other tasks.

### Journey 2: Maintainer validates the full catalog post Wave-3 landing

**Цель**: подтвердить SC-1..SC-6 одним sweep.

| Шаг | Действие | Ответ системы | FR coverage |
|-----|----------|---------------|-------------|
| 1 | `find evals/task-packs -name task.yaml \| wc -l` | reports 20 | SC-1 |
| 2 | `make validate-tasks` | exit 0 for all 20 | SC-3, FR-002 |
| 3 | `make audit-task-licenses` (or equivalent inline script) | reports 0 unattributed sourced tasks | SC-4, FR-009 |
| 4 | Inspects `task.yaml` `weight_components` counts | each ≥3 | SC-2, FR-003 |
| 5 | Triggers 1 smoke run on ≥10 new tasks (PRD-001 pattern) | manifest published with new task slugs | SC-6, FR-008 |
| 6 | Reads aggregate stats | confirms per-category coverage matches dd.md table | — |

**Результат**: PRD-006 ready for `activate` after EVID linked.

---

## Dependencies

| Dependency | Type | Status | Owner |
|-----------|------|--------|-------|
| Task-pack JSON Schema in `packages/contracts/` | Internal | exists (3 tasks validate) — verify compatibility for new categories (db, ops, review) | maintainer |
| `make validate-tasks` script | Internal | exists; may need extensions for SQL probe / actionlint / Trivy validation hooks | maintainer |
| `scoring.md` v0.1.0 frozen formulas | Internal | ✅ Done | — |
| `task-lifecycle.md` (slug + version policy) | Internal | ✅ Done | — |
| Phase 2D Slice 1 evaluators (lint / complexity / secret_scan) | Internal | partial (per NOTE-005 Section F step 6); not blocking for **authoring** tasks, but blocking for SC-6 smoke if evaluators not wired | maintainer |
| Phase 2D Slice 2 (vitest + c8 + sandbox) | Internal | not done; **not blocking PRD-006** — PRD-006 produces task definitions; Slice 2 consumes them | maintainer |
| SWE-Lancer / DevBench / BigCodeBench source corpora | External | publicly available; license review per task at cherry-pick time | maintainer |
| Author time budget (~136h across 17 tasks, 3 waves) | Resource | solo maintainer; primary R-1 risk | maintainer |

---

## Related Artifacts

| Artifact | Relation | Why |
|----------|----------|-----|
| PRD-001 | informs | smoke run pattern + manifest format reused for SC-6 validation |
| NOTE-005 | refines | closes Section D 17-task gap explicitly |
| NOTE-004 | informs | Section 5 extended metrics inform `weight_components` choices and Phase 2D consumption |
| ADR-003 | informs (transitively) | 5-model lineup; this PRD enables full 14×20 radar once ADR-006 expands to 14 models |
| ADR-006 (if/when authored) | informs (future) | full 14-model adoption requires 20-task content from this PRD to produce honest grid |
| SPEC-001 | informs | TaskPin contract + version semantics |
| EPIC-001 | parent (implicit) | POLLMEVALS v0.1 content vision |
| `docs/02-methodology/scoring.md` (frozen v0.1.0) | informs | source for `weight_components` keys |
| `docs/02-methodology/task-lifecycle.md` (frozen v0.1.0) | informs | slug + version semantics |
| `docs/04-runbook/04-task-authoring-guide.md` | informs | per-task authoring contract |
| `docs/old/dd.md` lines 974-997 + 1227-1300 | seed source | the 20-task list verbatim |

---

## Risks & Mitigations

| ID | Risk | Probability | Impact | Mitigation | Owner |
|----|------|-------------|--------|------------|-------|
| R-1 | Authoring 17 tasks = ~136h solo work → schedule slip past v0.1 target | High | High | Wave prioritization (7 + 6 + 4); Wave 1 alone unlocks meaningful 14×10×3=420-eval baseline; Waves 2-3 may slip to PRD-006a if needed | maintainer |
| R-2 | TypeScript bias in catalog (BE+FE+FS+Tests all TS) under-samples Python/SQL model strengths | Medium | Medium | Explicit `ops_*` Python allocation + `db_*` SQL allocation; documented allocation in SC-5 measurement criterion; future v0.2 can add Python-heavy tasks | maintainer |
| R-3 | Gold solutions biased toward solo author style → favors models trained on similar style | Medium | Medium | Target 30-40% sourced (SWE-Lancer / DevBench / BigCodeBench) with attribution; own gold reviewed against external style guides (Airbnb TS, PEP 8); judge panel diversification (PRD-002) provides downstream check | maintainer |
| R-4 | Phase 2D evaluator wiring (Slice 2) not ready when tasks land → SC-6 smoke blocked | Medium | Medium | Decoupled: PRD-006 authors **inputs**, Slice 2 wires **execution**. SC-6 explicitly requires smoke run; if Slice 2 not ready, SC-6 satisfied via narrower smoke covering Slice 1-compatible categories (docs, review) plus PRD-001-pattern raw evaluator | maintainer |
| R-5 | Sourced tasks (SWE-Lancer etc.) have license incompatible with MIT redistribution | Low | High | License audit per cherry-pick (FR-004 + FR-009); reject + author own if incompatible; SWE-Lancer + DevBench + BigCodeBench documented MIT-friendly per NOTE-004 Section 7 source notes | maintainer |
| R-6 | `task.yaml` schema does not support new categories (db / ops / review) without changes | Low | Medium | First task per new category (db_01, ops_01, rev_01) authored first to probe schema; schema extension PR (if needed) lands before bulk authoring | maintainer |
| R-7 | NFR-002 (≤200 LOC gold) too tight for fullstack tasks (fs_01, fs_02) | Low | Low | Fullstack gold may legitimately exceed 200 LOC across multiple files; NFR-002 measured per-file with cumulative `≤ 400 LOC` budget for fullstack; documented per-task exception in `task.yaml: gold_loc_budget:` field | maintainer |

---

## Affected Files

- `evals/task-packs/be_02_rest_post_users/` — NEW
- `evals/task-packs/be_03_webhook_hmac/` — NEW
- `evals/task-packs/be_04_cursor_pagination/` — NEW
- `evals/task-packs/fe_02_debounced_search/` — NEW
- `evals/task-packs/fe_03_dnd_kanban/` — NEW
- `evals/task-packs/fs_01_feature_flag/` — NEW
- `evals/task-packs/fs_02_resumable_upload/` — NEW
- `evals/task-packs/db_01_zero_downtime_migration/` — NEW
- `evals/task-packs/db_02_query_optimization/` — NEW
- `evals/task-packs/ops_01_multistage_dockerfile/` — NEW
- `evals/task-packs/ops_02_github_actions_workflow/` — NEW
- `evals/task-packs/tst_01_legacy_function_tests/` — NEW
- `evals/task-packs/tst_02_testcontainers_integration/` — NEW
- `evals/task-packs/doc_02_adr_postgres_vs_mongodb/` — NEW
- `evals/task-packs/rev_01_find_bugs_in_diff/` — NEW
- `evals/task-packs/ref_01_solid_refactor/` — NEW
- `evals/task-packs/ref_02_n_plus_one_orm/` — NEW
- `infra/scripts/validate-task-specs.py` — may extend for new categories (db/ops/review category-specific checks)
- `infra/scripts/audit-task-licenses.{sh,py}` — NEW (FR-009)
- `Makefile` — add `audit-task-licenses` target
- `docs/04-runbook/04-task-authoring-guide.md` — may extend with sourced-task attribution recipe

---

## Acceptance Criteria

- AC-1: 17 new `task.yaml` files committed under `evals/task-packs/<slug>/task.yaml` (SC-1).
- AC-2: 17 new `prompt.md` files with task description + input examples + acceptance criteria.
- AC-3: 17 new `gold/` directories with reference solutions (own MIT OR sourced with `LICENSE.md` + `ATTRIBUTION.md`).
- AC-4: 17 new `evaluator/` directories with runnable configs (vitest / pytest / SQL probe / etc.) syntactically valid for their tool.
- AC-5: `make validate-tasks` exit 0 on all 20 tasks (SC-3).
- AC-6: `make audit-task-licenses` reports 0 unattributed sourced tasks (SC-4).
- AC-7: At least 1 smoke run completed using ≥10 new tasks; manifest published per PRD-001 manifest format (SC-6).

---

> **Next step**: validate PRD-006 → guardian review → spawn Wave 1 authoring (7 tasks) → land first task `be_02_rest_post_users` as canary → adjust schema if needed → bulk-author Wave 1 remainder → EVID against SC-1..SC-3 → repeat for Waves 2 + 3.










