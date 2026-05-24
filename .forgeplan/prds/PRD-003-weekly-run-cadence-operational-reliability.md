---
depth: standard
id: PRD-003
kind: prd
last_modified_at: 2026-05-23T21:16:22.625081+00:00
last_modified_by: claude-code/2.1.150
links:
- target: EPIC-001
  relation: based_on
status: draft
title: weekly run cadence — operational reliability
---

# PRD-003: weekly run cadence — operational reliability

> **STATUS: STUB** — full requirements развернутся в Phase 4 (T+4..T+5 weeks). Сейчас фиксирована scope-граница.

## Problem

POLLMEVALS-thesis требует **публикуемого канала доказательств**, а не разового прогона. Без регулярной cadence сравнения «новая модель vs predecessor» становятся ручными и неконсистентными; drift в закрытых API-моделях (Claude, GPT, Gemini могут silently апдейтиться) уйдёт незамеченным; community-импакт упадёт.

**Impact**: leaderboard (PRD-004) без cadence = снимок во времени, не living evidence. EPIC outcome #1 (2 consecutive weekly runs) недостижим.

## Goals

| ID | Criterion | Target |
|----|-----------|--------|
| SC-1 | Cron-триггер работает | 4 недели подряд без missed runs |
| SC-2 | Failed eval не блокирует run | 100% failed evals сохранены с error_class |
| SC-3 | Drift detection | Δ > 2σ на baseline-задачах vs предыдущий run → public alert |
| SC-4 | Provider degradation handling | Manifest помечен `degraded` если < 3 моделей доступны, run всё равно публикуется |

## Target Users

| Персона | Описание | Боль |
|---------|----------|------|
| Maintainer | Следит за weekly cron, реагирует на drift alerts | Без cadence — каждый run ручной; drift в closed-API моделях уйдёт незамеченным |
| Methodology reviewer | Внешний рецензент перед v1.0 | Нужны 2+ публикуемых run'а для проверки stability метрик (EPIC outcome #1) |
| Production tech lead (downstream consumer) | Будет потреблять leaderboard (PRD-004) | Нужен честный baseline «новая модель vs previous week» |

## Product Scope

### In Scope
- Cron trigger: понедельник 03:00 UTC (cheapest off-peak для US providers)
- Retry policy: на rate limit → exponential backoff, на 5xx → 1 retry, на 4xx → fail-fast
- Provider health pre-flight (Шаг 4 из smoke playbook, расширено)
- Drift alerting через Δ baseline scores (per-task, per-model)
- Run manifest carries `methodology_version` pin (frozen v0.1.0 пока не изменена)
- GitHub Actions workflow `.github/workflows/eval-weekly.yml`

### Out of Scope
- On-demand runs триггер из API (это PRD-005 / v1.0)
- Per-task cadence (пока всё или ничего)
- Cross-region failover (eu-central only до v0.2)

## Functional Requirements (high-level)

| ID | Requirement | Used by Journey/SC |
|----|-------------|-------------------|
| FR-001 | Orchestrator can trigger weekly run via GitHub Actions cron | SC-1 |
| FR-002 | Orchestrator can store failed evals with error_class (network, rate_limit, 5xx, contract_violation) without dropping from denominator | SC-2 |
| FR-003 | System can compute per-task drift (this run vs last) and trigger alert if Δ > 2σ | SC-3 |
| FR-004 | System can mark run as `degraded` and still publish if 3 ≤ available_models < 5 | SC-4 |

## Non-Functional Requirements

| ID | Category | Target |
|----|----------|--------|
| NFR-001 | Run duration | ≤ 4 hours wall clock for full grid (45+ evals × 3-5 judges) |
| NFR-002 | Cost per weekly run | ≤ $200 (45 evals × ~$3 incl judges) |
| NFR-003 | Alert latency | drift detected → maintainer notified within 1 hour of run end |

## Dependencies

- **PRD-001 + PRD-002 must be active** (smoke + judges are prerequisites)
- GitHub Actions runners (free tier sufficient for cron)
- LiteLLM proxy stable
- Alert channel (Slack? Email? — decide in Deep version)

## Related Artifacts

- EPIC-001 (parent)
- PRD-001, PRD-002 (predecessors)
- EVID-003 (LM Harness — contamination still unresolved, our cadence must include monthly contamination probe)

> **Next step (Phase 4, T+4 weeks)**: углубить — decide alert channel, drift formula (Δ vs predecessor or rolling-window), backfill policy when a weekly run misses.



