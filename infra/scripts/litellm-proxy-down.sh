#!/usr/bin/env bash
# litellm-proxy-down.sh — Stop the LiteLLM proxy for POLLMEVALS smoke run
#
# Usage:
#   ./infra/scripts/litellm-proxy-down.sh
#
# Requires: docker, docker compose v2+

set -euo pipefail

COMPOSE_FILE="docker-compose.litellm.yml"

# Resolve infra/ directory regardless of $PWD
REPO_ROOT="$(git rev-parse --show-toplevel)"
INFRA_DIR="${REPO_ROOT}/infra"

cd "${INFRA_DIR}"

echo "Stopping LiteLLM proxy..."
docker compose -f "${COMPOSE_FILE}" down

echo "LiteLLM proxy stopped."
