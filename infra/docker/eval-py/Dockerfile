# syntax=docker/dockerfile:1.7
#
# pollmevals-eval-py -- sandboxed Python test runner image for dynamic evaluators.
#
# Used by PythonCorrectnessEvaluator via SandboxRun to run a BigCodeBench-style
# `unittest` suite against a candidate solution.py. Image MUST stay
# self-contained: no network at evaluator-run time (network_mode=none), so every
# third-party lib a BigCodeBench solution/test imports must be baked in here.
#
# Pinned base; the scientific stack covers the libs BCB gold solutions import
# (numpy/pandas/matplotlib/seaborn/scikit-learn — surveyed across evals/task-packs/bcb-*).
#
# Build:
#   docker build -t pollmevals-eval-py:0.1.0 infra/docker/eval-py/
#
# Run (referenced from SandboxRun -- not invoked by humans directly):
#   docker run --rm \
#     --network=none --read-only --tmpfs /tmp:size=100m \
#     --memory=512m --pids-limit=50 --cap-drop=ALL \
#     --security-opt=no-new-privileges:true \
#     -e PYTHONDONTWRITEBYTECODE=1 \
#     -v $(pwd)/workspace:/workspace:ro \
#     pollmevals-eval-py:0.1.0 \
#     python /workspace/_runner.py
#
# v0.3+ note: when the sandbox runtime upgrades to gVisor / Kata, this image
# stays the same -- only the docker daemon's `runtime` flag changes.

FROM python:3.12-slim AS base

# Common BigCodeBench third-party deps. Baked at build time because the sandbox
# runs --network=none. Kept to a permissive scientific stack with headroom.
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    scipy \
    matplotlib \
    seaborn \
    scikit-learn \
    requests \
    Pillow \
    && python -c "import numpy, pandas, scipy, matplotlib, seaborn, sklearn, PIL, requests"

# Headless matplotlib + a writable config dir (the sandbox rootfs is read-only;
# only /tmp is a writable tmpfs at run time). Skip .pyc writes into the ro mount.
ENV MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/mpl \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Refuse to run as root (defense-in-depth on top of --cap-drop=ALL +
# --security-opt=no-new-privileges). SandboxRun passes the argv command
# directly (no shell), so leave the image ENTRYPOINT unset.
RUN useradd --create-home --uid 10001 runner
USER runner
WORKDIR /workspace

CMD ["python", "-c", "print('pollmevals-eval-py ready; provide command via SandboxRun')"]
