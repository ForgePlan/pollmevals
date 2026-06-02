"""Unit tests for the Half A -> Half B scoring bridge (RFC-006 Phase 4).

Pure mapping logic — no Docker, no judges, no network.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.contracts import EvalStatus
from src.orchestrator.stack_executor import (
    ExecStatus,
    StackAdapter,
    StackExecRequest,
    StackExecResult,
)
from src.orchestrator.stack_scoring import (
    changed_files,
    exec_result_to_eval_result,
    extract_submission,
)

_ADAPTER_YAML = """
slug: aider
agent_cli: aider
execution:
  mode: repository_patch
  command: aider
"""

_PATCH = """diff --git a/.gitignore b/.gitignore
new file mode 100644
--- /dev/null
+++ b/.gitignore
@@ -0,0 +1 @@
+.aider*
diff --git a/solution.ts b/solution.ts
--- a/solution.ts
+++ b/solution.ts
@@ -1 +1,2 @@
-// stub
+export const ok = true;
diff --git a/old.ts b/old.ts
--- a/old.ts
+++ /dev/null
"""


def _exec_result(
    tmp_path: Path, *, status: ExecStatus = ExecStatus.OK, patch: str = _PATCH
) -> StackExecResult:
    adapter = StackAdapter.from_yaml_text(_ADAPTER_YAML)
    req = StackExecRequest(
        eval_id="raw-id",
        model_id="openrouter/qwen/qwen-3-14b",
        model_alias="qwen-3-14b",
        stack=adapter,
        task_id="be_01_jwt_auth",
        task_prompt="impl",
        repo_snapshot_dir=tmp_path,
        seed=1,
    )
    return StackExecResult(
        request=req,
        status=status,
        patch=patch,
        trace="t",
        cost_usd=Decimal("0.000626"),
        input_tokens=1400,
        output_tokens=2200,
        tool_calls=0,
        wall_ms=55000,
        error_detail=None,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


class TestChangedFiles:
    def test_parses_and_filters_noise(self) -> None:
        files = changed_files(_PATCH)
        assert "solution.ts" in files
        assert ".gitignore" not in files  # harness bookkeeping filtered
        assert "old.ts" not in files  # deletion (+++ /dev/null) dropped

    def test_empty_patch(self) -> None:
        assert changed_files("") == []


class TestExtractSubmission:
    def test_reads_changed_file_content(self, tmp_path: Path) -> None:
        (tmp_path / "solution.ts").write_text("export const ok = true;\n")
        sub = extract_submission(tmp_path, _PATCH)
        assert "=== solution.ts ===" in sub
        assert "export const ok = true;" in sub

    def test_skips_missing_files(self, tmp_path: Path) -> None:
        # solution.ts referenced by the patch but not on disk -> skipped, no raise
        assert extract_submission(tmp_path, _PATCH) == ""


class TestExecResultToEvalResult:
    def test_maps_ok_result(self, tmp_path: Path) -> None:
        (tmp_path / "solution.ts").write_text("export const ok = true;\n")
        log_dir = tmp_path / "artifacts"
        result = _exec_result(tmp_path)
        ev = exec_result_to_eval_result(result, log_dir=log_dir)

        assert ev.eval_row is not None
        row = ev.eval_row
        assert row.stack_id == "aider"  # adapter slug, not the raw eval_id stack
        assert row.model_id == "openrouter/qwen/qwen-3-14b"
        assert row.task_id == "be_01_jwt_auth"
        assert row.status is EvalStatus.SCORED
        assert len(row.eval_id) == 16  # 16-hex contract
        # cost + tokens carried over from Half A
        assert row.stats.cost_usd == Decimal("0.000626")
        assert row.stats.input_tokens == 1400
        # the raw_output artifact file was written with the submission
        uri = row.artifact_refs.raw_output.uri
        assert uri.startswith("file://")
        written = Path(uri[len("file://") :]).read_text()
        assert "export const ok = true;" in written

    def test_rejects_non_ok(self, tmp_path: Path) -> None:
        result = _exec_result(tmp_path, status=ExecStatus.NO_PATCH, patch="")
        with pytest.raises(ValueError, match="non-OK execution"):
            exec_result_to_eval_result(result, log_dir=tmp_path)
