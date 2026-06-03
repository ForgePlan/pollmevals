# syntax=docker/dockerfile:1.7
#
# pollmevals-harness-mini-swe -- sandboxed "mini-swe-agent" (CLI `mini`) image
# (RFC-006 Half A, candidate side). mini-swe-agent is a deliberately minimal,
# model-AGNOSTIC SWE agent (just bash, no bespoke tools) -- it runs the SAME
# coder models aider/goose do, so it's another clean "swap the harness, hold the
# model" comparison column, but at the OTHER extreme of the scaffolding ladder
# (a single bash tool + a built-in step/validator loop, no tool zoo).
#
# Same candidate-side shape as harness-aider / harness-goose (the OPPOSITE of the
# Half B evaluator image):
#   * /workspace is WRITABLE (the harness edits files to produce a patch)
#   * the container joins the `pollmevals-sandbox` INTERNAL network so it can
#     reach ONLY the LiteLLM proxy (bastion) -- no general egress. mini talks to
#     the proxy (which meters every token); it never holds the upstream key.
#
# Pinned dependencies (Library-first; bump deliberately, never floating):
#   python          3.12-slim   (mini-swe-agent supports 3.10+)
#   mini-swe-agent  2.3.0        (PyPI; provides the `mini` console script)
#   git             (Debian stable) -- the launcher captures the diff host-side
#                                via git; mini itself runs bash edits in-place
#
# Headless gotchas baked in (each one hangs or crashes a non-interactive run):
#   * MSWEA_CONFIGURED=true        -- skip the first-run interactive setup wizard
#                                     (otherwise `mini` blocks asking for config).
#   * MSWEA_COST_TRACKING=ignore_errors
#                                  -- our LiteLLM proxy reports $0 cost for local
#                                     models; mini's default cost tracking raises
#                                     a RuntimeError on a $0 / missing-cost reply.
#                                     `ignore_errors` downgrades that to a warning.
#   The model name + proxy wiring (MSWEA_MODEL_NAME / OPENAI_API_BASE /
#   OPENAI_API_KEY, and the inline `-c model.*` overrides) are injected at RUN
#   time by the recipe (_mini_swe_invocation in stack_executor.py), not baked
#   here -- the image stays model-agnostic.
#
# Build:
#   docker build -t pollmevals-harness-mini-swe:0.1.0 infra/docker/harness-mini-swe/
#   (or: make harness-image-mini-swe)
#
# Run (referenced from DockerHarnessLauncher -- not invoked by humans directly):
#   docker run --rm \
#     --network=pollmevals-sandbox \
#     --cap-drop=ALL --security-opt=no-new-privileges:true \
#     --memory=2g --pids-limit=256 \
#     -v $(pwd)/snapshot:/workspace \
#     -e MSWEA_CONFIGURED=true \
#     -e MSWEA_COST_TRACKING=ignore_errors \
#     -e MSWEA_MODEL_NAME=openai/<alias> \
#     -e OPENAI_API_BASE=http://pollmevals-litellm-proxy:4000/v1 \
#     -e OPENAI_API_KEY=$LITELLM_MASTER_KEY \
#     pollmevals-harness-mini-swe:0.1.0 \
#     mini --environment-class local -y --exit-immediately \
#       -c model.model_name=openai/<alias> \
#       -c model.model_kwargs.api_base=http://pollmevals-litellm-proxy:4000/v1 \
#       -c model.model_kwargs.custom_llm_provider=openai \
#       -c agent.step_limit=40 -c environment.timeout=600 \
#       -t "<task prompt>"
#   (--environment-class local is CRITICAL: it runs bash in /workspace, NOT a
#    nested Docker -- the sandbox has no docker socket and must never get one.)
#
# Smoke (no proxy needed):
#   docker run --rm pollmevals-harness-mini-swe:0.1.0   # -> prints `mini --help`

FROM python:3.12-slim AS base

# git: the launcher tracks edits / computes the diff via git host-side, and a
#   fresh snapshot must be a valid repo. ca-certificates: TLS to the proxy.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Pinned mini-swe-agent (library-first; bump deliberately). Installed at build
# time so the run-time container needs no PyPI access on the internal network.
# Provides the `mini` console script.
RUN pip install --no-cache-dir mini-swe-agent==2.3.0

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

# Headless defaults (see header). Skip the setup wizard and tolerate the proxy's
# $0 cost reports. Model + proxy wiring are injected by the recipe at run time.
ENV MSWEA_CONFIGURED=true \
    MSWEA_COST_TRACKING=ignore_errors

# Default command is a harmless help probe; DockerHarnessLauncher overrides
# `command` with the full `mini ...` invocation. No restrictive ENTRYPOINT so the
# launcher can pass either an argv list or an explicit sh -c wrapper.
CMD ["mini", "--help"]
