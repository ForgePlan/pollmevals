---
depth: standard
id: PRD-002
kind: prd
last_modified_at: 2026-05-23T19:17:30.904287+00:00
last_modified_by: claude-code/2.1.150
links:
- target: EPIC-001
  relation: based_on
status: active
title: judge panel layer — methodology + scoring infrastructure
---

# PRD-002: judge panel layer — methodology + scoring infrastructure

> **STATUS: STUB** — full requirements развернутся в Phase 3 (T+2..T+4 weeks). Сейчас фиксирована scope-граница и outcome.

## Problem

После того как smoke run (PRD-001) докажет работоспособность пайплайна на automatic metrics only, без judge-слоя нельзя ни (а) сравнивать качество subjective-выходов (frontend UX, docs clarity), ни (б) опубликовать leaderboard, потому что v0.1.0 frozen methodology требует median по ≥3 судьям.

**Impact**: без PRD-002 проект застрянет на smoke-уровне — leaderboard не имеет смысла без judge-scoring; weekly cadence (PRD-003) технически возможна, но публиковать нечего.

## Goals

| ID | Criterion | Target |
|----|-----------|--------|
| SC-1 | Krippendorff α на judge-panel | ≥ 0.70 на калибровочной выборке |
| SC-2 | Self-judging incidents | 0 (judge никогда не оценивает свою модель) |
| SC-3 | Calibration MAD на known-score samples | ≤ 1.5 (на шкале 0-10) |
| SC-4 | Position-bias detection (model-ID probe accuracy) | ≤ 30% (judge не должен узнавать кандидата по стилю) |

## Target Users

| Персона | Описание | Боль |
|---------|----------|------|
| Maintainer | Готовится опубликовать первый weekly run | Нужны judge'ы поверх smoke, без которых публиковать нечего |
| Methodology reviewer (external) | Будет рецензировать перед v1.0 | Должен видеть calibration данные + α-метрику |

## Product Scope

### In Scope
- JudgePanel impl поверх Inspect AI's `multi_scorer(model_graded_qa(model=[...]))` (см. EVID-004)
- Median reducer (override Inspect's default mean — см. EVID-001, HELM использует mean, мы — median)
- Blind labels (judges не знают какой кандидат генерировал output)
- Anonymisation pipeline (стрипка signatures, greetings из output до judge call)
- Calibration suite: perfect/good/mediocre/poor/broken samples per task
- Per-judge metrics: MAD, rank correlation, length bias, self-enhancement bias

### Out of Scope
- Human judges (отложено до v2.0)
- Adaptive judge selection (пока fixed panel)
- Multi-language judges (English-only до v2.0)

## Functional Requirements (high-level — детализация в Deep version)

| ID | Requirement |
|----|-------------|
| FR-001 | Orchestrator can route eval output to N≥3 judges (different vendor families) |
| FR-002 | Orchestrator can refuse self-judging (judge_model_id ≠ candidate_model_id) |
| FR-003 | System can compute median score across panel + Krippendorff α |
| FR-004 | System can run calibration suite before production scoring and refuse to publish if MAD > 1.5 |

## Non-Functional Requirements (high-level)

| ID | Category | Target |
|----|----------|--------|
| NFR-001 | Cost | Judge calls ≤ 5× eval cost (3 judges × ~1.7× tokens, with budget breakpoint) |
| NFR-002 | Latency | Judge round ≤ 30s p95 per eval |

## Dependencies

- **PRD-001** (must be active first — judge panel runs on top of working smoke pipeline)
- **EVID-004** (Inspect AI prior art — `multi_scorer` pattern)
- **EVID-001** (HELM — divergence on mean vs median)
- `docs/02-methodology/judge-policy.md` — frozen v0.1.0 source of truth

## Related Artifacts

- EPIC-001 (parent — based_on link)
- PRD-001 (predecessor — informs)
- Future: SPEC-002 (judge panel contracts), RFC-002 (judge routing implementation), ADR-004 (median vs mean rationale)

> **Next step (Phase 3, T+2 weeks)**: углубить до Standard depth — fill out User Journeys, expand FRs, add Risks table, link EVID-001 + EVID-004 evidence.





