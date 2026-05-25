"""SandboxRun -- Docker-backed code-execution helper for dynamic evaluators.

Phase 2D Slice 2 part 2 (per NOTE-007 static/dynamic boundary rule).

Frozen policy (verbatim from docs/04-runbook/09-sandbox-security.md):

    network_mode: none
    read_only: true
    tmpfs:
      - /tmp:size=100M
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 50
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    ulimits:
      nofile: 1024
      fsize: 10485760
    hard timeout

These are MANDATORY defaults — callers may make limits stricter but never
looser. Loose limits = security debt; future hardening (v0.3 gVisor / Kata,
v1.0 Firecracker) replaces the runtime but keeps these flags.

Library-first (CLAUDE.md, 2026-05-25):
  docker SDK: Context7 /docker/docker-py confirmed `client.containers.run(...)`
  accepts every flag above verbatim (network_mode, read_only, tmpfs, mem_limit,
  cap_drop, security_opt, pids_limit). Pinned: docker>=7.1,<8 in pyproject.toml.

Async surface:
  docker-py is synchronous. Evaluator.evaluate is async. SandboxRun.run()
  wraps the blocking docker call in `asyncio.to_thread()` so the evaluator
  stays non-blocking while the container executes. This matches how
  ComplexityEvaluator wraps the synchronous lizard Python API.

Web validation (2026-05-25): industry consensus (arxiv 2603.02277,
dev.to "4 ways to sandbox untrusted code 2026", Bunnyshell sandboxed-env
guide) is that **Docker alone is insufficient** for hardened untrusted-code
isolation -- container escapes give host access. Our roadmap aligns:
v0.1 Docker rootless -> v0.3 gVisor/Kata -> v1.0 Firecracker. This module
implements the v0.1 baseline. The class signature is stable so v0.3+
replaces the runtime without touching evaluator code.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Frozen sandbox-policy defaults (security-sandbox.md v0.1.0)
# ---------------------------------------------------------------------------

_DEFAULT_MEM_LIMIT: str = "512m"
_DEFAULT_NANO_CPUS: int = 1_000_000_000  # 1.0 CPU in nano-units (docker-py syntax)
_DEFAULT_TMPFS: dict[str, str] = {"/tmp": "size=100m"}
_DEFAULT_PIDS_LIMIT: int = 50
_DEFAULT_TIMEOUT_S: int = 60
_DEFAULT_SECURITY_OPT: tuple[str, ...] = ("no-new-privileges:true",)
_DEFAULT_CAP_DROP: tuple[str, ...] = ("ALL",)
# ulimits per policy (nofile, fsize); docker-py uses Ulimit dicts.
_DEFAULT_ULIMITS: tuple[dict[str, Any], ...] = (
    {"name": "nofile", "soft": 1024, "hard": 1024},
    {"name": "fsize", "soft": 10_485_760, "hard": 10_485_760},
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SandboxTimeoutError(Exception):
    """Raised when the container fails to finish within the configured timeout."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SandboxConfig:
    """Per-invocation sandbox configuration.

    Defaults to the frozen v0.1.0 policy. Callers may TIGHTEN any field
    (lower mem, fewer PIDs, shorter timeout) but must not loosen.

    Fields:
        image:        Docker image to run (e.g. 'pollmevals-eval-ts:0.1.0').
        command:      argv list passed to the container entrypoint. Arg-list
                      form only -- no shell string, no f-strings of user input.
        workdir:      WORKDIR inside the container (None = image default).
        mount_dir:    Host directory to expose read-only at /workspace.
                      Pass None to skip the mount (env-only invocation).
        environment:  Env vars set inside the container. Use this for
                      configuration; the network is disabled.
        timeout_s:    Hard wall-clock limit. Container is killed on overrun.
        mem_limit:    Docker mem_limit string (e.g. '256m', '1g').
        nano_cpus:    CPU quota in nano-units (1e9 = 1 CPU).
        tmpfs:        Mount table for tmpfs filesystems. Defaults: {/tmp: 100m}.
        pids_limit:   Max processes inside the container.
    """

    image: str
    command: list[str]
    workdir: str | None = None
    mount_dir: Path | None = None
    environment: dict[str, str] = field(default_factory=dict)
    timeout_s: int = _DEFAULT_TIMEOUT_S
    mem_limit: str = _DEFAULT_MEM_LIMIT
    nano_cpus: int = _DEFAULT_NANO_CPUS
    tmpfs: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_TMPFS))
    pids_limit: int = _DEFAULT_PIDS_LIMIT


@dataclass(frozen=True)
class SandboxResult:
    """Outcome of one sandboxed container run.

    Fields:
        exit_code: Container exit code. 0 = success, non-zero = process error.
                   When timed_out=True, exit_code is the kill signal (137 SIGKILL
                   on docker engine).
        stdout:    Decoded stdout (utf-8, errors=replace).
        stderr:    Decoded stderr (utf-8, errors=replace).
        timed_out: True when the container hit the SandboxConfig.timeout_s gate.
        wall_ms:   Approximate wall-clock duration (millis), measured from
                   container create to container wait return.
    """

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    wall_ms: int


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class SandboxRun:
    """Single-shot sandbox executor.

    Instances are stateless apart from the docker client connection. Reuse
    one instance across multiple `run()` calls within an evaluator instance.

    Usage::

        runner = SandboxRun()
        result = await runner.run(SandboxConfig(
            image="node:22-alpine",
            command=["sh", "-c", "echo hello"],
        ))
        if result.exit_code != 0:
            ...

    The runner does NOT pre-pull images -- the caller is responsible for
    image availability. This keeps the helper deterministic (no surprise
    network calls inside `run()`) and lets the caller decide whether image
    fetch should be a build-time step or a sandbox-time step.
    """

    def __init__(self) -> None:
        # Deferred import + client init: lets tests monkeypatch _client_factory
        # without requiring a real Docker daemon.
        self._client: Any = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, config: SandboxConfig) -> SandboxResult:
        """Run *config* in a fresh sandboxed container and return the result.

        Never raises on container failure -- exit_code captures it. Raises
        on docker-daemon errors (ImportError if SDK missing, connection
        errors if daemon unreachable) so the caller can surface the
        environment problem.
        """
        return await asyncio.to_thread(self._run_sync, config)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_client(self) -> Any:
        """Lazy-init the docker client. Raises ImportError if SDK missing."""
        if self._client is None:
            try:
                import docker  # type: ignore[import-untyped]
            except ImportError as exc:
                raise ImportError(
                    "docker SDK not installed; add `docker>=7.1,<8` to "
                    "apps/eval-core-py/pyproject.toml dependencies."
                ) from exc
            self._client = docker.from_env()
        return self._client

    def _build_run_kwargs(self, config: SandboxConfig) -> dict[str, Any]:
        """Translate SandboxConfig into docker-py containers.run kwargs.

        All security flags are derived from the frozen policy. The caller's
        SandboxConfig only controls image/command/env/limits-tightening.
        """
        kwargs: dict[str, Any] = {
            "image": config.image,
            "command": config.command,
            "detach": True,  # required to get a Container object for wait()
            # ---- Security policy (frozen, NEVER loosen) ----
            "network_mode": "none",
            "read_only": True,
            "tmpfs": config.tmpfs,
            "mem_limit": config.mem_limit,
            "nano_cpus": config.nano_cpus,
            "pids_limit": config.pids_limit,
            "cap_drop": list(_DEFAULT_CAP_DROP),
            "security_opt": list(_DEFAULT_SECURITY_OPT),
            "ulimits": [_make_ulimit(u) for u in _DEFAULT_ULIMITS],
            # ---- Per-config ----
            "environment": dict(config.environment),
        }
        if config.workdir is not None:
            kwargs["working_dir"] = config.workdir
        if config.mount_dir is not None:
            # Read-only bind mount (workspace = candidate output / fixture).
            kwargs["volumes"] = {
                str(config.mount_dir): {"bind": "/workspace", "mode": "ro"},
            }
        return kwargs

    def _run_sync(self, config: SandboxConfig) -> SandboxResult:
        """Blocking implementation invoked via asyncio.to_thread."""
        import time

        client = self._ensure_client()
        run_kwargs = self._build_run_kwargs(config)

        start_ns = time.monotonic_ns()
        container = client.containers.run(**run_kwargs)

        timed_out = False
        try:
            wait_result = container.wait(timeout=config.timeout_s)
            exit_code = int(wait_result.get("StatusCode", -1))
        except Exception as exc:
            # docker-py raises ReadTimeout (requests.exceptions) on wait-timeout.
            # The container is still alive; kill it deterministically.
            logger.warning("Sandbox container timed out after %ds: %s", config.timeout_s, exc)
            timed_out = True
            with contextlib.suppress(Exception):
                container.kill()
            # Re-fetch exit code after kill (SIGKILL -> 137).
            exit_code = 137
            with contextlib.suppress(Exception):
                container.reload()
                exit_code = int(container.attrs.get("State", {}).get("ExitCode", 137))

        # Capture logs BEFORE remove (logs are gone after container deletion).
        try:
            stdout_bytes = container.logs(stdout=True, stderr=False)
            stderr_bytes = container.logs(stdout=False, stderr=True)
        except Exception as exc:
            logger.warning("Sandbox log capture failed: %s", exc)
            stdout_bytes = b""
            stderr_bytes = b""

        try:
            container.remove(v=True, force=True)
        except Exception as exc:
            # Container cleanup is best-effort -- never blocks the result.
            logger.warning("Sandbox container cleanup failed: %s", exc)

        wall_ms = (time.monotonic_ns() - start_ns) // 1_000_000

        return SandboxResult(
            exit_code=exit_code,
            stdout=stdout_bytes.decode(errors="replace") if stdout_bytes else "",
            stderr=stderr_bytes.decode(errors="replace") if stderr_bytes else "",
            timed_out=timed_out,
            wall_ms=int(wall_ms),
        )


def _make_ulimit(spec: dict[str, Any]) -> Any:
    """Build a docker.types.Ulimit; deferred import keeps this module mockable."""
    import docker.types  # type: ignore[import-untyped]

    return docker.types.Ulimit(
        name=spec["name"],
        soft=spec["soft"],
        hard=spec["hard"],
    )
