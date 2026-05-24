# Dockerfile — be_01_jwt_auth evaluator sandbox
#
# Sandbox for the JWT-auth-middleware-in-Express coding eval (be_01, TypeScript).
# Follows the SWE-bench harness pattern (EVID-005): gold test suite runs inside
# isolated Docker container; submission patch applied via `git apply`.
#
# POLLMEVALS DIVERGENCE (architect finding #5, EVID-005):
#   Image is pinned by digest, not tag — tags are mutable on DockerHub, digests are not.
#   Re-pin by running:
#     docker pull node:22-alpine
#     docker inspect node:22-alpine --format '{{.RepoDigests}}'
#   before each major eval-protocol release.
#
# Image pinned 2026-05-24:
#   node:22-alpine@sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920
#
# Build + run lifecycle (orchestrator-driven, NOT standalone):
#   1. Orchestrator builds this image once per eval session.
#   2. Per eval: orchestrator mounts submission as a volume or applies patch.
#   3. Container runs evaluator_commands from task.yaml (npm test, eslint, tsc --noEmit).
#   4. Exit code 0 = evaluator pass (score computed from stdout JSON); non-zero = failure.
#
# To build manually for debugging:
#   docker build -t pollmevals-be01-sandbox evals/task-packs/be_01_jwt_auth/
#
# To test with gold solution (pre-flight check per ADR-003):
#   docker run --rm -v $(pwd)/evals/task-packs/be_01_jwt_auth/gold:/workspace/gold \
#     pollmevals-be01-sandbox

# Digest-pinned base image — Node 22 LTS on Alpine (smallest production-ready Node image)
FROM node:22-alpine@sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920

# Metadata labels for traceability
LABEL org.opencontainers.image.title="pollmevals-be01-jwt-auth-sandbox"
LABEL org.opencontainers.image.description="Evaluator sandbox for be_01_jwt_auth coding task"
LABEL org.opencontainers.image.version="1.0.0"
LABEL pollmevals.task.id="be_01"
LABEL pollmevals.task.version="1.0"
LABEL pollmevals.methodology.version="v0.1.0"

WORKDIR /workspace

# Install global dev toolchain used by evaluator_commands in task.yaml:
#   - typescript@5  → tsc --noEmit --strict workspace/solution.ts
#   - tsx@4         → ts-node-style execution for test helpers
#   - eslint        → eslint --max-warnings=0 workspace/solution.ts
#
# Versions pinned for reproducibility; bump via explicit ADR when upgrading.
RUN npm install -g \
      typescript@5 \
      tsx@4 \
      eslint@9 \
  && npm cache clean --force

# Copy the task pack's package.json and install test dependencies.
# The orchestrator mounts the submission at /workspace/solution.ts at runtime.
# gold/ and test files are baked in so the evaluator is self-contained.
COPY package*.json ./

# Install test runtime dependencies (jest + ts-jest + type stubs + jsonwebtoken + express)
# package.json is created by Agent 2 (eval-core-py); this RUN is a no-op if package.json
# does not yet exist — orchestrator re-builds after package.json lands.
RUN if [ -f package.json ]; then npm ci --omit=optional 2>/dev/null || npm install --omit=optional; fi

# Copy test suite and supporting files (not the submission — that comes at runtime)
# gold/  → contains calibration samples and the canonical passing solution
# Tests reference ./workspace/solution.ts which the orchestrator writes before running.
COPY . .

# The submission file is written by the orchestrator at runtime via:
#   docker cp submission.ts <container>:/workspace/solution.ts
#   OR via bind-mount: -v /path/to/submission.ts:/workspace/solution.ts:ro
# No EXPOSE needed — this is a batch evaluator, not a server.

# Default command: run the canonical gold test suite.
# The orchestrator overrides CMD at runtime to run evaluator_commands from task.yaml.
# Exit code is the canonical pass/fail signal — stdout carries evaluator_json.
CMD ["sh", "-c", "echo 'be_01 sandbox ready — no submission mounted'; echo '{\"error\": \"no submission\"}'; exit 1"]
