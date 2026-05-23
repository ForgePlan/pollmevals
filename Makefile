SHELL := /bin/bash

.PHONY: demo-run docker-up docker-down api-dev site-dev format-tree validate-tasks reproduce

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

validate-tasks:
	python infra/scripts/validate-task-specs.py

reproduce:
	bash infra/scripts/reproduce-local-run.sh

format-tree:
	find . -maxdepth 3 -type f | sort
