SHELL := /bin/bash

# Auto-load .env (gitignored — secrets store).
# Provides OPENROUTER_API_KEY, LITELLM_MASTER_KEY, NATS_URL etc to all targets
# AND to subprocesses (docker compose, python, pnpm). See .env.example for keys.
ifneq (,$(wildcard .env))
    include .env
    export
endif

.PHONY: demo-run docker-up docker-down api-dev site-dev format-tree \
        validate-tasks validate-stacks reproduce \
        smoke-run smoke-dry resume postmortem \
        eval-core-test litellm-up litellm-down stack-up stack-down stack-status \
        openrouter-smoke env-check

demo-run:
	python -m pollmevals_eval_core.demo_run --tasks evals/tasks --output artifacts

docker-up:
	docker compose -f infra/docker-compose.dev.yml up -d

docker-down:
	docker compose -f infra/docker-compose.dev.yml down

api-dev:
	cd apps/api && pnpm dev

site-dev:
	cd apps/site && pnpm dev

format-tree:
	find . -maxdepth 3 -type f | sort

# ---------------------------------------------------------------------------
# Smoke-run targets (Phase 2B coda — entrypoint implemented)
# ---------------------------------------------------------------------------

smoke-dry:
	uv run --project apps/eval-core-py python apps/eval-core-py/scripts/smoke_run.py --dry-run

smoke-run:
	@echo "Smoke run will spend \$$5-15 in real OpenRouter inference."
	@echo "Use 'make smoke-dry' first to verify all pre-flight checks pass."
	@echo "To execute: uv run --project apps/eval-core-py python apps/eval-core-py/scripts/smoke_run.py --confirm-spend"
	@echo ""
	@echo "(make smoke-run is intentionally NOT one command — explicit --confirm-spend prevents accidental spend)"

resume:
	@echo "TODO: resume not yet implemented (Phase 2A wave 5)."
	@echo "Will load manifest.journal.ndjson and reschedule missing eval rows."
	@exit 0

postmortem:
	@echo "TODO: postmortem not yet implemented (Phase 2C)."
	@echo "Will read artifacts/runs/<hash>/manifest.json and generate a summary report."
	@exit 0

# ---------------------------------------------------------------------------
# Validation targets
# ---------------------------------------------------------------------------

validate-tasks:
	python infra/scripts/validate-task-specs.py

validate-stacks:
	python infra/scripts/validate-stack-specs.py

# ---------------------------------------------------------------------------
# Python eval-core targets
# ---------------------------------------------------------------------------

eval-core-test:
	moon run eval-core-py:test

# ---------------------------------------------------------------------------
# LiteLLM proxy targets (scripts created by Agent 3 in Wave 1)
# ---------------------------------------------------------------------------

litellm-up:
	bash infra/scripts/litellm-proxy-up.sh

litellm-down:
	bash infra/scripts/litellm-proxy-down.sh

# ---------------------------------------------------------------------------
# Dev stack (NATS + LiteLLM proxy) — combined compose
# ---------------------------------------------------------------------------

stack-up:
	@if [ -z "$$OPENROUTER_API_KEY" ] || [ -z "$$HF_TOKEN" ] || [ -z "$$LITELLM_MASTER_KEY" ]; then \
	  echo "❌ missing required env (run 'make env-check' for diagnostic)"; exit 1; \
	fi
	docker compose -f infra/docker-compose.litellm.yml up -d
	@echo "waiting for Postgres + NATS + LiteLLM to be healthy (up to 90s)..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18; do \
	  pg_ok=$$(docker inspect --format '{{.State.Health.Status}}' pollmevals-postgres 2>/dev/null || echo "starting"); \
	  nats_ok=$$(docker inspect --format '{{.State.Health.Status}}' pollmevals-nats 2>/dev/null || echo "starting"); \
	  ll_ok=$$(docker inspect --format '{{.State.Health.Status}}' pollmevals-litellm-proxy 2>/dev/null || echo "starting"); \
	  echo "  [$$i/18] pg=$$pg_ok nats=$$nats_ok litellm=$$ll_ok"; \
	  if [ "$$pg_ok" = "healthy" ] && [ "$$nats_ok" = "healthy" ] && [ "$$ll_ok" = "healthy" ]; then echo "✅ stack ready"; exit 0; fi; \
	  sleep 5; \
	done; \
	echo "⚠️ healthcheck timeout — see 'docker compose -f infra/docker-compose.litellm.yml logs'"; exit 1

stack-down:
	docker compose -f infra/docker-compose.litellm.yml down

stack-status:
	@docker ps --filter 'name=pollmevals-' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# ---------------------------------------------------------------------------
# Observability stack (LGTM + OTEL collector) — per NOTE-003
# ---------------------------------------------------------------------------

obs-up:
	docker compose -f infra/docker-compose.observability.yml up -d
	@echo "Grafana → http://localhost:3000 (admin / pollmevals_dev)"
	@echo "Prometheus → http://localhost:9090"
	@echo "Tempo (API) → http://localhost:3200"

obs-down:
	docker compose -f infra/docker-compose.observability.yml down

obs-status:
	@docker ps --filter 'name=pollmevals-(otel|prometheus|tempo|loki|grafana)' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

grafana:
	@open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || echo "Open http://localhost:3000 manually"

# ---------------------------------------------------------------------------
# OpenRouter smoke test — pre-flight for `make smoke-run` (Phase 2B).
# Tests ADR-003 5-model lineup with minimal chat completion (~$0.0003 total).
# Exit 0 if ≥3 models OK (PRD-001 degraded threshold).
# ---------------------------------------------------------------------------

openrouter-smoke:
	uv run --project apps/eval-core-py python infra/scripts/smoke-openrouter.py

# LiteLLM proxy smoke — through the unified-routing layer (Phase 2B validation)
# Prerequisite: `make stack-up` must succeed first.
litellm-smoke:
	uv run --project apps/eval-core-py python infra/scripts/smoke-litellm.py

# ---------------------------------------------------------------------------
# Env diagnostics (no secrets in output — only key names + set/missing)
# ---------------------------------------------------------------------------

env-check:
	@echo "=== .env loaded: $(if $(wildcard .env),yes,NO — copy .env.example → .env) ==="
	@echo "OPENROUTER_API_KEY:       $(if $(OPENROUTER_API_KEY),set,MISSING — required for Phase 2B closed models)"
	@echo "HF_TOKEN:                 $(if $(HF_TOKEN),set,MISSING — required for qwen-3-14b via HF/Cerebras)"
	@echo "LITELLM_MASTER_KEY:       $(if $(LITELLM_MASTER_KEY),set,missing — required for LiteLLM proxy admin)"
	@echo "NATS_URL:                 $(if $(NATS_URL),set,missing — Phase 3 MoleculerPy broker)"
	@echo "OPENROUTER_API_KEY_JUDGE: $(if $(OPENROUTER_API_KEY_JUDGE),set,missing — PRD-002 judges separation)"
	@echo "DATABASE_URL:             $(if $(DATABASE_URL),set,missing — LiteLLM spend tracking)"
	@echo "CEREBRAS_API_KEY:         $(if $(CEREBRAS_API_KEY),set,missing — direct Cerebras fallback)"
	@echo "RUNPOD_VLLM_API_BASE:     $(if $(RUNPOD_VLLM_API_BASE),set,missing — direct Runpod vLLM)"
	@echo "GEMINI_API_KEY:           $(if $(GEMINI_API_KEY),set,missing — forgeplan LLM provider)"
