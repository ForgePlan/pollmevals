SHELL := /bin/bash

.PHONY: demo-run docker-up docker-down api-dev site-dev format-tree \
        validate-tasks validate-stacks reproduce \
        smoke-run resume postmortem \
        eval-core-test litellm-up litellm-down

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
