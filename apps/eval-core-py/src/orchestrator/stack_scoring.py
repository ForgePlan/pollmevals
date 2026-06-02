"""Bridge Half A (StackExecResult patch) -> Half B (judge panel / evaluators).

RFC-006 Phase 4. Maps a ``StackExecResult`` (harness -> patch, Half A) into the
``EvalResult`` shape that ``JudgePanel.score`` (and the evaluators) consume, so a
``(model x harness x task)`` run yields a real score. GridRunner dispatch-by-stack
reuses this so CLI stacks flow through the SAME scoring path as ``raw-llm``.

The judge panel reads the candidate's output from the ``raw_output`` artifact
URI (a file on disk), so the bridge writes the submission there.

Submission = the FINAL content of the candidate's changed source files (not the
raw diff), with harness bookkeeping (``.aider*``, ``.gitignore``,
``.pollmevals*``) filtered out — code-quality judging wants the code, not a diff.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from src.contracts import (
    ArtifactRef,
    EvalArtifactRefs,
    EvalRow,
    EvalStats,
    EvalStatus,
)
from src.orchestrator.eval_caller import EvalRequest, EvalResult, compute_eval_id
from src.orchestrator.stack_executor import ExecStatus, StackExecResult

# Harness bookkeeping files that are NOT part of the candidate submission.
_NOISE_RE = re.compile(r"(^|/)(\.aider|\.gitignore|\.pollmevals|node_modules/)")

# Synthetic run_hash fragment for standalone (non-grid) scoring. GridRunner
# passes the real run_hash; this default keeps single-eval scoring deterministic.
_STANDALONE_RUN_HASH = "sha256:" + "5" * 64


def changed_files(patch: str) -> list[str]:
    """Return the candidate's changed source paths from a unified diff.

    Reads ``+++ b/<path>`` headers; drops ``/dev/null`` (pure deletions) and
    harness bookkeeping noise.
    """
    out: list[str] = []
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/") :].strip()
            if path and path != "/dev/null" and not _NOISE_RE.search(path):
                out.append(path)
    return out


def extract_submission(snapshot_dir: Path, patch: str) -> str:
    """Concatenated final content of the candidate's changed source files.

    Each file is prefixed with a ``// === <path> ===`` banner so a multi-file
    submission stays legible to the judge. Files referenced by the patch but
    missing on disk (e.g. deletions) are skipped.
    """
    parts: list[str] = []
    for rel in changed_files(patch):
        f = snapshot_dir / rel
        if f.exists():
            body = f.read_text(encoding="utf-8", errors="replace")
            parts.append(f"// === {rel} ===\n{body}")
    return "\n\n".join(parts)


def _artifact(log_dir: Path, eval_id: str, label: str, content: str) -> ArtifactRef:
    """Write *content* to a content-addressed file and return its ArtifactRef."""
    sha256 = hashlib.sha256(content.encode()).hexdigest()
    mime = "application/json" if label == "evaluator_json" else "text/plain"
    ext = ".json" if label == "evaluator_json" else ".txt"
    dest = log_dir / eval_id / f"{label}-{sha256}{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return ArtifactRef(
        sha256=sha256,
        size_bytes=len(content.encode()),
        uri=f"file://{dest}",
        mime_type=mime,
    )


def exec_result_to_eval_result(
    exec_result: StackExecResult,
    *,
    log_dir: Path,
    run_hash: str = _STANDALONE_RUN_HASH,
) -> EvalResult:
    """Map a StackExecResult into a judge-ready EvalResult.

    The candidate submission (changed source files) is written as the
    ``raw_output`` + ``normalized_output`` artifacts so ``JudgePanel.score`` can
    read it. ``stack_id`` is the adapter slug; cost/tokens carry over from Half A.

    Raises:
        ValueError: the executor did not produce a patch (status != OK) — there
            is nothing to score.
    """
    req = exec_result.request
    if exec_result.status is not ExecStatus.OK or not exec_result.patch:
        raise ValueError(
            f"cannot score a non-OK execution (status={exec_result.status}, eval_id={req.eval_id})"
        )

    stack_id = req.stack.slug
    eval_id = compute_eval_id(run_hash, req.model_id, stack_id, req.task_id, req.seed)
    submission = extract_submission(req.repo_snapshot_dir, exec_result.patch)
    evaluator_json = (
        f'{{"eval_id":"{eval_id}","harness":"{req.stack.agent_cli}",'
        f'"patch_bytes":{len(exec_result.patch.encode())}}}'
    )

    artifact_refs = EvalArtifactRefs(
        raw_output=_artifact(log_dir, eval_id, "raw_output", submission),
        normalized_output=_artifact(log_dir, eval_id, "normalized_output", submission.strip()),
        evaluator_json=_artifact(log_dir, eval_id, "evaluator_json", evaluator_json),
    )
    stats = EvalStats(
        input_tokens=exec_result.input_tokens,
        output_tokens=exec_result.output_tokens,
        wall_clock_ms=exec_result.wall_ms,
        cost_usd=exec_result.cost_usd,
    )
    row = EvalRow(
        eval_id=eval_id,
        model_id=req.model_id,
        stack_id=stack_id,
        task_id=req.task_id,
        seed=req.seed,
        status=EvalStatus.SCORED,
        artifact_refs=artifact_refs,
        stats=stats,
        started_at=exec_result.started_at,
        completed_at=exec_result.completed_at,
    )
    request = EvalRequest(
        eval_id=eval_id,
        model_id=req.model_id,
        stack_id=stack_id,
        task_id=req.task_id,
        seed=req.seed,
    )
    return EvalResult(
        request=request,
        eval_row=row,
        exception=None,
        started_at=exec_result.started_at,
        completed_at=datetime.now(UTC),
    )


def cost_with_judges(exec_cost: Decimal, judgments_cost: Decimal) -> Decimal:
    """Total eval cost = harness spend + judge spend (CONTEXT.md cost rule)."""
    return exec_cost + judgments_cost
