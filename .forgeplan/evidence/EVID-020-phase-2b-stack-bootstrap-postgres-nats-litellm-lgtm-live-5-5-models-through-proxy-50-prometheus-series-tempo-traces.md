---
depth: standard
id: EVID-020
kind: evidence
last_modified_at: 2026-05-24T09:25:59.230246+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: NOTE-003
  relation: informs
status: active
title: Phase 2B stack bootstrap — Postgres+NATS+LiteLLM+LGTM live; 5/5 models through proxy; 50 Prometheus series + Tempo traces
---

# EVID-020: Phase 2B stack bootstrap — Postgres+NATS+LiteLLM+LGTM live; 5/5 models through proxy; 50 Prometheus series + Tempo traces

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "is the full Phase 2B stack viable?")

- **H1**: LiteLLM proxy alone is enough — direct routing to OpenRouter/HF works; Postgres + observability are over-engineering for v0.1 smoke.
- **H2**: Full stack (Postgres + NATS + LiteLLM + LGTM observability) is needed — LiteLLM v latest mandates DB; observability gives end-to-end visibility per NOTE-003; NATS pre-positioned for PRD-003 MoleculerPy (ADR-004).
- **H3**: Cloud-managed (Datadog/Honeycomb) is faster path than self-hosted LGTM — trade $$ for ops effort.

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 (minimal) | LiteLLM without DB returns 200 on /chat/completions | Direct curl test |
| H2 (full stack) | All 5 ADR-003 models respond through proxy + Prometheus has LiteLLM metrics + Tempo has traces tagged `service.name=pollmevals-litellm` | `make litellm-smoke` + `curl /api/v1/label/__name__/values` on Prometheus + `curl /api/search` on Tempo |
| H3 (SaaS) | Setup time ~30min for Datadog vs ~2h for LGTM; ongoing cost $50-500/mo vs $0 self-hosted | Estimate; not directly measured |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (minimal works) | First attempt: LiteLLM without DATABASE_URL → `{"error":"no_db_connection"}` HTTP 400 on ALL chat completions; without `max_budget` and without `database_url` config keys still rejects. Current LiteLLM image is hard-coupled to Postgres. | False — H1 refuted by LiteLLM image behavior | **H1 REFUTED** |
| Y2 (full stack works) | After Postgres added: `make litellm-smoke` returns **5/5 models OK** through proxy with `db: connected`. Per-model latencies: claude=2377ms, gpt-5-mini=737ms, gemini-3-flash=867ms, qwen-3-14b=1991ms, llama-3-3-70b=2213ms. Total real cost $0.00017. After OTEL+Prometheus callbacks enabled: Prometheus has **50 litellm-prefixed metric series** scraped from /metrics (bearer-token auth); Tempo has traces with `rootServiceName: pollmevals-litellm` and `rootTraceName: litellm_request`. Grafana auto-provisioned with 3 datasources (Prometheus, Tempo, Loki). | All predictions held | **H2 SUPPORTED** |
| Y3 (SaaS path) | Not measured directly. Rejected on first-principles: POLLMEVALS thesis = open transparency; vendor lock-in conflicts with that. Self-hosted LGTM matches Docker-compose pattern already in use. User owns MoleculerPy (per EVID-018) → comfortable with self-hosted ops. | Acknowledged but rejected for POLLMEVALS scope | **H3 REJECTED** |

**Surviving hypothesis**: H2 — full self-hosted stack. Matches shipped 8-service deployment.

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| 5/5 ADR-003 models respond through LiteLLM proxy | 9 | 9 | 9 | 27/27 | F: explicit pass count. G: per-model latency + tokens + cost listed. R: reproducible `make litellm-smoke`. |
| qwen-3-14b routed through HF router (resolved Phase 2A carry-forward) | 9 | 9 | 9 | 27/27 | F: explicit. G: precise (HF router, no provider suffix, case-sensitive `Qwen/Qwen3-14B`). R: live measurement returned `backend=qwen-3-14b` with usage. |
| LiteLLM image requires Postgres (no DB → 400 on /chat/completions) | 9 | 9 | 9 | 27/27 | F: explicit HTTP 400 response. G: exact error code `no_db_connection`. R: reproducible via DATABASE_URL removal. |
| 8 Docker services healthy: postgres, nats, litellm-proxy, otel-collector, prometheus, tempo, loki, grafana | 9 | 9 | 9 | 27/27 | F: `docker ps` Status=Up. G: explicit per-service ports + names. R: `make stack-status` + `make obs-status` reproducible. |
| All Docker images pinned by SHA digest | 9 | 9 | 9 | 27/27 | F: explicit digest strings in compose files. G: each image has full sha256 prefix. R: `docker inspect` confirmed at pull time. |
| Prometheus scrapes LiteLLM /metrics with bearer-token auth | 9 | 9 | 9 | 27/27 | F: prometheus.yml `authorization.type=Bearer`. G: precise (job=litellm, target=litellm-proxy:4000, status=up). R: `/api/v1/targets?state=active` confirms. |
| 50 litellm-prefixed metric series exposed | 9 | 9 | 9 | 27/27 | F: API `label/__name__/values` enumeration. G: precise count. R: reproducible. |
| Tempo received traces with `pollmevals-litellm` service.name | 9 | 9 | 9 | 27/27 | F: API `/api/search` returned traces. G: explicit `rootServiceName` + `rootTraceName`. R: reproducible. |
| Grafana provisioned with 3 datasources (Prometheus, Tempo, Loki) | 9 | 9 | 9 | 27/27 | F: `/api/datasources` enumeration via admin auth. G: 3 named. R: reproducible. |
| OTEL collector exports both /metrics (port 8889) and traces (gRPC 4317) | 8 | 8 | 8 | 24/27 | F: config explicit. G: port mapping documented. R: confirmed via prometheus scrape target=`otel-pollmevals-metrics:up`. |
| Postgres LiteLLM DB initialized cleanly on `make stack-up` (after `docker volume rm` to wipe stale master_key hash) | 8 | 8 | 8 | 24/27 | F: stack-up sequence verified. G: precise (need wipe if changing LITELLM_MASTER_KEY). R: reproducible. |

**Decision strength**: average sum = 26.4/27 (98%). 9 claims at 27/27 (the load-bearing infrastructure facts). Weakest claims (24/27): OTEL collector port detail (collector self-metrics endpoint reported "down" — investigated, it's separate from the exporter port — non-blocking) and Postgres wipe requirement (operational gotcha worth documenting).

## Stack inventory (live snapshot 2026-05-24)

```
LiteLLM/data stack (infra/docker-compose.litellm.yml):
  pollmevals-postgres       Up 2m (healthy)   :5432
  pollmevals-nats           Up 2m (healthy)   :4222 :8222
  pollmevals-litellm-proxy  Up 2m (healthy)   :4000

Observability stack (infra/docker-compose.observability.yml):
  pollmevals-grafana          Up 4m   :3000
  pollmevals-otel-collector   Up 4m   :4317 :4318 :8888 :8889
  pollmevals-prometheus       Up 34s  :9090
  pollmevals-tempo            Up 4m   :3200
  pollmevals-loki             Up 4m   :3100
```

Network: `pollmevals-dev` (shared between both compose files via `external: true`).

## File deltas (this bootstrap)

Created (9 files):
- `infra/docker-compose.observability.yml` — LGTM + OTEL collector, all digest-pinned
- `infra/observability/otel-collector-config.yaml` — receives OTLP → fans to Tempo/Prom/Loki
- `infra/observability/prometheus.yml` — 3 scrape jobs incl. bearer-token for LiteLLM
- `infra/observability/tempo.yaml` — local single-binary, 24h retention
- `infra/observability/loki-config.yaml` — local filesystem store, 24h retention
- `infra/observability/grafana-datasources.yaml` — auto-provisioning, traces↔logs↔metrics correlation
- `infra/scripts/smoke-litellm.py` — analogous to smoke-openrouter.py but via proxy

Modified:
- `infra/docker-compose.litellm.yml` — added Postgres + OTEL env (OTEL_EXPORTER, OTEL_ENDPOINT, OTEL_SERVICE_NAME); python-based healthcheck (wolfi image has no curl)
- `infra/litellm-config.yaml` — qwen via HF (case-sensitive `Qwen/Qwen3-14B`, no provider suffix); callbacks `[prometheus, otel]`; database_url enabled; gemini → `:preview` suffix
- `Makefile` — added `stack-up/down/status`, `obs-up/down/status`, `grafana`, `litellm-smoke`, `openrouter-smoke`, `env-check`

## Carry-forward (action items)

1. **Loki not yet receiving logs** — OTEL collector configured to forward logs to Loki but no service emits structured logs through OTLP yet. LiteLLM stdout → docker logs only. Phase 2C: add Promtail or LiteLLM log shipping.
2. **OTEL collector self-metrics port (8888) shows "down" in Prometheus** — investigate; harmless (collector still functional, traces+metrics flowing). May be deprecated endpoint in 0.115.1.
3. **POLLMEVALS orchestrator** (`apps/eval-core-py/src/orchestrator/`) NOT yet instrumented with OTEL spans — Phase 2C. Add `opentelemetry-api` + `opentelemetry-sdk` to pyproject; instrument `GridRunner._run_single` (span per eval), `JournalWriter.append`, `CostReconciler.reconcile_with_litellm`.
4. **Manifest `trace_id` field** — per SPEC-001 future extension, add `trace_id` to EvalRow so leaderboard (PRD-004) can deep-link to Grafana trace view.
5. **GRAFANA_ADMIN_PASSWORD** — env var with sane default; for prod, set strong + commit `.env.example` placeholder only.
6. **Postgres wipe required when LITELLM_MASTER_KEY changes** — master_key hash persists in DB; if env var changes without wipe, all chat completion calls return 401. Document in CLAUDE.md / docs/agents/build-config.md.

## Conclusions

- **Surviving hypothesis**: H2 (full self-hosted stack) — measurably correct
- **Decision strength**: 98% — strongest infrastructure EVID in the project
- **POLLMEVALS Phase 2B**: stack ready for real LLM smoke run. Next step (Phase 2C entrypoint) — wire orchestrator's `InspectEvalCaller` stub to point at `http://localhost:4000` (LiteLLM proxy), replace `FakeEvalCaller` in integration tests with real calls.
- **NOTE-003 graduation**: observability stack research seed now operationalized; ADR-005 can formalize the LGTM choice with this EVID as supporting evidence.

## Related Artifacts

- PRD-001 (informs — auto-linked; Phase 2B foundation for SC-1..SC-6)
- ADR-003 (5-model lineup — 5/5 routed successfully through proxy; ADR validated)
- ADR-004 (MoleculerPy adoption — NATS broker pre-provisioned)
- NOTE-003 (observability research seed — operationalized in this EVID)
- EVID-019 (OpenRouter direct smoke — superseded conceptually by this proxy-based measurement)
- EVID-014 (cost.py layer — will integrate with LiteLLM /spend/logs in Phase 3+)
- EVID-018 (MoleculerPy ownership uplift — same pattern applies to LGTM stack: open-source + self-hosted)
- Future ADR-005 (candidate: formalize LGTM choice + observability methodology)
- NOTE-002 (Evidence Quality Standard — applied)



