# syntax=docker/dockerfile:1.7
#
# pollmevals-eval-ts -- sandboxed TypeScript test runner image for dynamic evaluators.
#
# Built once, used by CorrectnessEvaluator and CoverageEvaluator via SandboxRun.
# Image MUST stay self-contained: no network at evaluator-run time (network_mode=none).
#
# Pinned dependencies (Library-first; bump deliberately, never floating):
#   node           22.18-alpine  (matches CI runner Node version)
#   typescript     5.9.x
#   vitest         3.2.x
#   @vitest/coverage-v8           (matched to vitest minor)
#
# Build:
#   docker build -t pollmevals-eval-ts:0.1.0 infra/docker/eval-ts/
#
# Run (referenced from SandboxRun -- not invoked by humans directly):
#   docker run --rm \
#     --network=none --read-only --tmpfs /tmp:size=100m \
#     --memory=512m --pids-limit=50 --cap-drop=ALL \
#     --security-opt=no-new-privileges:true \
#     -v $(pwd)/candidate:/workspace:ro \
#     pollmevals-eval-ts:0.1.0 \
#     npx vitest run --coverage --reporter=json
#
# v0.3+ note: when the sandbox runtime upgrades to gVisor / Kata (per
# docs/04-runbook/09-sandbox-security.md roadmap), this image stays the same --
# only the docker daemon's `runtime` flag changes.

FROM node:22.18-alpine AS base

# Refuse to run as root inside the container (defense-in-depth on top of
# --cap-drop=ALL + --security-opt=no-new-privileges). The node image ships
# a non-root `node` user; we use it.
USER node
WORKDIR /home/node/app

# Copy the pinned package descriptor and install once at build time.
# At evaluator run-time the container has --network=none so npm install
# would fail -- everything must be baked here.
COPY --chown=node:node package.json package-lock.json* ./

# `npm ci` requires a lockfile; use `npm install` for first-time greenfield.
# Frozen versions: vitest 3.2 was the first version with coverageMap embedded
# in the JSON reporter output (web research 2026-05-25).
RUN npm install --no-audit --no-fund \
    && npm cache clean --force

# Default CMD is overridden by SandboxRun via command=[...]; the entrypoint
# stays a thin /bin/sh wrapper so the evaluator can pass vitest args directly.
ENTRYPOINT ["/bin/sh", "-c"]
CMD ["echo 'pollmevals-eval-ts ready; provide command via SandboxRun'"]
