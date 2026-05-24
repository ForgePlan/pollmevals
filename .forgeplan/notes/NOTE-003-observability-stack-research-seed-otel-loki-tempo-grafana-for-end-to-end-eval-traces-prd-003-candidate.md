---
depth: standard
id: NOTE-003
kind: note
last_modified_at: 2026-05-24T08:57:50.057401+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-003
  relation: informs
- target: PRD-004
  relation: informs
status: active
title: Observability stack research seed — OTEL + Loki + Tempo + Grafana for end-to-end eval traces (PRD-003+ candidate)
---

# NOTE-003: Observability stack research seed — OTEL + Loki + Tempo + Grafana for end-to-end eval traces

## Context

**Captured 2026-05-24** from user direction during Phase 2B bootstrap:

> «так как у нас litellm будет занимать проксирование и ещё где-то то нам нужно строить OTEL + Loki + Drill down + Grafana stack чтобы видеть что и сколько занимало времени и т.д. чтобы потом отчёт строить нормальный и видеть — стоимость / время (и где что сколько занимало) и т.д.»

This Note captures the idea as **research seed** for later promotion to ADR-005 (or merging into PRD-003 design). Not yet a decision — need (a) iteration on stack choice, (b) integration plan with LiteLLM proxy + MoleculerPy (ADR-004) + Inspect AI (EVID-004).

## Why this matters for POLLMEVALS

End-to-end eval has multiple stages where time + cost accumulate:

```
make smoke-run
    ↓
GridRunner (Wave 5)                       ← scheduler latency
    ↓
EvalCaller Protocol (Wave 4)              ← Protocol overhead (~ms)
    ↓
LiteLLM proxy (Phase 2B+, port 4000)      ← proxy routing + failover (~10-50ms)
    ↓
Backend provider (OpenRouter / HF / Cerebras direct)  ← network + provider latency
    ↓
Provider's underlying model serving (GPU)  ← model inference (dominant cost)
    ↓
Response → cost.py (cost computation)     ← Decimal precision attribution
    ↓
JournalWriter (Wave 3, NDJSON fsync)      ← write durability
    ↓
ManifestWriter (Wave 3, atomic rename)    ← final commit (only at aggregating→published)
```

Without observability stack: cannot answer questions like:
- "Why does eval_id=X take 4× longer than eval_id=Y for the same model+task?"
- "How much of total runtime is LiteLLM proxy overhead vs actual inference?"
- "When budget breach happens, where was time wasted before abort?"
- "Per-stack (raw-llm vs claude-code-basic) breakdown of latency tails?"

These are critical for PRD-003 weekly cadence + PRD-004 leaderboard (cost-vs-quality Pareto plots NEED reliable latency data).

## Candidate stack (user-proposed)

| Component | Purpose | Why Grafana Labs (LGTM) |
|---|---|---|
| **OpenTelemetry collector** | Vendor-neutral instrumentation standard (traces + metrics + logs) | Open standard — LiteLLM proxy + MoleculerPy + Inspect AI all support OTEL export natively |
| **Loki** | Log aggregation (label-indexed, like Prometheus but for logs) | Lightweight; works well with K8s; same query language family as PromQL |
| **Tempo** | Distributed tracing backend (OTEL-compatible) | Stores traces; Grafana-native visualisation; supports trace-to-log correlation |
| **Mimir** or **Prometheus** | Metrics storage | Long-term retention (Mimir) or simpler (Prometheus) |
| **Grafana** | Visualisation + dashboards + drill-down | Unified UI for traces+logs+metrics; trace → log correlation via shared trace_id |
| Optional: **Pyroscope** | Continuous profiling | If we need per-function CPU/memory profiling under load |

## Hypotheses (for future ADR-005)

### Abduction — 3 hypotheses about observability scope/stack

- **H1**: SaaS observability (Datadog / New Relic / Honeycomb) — easier setup, paid per-seat + ingestion; trades $$ for time.
- **H2**: Self-hosted **LGTM** (Loki+Grafana+Tempo+Mimir) per user proposal — open-source, full control, no per-eval ingestion cost, but requires ops effort (Docker compose or K8s).
- **H3**: Minimal — log to files + per-eval timing in manifest's `RunAggregates.per_task_metrics` already; no separate stack until PRD-003 weekly cadence proves we need fancier drill-down.

### Deduction (what each would observe)

| Hypothesis | What we'd see | When pain emerges |
|---|---|---|
| H1 (SaaS) | Full traces in vendor UI; correlation via trace_id; alerting; $50-500/month for our scale | Vendor lock-in; ingestion costs at PRD-003 weekly scale (~1000 evals × multiple spans each) |
| H2 (LGTM self-hosted) | Same as H1 functionally; full control; ~1 person-day setup + ongoing maintenance | Maintenance burden; setup time |
| H3 (minimal) | Manifest-level aggregates only; no per-stage breakdown | First time we ask "why is X slow", no answer |

### Induction (where evidence pulls us)

- LiteLLM proxy **already supports OTEL export** (per LiteLLM docs) — H1 + H2 both leverage this; H3 wastes it.
- MoleculerPy **already supports Jaeger/Zipkin** built-in (per EVID-004 + ADR-004) — H1 + H2 capture this; H3 ignores it.
- Inspect AI has tracing primitives (per EVID-004).
- POLLMEVALS thesis = **transparency** ("open evidence layer") — observability traces support transparency claim (third parties can audit our cost+time data).
- User-as-MoleculerPy-owner pattern (per EVID-018 ownership uplift) suggests **self-hosted is fine** if maintainer is comfortable with Docker + YAML.

**Tentative leaning**: H2 (LGTM self-hosted) — aligns with infra discipline (Docker compose pattern same as LiteLLM proxy), open-source thesis, no vendor lock-in. But H1 is reasonable if maintenance burden becomes a problem. Final decision in ADR-005 when written.

## Trust Calculus (very preliminary — note not evidence)

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| LiteLLM has built-in OTEL export | 7 | 7 | 7 | 21/27 | F: stated. G: stated. R: LiteLLM docs not yet directly inspected. Verify before ADR-005. |
| MoleculerPy supports Jaeger/Zipkin out of box | 7 | 7 | 8 | 22/27 | F: stated. G: stated. R: Moleculer.js docs confirmed (per EVID-004); MoleculerPy parity assumed but not verified. Verify in Phase 3 first integration. |
| Self-hosted LGTM ~1 person-day initial setup | 6 | 6 | 6 | 18/27 | F: rough estimate. G: range, not specific. R: industry hearsay. Concrete setup will calibrate. |

These claims will be sharpened in ADR-005.

## Integration touchpoints (where instrumentation lands)

1. **LiteLLM proxy** (Docker, Phase 2B+) — enable OTEL exporter via env var; points to OTEL collector
2. **POLLMEVALS orchestrator** (`apps/eval-core-py/src/orchestrator/`) — add `opentelemetry-api` + `opentelemetry-sdk` deps; instrument `GridRunner._run_single` (span per eval), `JournalWriter.append` (span per write), `CostReconciler.reconcile_with_litellm` (span per reconcile)
3. **MoleculerPy services** (Phase 3+ per ADR-004) — enable built-in Jaeger/Zipkin → routed to OTEL collector
4. **Inspect AI calls** — wrap via OTEL span context propagation
5. **Manifest** — add `trace_id` to each EvalRow → leaderboard can deep-link to Grafana trace view

## Next steps

1. (Now) Pin this Note in `.forgeplan/notes/`; commit + push.
2. (When user back) Iterate on H1/H2/H3 choice; verify H2 claims (LiteLLM OTEL export, MoleculerPy Jaeger).
3. (Phase 2B/2C) If user picks H2, draft ADR-005 "Observability stack: OTEL + LGTM for end-to-end eval traces" via `forgeplan_new adr` + NOTE-002 standard.
4. (Phase 2B/2C) Add `infra/docker-compose.observability.yml` (separate from litellm compose) — OTEL collector + Loki + Tempo + Grafana with seeded dashboards.
5. (Phase 2C) Instrument orchestrator with OTEL spans; verify trace appears in Tempo.
6. (Phase 4 PRD-004) Leaderboard rows link to Grafana trace for deep-dive (one of the differentiators vs HELM/MTEB).

## Related Artifacts

- PRD-003 (weekly cadence — needs observability for cost/time alerting)
- PRD-004 (leaderboard — needs per-eval trace links per user direction)
- ADR-004 (MoleculerPy adoption — built-in tracing primitives factor into stack choice)
- EVID-004 (Inspect AI — tracing primitives noted but not yet wired into POLLMEVALS)
- EVID-018 (MoleculerPy capability audit — Jaeger/Zipkin support claimed)
- EVID-019 (OpenRouter smoke — already measures latency per call; first POLLMEVALS measurement data, baseline for future drill-down)
- LiteLLM proxy (infra/docker-compose.litellm.yml) — instrumentation target
- NOTE-002 (Evidence Quality Standard — informs how observability data will be reported in future EVIDs)
- Future ADR-005 (this Note's graduation target)




