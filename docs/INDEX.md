# docs/ — focused index

Карта документации POLLMEVALS. Корневой `INDEX.md` индексирует весь репозиторий; этот файл фокусируется только на `docs/`.

> **Не редактировать `.forgeplan/`** (red line CLAUDE.md). Documentation в этой папке (`docs/`) редактируется напрямую.

---

## Карта по слоям

```
docs/
├── 00-research/   ← оригинальное research (read-only архив, не править)
├── 01-vision/     ← executive vision + product requirements + business
├── 02-methodology/ ← FROZEN v0.1.0 — judge policy, scoring, sandbox
├── 03-architecture/ ← system architecture, stack decision, domain model
├── 04-runbook/    ← implementation plan + operations + playbooks
├── adr/           ← legacy ADRs (pre-forgeplan; новые → .forgeplan/adrs/)
├── agents/        ← per-project metadata, auto-loaded в CLAUDE.md
├── old/           ← старая research база (используется как seed для NOTE-004)
├── visuals/       ← HTML/SVG диаграммы
├── PROJECT_TREE.md
└── INDEX.md       ← этот файл
```

---

## 00-research/ — оригинальное research (read-only)

Архив research который был основой frozen methodology v0.1.0. Не редактировать.

| Файл | О чём |
|---|---|
| `00-MASTER.md` | свод |
| `01-problem-vision.md` | боль пользователей, UVP |
| `02-methodology.md` | таксономия L0-L8, panel of judges, 9 biases |
| `03-experiment-design.md` | **5-фазный factorial design (~470 прогонов)** — основа всей timeline |
| `04-infrastructure.md` | Inspect AI, LiteLLM, geo workers, cost estimate |
| `05-product-spec.md` | продуктовая спецификация |
| `06-site-architecture.md` | IA сайта, data model, eval pipeline |
| `07-onboarding-flows.md` | добавление модели/стека/задачи |
| `08-must-consider.md` | 20 критичных моментов |
| `09-business-model.md` | Tier 0→4 монетизация |
| `10-competitive-landscape.md` | карта рынка, конкуренты |
| `11-roadmap.md` | v0.0 → v2.0 |
| `12-next-steps.md` | Week 0 actions, open questions, decision log |
| `examples/` | inspect-task.yaml, litellm-config.yaml, scoring-formulas.md |

---

## 01-vision/

| Файл | Что внутри |
|---|---|
| `00-executive-vision.md` | "Phase 2 scaffolding ablation must be the first proof. How much does each layer L0 → L8 add?" |
| `01-product-requirements.md` | функциональные требования |
| `02-project-brief.md` | расширенный brief |
| `03-product-vision-detailed.md` | детальное видение |
| `04-business-and-roadmap.md` | монетизация + roadmap |

---

## 02-methodology/ — FROZEN v0.1.0 ⛔ не править без ADR

| Файл | Что внутри |
|---|---|
| `methodology.md` | манифест, L0-L8 ladder |
| `task-lifecycle.md` | 8 состояний задачи |
| `scoring.md` | **формулы по категориям** — coding (correctness + coverage + complexity + lint + type-safety + judge_pattern), docs, review |
| `judge-policy.md` | **правила судейства** — minimum α ≥ 0.70, calibration MAD ≤ 1.5, ID probe ≤ 30% |
| `stack-adapter-spec.md` | YAML контракт стека |
| `security-sandbox.md` | Docker/gVisor/Firecracker |
| `decisions/2026-05-23-hybrid-stack.md` | TS + Python hybrid |

**Изменения** требуют ADR (`.forgeplan/adrs/`) и нового MethodologyVersion. Существующие Runs остаются bound к их MethodologyVersion навсегда.

---

## 03-architecture/

| Файл | Что внутри |
|---|---|
| `00-architecture-overview.md` | Product plane + Eval plane |
| `01-stack-decision.md` | выбор стека |
| `02-domain-model.md` | Model/Stack/Task/Run/Eval/Judgment |
| `03-system-architecture-detailed.md` | детали |
| `04-stack-decision-detailed.md` | обоснование hybrid TS+Python |
| `05-domain-model-detailed.md` | связи сущностей |
| `06-repo-structure.md` | структура monorepo |

---

## 04-runbook/

| Файл | Что внутри |
|---|---|
| `00-implementation-plan.md` | Phase 0-5 codebase phases (НЕ research phases — см. NOTE-004 disambiguation) |
| `01-operational-runbook.md` | daily/weekly ops |
| `02-missing-pieces-checklist.md` | дыры P0/P1/P2 |
| `03-implementation-plan-detailed.md` | детали |
| `04-task-authoring-guide.md` | как писать задачи |
| `05-stack-adapter-guide.md` | как написать adapter |
| `06-run-manifest-and-artifacts.md` | формат manifest |
| `07-judge-panel.md` | судейство pipeline |
| `08-scoring-contract.md` | формулы |
| `09-sandbox-security.md` | Docker policy |
| `10-operations-runbook-detailed.md` | детали ops |
| `11-missing-pieces-checklist-detailed.md` | детали дыр |
| `12-first-smoke-run-playbook.md` | **playbook первого запуска** (steps 1-14) |
| `13-agent-handoff-brief.md` | миссия + non-negotiables |

---

## adr/ — legacy (новые ADR → `.forgeplan/adrs/`)

| Файл | Status |
|---|---|
| `0001-use-hybrid-stack.md` | Accepted |
| `0002-run-immutability.md` | Accepted |

---

## agents/ — auto-loaded в CLAUDE.md через @import

| Файл | Назначение |
|---|---|
| `issue-tracker.md` | какой tracker (Orchestra/Linear/Jira/GitHub Issues/local TODO) |
| `build-config.md` | как билдить и тестить |
| `paths.md` | где что лежит — версия краткая |
| `domain.md` | domain glossary краткая |

---

## old/ — старая research база

| Папка | Что внутри |
|---|---|
| `pollmevals-research 2/` | оригинальное исследование (00-MASTER.md, 03-experiment-design.md, 10-competitive-landscape.md и др.) — используется как **источник для NOTE-004 expanded vision** |

---

## visuals/

HTML/SVG диаграммы (radar, ablation bars, roadmap, competitive landscape, site IA).

---

## Где искать ответы

| Вопрос | Куда смотреть |
|---|---|
| Что мы строим и зачем | `docs/01-vision/00-executive-vision.md` |
| Какие правила оценки | `docs/02-methodology/scoring.md` + `judge-policy.md` |
| Какой формат manifest | `docs/04-runbook/06-run-manifest-and-artifacts.md` + `packages/contracts/schemas/run-manifest.schema.json` + `SPEC-001` |
| Как добавить задачу | `docs/04-runbook/04-task-authoring-guide.md` |
| Как добавить stack | `docs/04-runbook/05-stack-adapter-guide.md` + `docs/02-methodology/stack-adapter-spec.md` |
| Как воспроизвести run | `docs/04-runbook/06-run-manifest-and-artifacts.md` + `make reproduce HASH=...` |
| План фаз (research vs infra) | `forgeplan get NOTE-004` Section 6 (phase disambiguation table) |
| Полный каталог stacks/memory/tools/metrics | `forgeplan get NOTE-004` (canonical) |
| Архитектурные решения | `.forgeplan/adrs/ADR-001..005` (новые) + `docs/adr/` (legacy 0001-0002) |
| Active PRDs/RFCs | `forgeplan list status=active` |
| Текущие blockers/drafts | `forgeplan health` |

---

## Жизненный цикл документации

- **frozen v0.1.0** (`docs/02-methodology/`) → требует ADR для изменения, новые runs bound к версии
- **active runbook** (`docs/04-runbook/`) → редактируется по мере implementation
- **forgeplan artifacts** (`.forgeplan/`) → CLI/MCP only, версионируется через supersede/deprecate
- **research seed** (`docs/00-research/`, `docs/old/`) → read-only архив

---

## Что НЕ в docs/

| Кладётся | Где |
|---|---|
| Управляемые артефакты (PRD/RFC/ADR/Spec/Evidence/Note) | `.forgeplan/` через MCP |
| Code | `apps/`, `packages/` |
| Tests | `apps/*/tests/` |
| Task content (prompts + gold) | `evals/task-packs/<slug>/` |
| Stack YAMLs | `stacks/<slug>/stack.yaml` |
| Infra configs | `infra/` |
| Smoke run outputs | `artifacts/runs/sha256:<hash>/` (gitignored) |
| Secrets | `.env` (gitignored) |
| Memory | `~/.claude/projects/.../memory/` (auto-memory) + Hindsight MCP (long-term) |
