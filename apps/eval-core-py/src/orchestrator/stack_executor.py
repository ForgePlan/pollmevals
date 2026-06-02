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

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.orchestrator.cost import PricingTuple, compute_cost

logger = logging.getLogger(__name__)

# Default LiteLLM proxy endpoint (Wave 1 infra). All harness model calls
# traverse this so we (a) choose the model and (b) meter every token.
DEFAULT_PROXY_BASE_URL = "http://localhost:4000"


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


# Proven recipes (validated end-to-end via the proxy). aider is the RFC-006
# first slice (aider x qwen x be_01).
_PROVEN_RECIPES: dict[str, _RecipeBuilder] = {
    "aider": _aider_invocation,
}

# Known harnesses whose recipe is proven in spikes but lands at its per-stack
# smoke (RFC-006 Phase 5). Keying off the stack.yaml ``agent_cli`` value.
_PENDING_RECIPES: frozenset[str] = frozenset(
    {
        "claude-code",
        "codex",
        "opencode",
        "goose",
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
        # PROXY_ONLY — the security-sensitive bridge is an open RFC-006 decision.
        raise NetworkPolicyNotConfigured(
            "PROXY_ONLY egress bridge is an open RFC-006 decision "
            "(sidecar-in-container-net vs host-gateway firewall). Wire it in "
            f"Phase 2 for proxy {plan.proxy_host}:{plan.proxy_port}."
        )
    return kwargs


class DockerHarnessLauncher:
    """Real HarnessLauncher — RFC-006 Phase 2 (NOT wired in Phase 1).

    Present as the typed seam + provenance anchor; ``launch()`` raises until
    Phase 2 builds the CLI sandbox images and resolves the proxy-only bridge.
    The pure ``build_docker_run_kwargs`` above is already testable.
    """

    async def launch(self, plan: HarnessRunPlan) -> HarnessRunOutcome:
        raise NotImplementedError(
            "DockerHarnessLauncher.launch is RFC-006 Phase 2 — needs the CLI "
            "sandbox image + the proxy-only network bridge. Phase 1 uses "
            "FakeHarnessLauncher."
        )


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
        proxy_base_url: str = DEFAULT_PROXY_BASE_URL,
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
