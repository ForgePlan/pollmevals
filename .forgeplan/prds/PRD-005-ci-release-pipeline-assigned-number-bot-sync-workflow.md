---
depth: standard
id: PRD-005
kind: prd
last_modified_at: 2026-05-23T21:17:09.305271+00:00
last_modified_by: claude-code/2.1.150
links:
- target: EPIC-001
  relation: based_on
status: draft
title: CI release pipeline — assigned_number bot + sync workflow
---

# PRD-005: CI release pipeline — assigned_number bot + sync workflow

> **STATUS: STUB** — discrete tactical items, развернутся параллельно с другими PRDs. Сейчас фиксирована scope-граница.

## Problem

Forgeplan-контракт требует, чтобы `assigned_number` для PRD/RFC/ADR назначался **CI-ботом при merge в default branch** (write-once, нельзя руками). Сейчас бот отсутствует — все merge'и пройдут без финализации номеров, и `prd-v0-1-smoke-evaluation-run` останется без display ID `PRD-001` в graph метаданных.

Дополнительно: release loop `release/v* → main` требует sync ветки `main → dev` (CLAUDE.md упоминает `chore/sync-main-to-dev` PR), который сейчас не автоматизирован.

**Impact**: без бота forgeplan-граф будет показывать `PRD-74?` навсегда (с маркером "predicted, not final"). Это технически валидно но визуально мусорно и блокирует чистый `Refs:` в коммитах после merge.

## Goals

| ID | Criterion | Target |
|----|-----------|--------|
| SC-1 | `assigned_number` бот установлен | работает на каждом merge PR с staged `.forgeplan/*` |
| SC-2 | Sync workflow автоматизирован | после `release/v* → main` merge открывается PR `chore/sync-main-to-dev` |
| SC-3 | Pre-commit hook (lefthook) интегрирован с CI | CI запускает те же проверки + дополнительно полный `moon ci` |

## Target Users

| Персона | Описание | Боль |
|---------|----------|------|
| Maintainer | Опирается на чистый `Refs:` в коммитах после merge | `PRD-74?` в metadata навсегда — мусорно, ломает graph display |
| Future contributor (post-public) | Создаёт PRs с forgeplan artifacts | Без бота — нужно вручную следить за номерами; ошибка ломает write-once contract |
| Release engineer (when team grows) | Управляет release branches и main↔dev sync | Без автоматики — ручной chore на каждый release |

## Product Scope

### In Scope
- GitHub Action `.github/workflows/assigned-number-bot.yml`: при merge в main с измёнными `.forgeplan/{prds,rfcs,adrs,specs,epics}/*.md` → присваивает `assigned_number` в frontmatter (если ещё `null`), commit'ит back в main
- GitHub Action `.github/workflows/sync-main-to-dev.yml`: при push в main, открывает PR `main → dev` если diverged
- Существующий `.github/workflows/ci.yml` уже работает — лишь добавить интеграцию с этими ботами
- Branch protection rules: main и dev требуют PR + CI green

### Out of Scope
- Auto-merge ботов (manual review required)
- Multi-repo sync (POLLMEVALS — single repo)
- Release notes generator (отдельная задача, v0.2)

## Functional Requirements

| ID | Requirement | Used by Journey/SC |
|----|-------------|-------------------|
| FR-001 | Bot can detect staged forgeplan artifacts with `assigned_number: null` in merge PR | SC-1 |
| FR-002 | Bot can write `assigned_number` (next free integer per kind) into frontmatter and commit | SC-1 |
| FR-003 | Bot can open `chore/sync-main-to-dev` PR after `release/v*` merge, with auto-generated changelog summary | SC-2 |
| FR-004 | CI workflow rejects PRs that modify `assigned_number` directly (write-once enforcement) | SC-1, SC-3 |

## Non-Functional Requirements

| ID | Category | Target |
|----|----------|--------|
| NFR-001 | Bot latency | ≤ 2 min from merge to assigned_number commit |
| NFR-002 | Idempotence | re-running bot on same PR has 0 effect (already-numbered artifacts skipped) |

## Dependencies

- GitHub repo создан + auth работает ✅ (unblocked 2026-05-24)
- `forgeplan` CLI должен поддерживать `--write-assigned-number` flag (verify or RFC)
- Existing `.github/workflows/ci.yml`

## Related Artifacts

- EPIC-001 (parent)
- Существующий `.github/workflows/ci.yml`, `lefthook.yml` (Phase 1 infrastructure)
- CLAUDE.md "Artifact IDs (slug + assigned number)" section — контракт write-once

> **Next step**: после v0.1 smoke run published — start Tactical depth implementation. Bot scripts малые (~50 строк bash + gh CLI).

