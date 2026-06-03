# syntax=docker/dockerfile:1.7
#
# pollmevals-harness-crush -- sandboxed Charmbracelet "crush" CLI image (RFC-006
# Half A). Model-AGNOSTIC agentic CLI (Go), `openai-compat` provider → any
# OpenAI-compatible endpoint, so it runs the same open coder models as
# aider/goose -- another "swap the harness, hold the model" column.
#
# Candidate-side shape (same as aider/goose, OPPOSITE of the Half B evaluator):
#   * /workspace WRITABLE (the harness edits files to produce a patch)
#   * joins the `pollmevals-sandbox` INTERNAL net -> reaches ONLY the proxy.
#
# Pinned dependencies (Library-first; bump deliberately):
#   python   3.12-slim   (base only -- crush is a standalone Go binary; reuses
#                          the cached base layer)
#   crush    v0.75.0       (charmbracelet release binary, pinned + direct download)
#   git      (Debian stable) -- crush tracks edits; we capture the diff via git
#
# crush headless: `crush run -q "<prompt>"` (quiet, non-interactive, reads the
# prompt as arg/stdin). The provider/model config rides a crush.json written by
# the recipe via config_files (not baked -- run-time proxy URL).
#
# Build:  docker build -t pollmevals-harness-crush:0.1.0 infra/docker/harness-crush/
#         (or: make harness-image-crush)
# Smoke:  docker run --rm pollmevals-harness-crush:0.1.0   # -> prints crush version

FROM python:3.12-slim AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# Install crush (root -> /usr/local/bin). Pinned release tarball; arch from
# BuildKit's TARGETARCH (Go-style names: arm64/amd64). Pulled at BUILD time so
# the run-time container needs no network beyond the proxy.
ARG TARGETARCH
ARG CRUSH_VERSION=0.75.0
RUN set -eux; \
    case "${TARGETARCH}" in \
      arm64) CARCH=arm64 ;; \
      amd64) CARCH=amd64 ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}"; exit 1 ;; \
    esac; \
    url="https://github.com/charmbracelet/crush/releases/download/v${CRUSH_VERSION}/crush_${CRUSH_VERSION}_Linux_${CARCH}.tar.gz"; \
    curl -fsSL -o /tmp/crush.tar.gz "$url"; \
    mkdir -p /tmp/crush-x; \
    tar -xzf /tmp/crush.tar.gz -C /tmp/crush-x; \
    bin="$(find /tmp/crush-x -maxdepth 2 -type f -name crush | head -1)"; \
    cp "$bin" /usr/local/bin/crush; \
    chmod +x /usr/local/bin/crush; \
    rm -rf /tmp/crush.tar.gz /tmp/crush-x; \
    /usr/local/bin/crush --version

# Non-root user: defense-in-depth on top of --cap-drop=ALL and
# --security-opt=no-new-privileges. uid 1000 matches the host bind owner.
RUN useradd --create-home --uid 1000 harness
USER harness
WORKDIR /workspace

RUN git config --global user.email "harness@pollmevals.local" \
    && git config --global user.name "pollmevals-harness" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /workspace

# Keep crush from phoning home on the isolated net.
ENV CRUSH_DISABLE_AUTOUPDATE=1

# Default command is a harmless version probe; DockerHarnessLauncher overrides
# `command` with the full `crush run ...` invocation.
CMD ["crush", "--version"]
