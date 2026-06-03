# syntax=docker/dockerfile:1.7
#
# pollmevals-harness-gptme -- sandboxed gptme CLI image (RFC-006 Half A,
# candidate side). gptme is a model-AGNOSTIC terminal agent (it speaks the
# OpenAI-compatible Chat Completions API), so it runs the SAME open coder models
# aider/goose/opencode do -> another clean "swap the harness, hold the model"
# comparison column.
#
# Same candidate-side shape as the other harnesses (the OPPOSITE of the Half B
# evaluator image):
#   * /workspace is WRITABLE (the harness edits files to produce a patch)
#   * the container joins the `pollmevals-sandbox` INTERNAL network so it can
#     reach ONLY the LiteLLM proxy (bastion) -- no general egress. gptme talks
#     to the proxy (which meters every token); it never holds the upstream key.
#
# Pinned dependencies (Library-first; bump deliberately, never floating):
#   python   3.12-slim   (gptme is a pure-Python package; reuses the cached
#                          aider/goose/eval-py base layer)
#   gptme    0.31.0       (latest on PyPI 2026-06-03)
#   git      (Debian stable) -- gptme tracks edits; we capture the diff via git
#
# gptme headless / config gotchas (ENV-ONLY config, no config file needed):
#   * gptme reads provider config from env: OPENAI_BASE_URL + OPENAI_API_KEY
#     select the OpenAI-compatible endpoint (our proxy). The MODEL env (or the
#     -m flag) takes a `local/<model>` form -- gptme strips the `local/` prefix
#     and forwards the bare model name to the proxy, which is exactly the model
#     id LiteLLM exposes (e.g. qwen3-coder-30b). All injected by the recipe at
#     run time (proxy URL + key + model), NOT baked here.
#   * GPTME_LOGS_HOME points gptme's conversation logs inside the container HOME
#     so a fresh, possibly read-only-elsewhere bind never blocks log writes.
#   * gptme counts tokens with `tiktoken`, which LAZILY DOWNLOADS its encoding
#     file (cl100k_base / o200k_base) from openaipublic.blob.core.windows.net on
#     first use. The no-egress sandbox blocks that DNS, so an un-warmed image
#     fatals BEFORE it ever reaches the proxy (empirical: smoke iteration 1 died
#     with "Failed to resolve openaipublic.blob.core.windows.net"). Fix: warm
#     both base encodings into a baked TIKTOKEN_CACHE_DIR at BUILD time (build
#     has egress; only the run-time container is sealed). tiktoken keys each
#     blob by sha1(url), so a populated cache dir = a pure offline hit, zero net.
#   * `gptme -n ...` is non-interactive and implies --no-confirm, so the file/
#     shell tools auto-execute (a headless run must never wait on a prompt);
#     `-w .` pins the workspace to cwd (/workspace).
#
# Build:
#   docker build -t pollmevals-harness-gptme:0.1.0 infra/docker/harness-gptme/
#   (or: make harness-image-gptme)
#
# Run (referenced from DockerHarnessLauncher -- not invoked by humans directly):
#   docker run --rm \
#     --network=pollmevals-sandbox \
#     --cap-drop=ALL --security-opt=no-new-privileges:true \
#     --memory=2g --pids-limit=256 \
#     -v $(pwd)/snapshot:/workspace \
#     -e OPENAI_BASE_URL=http://pollmevals-litellm-proxy:4000/v1 \
#     -e OPENAI_API_KEY=$LITELLM_MASTER_KEY \
#     -e MODEL=local/<alias> \
#     pollmevals-harness-gptme:0.1.0 \
#     gptme -n -w . -m local/<alias> "<task prompt>"
#
# Smoke (no proxy needed):
#   docker run --rm pollmevals-harness-gptme:0.1.0   # -> prints gptme version

FROM python:3.12-slim AS base

# git: gptme tracks edits; the launcher captures the diff host-side via git.
# ca-certificates: TLS to the proxy bastion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Pinned gptme (library-first; bump deliberately). Installed at build time so
# the run-time container needs no PyPI access on the internal network.
RUN pip install --no-cache-dir gptme==0.31.0

# Warm tiktoken's encoding cache at BUILD time so the no-egress run-time
# container never tries to download cl100k_base/o200k_base from Azure blob (see
# header). World-readable dir so the non-root `harness` user can read it.
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken_cache
RUN mkdir -p "$TIKTOKEN_CACHE_DIR" \
    && python3 -c "import tiktoken; [tiktoken.get_encoding(e) for e in ('cl100k_base','o200k_base')]" \
    && chmod -R a+rX "$TIKTOKEN_CACHE_DIR"

# Non-root user: defense-in-depth on top of --cap-drop=ALL and
# --security-opt=no-new-privileges. The python base ships NO uid-1000 user, so
# we create one; uid 1000 matches the host bind owner so the produced patch is
# writable back on the host snapshot.
RUN useradd --create-home --uid 1000 harness
USER harness
WORKDIR /workspace

# Default git identity so gptme's edit-tracking never fails on a fresh snapshot.
RUN git config --global user.email "harness@pollmevals.local" \
    && git config --global user.name "pollmevals-harness" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /workspace

# Keep gptme's conversation logs inside the container HOME (see header).
ENV GPTME_LOGS_HOME=/home/harness/.local/share/gptme/logs

# Default command is a harmless version probe; DockerHarnessLauncher overrides
# `command` with the full `gptme -n ...` invocation. No restrictive ENTRYPOINT
# so the launcher can pass either an argv list or an explicit sh -c wrapper.
CMD ["gptme", "--version"]
