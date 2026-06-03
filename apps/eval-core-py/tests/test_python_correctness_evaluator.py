"""Tests for PythonCorrectnessEvaluator (BigCodeBench unittest in sandbox).

Real Docker is NOT required: SandboxRun is replaced with a fake that returns a
programmed JSON document on stdout. One fake also snapshots the assembled
/workspace so the namespace-wiring (solution.py + test_run.py + _runner.py) is
asserted directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluators.protocol import Evaluator
from src.evaluators.python_correctness_evaluator import PythonCorrectnessEvaluator
from src.evaluators.sandbox import SandboxConfig, SandboxResult


class _FakeSandbox:
    """Fake SandboxRun — returns a programmed result; snapshots the mount dir."""

    def __init__(
        self,
        *,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        timed_out: bool = False,
        raise_exc: Exception | None = None,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.timed_out = timed_out
        self._raise_exc = raise_exc
        self.last_config: SandboxConfig | None = None
        self.mounted: dict[str, str] = {}

    async def run(self, config: SandboxConfig) -> SandboxResult:
        self.last_config = config
        if config.mount_dir is not None:
            for f in Path(config.mount_dir).glob("*"):
                if f.is_file():
                    self.mounted[f.name] = f.read_text(encoding="utf-8")
        if self._raise_exc is not None:
            raise self._raise_exc
        return SandboxResult(
            exit_code=self.exit_code,
            stdout=self.stdout,
            stderr=self.stderr,
            timed_out=self.timed_out,
            wall_ms=42,
        )


def _result_json(total: int = 5, passed: int = 5, failed: int = 0) -> str:
    return json.dumps({"numTotalTests": total, "numPassedTests": passed, "numFailedTests": failed})


@pytest.fixture
def pack(tmp_path: Path) -> Path:
    """A minimal bcb-style pack: packs_root/bcb-9999/gold/{test.py,meta.json}."""
    gold = tmp_path / "bcb-9999" / "gold"
    gold.mkdir(parents=True)
    (gold / "test.py").write_text(
        "import unittest\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_it(self):\n"
        "        self.assertEqual(task_func(2), 4)\n",
        encoding="utf-8",
    )
    (gold / "meta.json").write_text(json.dumps({"entry_point": "task_func"}), encoding="utf-8")
    return tmp_path


@pytest.fixture
def candidate(tmp_path: Path) -> Path:
    d = tmp_path / "out"
    d.mkdir()
    (d / "solution.py").write_text("def task_func(x):\n    return x * 2\n", encoding="utf-8")
    return d


class TestProtocol:
    def test_satisfies_protocol(self, tmp_path: Path) -> None:
        ev = PythonCorrectnessEvaluator(packs_root=tmp_path, sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        assert isinstance(ev, Evaluator)

    def test_name_is_correctness(self, tmp_path: Path) -> None:
        assert PythonCorrectnessEvaluator(packs_root=tmp_path).name == "correctness"


class TestSkips:
    async def test_skip_non_bcb_prefix(self, pack: Path, candidate: Path) -> None:
        ev = PythonCorrectnessEvaluator(packs_root=pack, sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        r = await ev.evaluate(str(candidate), "be_01_jwt_auth")
        assert r.skipped and r.score == 0.0

    async def test_skip_no_candidate(self, pack: Path, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        ev = PythonCorrectnessEvaluator(packs_root=pack, sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        r = await ev.evaluate(str(empty), "bcb-9999")
        assert r.skipped and "solution.py" in (r.skip_reason or "")

    async def test_skip_missing_gold(self, candidate: Path, tmp_path: Path) -> None:
        ev = PythonCorrectnessEvaluator(packs_root=tmp_path, sandbox_run=_FakeSandbox())  # type: ignore[arg-type]
        r = await ev.evaluate(str(candidate), "bcb-0000")  # no such pack under tmp_path
        assert r.skipped and "test.py" in (r.skip_reason or "")

    async def test_skip_docker_missing(self, pack: Path, candidate: Path) -> None:
        fake = _FakeSandbox(raise_exc=ImportError("docker SDK not installed"))
        ev = PythonCorrectnessEvaluator(packs_root=pack, sandbox_run=fake)  # type: ignore[arg-type]
        r = await ev.evaluate(str(candidate), "bcb-9999")
        assert r.skipped and "docker" in r.library_version


class TestScoring:
    async def test_all_pass(self, pack: Path, candidate: Path) -> None:
        fake = _FakeSandbox(stdout=_result_json(5, 5, 0))
        ev = PythonCorrectnessEvaluator(packs_root=pack, sandbox_run=fake)  # type: ignore[arg-type]
        r = await ev.evaluate(str(candidate), "bcb-9999")
        assert not r.skipped
        assert r.score == 1.0
        assert r.findings_count == 0

    async def test_partial_pass(self, pack: Path, candidate: Path) -> None:
        fake = _FakeSandbox(stdout=_result_json(4, 3, 1))
        ev = PythonCorrectnessEvaluator(packs_root=pack, sandbox_run=fake)  # type: ignore[arg-type]
        r = await ev.evaluate(str(candidate), "bcb-9999")
        assert r.score == pytest.approx(0.75)
        assert r.findings_count == 1

    async def test_timeout_skips(self, pack: Path, candidate: Path) -> None:
        fake = _FakeSandbox(stdout="", timed_out=True)
        ev = PythonCorrectnessEvaluator(packs_root=pack, sandbox_run=fake)  # type: ignore[arg-type]
        r = await ev.evaluate(str(candidate), "bcb-9999")
        assert r.skipped and "timed out" in (r.skip_reason or "")

    async def test_no_json_skips(self, pack: Path, candidate: Path) -> None:
        fake = _FakeSandbox(stdout="ModuleNotFoundError: numpy", exit_code=1)
        ev = PythonCorrectnessEvaluator(packs_root=pack, sandbox_run=fake)  # type: ignore[arg-type]
        r = await ev.evaluate(str(candidate), "bcb-9999")
        assert r.skipped and "no JSON" in (r.skip_reason or "")


class TestWiring:
    async def test_assembles_namespace(self, pack: Path, candidate: Path) -> None:
        """The mounted /workspace carries solution + namespace-wired test + runner."""
        fake = _FakeSandbox(stdout=_result_json(1, 1, 0))
        ev = PythonCorrectnessEvaluator(packs_root=pack, sandbox_run=fake)  # type: ignore[arg-type]
        await ev.evaluate(str(candidate), "bcb-9999")
        assert set(fake.mounted) == {"solution.py", "test_run.py", "_runner.py"}
        # the gold suite (bare task_func) is wired to the candidate via import
        assert "from solution import" in fake.mounted["test_run.py"]
        assert "task_func" in fake.mounted["test_run.py"]
        assert "return x * 2" in fake.mounted["solution.py"]
        # runner targets the read-only workspace
        assert fake.last_config is not None
        assert fake.last_config.command == ["python", "/workspace/_runner.py"]
        assert fake.last_config.environment.get("PYTHONDONTWRITEBYTECODE") == "1"
