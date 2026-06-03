# syntax=docker/dockerfile:1.7
#
# pollmevals-harness-cline -- sandboxed Cline CLI image (RFC-006 Half A). Cline is
# a model-AGNOSTIC agentic CLI (it speaks any OpenAI-compatible endpoint via its
# `openai-native` provider + a base-URL override), so it runs the same open coder
# models as aider/goose/opencode/crush -- another "swap the harness" column.
#
# Candidate-side shape (same as the other harnesses, OPPOSITE of Half B):
#   * /workspace WRITABLE (the harness edits files to produce a patch)
#   * joins the `pollmevals-sandbox` INTERNAL net -> reaches ONLY the proxy.
#
# Pinned dependencies (Library-first; bump deliberately):
#   node   22-slim     (cline ships a Bun-compiled binary via npm optionalDeps
#                        @cline/cli-linux-<arch>; the `cline` launcher is a Node
#                        script -> Node base. Both arm64 + x64 publish at 3.0.15.)
#   cline  3.0.15       (npm; pulls the platform binary, glibc -> node-slim)
#   git    (Debian stable) -- cline tracks edits; we capture the diff via git
#
# Cline headless gotchas (cline 3.0.15 README + docs.cline.bot):
#   * A custom base URL is NOT an env var and NOT a run flag -- it is seeded only
#     via `cline auth --provider openai-native --baseurl <proxy>/v1`, which
#     persists to <data-dir>/settings/providers.json. So the run is a two-step
#     sh -c: auth (seed) then the one-shot. Both share --data-dir /tmp/clinedata,
#     placed OUTSIDE /workspace so providers.json + the session DB never land in
#     the captured patch (same discipline as crush's CRUSH_GLOBAL_DATA=/tmp).
#   * `--yolo` makes the run fully non-interactive (auto-approve all tools + exit).
#   The provider/model/proxy/base-url is injected at run time by the recipe.
#
# Build:  docker build -t pollmevals-harness-cline:0.1.0 infra/docker/harness-cline/
#         (or: make harness-image-cline)
# Smoke:  docker run --rm pollmevals-harness-cline:0.1.0   # -> prints cline version

FROM node:22-slim AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install cline globally (pulls the platform binary via optionalDependencies:
# @cline/cli-linux-arm64 / @cline/cli-linux-x64, both present at 3.0.15). The
# binary is Bun-embedded/self-contained, so the no-egress run-time container needs
# no npm. Pinned.
RUN npm install -g --no-fund --no-audit cline@3.0.15 \
    && npm cache clean --force \
    && cline --version

# Non-root user: the node base already ships a uid-1000 `node` user, which matches
# the host bind owner so the produced patch is writable back.
USER node
WORKDIR /workspace

RUN git config --global user.email "harness@pollmevals.local" \
    && git config --global user.name "pollmevals-harness" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /workspace

# Keep all cline state OUT of /workspace (providers.json + session DB live in
# /tmp so they never land in the captured patch). The recipe ALSO passes
# --data-dir /tmp/clinedata explicitly (authoritative); this is the matching default.
ENV CLINE_DATA_DIR=/tmp/clinedata \
    CLINE_LOG_ENABLED=0

# Default command is a harmless version probe; DockerHarnessLauncher overrides
# `command` with the full `sh -c "cline auth ... && cline --yolo ..."` invocation.
CMD ["cline", "--version"]
