"""Unit tests for the RFC-006 Phase 1 stack executor (Half A candidate path).

No Docker, no network, no spend — everything runs through FakeHarnessLauncher
and the pure builders. Mirrors the test_eval_caller.py class-grouping style.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.orchestrator.cost import PricingTuple
from src.orchestrator.stack_executor import (
    DEFAULT_PROXY_BASE_URL,
    DockerHarnessLauncher,
    ExecStatus,
    ExecutionMode,
    FakeHarnessLauncher,
    HarnessRecipePending,
    HarnessRunOutcome,
    HarnessRunPlan,
    NetworkPolicy,
    NetworkPolicyNotConfigured,
    StackAdapter,
    StackExecRequest,
    StackExecutor,
    UnsupportedHarnessError,
    build_docker_run_kwargs,
    build_proxy_invocation,
    default_image_for_cli,
    supported_harnesses,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_AIDER_YAML = """
schema_version: pollmevals.stack.v1
slug: aider
name: Aider
base_model_slug: configurable
agent_cli: aider
layers:
  L0_bare_llm: false
  L2_tools: true
execution:
  mode: repository_patch
  command: aider
  args:
    - --no-pretty
    - --yes
input_contract:
  receives: [task_prompt, repository_snapshot]
output_contract:
  produces: [patch, trace]
limits:
  max_wall_clock_seconds: 600
  max_tool_calls: 50
  max_input_tokens: 50000
  max_output_tokens: 10000
sandbox:
  network: false
  writable_paths:
    - /workspace
"""

_RAW_LLM_YAML = """
schema_version: pollmevals.stack.v1
slug: raw-llm
name: Raw LLM
agent_cli: null
execution:
  mode: direct_completion
  command: litellm
  args: []
limits:
  max_wall_clock_seconds: 300
"""


def _aider_adapter() -> StackAdapter:
    return StackAdapter.from_yaml_text(_AIDER_YAML)


def _request(stack: StackAdapter, tmp_path: Path, **overrides: object) -> StackExecRequest:
    defaults: dict[str, object] = {
        "eval_id": "abc123",
        "model_id": "openrouter/qwen/qwen-3-14b",
        "model_alias": "qwen-3-14b",
        "stack": stack,
        "task_id": "be_01_jwt_auth",
        "task_prompt": "Implement JWT auth middleware.",
        "repo_snapshot_dir": tmp_path,
        "seed": 1,
    }
    defaults.update(overrides)
    return StackExecRequest(**defaults)  # type: ignore[arg-type]


_PRICING = {
    "openrouter/qwen/qwen-3-14b": PricingTuple(
        "openrouter/qwen/qwen-3-14b",
        Decimal("0.20"),
        Decimal("0.80"),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
}


# ---------------------------------------------------------------------------
# StackAdapter parsing
# ---------------------------------------------------------------------------


class TestStackAdapter:
    def test_parses_aider_adapter(self) -> None:
        a = _aider_adapter()
        assert a.slug == "aider"
        assert a.agent_cli == "aider"
        assert a.execution.mode is ExecutionMode.REPOSITORY_PATCH
        assert a.execution.command == "aider"
        assert a.execution.args == ["--no-pretty", "--yes"]
        assert a.limits.max_wall_clock_seconds == 600
        assert a.sandbox.network is False

    def test_ignores_unknown_keys(self) -> None:
        # schema_version / layers / *_contract are not modelled; must not raise.
        a = _aider_adapter()
        assert a.name == "Aider"

    def test_raw_llm_mode_and_null_cli(self) -> None:
        a = StackAdapter.from_yaml_text(_RAW_LLM_YAML)
        assert a.execution.mode is ExecutionMode.DIRECT_COMPLETION
        assert a.agent_cli is None

    def test_from_yaml_path(self, tmp_path: Path) -> None:
        p = tmp_path / "stack.yaml"
        p.write_text(_AIDER_YAML, encoding="utf-8")
        a = StackAdapter.from_yaml_path(p)
        assert a.slug == "aider"

    def test_non_mapping_yaml_raises(self) -> None:
        with pytest.raises(ValueError, match="must parse to a mapping"):
            StackAdapter.from_yaml_text("- just\n- a\n- list\n")

    def test_limits_and_sandbox_defaults(self) -> None:
        a = StackAdapter.from_yaml_text(
            "slug: x\nexecution:\n  mode: repository_patch\n  command: x\n"
        )
        assert a.limits.max_wall_clock_seconds == 300
        assert a.sandbox.writable_paths == ["/workspace"]


# ---------------------------------------------------------------------------
# Proxy recipe builder
# ---------------------------------------------------------------------------


class TestProxyInvocation:
    def test_aider_recipe_is_proven(self) -> None:
        inv = build_proxy_invocation(
            "aider",
            proxy_base_url="http://localhost:4000",
            api_key="sk-local-xyz",
            model_alias="qwen-3-14b",
            prompt="do the thing",
        )
        assert inv.env["OPENAI_API_BASE"] == "http://localhost:4000/v1"
        assert inv.env["OPENAI_API_KEY"] == "sk-local-xyz"
        assert inv.extra_args == ["--model", "openai/qwen-3-14b"]
        assert inv.prompt_args == ["--message", "do the thing"]
        assert inv.config_files == {}

    def test_aider_strips_trailing_slash(self) -> None:
        inv = build_proxy_invocation(
            "aider",
            proxy_base_url="http://localhost:4000/",
            api_key="k",
            model_alias="m",
            prompt="p",
        )
        assert inv.env["OPENAI_API_BASE"] == "http://localhost:4000/v1"

    @pytest.mark.parametrize("cli", ["claude-code", "codex", "goose", "openhands", "opencode"])
    def test_known_but_pending_harness_raises_pending(self, cli: str) -> None:
        with pytest.raises(HarnessRecipePending, match="Phase 5"):
            build_proxy_invocation(
                cli, proxy_base_url="x", api_key="k", model_alias="m", prompt="p"
            )

    def test_unknown_harness_raises_unsupported(self) -> None:
        with pytest.raises(UnsupportedHarnessError, match="unknown agent_cli"):
            build_proxy_invocation(
                "nope", proxy_base_url="x", api_key="k", model_alias="m", prompt="p"
            )

    def test_none_cli_raises_unsupported(self) -> None:
        with pytest.raises(UnsupportedHarnessError, match="no agent_cli"):
            build_proxy_invocation(
                None, proxy_base_url="x", api_key="k", model_alias="m", prompt="p"
            )

    def test_supported_harnesses_is_aider_only_in_phase_1(self) -> None:
        assert supported_harnesses() == frozenset({"aider"})


# ---------------------------------------------------------------------------
# Docker kwargs builder (pure, security-sensitive surface)
# ---------------------------------------------------------------------------


def _plan(policy: NetworkPolicy, tmp_path: Path) -> HarnessRunPlan:
    return HarnessRunPlan(
        image="img:0.1.0",
        command=["aider", "--yes"],
        workdir="/workspace",
        mount_dir=tmp_path,
        environment={"OPENAI_API_KEY": "k"},
        config_files={},
        timeout_s=600,
        network_policy=policy,
        proxy_host="localhost",
        proxy_port=4000,
    )


class TestDockerRunKwargs:
    def test_workspace_bind_is_writable(self, tmp_path: Path) -> None:
        kw = build_docker_run_kwargs(_plan(NetworkPolicy.NONE, tmp_path))
        volumes = kw["volumes"]
        assert isinstance(volumes, dict)
        assert volumes[str(tmp_path)] == {"bind": "/workspace", "mode": "rw"}
        assert kw["read_only"] is False

    def test_security_flags_locked_down(self, tmp_path: Path) -> None:
        kw = build_docker_run_kwargs(_plan(NetworkPolicy.NONE, tmp_path))
        assert kw["cap_drop"] == ["ALL"]
        assert kw["security_opt"] == ["no-new-privileges:true"]
        assert kw["network_mode"] == "none"

    def test_proxy_only_is_an_open_decision(self, tmp_path: Path) -> None:
        # The crux: the proxy-only egress bridge is not baked in until Phase 2.
        with pytest.raises(NetworkPolicyNotConfigured, match="open RFC-006 decision"):
            build_docker_run_kwargs(_plan(NetworkPolicy.PROXY_ONLY, tmp_path))


# ---------------------------------------------------------------------------
# StackExecutor orchestration
# ---------------------------------------------------------------------------


class TestStackExecutorHappyPath:
    @pytest.mark.asyncio
    async def test_ok_status_and_patch(self, tmp_path: Path) -> None:
        launcher = FakeHarnessLauncher()
        ex = StackExecutor(launcher=launcher, pricing_snapshot=_PRICING)
        result = await ex.execute(_request(_aider_adapter(), tmp_path))
        assert result.status is ExecStatus.OK
        assert result.patch is not None and result.patch.startswith("diff --git")
        assert result.error_detail is None

    @pytest.mark.asyncio
    async def test_cost_computed_from_metered_tokens(self, tmp_path: Path) -> None:
        # 1000 in * 0.20 + 500 out * 0.80 = 200 + 400 = 600 / 1e6 = 0.0006
        launcher = FakeHarnessLauncher()
        ex = StackExecutor(launcher=launcher, pricing_snapshot=_PRICING)
        result = await ex.execute(_request(_aider_adapter(), tmp_path))
        assert result.cost_usd == Decimal("0.000600")
        assert result.input_tokens == 1000
        assert result.output_tokens == 500

    @pytest.mark.asyncio
    async def test_no_pricing_yields_zero_cost(self, tmp_path: Path) -> None:
        ex = StackExecutor(launcher=FakeHarnessLauncher())  # no pricing_snapshot
        result = await ex.execute(_request(_aider_adapter(), tmp_path))
        assert result.cost_usd == Decimal("0")

    @pytest.mark.asyncio
    async def test_command_assembled_and_proxy_only(self, tmp_path: Path) -> None:
        launcher = FakeHarnessLauncher()
        ex = StackExecutor(launcher=launcher, pricing_snapshot=_PRICING)
        await ex.execute(_request(_aider_adapter(), tmp_path, task_prompt="P"))
        plan = launcher.last_plan
        assert plan is not None
        assert plan.command == [
            "aider",
            "--no-pretty",
            "--yes",
            "--model",
            "openai/qwen-3-14b",
            "--message",
            "P",
        ]
        assert plan.network_policy is NetworkPolicy.PROXY_ONLY
        assert plan.mount_dir == tmp_path
        assert plan.proxy_host == "localhost"
        assert plan.proxy_port == 4000

    @pytest.mark.asyncio
    async def test_timeout_is_min_of_request_and_limit(self, tmp_path: Path) -> None:
        launcher = FakeHarnessLauncher()
        ex = StackExecutor(launcher=launcher, pricing_snapshot=_PRICING)
        # request 9999 vs adapter limit 600 -> 600
        await ex.execute(_request(_aider_adapter(), tmp_path, timeout_s=9999))
        assert launcher.last_plan is not None
        assert launcher.last_plan.timeout_s == 600


class TestStackExecutorFailureModes:
    @pytest.mark.asyncio
    async def test_empty_patch_is_no_patch(self, tmp_path: Path) -> None:
        launcher = FakeHarnessLauncher(
            outcome=HarnessRunOutcome(0, "   \n  ", "t", "", 10, 5, 0, 100, False)
        )
        ex = StackExecutor(launcher=launcher, pricing_snapshot=_PRICING)
        result = await ex.execute(_request(_aider_adapter(), tmp_path))
        assert result.status is ExecStatus.NO_PATCH
        assert result.patch is None

    @pytest.mark.asyncio
    async def test_nonzero_exit_is_failed(self, tmp_path: Path) -> None:
        launcher = FakeHarnessLauncher(
            outcome=HarnessRunOutcome(1, "diff --git a b\n", "t", "boom", 10, 5, 0, 100, False)
        )
        ex = StackExecutor(launcher=launcher)
        result = await ex.execute(_request(_aider_adapter(), tmp_path))
        assert result.status is ExecStatus.FAILED
        assert result.error_detail is not None and "exit_code=1" in result.error_detail

    @pytest.mark.asyncio
    async def test_timed_out_is_timeout(self, tmp_path: Path) -> None:
        launcher = FakeHarnessLauncher(
            outcome=HarnessRunOutcome(137, "", "t", "", 10, 5, 0, 600_000, True)
        )
        ex = StackExecutor(launcher=launcher)
        result = await ex.execute(_request(_aider_adapter(), tmp_path))
        assert result.status is ExecStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_direct_completion_is_unsupported(self, tmp_path: Path) -> None:
        raw = StackAdapter.from_yaml_text(_RAW_LLM_YAML)
        ex = StackExecutor(launcher=FakeHarnessLauncher())
        result = await ex.execute(_request(raw, tmp_path))
        assert result.status is ExecStatus.UNSUPPORTED
        assert result.error_detail is not None and "repository_patch" in result.error_detail

    @pytest.mark.asyncio
    async def test_pending_harness_is_unsupported_with_phase5_hint(self, tmp_path: Path) -> None:
        codex_yaml = _AIDER_YAML.replace("slug: aider", "slug: codex").replace(
            "agent_cli: aider", "agent_cli: codex"
        )
        codex = StackAdapter.from_yaml_text(codex_yaml)
        ex = StackExecutor(launcher=FakeHarnessLauncher())
        result = await ex.execute(_request(codex, tmp_path))
        assert result.status is ExecStatus.UNSUPPORTED
        assert result.error_detail is not None and "Phase 5" in result.error_detail

    @pytest.mark.asyncio
    async def test_launcher_exception_is_captured_not_raised(self, tmp_path: Path) -> None:
        class Boom:
            async def launch(self, plan: HarnessRunPlan) -> HarnessRunOutcome:
                raise RuntimeError("daemon down")

        ex = StackExecutor(launcher=Boom())
        result = await ex.execute(_request(_aider_adapter(), tmp_path))
        assert result.status is ExecStatus.FAILED
        assert result.error_detail is not None and "daemon down" in result.error_detail


# ---------------------------------------------------------------------------
# Phase-2 seam: Docker launcher is intentionally not wired yet
# ---------------------------------------------------------------------------


class TestPhase2Seam:
    @pytest.mark.asyncio
    async def test_docker_launcher_not_wired(self, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError, match="Phase 2"):
            await DockerHarnessLauncher().launch(_plan(NetworkPolicy.NONE, tmp_path))

    def test_default_image_name(self) -> None:
        assert default_image_for_cli("aider") == "pollmevals-harness-aider:0.1.0"

    def test_default_proxy_base_url(self) -> None:
        assert DEFAULT_PROXY_BASE_URL == "http://localhost:4000"
