# syntax=docker/dockerfile:1.7
#
# pollmevals-harness-pi -- sandboxed pi-coding-agent CLI image (RFC-006 Half A).
# Model-AGNOSTIC agentic CLI (`@earendil-works/pi-coding-agent`, pure JS, binary
# `pi`) -> runs the SAME open coder models as aider/opencode/goose -- another
# clean "swap the harness, hold the model" column.
#
# Candidate-side shape (same as aider/opencode/goose, OPPOSITE of the Half B
# evaluator image):
#   * /workspace is WRITABLE (the harness edits files to produce a patch)
#   * joins the `pollmevals-sandbox` INTERNAL net -> reaches ONLY the LiteLLM
#     proxy (bastion). pi talks to the proxy (which meters every token); it
#     never holds the upstream provider key (RFC-006 invariant: no un-metered
#     egress).
#
# Pinned dependencies (Library-first; bump deliberately, never floating):
#   node     22-slim   (pi requires Node >=22.19; the 22-slim tag ships a
#                        22.19+ runtime AND a pre-made uid-1000 `node` user we
#                        reuse -- matches the host bind owner so the patch is
#                        writable back, same as the opencode harness)
#   @earendil-works/pi-coding-agent 0.78.0   (npm; pure JS, no platform binary)
#   git      (Debian stable) -- pi tracks edits; we capture the diff via git
#
# pi headless gotchas baked in (researched + source-verified):
#   * pi reads its models.json from $PI_CODING_AGENT_DIR (default ~/.pi/agent).
#     We default that env to /workspace/.pi/agent so a config the launcher writes
#     INTO the bind-mounted /workspace is found at run time. The models.json
#     itself is written by the recipe (config_files) -- not baked -- because it
#     carries the run-time proxy URL + the chosen model. pi expands
#     $LITELLM_MASTER_KEY (and other $VARS) in models.json from the env.
#   * PI_OFFLINE / PI_SKIP_VERSION_CHECK / PI_TELEMETRY=0 -- the no-egress
#     sandbox can't reach the registry/telemetry endpoints; without these pi
#     would block or warn on a network call it can never complete.
#   * Run form: `pi --model litellm/<model> --no-context-files -p "<prompt>"`.
#     No permission gate in the headless `-p` path (writes unconditionally), so
#     a one-shot run never stalls on an interactive confirmation.
#
# Build:  docker build -t pollmevals-harness-pi:0.1.0 infra/docker/harness-pi/
#         (or: make harness-image-pi)
# Smoke:  docker run --rm pollmevals-harness-pi:0.1.0   # -> prints pi version

FROM node:22-slim AS base

# git: pi tracks edits; the launcher captures the diff host-side via git.
# ca-certificates: TLS to the proxy bastion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install pi globally (pure-JS npm package -- no optional platform binary).
# Pulled at BUILD time so the no-egress run-time container needs no npm at all.
# Pinned (library-first; bump deliberately).
RUN npm install -g --no-fund --no-audit @earendil-works/pi-coding-agent@0.78.0 \
    && npm cache clean --force \
    && pi --version

# Non-root user: defense-in-depth on top of --cap-drop=ALL and
# --security-opt=no-new-privileges. The node base already ships a uid-1000
# `node` user, which matches the host bind owner so the produced patch is
# writable back. Reuse it (do NOT useradd).
USER node
WORKDIR /workspace

# Default git identity so a fresh snapshot is a valid repo to diff against.
RUN git config --global user.email "harness@pollmevals.local" \
    && git config --global user.name "pollmevals-harness" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /workspace

# Headless / no-egress defaults (see header). PI_CODING_AGENT_DIR points pi at a
# config dir inside the bind-mounted workspace so the recipe-written models.json
# is found. The proxy URL + model live in that models.json (run-time), not here.
ENV PI_CODING_AGENT_DIR=/workspace/.pi/agent \
    PI_OFFLINE=1 \
    PI_SKIP_VERSION_CHECK=1 \
    PI_TELEMETRY=0

# Default command is a harmless version probe; DockerHarnessLauncher overrides
# `command` with the full `pi --model ... -p ...` invocation. No restrictive
# ENTRYPOINT so the launcher can pass either an argv list or an `sh -c` wrapper.
CMD ["pi", "--version"]
