#!/usr/bin/env bash
# litellm-proxy-up.sh — Start the LiteLLM proxy for POLLMEVALS smoke run
#
# Starts the proxy via Docker Compose, waits up to 60s for the health endpoint,
# prints the ready URL, or dumps logs and exits 1 on timeout.
#
# Usage:
#   source .env && ./infra/scripts/litellm-proxy-up.sh
#   OR from repo root: OPENROUTER_API_KEY=sk-... LITELLM_MASTER_KEY=sk-... infra/scripts/litellm-proxy-up.sh
#
# Requires: docker, docker compose v2+, curl

set -euo pipefail

PROXY_URL="http://localhost:4000"
HEALTH_URL="${PROXY_URL}/health"
COMPOSE_FILE="docker-compose.litellm.yml"
MAX_WAIT_SECONDS=60
POLL_INTERVAL=5

# ── Preflight: required env vars ─────────────────────────────────────────────

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "ERROR: OPENROUTER_API_KEY is not set." >&2
  echo "  Export it or source your .env file before running this script." >&2
  echo "  Example: source .env && $0" >&2
  exit 1
fi

if [[ -z "${LITELLM_MASTER_KEY:-}" ]]; then
  echo "ERROR: LITELLM_MASTER_KEY is not set." >&2
  echo "  Export it or source your .env file before running this script." >&2
  exit 1
fi

# ── Resolve infra/ directory (works regardless of $PWD) ──────────────────────

REPO_ROOT="$(git rev-parse --show-toplevel)"
INFRA_DIR="${REPO_ROOT}/infra"

cd "${INFRA_DIR}"

# ── Start proxy ───────────────────────────────────────────────────────────────

echo "Starting LiteLLM proxy..."
docker compose -f "${COMPOSE_FILE}" up -d

# ── Wait for health endpoint ──────────────────────────────────────────────────

echo "Waiting for proxy to become healthy (up to ${MAX_WAIT_SECONDS}s)..."

elapsed=0
while [[ ${elapsed} -lt ${MAX_WAIT_SECONDS} ]]; do
  if curl -fsS "${HEALTH_URL}" > /dev/null 2>&1; then
    echo ""
    echo "LiteLLM proxy ready at ${PROXY_URL}"
    echo "  Health: ${HEALTH_URL}"
    echo "  Models: ${PROXY_URL}/models  (requires Authorization: Bearer \$LITELLM_MASTER_KEY)"
    exit 0
  fi
  printf "."
  sleep ${POLL_INTERVAL}
  elapsed=$(( elapsed + POLL_INTERVAL ))
done

# ── Timeout: dump logs for diagnosis ─────────────────────────────────────────

echo ""
echo "ERROR: LiteLLM proxy did not become healthy after ${MAX_WAIT_SECONDS}s." >&2
echo "--- Last 30 lines of container logs ---" >&2
docker compose -f "${COMPOSE_FILE}" logs litellm-proxy --tail=30 >&2
echo "---------------------------------------" >&2
echo "Run 'docker compose -f infra/${COMPOSE_FILE} ps' to check container status." >&2
exit 1
