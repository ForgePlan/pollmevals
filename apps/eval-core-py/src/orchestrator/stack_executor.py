"""Stack executor — Half A candidate path: run an agent-CLI harness in a sandbox.

RFC-006 Phase 1 (no Docker, mocked). Provides the core executor + the per-CLI
proxy-config builder + patch/trace/cost capture behind a Protocol seam, so unit
tests run without Docker or network. NO spend.

Where this sits in the pipeline (two-half sandbox, RFC-006):

    Half A — candidate (THIS module): run the harness CLI -> produce a patch.
    Half B — evaluator (evaluators/sandbox/runner.py): run the produced code
             -> scores. Already built.

The executor produces the patch that Half B then scores.

Design discipline (mirrors existing seams):
  * EvalCaller / FakeEvalCaller (eval_caller.py) — the Protocol-seam pattern:
    a real implementation + a deterministic Fake for unit tests. Here the seam
    is ``HarnessLauncher`` (Docker is behind it), so ``StackExecutor`` is fully
    testable with ``FakeHarnessLauncher`` — no daemon, no network, no spend.
  * SandboxRun (evaluators/sandbox/runner.py) — docker-py + frozen security
    policy. Half B is ``network=none`` + ``read_only=True``; Half A is the
    opposite (writable /workspace + a single allowed egress to the LiteLLM
    proxy), so it CANNOT reuse SandboxRun — hence a distinct launcher seam.

Scope split:
  * ``raw-llm`` (execution.mode = direct_completion) stays on InspectEvalCaller.
  * Every ``repository_patch`` stack (aider, claude-code, codex, goose,
    openhands, opencode, hermes, ...) runs through StackExecutor.

Phase boundary: the real ``DockerHarnessLauncher`` (network bridge + image run)
lands in RFC-006 Phase 2. Phase 1 ships the Protocol, the deterministic Fake,
the pure docker-kwargs builder (tested), and the full executor orchestration.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.orchestrator.cost import PricingTuple, compute_cost

logger = logging.getLogger(__name__)

# Default LiteLLM proxy endpoint (Wave 1 infra). All harness model calls
# traverse this so we (a) choose the model and (b) meter every token.
DEFAULT_PROXY_BASE_URL = "http://localhost:4000"

# RFC-006 network decision A (2026-06-02): the harness runs on a Docker
# `internal` network with the LiteLLM proxy attached as the only reachable host
# (bastion). The internal net has NO external route, so the harness reaches ONLY
# the proxy -- no NET_ADMIN needed, cap_drop ALL holds, portable Linux/macOS/CI.
SANDBOX_NETWORK = "pollmevals-sandbox"
PROXY_CONTAINER = "pollmevals-litellm-proxy"
# In-sandbox the proxy is addressed by its container name (Docker DNS), NOT
# localhost -- localhost:4000 only works from the host, and the internal net has
# no host route. This is what gets baked into the harness OPENAI_API_BASE.
SANDBOX_PROXY_BASE_URL = f"http://{PROXY_CONTAINER}:4000"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StackExecutorError(Exception):
    """Base class for all stack-executor errors."""


class UnsupportedHarnessError(StackExecutorError):
    """Raised when an ``agent_cli`` has no known proxy recipe at all."""


class HarnessRecipePending(StackExecutorError):
    """Raised for a KNOWN harness whose proxy recipe is not yet codified.

    The recipe is proven (memory: research-cli-harness-execution) but is
    validated + landed at its per-stack smoke (RFC-006 Phase 5). Surfacing this
    distinctly from UnsupportedHarnessError keeps "we haven't wired it yet" from
    masquerading as "we don't support it".
    """


class NetworkPolicyNotConfigured(StackExecutorError):
    """Raised when the PROXY_ONLY network bridge is requested before Phase 2.

    The proxy-only egress bridge (the RFC-006 "crux") is a security-sensitive
    open decision (sidecar-in-container-net vs host-gateway firewall rule). It
    is intentionally NOT baked into the kwargs builder until that decision is
    made — this exception is the single, explicit seam where it plugs in.
    """


# ---------------------------------------------------------------------------
# StackAdapter — executor-side parse of stacks/<slug>/stack.yaml
# ---------------------------------------------------------------------------
#
# Distinct from contracts.StackPin (the write-once run-pin: stack_id + sha256).
# This is the OPERATIONAL view the executor needs. ``extra="ignore"`` because
# stack.yaml carries many keys this module does not consume (schema_version,
# layers, input_contract, output_contract); we model only execution/limits/
# sandbox and let the rest pass through untouched.


class ExecutionMode(StrEnum):
    """How a stack produces its output."""

    DIRECT_COMPLETION = "direct_completion"  # raw-llm -> InspectEvalCaller
    REPOSITORY_PATCH = "repository_patch"  # CLI harness -> StackExecutor


class ExecutionSpec(BaseModel):
    """``execution:`` block of stack.yaml."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    mode: ExecutionMode
    command: str
    args: list[str] = Field(default_factory=list)


class LimitsSpec(BaseModel):
    """``limits:`` block — wall-clock / tool-call / token caps."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    max_wall_clock_seconds: int = 300
    max_tool_calls: int = 0
    max_input_tokens: int = 50_000
    max_output_tokens: int = 10_000


class SandboxSpec(BaseModel):
    """``sandbox:`` block — isolation hints."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    network: bool = False
    writable_paths: list[str] = Field(default_factory=lambda: ["/workspace"])


class StackAdapter(BaseModel):
    """Operational parse of one ``stacks/<slug>/stack.yaml`` adapter."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    slug: str
    name: str = ""
    agent_cli: str | None = None
    base_model_slug: str = "configurable"
    execution: ExecutionSpec
    limits: LimitsSpec = Field(default_factory=LimitsSpec)
    sandbox: SandboxSpec = Field(default_factory=SandboxSpec)

    @classmethod
    def from_yaml_text(cls, text: str) -> StackAdapter:
        """Parse adapter YAML text into a StackAdapter (validates the schema)."""
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError("stack.yaml must parse to a mapping")
        return cls.model_validate(data)

    @classmethod
    def from_yaml_path(cls, path: Path) -> StackAdapter:
        """Load + parse ``stacks/<slug>/stack.yaml`` from disk."""
        return cls.from_yaml_text(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Per-CLI proxy recipe — how one harness is pointed at the proxy + given a task
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProxyInvocation:
    """Everything needed to point one harness CLI at the LiteLLM proxy.

    Fields:
        env:          Env vars injected into the sandbox (proxy base + key).
        config_files: Relative-path -> file-content map written into the
                      sandbox before the run (e.g. codex config.toml). Empty
                      for env-only CLIs like aider.
        extra_args:   Args appended to ``execution.command + execution.args`` to
                      select the model / provider (e.g. ``--model openai/<alias>``).
        prompt_args:  Args that deliver the task prompt (e.g. ``--message <p>``).
    """

    env: dict[str, str]
    config_files: dict[str, str]
    extra_args: list[str]
    prompt_args: list[str]


# A recipe builder takes (proxy_base_url, api_key, model_alias, prompt).
_RecipeBuilder = Callable[[str, str, str, str], ProxyInvocation]


def _aider_invocation(
    proxy_base_url: str, api_key: str, model_alias: str, prompt: str
) -> ProxyInvocation:
    """Aider recipe — PROVEN first slice (2026-06-02 spike; memory).

    aider is model-agnostic: it reads ``OPENAI_API_BASE`` / ``OPENAI_API_KEY``
    and takes the model as ``--model openai/<alias>``. The task is delivered
    non-interactively via ``--message`` (stack.yaml already pins
    ``--no-pretty --yes``).
    """
    base = proxy_base_url.rstrip("/")
    return ProxyInvocation(
        env={
            "OPENAI_API_BASE": f"{base}/v1",
            "OPENAI_API_KEY": api_key,
        },
        config_files={},
        extra_args=["--model", f"openai/{model_alias}"],
        prompt_args=["--message", prompt],
    )


def _goose_invocation(
    proxy_base_url: str, api_key: str, model_alias: str, prompt: str
) -> ProxyInvocation:
    """Goose recipe — PROVEN (2026-06-03 isolation smoke; memory).

    Block's goose is model-agnostic via an OpenAI-compatible provider. Unlike
    aider's single ``OPENAI_API_BASE``, goose splits the endpoint into
    ``OPENAI_HOST`` (scheme+host, NO path) + ``OPENAI_BASE_PATH`` (the chat
    route), and selects provider/model via ``GOOSE_PROVIDER`` / ``GOOSE_MODEL``.
    ``GOOSE_DISABLE_KEYRING`` (no system keyring in a sandbox container) and
    ``GOOSE_MODE=auto`` (never block waiting on a tool-call confirmation) are
    baked into the image; set here too so the recipe is self-contained. The
    model is chosen by env, so ``extra_args`` is empty; the prompt rides ``-t``
    and the ``goose run --no-session --with-builtin developer`` scaffolding
    lives in stack.yaml ``execution.args``.
    """
    base = proxy_base_url.rstrip("/")
    return ProxyInvocation(
        env={
            "GOOSE_PROVIDER": "openai",
            "GOOSE_MODEL": model_alias,
            "GOOSE_MODE": "auto",
            "GOOSE_DISABLE_KEYRING": "1",
            "OPENAI_API_KEY": api_key,
            "OPENAI_HOST": base,
            "OPENAI_BASE_PATH": "v1/chat/completions",
        },
        config_files={},
        extra_args=[],
        prompt_args=["-t", prompt],
    )


# Proven recipes (validated end-to-end via the proxy). aider is the RFC-006
# first slice (aider x qwen x be_01); goose is the second harness (2026-06-03),
# a model-agnostic peer that runs the same coder models for a clean comparison.
_PROVEN_RECIPES: dict[str, _RecipeBuilder] = {
    "aider": _aider_invocation,
    "goose": _goose_invocation,
}

# Known harnesses whose recipe is proven in spikes but lands at its per-stack
# smoke (RFC-006 Phase 5). Keying off the stack.yaml ``agent_cli`` value.
_PENDING_RECIPES: frozenset[str] = frozenset(
    {
        "claude-code",
        "codex",
        "opencode",
        "openhands",
        "hermes",
        "cline",
        "pi",
        "forgeplan-framework",
    }
)


def build_proxy_invocation(
    agent_cli: str | None,
    *,
    proxy_base_url: str,
    api_key: str,
    model_alias: str,
    prompt: str,
) -> ProxyInvocation:
    """Resolve the proxy invocation for ``agent_cli``.

    Raises:
        UnsupportedHarnessError: ``agent_cli`` is None or completely unknown.
        HarnessRecipePending: known harness, recipe lands at its Phase-5 smoke.
    """
    if agent_cli is None:
        raise UnsupportedHarnessError("stack has no agent_cli (is it a raw-llm stack?)")
    builder = _PROVEN_RECIPES.get(agent_cli)
    if builder is not None:
        return builder(proxy_base_url, api_key, model_alias, prompt)
    if agent_cli in _PENDING_RECIPES:
        raise HarnessRecipePending(
            f"harness '{agent_cli}' recipe is proven but not yet codified "
            "(RFC-006 Phase 5 per-stack smoke); only 'aider' is wired in Phase 1"
        )
    raise UnsupportedHarnessError(f"unknown agent_cli '{agent_cli}'")


def supported_harnesses() -> frozenset[str]:
    """Return the set of agent_cli values wired in this phase (proven only)."""
    return frozenset(_PROVEN_RECIPES)


# ---------------------------------------------------------------------------
# Launcher seam — Docker is behind this Protocol (testable without a daemon)
# ---------------------------------------------------------------------------


class NetworkPolicy(StrEnum):
    """Sandbox egress policy for a harness run."""

    NONE = "none"  # fully isolated (Half B evaluator default)
    PROXY_ONLY = "proxy_only"  # the crux: allow ONLY the LiteLLM proxy host:port


@dataclass(frozen=True)
class HarnessRunPlan:
    """Fully-resolved instructions for one sandboxed harness run."""

    image: str
    command: list[str]
    workdir: str
    mount_dir: Path  # writable bind at /workspace
    environment: dict[str, str]
    config_files: dict[str, str]
    timeout_s: int
    network_policy: NetworkPolicy
    proxy_host: str
    proxy_port: int
    sandbox_network: str = SANDBOX_NETWORK


@dataclass(frozen=True)
class HarnessRunOutcome:
    """Raw outcome of one launcher run (pre-scoring)."""

    exit_code: int
    patch: str  # unified git diff captured from /workspace ("" if none)
    trace: str  # harness stdout / structured trace blob
    stderr: str
    input_tokens: int
    output_tokens: int
    tool_calls: int
    wall_ms: int
    timed_out: bool


@runtime_checkable
class HarnessLauncher(Protocol):
    """Protocol for running one harness plan in a sandbox.

    Implementors:
      * DockerHarnessLauncher — real path (RFC-006 Phase 2).
      * FakeHarnessLauncher   — deterministic mock for StackExecutor unit tests.
    """

    async def launch(self, plan: HarnessRunPlan) -> HarnessRunOutcome: ...


def build_docker_run_kwargs(plan: HarnessRunPlan) -> dict[str, object]:
    """Translate a HarnessRunPlan into docker-py ``containers.run`` kwargs.

    Pure + tested (the security-sensitive surface is worth pinning now even
    though ``launch()`` is Phase 2). Mirrors SandboxRun's frozen flags but for
    the candidate side: the workspace bind is **writable** (the harness must
    produce a patch) while keep-the-rest-locked-down still holds (cap_drop ALL,
    no-new-privileges, pids/mem limits).

    The network branch is the explicit Phase-2 seam:
      * NONE       -> ``network_mode="none"`` (fully isolated).
      * PROXY_ONLY -> raises NetworkPolicyNotConfigured until the proxy-only
                      bridge decision is made (RFC-006 crux).
    """
    kwargs: dict[str, object] = {
        "image": plan.image,
        "command": plan.command,
        "detach": True,
        "working_dir": plan.workdir,
        # ---- Security policy (candidate side) ----
        "read_only": False,  # harness must write to /workspace to produce a patch
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "mem_limit": "2g",  # harness CLIs are heavier than Half B evaluators
        "nano_cpus": 2_000_000_000,  # 2.0 CPU
        "pids_limit": 256,
        # ---- Writable workspace bind (the produced patch lives here) ----
        "volumes": {str(plan.mount_dir): {"bind": "/workspace", "mode": "rw"}},
        "environment": dict(plan.environment),
    }
    if plan.network_policy is NetworkPolicy.NONE:
        kwargs["network_mode"] = "none"
    else:
        # PROXY_ONLY — RFC-006 decision A: join the Docker `internal` sandbox
        # network where the LiteLLM proxy is the only reachable host (bastion).
        # No host route on that net, so this is the entire egress surface.
        if not plan.sandbox_network:
            raise NetworkPolicyNotConfigured(
                "PROXY_ONLY requires a sandbox_network (RFC-006 decision A: the "
                "Docker internal bastion network the proxy is attached to)"
            )
        kwargs["network"] = plan.sandbox_network
    return kwargs


# aider prints a usage line like "Tokens: 1.2k sent, 850 received." at the end
# of a run. Best-effort parse for the first run; proxy-spend reconciliation
# (the harness-agnostic source) is the Phase 4 refinement.
_AIDER_TOKENS_RE = re.compile(
    r"Tokens:\s*([\d.]+)\s*([km]?)\s*sent.*?([\d.]+)\s*([km]?)\s*received",
    re.IGNORECASE,
)


def _scale(value: str, suffix: str) -> int:
    mult = {"k": 1_000, "m": 1_000_000}.get(suffix.lower(), 1)
    return int(float(value) * mult)


class DockerHarnessLauncher:
    """Real HarnessLauncher (RFC-006 Phase 3).

    Runs the harness in a fresh container on the internal bastion network
    (decision A) against a writable /workspace bind, then captures the produced
    patch HOST-side via git so the harness command stays a clean argv list (no
    shell-quoting of the multi-line task prompt):

        1. host-side: ensure /workspace is a git repo + record a base commit
        2. container: run ``plan.command`` (argv, no shell) — the harness edits
           /workspace and may auto-commit
        3. host-side: ``git add -A && git diff --cached <base>`` — robustly
           captures committed + working-tree + new files relative to the base

    Token metering is best-effort from the harness self-report for the first
    run; the proxy is the metered source of truth for cost reconciliation later.

    docker-py is synchronous; ``launch`` wraps the blocking run in
    ``asyncio.to_thread`` (same discipline as SandboxRun in Half B).
    """

    def __init__(self) -> None:
        self._client: Any = None

    async def launch(self, plan: HarnessRunPlan) -> HarnessRunOutcome:
        return await asyncio.to_thread(self._run_sync, plan)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_client(self) -> Any:
        if self._client is None:
            try:
                import docker  # type: ignore[import-untyped]
            except ImportError as exc:
                raise ImportError(
                    "docker SDK not installed; add `docker>=7.1,<8` to "
                    "apps/eval-core-py/pyproject.toml dependencies."
                ) from exc
            # docker-py's from_env() defaults to /var/run/docker.sock and does
            # NOT read the docker CLI context. On macOS Docker Desktop the socket
            # lives under ~/.docker/run, so discover it like the CLI does.
            if "DOCKER_HOST" not in os.environ:
                for cand in (
                    Path.home() / ".docker" / "run" / "docker.sock",
                    Path("/var/run/docker.sock"),
                ):
                    if cand.exists():
                        os.environ["DOCKER_HOST"] = f"unix://{cand}"
                        break
            self._client = docker.from_env()
        return self._client

    @staticmethod
    def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
        # -c safe.directory=* avoids "dubious ownership" when the container
        # (uid 1000) and the host user differ on the bind-mounted .git.
        return subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", str(workspace), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def _ensure_git_base(self, workspace: Path) -> str:
        """Init (if needed) + commit the snapshot AS GIVEN, return base SHA."""
        if not (workspace / ".git").exists():
            self._git(workspace, "init", "-q")
            self._git(workspace, "config", "user.email", "harness@pollmevals.local")
            self._git(workspace, "config", "user.name", "pollmevals-harness")
        self._git(workspace, "add", "-A")
        self._git(workspace, "commit", "-q", "-m", "pollmevals-base", "--allow-empty")
        return self._git(workspace, "rev-parse", "HEAD").stdout.strip()

    def _capture_patch(self, workspace: Path, base_sha: str) -> str:
        """Unified diff of everything (committed + working + new) vs base."""
        self._git(workspace, "add", "-A")
        return self._git(workspace, "diff", "--cached", base_sha).stdout

    def _run_sync(self, plan: HarnessRunPlan) -> HarnessRunOutcome:
        workspace = plan.mount_dir
        base_sha = self._ensure_git_base(workspace)

        client = self._ensure_client()
        run_kwargs = build_docker_run_kwargs(plan)
        run_kwargs["command"] = plan.command  # argv list, no shell

        start_ns = time.monotonic_ns()
        container = client.containers.run(**run_kwargs)

        timed_out = False
        try:
            wait_result = container.wait(timeout=plan.timeout_s)
            exit_code = int(wait_result.get("StatusCode", -1))
        except Exception as exc:  # docker-py ReadTimeout on overrun
            logger.warning("Harness container timed out after %ds: %s", plan.timeout_s, exc)
            timed_out = True
            with contextlib.suppress(Exception):
                container.kill()
            exit_code = 137

        try:
            stdout = container.logs(stdout=True, stderr=False).decode(errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode(errors="replace")
        except Exception as exc:
            logger.warning("Harness log capture failed: %s", exc)
            stdout, stderr = "", ""

        with contextlib.suppress(Exception):
            container.remove(v=True, force=True)

        wall_ms = (time.monotonic_ns() - start_ns) // 1_000_000
        patch = self._capture_patch(workspace, base_sha)
        in_tok, out_tok = self._parse_tokens(stdout + "\n" + stderr)

        return HarnessRunOutcome(
            exit_code=exit_code,
            patch=patch,
            trace=stdout,
            stderr=stderr,
            input_tokens=in_tok,
            output_tokens=out_tok,
            tool_calls=0,
            wall_ms=int(wall_ms),
            timed_out=timed_out,
        )

    @staticmethod
    def _parse_tokens(text: str) -> tuple[int, int]:
        """Best-effort token counts from the harness self-report (else 0/0)."""
        m = _AIDER_TOKENS_RE.search(text)
        if m is None:
            return 0, 0
        return _scale(m.group(1), m.group(2)), _scale(m.group(3), m.group(4))


@dataclass
class FakeHarnessLauncher:
    """Deterministic mock HarnessLauncher for StackExecutor unit tests.

    Captures the last plan it was handed (so tests can assert on the assembled
    command / env / network policy) and returns a configurable outcome. Never
    touches Docker or the network.
    """

    outcome: HarnessRunOutcome = field(
        default_factory=lambda: HarnessRunOutcome(
            exit_code=0,
            patch="diff --git a/x b/x\n+ok\n",
            trace="fake-trace",
            stderr="",
            input_tokens=1000,
            output_tokens=500,
            tool_calls=3,
            wall_ms=4000,
            timed_out=False,
        )
    )
    last_plan: HarnessRunPlan | None = None

    async def launch(self, plan: HarnessRunPlan) -> HarnessRunOutcome:
        self.last_plan = plan
        return self.outcome


# ---------------------------------------------------------------------------
# StackExecutor — orchestration: adapter + proxy recipe -> plan -> result
# ---------------------------------------------------------------------------


class ExecStatus(StrEnum):
    """Terminal status of one stack execution."""

    OK = "ok"  # patch produced, exit 0
    NO_PATCH = "no_patch"  # ran clean but produced an empty diff
    TIMEOUT = "timeout"  # hit the wall-clock limit
    FAILED = "failed"  # non-zero exit / launcher error
    UNSUPPORTED = "unsupported"  # wrong mode / no recipe for this harness


def default_image_for_cli(agent_cli: str) -> str:
    """Default sandbox image name for a harness (built in RFC-006 Phase 2)."""
    return f"pollmevals-harness-{agent_cli}:0.1.0"


@dataclass(frozen=True)
class StackExecRequest:
    """All inputs to execute one (model x stack x task x seed) harness run.

    Mirrors EvalRequest (eval_caller.py) but carries the resolved StackAdapter
    + the task prompt + a writable repo snapshot dir (the harness mutates it).

    Fields:
        model_id:    Cost-attribution key (provider route, matches the
                     pricing_snapshot key, e.g. "openrouter/qwen/qwen-3-14b").
        model_alias: Proxy-facing alias the CLI sends (litellm model_name).
    """

    eval_id: str
    model_id: str
    model_alias: str
    stack: StackAdapter
    task_id: str
    task_prompt: str
    repo_snapshot_dir: Path
    seed: int
    timeout_s: int = 600


@dataclass(frozen=True)
class StackExecResult:
    """Outcome of one StackExecutor.execute() invocation."""

    request: StackExecRequest
    status: ExecStatus
    patch: str | None
    trace: str
    cost_usd: Decimal
    input_tokens: int
    output_tokens: int
    tool_calls: int
    wall_ms: int
    error_detail: str | None
    started_at: datetime
    completed_at: datetime


@dataclass
class _TokenStats:
    """Minimal EvalStatsLike for compute_cost (needs only token counts).

    Not frozen: the EvalStatsLike protocol declares ``input_tokens`` /
    ``output_tokens`` as settable variables, which a frozen dataclass would
    expose as read-only (mypy --strict rejects the mismatch).
    """

    input_tokens: int
    output_tokens: int


class StackExecutor:
    """Run a ``repository_patch`` stack: adapter + proxy recipe -> patch + cost.

    Args:
        launcher: any HarnessLauncher (DockerHarnessLauncher / FakeHarnessLauncher).
        proxy_base_url: LiteLLM proxy base (harness model calls route here).
        api_key: proxy auth (LITELLM_MASTER_KEY — NOT the upstream provider key).
        pricing_snapshot: model_id -> PricingTuple, frozen at run start
            (RFC-001 Invariant #3). Cost is computed from proxy-metered tokens.
        image_resolver: agent_cli -> image name (injectable for tests).
    """

    def __init__(
        self,
        *,
        launcher: HarnessLauncher,
        proxy_base_url: str = SANDBOX_PROXY_BASE_URL,
        api_key: str = "",
        pricing_snapshot: dict[str, PricingTuple] | None = None,
        image_resolver: Callable[[str], str] = default_image_for_cli,
    ) -> None:
        self._launcher = launcher
        self._proxy_base_url = proxy_base_url.rstrip("/")
        self._api_key = api_key
        self._pricing_snapshot = pricing_snapshot or {}
        self._image_resolver = image_resolver

    def _proxy_host_port(self) -> tuple[str, int]:
        """Split the proxy base URL into (host, port) for the network bridge."""
        netloc = self._proxy_base_url.split("://", 1)[-1].split("/", 1)[0]
        host, _, port = netloc.partition(":")
        return host or "localhost", int(port) if port.isdigit() else 80

    async def execute(self, request: StackExecRequest) -> StackExecResult:
        """Execute one harness run and map its outcome to a StackExecResult.

        Never raises on a harness/launcher failure — failures are captured in
        ``status`` + ``error_detail`` (FR-009 discipline: a result is always
        produced). Re-raises nothing the launcher emits except programmer errors.
        """
        started_at = datetime.now(UTC)
        agent_cli = request.stack.agent_cli

        # Guard 1: this executor only handles repository_patch stacks.
        if request.stack.execution.mode is not ExecutionMode.REPOSITORY_PATCH:
            return self._unsupported(
                request,
                started_at,
                f"mode '{request.stack.execution.mode.value}' is not "
                "repository_patch (raw-llm runs through InspectEvalCaller)",
            )

        # Guard 2: resolve the proxy recipe (unsupported / pending -> UNSUPPORTED).
        try:
            invocation = build_proxy_invocation(
                agent_cli,
                proxy_base_url=self._proxy_base_url,
                api_key=self._api_key,
                model_alias=request.model_alias,
                prompt=request.task_prompt,
            )
        except (UnsupportedHarnessError, HarnessRecipePending) as exc:
            return self._unsupported(request, started_at, str(exc))

        # agent_cli is guaranteed non-None here (build_proxy_invocation guards it).
        assert agent_cli is not None

        # Assemble the full command: base command + adapter args + model + prompt.
        command = [
            request.stack.execution.command,
            *request.stack.execution.args,
            *invocation.extra_args,
            *invocation.prompt_args,
        ]
        host, port = self._proxy_host_port()
        plan = HarnessRunPlan(
            image=self._image_resolver(agent_cli),
            command=command,
            workdir="/workspace",
            mount_dir=request.repo_snapshot_dir,
            environment=invocation.env,
            config_files=invocation.config_files,
            timeout_s=min(request.timeout_s, request.stack.limits.max_wall_clock_seconds),
            network_policy=NetworkPolicy.PROXY_ONLY,
            proxy_host=host,
            proxy_port=port,
        )

        # Launch (the only place that can fail with an environment error).
        try:
            outcome = await self._launcher.launch(plan)
        except Exception as exc:  # graceful: capture, never drop (FR-009)
            logger.exception("Harness launch failed for eval_id=%s", request.eval_id)
            return self._failed(request, started_at, f"launcher error: {type(exc).__name__}: {exc}")

        return self._from_outcome(request, started_at, outcome)

    # ------------------------------------------------------------------
    # Outcome -> result mapping
    # ------------------------------------------------------------------

    def _cost(self, request: StackExecRequest, outcome: HarnessRunOutcome) -> Decimal:
        """Cost from proxy-metered tokens x the pinned pricing for this model."""
        pricing = self._pricing_snapshot.get(request.model_id)
        if pricing is None:
            return Decimal("0")
        return compute_cost(
            _TokenStats(outcome.input_tokens, outcome.output_tokens),
            pricing,
        )

    def _from_outcome(
        self,
        request: StackExecRequest,
        started_at: datetime,
        outcome: HarnessRunOutcome,
    ) -> StackExecResult:
        if outcome.timed_out:
            status = ExecStatus.TIMEOUT
            error_detail: str | None = f"timed out after {request.timeout_s}s"
            patch: str | None = outcome.patch or None
        elif outcome.exit_code != 0:
            status = ExecStatus.FAILED
            error_detail = f"harness exit_code={outcome.exit_code}"
            patch = outcome.patch or None
        elif not outcome.patch.strip():
            status = ExecStatus.NO_PATCH
            error_detail = "harness produced an empty diff"
            patch = None
        else:
            status = ExecStatus.OK
            error_detail = None
            patch = outcome.patch

        return StackExecResult(
            request=request,
            status=status,
            patch=patch,
            trace=outcome.trace,
            cost_usd=self._cost(request, outcome),
            input_tokens=outcome.input_tokens,
            output_tokens=outcome.output_tokens,
            tool_calls=outcome.tool_calls,
            wall_ms=outcome.wall_ms,
            error_detail=error_detail,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )

    def _unsupported(
        self, request: StackExecRequest, started_at: datetime, detail: str
    ) -> StackExecResult:
        return self._terminal(request, started_at, ExecStatus.UNSUPPORTED, detail)

    def _failed(
        self, request: StackExecRequest, started_at: datetime, detail: str
    ) -> StackExecResult:
        return self._terminal(request, started_at, ExecStatus.FAILED, detail)

    def _terminal(
        self,
        request: StackExecRequest,
        started_at: datetime,
        status: ExecStatus,
        detail: str,
    ) -> StackExecResult:
        """Build a zero-cost result for a pre-launch terminal condition."""
        return StackExecResult(
            request=request,
            status=status,
            patch=None,
            trace="",
            cost_usd=Decimal("0"),
            input_tokens=0,
            output_tokens=0,
            tool_calls=0,
            wall_ms=0,
            error_detail=detail,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
