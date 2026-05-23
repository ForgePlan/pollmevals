---
depth: standard
id: PRD-004
kind: prd
last_modified_at: 2026-05-23T21:16:45.998145+00:00
last_modified_by: claude-code/2.1.150
links:
- target: EPIC-001
  relation: based_on
status: draft
title: public leaderboard MVP — Pareto frontier visualization
---

# PRD-004: public leaderboard MVP — Pareto frontier visualization

> **STATUS: STUB** — full requirements развернутся в Phase 4 (T+5..T+6 weeks). Сейчас фиксирована scope-граница.

## Problem

После того как cadence (PRD-003) даст 1+ публикуемый weekly run, нужен **публичный канал** показа результатов. JSON-fixtures в `data/` и manifest в R2 — для maintainer'а; рынку нужен сайт с visualisation и честной cost-vs-quality картинкой.

**Impact**: без leaderboard не реализуется EPIC outcome #3 (public evidence visible). Vendor-команды и production-tech-leads не смогут потреблять данные → POLLMEVALS становится internal tool.

## Goals

| ID | Criterion | Target |
|----|-----------|--------|
| SC-1 | Leaderboard публично доступен | pollmevals.com отдаёт статический Next.js bundle |
| SC-2 | Pareto frontier визуализирован | per-task scatter chart cost-vs-quality + frontier line |
| SC-3 | Per-stack scoring визуализирован | breakdown по моделям внутри каждого stack'а |
| SC-4 | Drift alerts visible | публичный banner если последний run триггерил drift (PRD-003 SC-3) |

## Target Users

| Персона | Описание | Боль |
|---------|----------|------|
| Production tech lead | Выбирает model+stack для production deployment | HELM/MTEB/SWE-bench не показывают cost-vs-quality для целых стеков — каждая платформа покрывает только часть |
| Vendor team (Anthropic, OpenAI, …) | Хочет видеть, как их модель сравнивается на разных стеках | Vendor self-reports не верифицируемы (MTEB honor model gap per EVID-002) |
| Methodology reviewer | Внешний рецензент перед v1.0 | Нужны public artifacts для критики, не closed dashboards |

## Product Scope

### In Scope
- Статический Next.js 15 (App Router) сайт в `apps/site/`
- Источник данных: JSON manifest из R2 (read-only, cached at build time)
- Визуализация: per-task scatter chart cost-vs-quality + frontier line (chart library — выбор в Deep версии)
- Per-task drill-down: щелчок на dot → details page с calibration + judge breakdown
- Cost column **обязательно** (заполняет gap, который HELM и SWE-bench оставили — см. EVID-001, EVID-005)
- "Methodology version" pinned в footer (frozen v0.1.0)
- Без backend: SSG, deploy через статический хостинг (выбор провайдера — Deep версия)

### Out of Scope
- Submission UI (только PR workflow, см. PRD-005)
- User accounts / comments / voting
- Realtime data (rebuild on weekly cron)
- Mobile app
- Cross-run trend lines (пока только last vs predecessor — drift alert)

## Functional Requirements (high-level)

| ID | Requirement | Used by Journey/SC |
|----|-------------|-------------------|
| FR-001 | Visitor can see per-stack scores from latest published weekly run | SC-1, SC-3 |
| FR-002 | Visitor can see Pareto frontier (cost-vs-quality) per task family | SC-2 |
| FR-003 | Visitor can drill down from a leaderboard row to per-eval calibration + judge breakdown | SC-2 |
| FR-004 | Visitor can see methodology version pin in footer of every page | SC-1 |

## Non-Functional Requirements

| ID | Category | Target |
|----|----------|--------|
| NFR-001 | Page load | LCP ≤ 2s on 4G p95 |
| NFR-002 | Build time | full SSG rebuild ≤ 3 min |
| NFR-003 | Accessibility | WCAG AA on all data visualisations |

## Dependencies

- PRD-001, PRD-002, PRD-003 must be active
- Static hosting account + object storage (provider choice in Deep version)
- Domain `pollmevals.com` (purchase confirm — отдельный TODO)
- Design system tokens (минимальный Tailwind в MVP)

## Related Artifacts

- EPIC-001 (parent)
- PRD-001, PRD-002, PRD-003 (predecessors)
- EVID-001 (HELM lacks per-eval cost), EVID-005 (SWE-bench lacks per-instance cost) — POLLMEVALS закрывает этот gap
- EVID-002 (MTEB honor model gap) — informs vendor-verification stance

> **Next step (Phase 4, T+5 weeks)**: углубить — выбрать chart library, решить routing schema, design system tokens, hosting provider.

