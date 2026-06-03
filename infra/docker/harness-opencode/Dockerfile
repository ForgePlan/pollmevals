# syntax=docker/dockerfile:1.7
#
# pollmevals-harness-opencode -- sandboxed opencode (sst) CLI image (RFC-006
# Half A). Model-AGNOSTIC agentic CLI (built on the Vercel AI SDK with custom
# OpenAI-compatible providers), so it runs the SAME open coder models as
# aider/goose -- another clean "swap the harness, hold the model" column.
#
# Candidate-side shape (same as aider/goose, OPPOSITE of the Half B evaluator):
#   * /workspace WRITABLE (the harness edits files to produce a patch)
#   * joins the `pollmevals-sandbox` INTERNAL net -> reaches ONLY the proxy.
#
# Pinned dependencies (Library-first; bump deliberately):
#   node     22-slim      (opencode ships a Bun-compiled binary via npm
#                          optionalDependencies, opencode-linux-<arch>)
#   opencode-ai 1.15.13    (npm; pulls the platform binary)
#   git      (Debian stable) -- opencode tracks edits; we capture the diff via git
#
# opencode headless gotchas:
#   * opencode resolves custom AI-SDK provider packages (e.g.
#     @ai-sdk/openai-compatible) at RUN time via npm -- which the no-egress
#     sandbox cannot do. So we pre-install that provider at BUILD time and the
#     recipe points opencode at it (or uses a built-in provider). The opencode.json
#     config is written by the recipe (config_files), not baked (run-time proxy URL).
#   * `opencode run -m <provider>/<model> --dangerously-skip-permissions "<task>"`
#     is the one-shot headless form; `--print-logs`/`--format json` for output.
#
# Build:  docker build -t pollmevals-harness-opencode:0.1.0 infra/docker/harness-opencode/
#         (or: make harness-image-opencode)
# Smoke:  docker run --rm pollmevals-harness-opencode:0.1.0   # -> prints opencode version

FROM node:22-slim AS base

# git: opencode tracks edits; the launcher captures the diff host-side via git.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install opencode globally (pulls the platform binary via optionalDependencies).
# The recipe uses opencode's BUILT-IN `openai` provider with a baseURL override
# pointed at our proxy — that provider is bundled in the binary, so the no-egress
# run-time container needs no npm at all (verified: a smoke run edited a file with
# zero network beyond the proxy). Pinned.
RUN npm install -g --no-fund --no-audit opencode-ai@1.15.13 \
    && npm cache clean --force \
    && opencode --version

# Non-root user: defense-in-depth on top of --cap-drop=ALL and
# --security-opt=no-new-privileges. The node base already ships a uid-1000 `node`
# user, which matches the host bind owner so the produced patch is writable back.
USER node
WORKDIR /workspace

# Default git identity so a fresh snapshot is a valid repo to diff against.
RUN git config --global user.email "harness@pollmevals.local" \
    && git config --global user.name "pollmevals-harness" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /workspace

# opencode writes telemetry/state under $HOME; keep it inside the container.
ENV OPENCODE_DISABLE_AUTOUPDATE=1

# Default command is a harmless version probe; DockerHarnessLauncher overrides
# `command` with the full `opencode run ...` invocation.
CMD ["opencode", "--version"]
