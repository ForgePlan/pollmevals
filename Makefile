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
        smoke-run resume postmortem \
        eval-core-test litellm-up litellm-down \
        env-check

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
# Smoke-run targets (Phase 2B/2C — stubs; real implementation lands in later waves)
# ---------------------------------------------------------------------------

smoke-run:
	@echo "TODO: smoke-run not yet implemented (Phase 2B)."
	@echo "See docs/04-runbook/12-first-smoke-run-playbook.md for the planned entrypoint."
	@exit 0

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
# Env diagnostics (no secrets in output — only key names + set/missing)
# ---------------------------------------------------------------------------

env-check:
	@echo "=== .env loaded: $(if $(wildcard .env),yes,NO — copy .env.example → .env) ==="
	@echo "OPENROUTER_API_KEY:       $(if $(OPENROUTER_API_KEY),set,MISSING)"
	@echo "OPENROUTER_API_KEY_JUDGE: $(if $(OPENROUTER_API_KEY_JUDGE),set,missing — needed for PRD-002 judges)"
	@echo "LITELLM_MASTER_KEY:       $(if $(LITELLM_MASTER_KEY),set,missing)"
	@echo "NATS_URL:                 $(if $(NATS_URL),set,missing — needed for PRD-003 MoleculerPy)"
	@echo "DATABASE_URL:             $(if $(DATABASE_URL),set,missing — needed for LiteLLM spend tracking)"
	@echo "CEREBRAS_API_KEY:         $(if $(CEREBRAS_API_KEY),set,missing — needed for Qwen 3 14B per ADR-003)"
	@echo "RUNPOD_VLLM_API_BASE:     $(if $(RUNPOD_VLLM_API_BASE),set,missing — needed for Llama 4 70B per ADR-003)"
	@echo "GEMINI_API_KEY:           $(if $(GEMINI_API_KEY),set,missing — forgeplan LLM provider)"
