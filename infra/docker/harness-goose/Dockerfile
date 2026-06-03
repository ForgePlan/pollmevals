# syntax=docker/dockerfile:1.7
#
# pollmevals-harness-goose -- sandboxed Block "goose" CLI image (RFC-006 Half A,
# candidate side). Second harness after aider; goose is a model-AGNOSTIC agent
# (OpenAI-compatible provider), so it runs the SAME coder models aider does ->
# the cleanest "swap the harness, hold the model" comparison column.
#
# Same candidate-side shape as harness-aider (the OPPOSITE of the Half B
# evaluator image):
#   * /workspace is WRITABLE (the harness edits files to produce a patch)
#   * the container joins the `pollmevals-sandbox` INTERNAL network so it can
#     reach ONLY the LiteLLM proxy (bastion) -- no general egress. goose talks
#     to the proxy (which meters every token); it never holds the upstream key.
#
# Pinned dependencies (Library-first; bump deliberately, never floating):
#   python       3.12-slim   (base only -- goose is a standalone Rust binary;
#                              reuses the cached aider/eval-py base layer)
#   goose        v1.36.0       (Block release binary, pinned + downloaded
#                              directly -- the official download_cli.sh falls
#                              back to a stale mirror that lacks the arm64 asset,
#                              so we fetch the exact tarball ourselves)
#   git          (Debian stable) -- goose tracks edits; we capture the diff via git
#
# goose headless gotchas baked in (empirical spike + goose docs):
#   * GOOSE_DISABLE_KEYRING=1 -- in a container there is no system keyring;
#     without this goose errors on secret storage. Forces file-based secrets.
#   * GOOSE_MODE=auto -- auto-approve tool calls; a headless run must never
#     block waiting for an interactive confirmation.
#   The provider/model/proxy env is injected at run time by the recipe
#   (_goose_invocation in stack_executor.py), not baked here.
#
# Build:
#   docker build -t pollmevals-harness-goose:0.1.0 infra/docker/harness-goose/
#   (or: make harness-image-goose)
#
# Run (referenced from DockerHarnessLauncher -- not invoked by humans directly):
#   docker run --rm \
#     --network=pollmevals-sandbox \
#     --cap-drop=ALL --security-opt=no-new-privileges:true \
#     --memory=2g --pids-limit=256 \
#     -v $(pwd)/snapshot:/workspace \
#     -e GOOSE_PROVIDER=openai -e GOOSE_MODEL=<alias> \
#     -e OPENAI_API_KEY=$LITELLM_MASTER_KEY \
#     -e OPENAI_HOST=http://pollmevals-litellm-proxy:4000 \
#     -e OPENAI_BASE_PATH=v1/chat/completions \
#     pollmevals-harness-goose:0.1.0 \
#     goose run --no-session -t "<task prompt>"
#
# Smoke (no proxy needed):
#   docker run --rm pollmevals-harness-goose:0.1.0   # -> prints goose version

FROM python:3.12-slim AS base

# curl + bzip2 + ca-certificates: fetch + extract the goose release tarball.
# git: goose tracks edits; the launcher captures the diff host-side via git.
# libxcb1 + libdbus-1-3: the goose binary dynamically links the keyring stack
#   even when GOOSE_DISABLE_KEYRING routes secrets to a file -- without these
#   shared objects the binary fails to start at all.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl ca-certificates bzip2 git libxcb1 libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# Install goose (root -> /usr/local/bin, on PATH for all users). Pinned tarball
# fetched directly: arch from BuildKit's TARGETARCH (arm64->aarch64, amd64->
# x86_64), gnu (glibc) variant to match the Debian base. Pulled at BUILD time so
# the run-time container needs no network beyond the proxy.
ARG TARGETARCH
ARG GOOSE_VERSION=v1.36.0
RUN set -eux; \
    case "${TARGETARCH}" in \
      arm64) GARCH=aarch64 ;; \
      amd64) GARCH=x86_64 ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}"; exit 1 ;; \
    esac; \
    url="https://github.com/block/goose/releases/download/${GOOSE_VERSION}/goose-${GARCH}-unknown-linux-gnu.tar.bz2"; \
    curl -fsSL -o /tmp/goose.tar.bz2 "$url"; \
    mkdir -p /tmp/goose-x; \
    tar -xjf /tmp/goose.tar.bz2 -C /tmp/goose-x; \
    find /tmp/goose-x -maxdepth 2 -type f -name goose  -exec cp {} /usr/local/bin/goose  \; ; \
    find /tmp/goose-x -maxdepth 2 -type f -name goosed -exec cp {} /usr/local/bin/goosed \; ; \
    chmod +x /usr/local/bin/goose; \
    rm -rf /tmp/goose.tar.bz2 /tmp/goose-x; \
    /usr/local/bin/goose --version

# Non-root user: defense-in-depth on top of --cap-drop=ALL and
# --security-opt=no-new-privileges. uid 1000 matches the host bind owner so the
# produced patch is writable back on the host snapshot.
RUN useradd --create-home --uid 1000 harness
USER harness
WORKDIR /workspace

# Default git identity so a fresh snapshot is a valid repo to diff against.
RUN git config --global user.email "harness@pollmevals.local" \
    && git config --global user.name "pollmevals-harness" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /workspace

# Headless defaults (see header). Provider/model/proxy are injected by the recipe.
ENV GOOSE_DISABLE_KEYRING=1 \
    GOOSE_MODE=auto

# Default command is a harmless version probe; DockerHarnessLauncher overrides
# `command` with the full `goose run ...` invocation. No restrictive ENTRYPOINT
# so the launcher can pass either an argv list or an explicit sh -c wrapper.
CMD ["goose", "--version"]
