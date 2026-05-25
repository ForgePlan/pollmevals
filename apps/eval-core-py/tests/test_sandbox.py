"""Tests for SandboxRun (docker-py wrapper).

The Docker daemon and the docker SDK are mocked at module level so these
tests run without a real container. A separate `test_sandbox_integration.py`
would exercise the real daemon but is NOT shipped in this PR -- it requires
the pollmevals-eval-ts image pre-built and runs much slower (~5s per case).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.evaluators.sandbox import (
    SandboxConfig,
    SandboxRun,
)


def _make_fake_container(
    *,
    exit_code: int = 0,
    stdout: bytes = b"",
    stderr: bytes = b"",
    wait_timeout: bool = False,
) -> MagicMock:
    """Fake docker.models.containers.Container -- programmable per test."""
    container = MagicMock()
    if wait_timeout:
        container.wait.side_effect = TimeoutError("read timeout")
    else:
        container.wait.return_value = {"StatusCode": exit_code}

    # logs(stdout=...) / logs(stderr=...) are called twice -- one per stream.
    def logs_side_effect(*, stdout: bool = False, stderr: bool = False, **_kw: Any) -> bytes:
        if stdout and not stderr:
            return locals_outer["_stdout"]
        if stderr and not stdout:
            return locals_outer["_stderr"]
        return b""

    locals_outer = {"_stdout": stdout, "_stderr": stderr}
    container.logs.side_effect = logs_side_effect
    container.attrs = {"State": {"ExitCode": exit_code}}
    return container


def _make_fake_client(container: MagicMock) -> MagicMock:
    client = MagicMock()
    client.containers.run.return_value = container
    return client


class TestSandboxConfigDefaults:
    def test_frozen_defaults_match_policy(self) -> None:
        """SandboxConfig defaults match security-sandbox.md v0.1.0."""
        cfg = SandboxConfig(image="alpine", command=["echo", "hi"])
        assert cfg.mem_limit == "512m"
        assert cfg.nano_cpus == 1_000_000_000  # 1.0 CPU
        assert cfg.pids_limit == 50
        assert cfg.tmpfs == {"/tmp": "size=100m"}
        assert cfg.timeout_s == 60
        assert cfg.environment == {}
        assert cfg.mount_dir is None


class TestSandboxRunHappyPath:
    @pytest.mark.asyncio
    async def test_exit_zero_returns_stdout(self, tmp_path: Path) -> None:
        container = _make_fake_container(
            exit_code=0,
            stdout=b"hello world\n",
            stderr=b"",
        )
        fake_client = _make_fake_client(container)

        runner = SandboxRun()
        with patch.object(runner, "_ensure_client", return_value=fake_client):
            result = await runner.run(
                SandboxConfig(image="alpine:latest", command=["echo", "hello world"])
            )

        assert result.exit_code == 0
        assert result.stdout == "hello world\n"
        assert result.stderr == ""
        assert result.timed_out is False
        assert result.wall_ms >= 0
        container.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_security_flags_passed_to_docker(self, tmp_path: Path) -> None:
        """Every frozen-policy flag must reach containers.run kwargs."""
        container = _make_fake_container(exit_code=0)
        fake_client = _make_fake_client(container)

        runner = SandboxRun()
        with (
            patch.object(runner, "_ensure_client", return_value=fake_client),
            # _make_ulimit imports docker.types -- bypass for the test
            patch(
                "src.evaluators.sandbox.runner._make_ulimit",
                side_effect=lambda spec: spec,
            ),
        ):
            await runner.run(SandboxConfig(image="alpine:latest", command=["true"]))

        kwargs = fake_client.containers.run.call_args.kwargs
        assert kwargs["network_mode"] == "none"
        assert kwargs["read_only"] is True
        assert kwargs["tmpfs"] == {"/tmp": "size=100m"}
        assert kwargs["mem_limit"] == "512m"
        assert kwargs["nano_cpus"] == 1_000_000_000
        assert kwargs["pids_limit"] == 50
        assert kwargs["cap_drop"] == ["ALL"]
        assert kwargs["security_opt"] == ["no-new-privileges:true"]
        assert kwargs["detach"] is True
        # Ulimits: nofile + fsize
        ulimit_names = {u["name"] for u in kwargs["ulimits"]}
        assert ulimit_names == {"nofile", "fsize"}

    @pytest.mark.asyncio
    async def test_mount_dir_becomes_readonly_workspace_bind(self, tmp_path: Path) -> None:
        container = _make_fake_container(exit_code=0)
        fake_client = _make_fake_client(container)

        runner = SandboxRun()
        with (
            patch.object(runner, "_ensure_client", return_value=fake_client),
            patch(
                "src.evaluators.sandbox.runner._make_ulimit",
                side_effect=lambda spec: spec,
            ),
        ):
            await runner.run(
                SandboxConfig(
                    image="alpine:latest",
                    command=["ls", "/workspace"],
                    mount_dir=tmp_path,
                )
            )

        volumes = fake_client.containers.run.call_args.kwargs["volumes"]
        assert volumes == {str(tmp_path): {"bind": "/workspace", "mode": "ro"}}


class TestSandboxRunTimeout:
    @pytest.mark.asyncio
    async def test_timeout_kills_container_and_marks_timed_out(self) -> None:
        container = _make_fake_container(
            exit_code=137,
            stdout=b"",
            stderr=b"killed",
            wait_timeout=True,
        )
        fake_client = _make_fake_client(container)

        runner = SandboxRun()
        with (
            patch.object(runner, "_ensure_client", return_value=fake_client),
            patch(
                "src.evaluators.sandbox.runner._make_ulimit",
                side_effect=lambda spec: spec,
            ),
        ):
            result = await runner.run(
                SandboxConfig(image="alpine:latest", command=["sleep", "999"], timeout_s=1)
            )

        assert result.timed_out is True
        container.kill.assert_called_once()
        # exit_code should be the SIGKILL signal or what container.attrs says.
        assert result.exit_code == 137
        container.remove.assert_called_once()


class TestSandboxRunMissingSDK:
    @pytest.mark.asyncio
    async def test_ensure_client_raises_when_docker_sdk_missing(self) -> None:
        runner = SandboxRun()
        with (
            patch.dict("sys.modules", {"docker": None}),
            pytest.raises(ImportError, match="docker SDK not installed"),
        ):
            # _ensure_client is sync; invoke directly so we bypass to_thread.
            runner._ensure_client()
