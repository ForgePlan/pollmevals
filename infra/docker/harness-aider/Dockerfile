# syntax=docker/dockerfile:1.7
#
# pollmevals-harness-aider -- sandboxed aider CLI image (RFC-006 Half A, candidate side).
#
# Built once, used by StackExecutor / DockerHarnessLauncher to run the aider
# harness against a task. Unlike the Half B evaluator image (eval-ts), the
# candidate side is the OPPOSITE shape:
#   * /workspace is WRITABLE (the harness must edit files to produce a patch)
#   * the container joins the `pollmevals-sandbox` INTERNAL network so it can
#     reach ONLY the LiteLLM proxy (bastion) -- no general egress. The harness
#     never gets the upstream provider key; it talks to the proxy, which meters
#     every token (RFC-006 invariant: no un-metered egress).
#
# Pinned dependencies (Library-first; bump deliberately, never floating):
#   python       3.12-slim   (aider-chat requires <3.13,>=3.10)
#   aider-chat   0.86.2       (latest on PyPI 2026-06-02)
#   git          (Debian stable) -- aider tracks edits / computes diffs via git
#
# Build:
#   docker build -t pollmevals-harness-aider:0.1.0 infra/docker/harness-aider/
#   (or: make harness-image-aider)
#
# Run (referenced from DockerHarnessLauncher -- not invoked by humans directly):
#   docker run --rm \
#     --network=pollmevals-sandbox \
#     --cap-drop=ALL --security-opt=no-new-privileges:true \
#     --memory=2g --pids-limit=256 \
#     -v $(pwd)/snapshot:/workspace \
#     -e OPENAI_API_BASE=http://pollmevals-litellm-proxy:4000/v1 \
#     -e OPENAI_API_KEY=$LITELLM_MASTER_KEY \
#     pollmevals-harness-aider:0.1.0 \
#     aider --no-pretty --yes --model openai/<alias> --message "<task prompt>"
#
# Smoke (no proxy needed):
#   docker run --rm pollmevals-harness-aider:0.1.0   # -> prints aider version

FROM python:3.12-slim AS base

# git: aider needs it to track edits and compute diffs.
# ca-certificates: TLS to the proxy bastion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Pinned aider (library-first; bump deliberately). Installed at build time so
# the run-time container needs no PyPI access on the internal network.
RUN pip install --no-cache-dir aider-chat==0.86.2

# Non-root user: defense-in-depth on top of --cap-drop=ALL and
# --security-opt=no-new-privileges. uid 1000 matches the host bind owner so the
# produced patch is writable back on the host snapshot.
RUN useradd --create-home --uid 1000 harness
USER harness
WORKDIR /workspace

# Default git identity so aider's edit-tracking never fails on a fresh snapshot.
RUN git config --global user.email "harness@pollmevals.local" \
    && git config --global user.name "pollmevals-harness" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /workspace

# aider also disables its own analytics / auto-update phone-home on the isolated
# network; set the env so it never blocks waiting on a network call it can't make.
ENV AIDER_ANALYTICS=false \
    AIDER_CHECK_UPDATE=false

# Default command is a harmless version probe; DockerHarnessLauncher overrides
# `command` with the full aider invocation (and, in Phase 3, a git-diff capture
# wrapper). Keeping NO restrictive ENTRYPOINT lets the launcher pass either an
# argv list or an explicit `sh -c` wrapper.
CMD ["aider", "--version"]
