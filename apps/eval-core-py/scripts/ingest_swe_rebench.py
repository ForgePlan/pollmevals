#!/usr/bin/env python
"""Ingest SWE-rebench-V2 instances into POLLMEVALS task packs (ADR-007 import).

Fetches N rows from the public HuggingFace datasets-server REST API (no auth)
and writes one task pack per instance under ``evals/task-packs/swe-<id>/`` in the
be_01_jwt_auth pack shape: ``task.yaml`` + ``prompt.md`` + ``gold/`` (gold.patch,
test.patch, expectations.json) + ``rubric.yaml`` + ``NOTE.md``.

These are CATALOGUE entries: a SWE-rebench task needs a full repo checkout at
``base_commit`` plus its Docker image to run, which the current single-file
executor (be_01-style) cannot do yet. The gold/test patches are preserved
verbatim so correctness becomes checkable once the executor learns repo-based
tasks (see each pack's NOTE.md).

Run from anywhere (the script chdir's to the repo root):
  uv run --project apps/eval-core-py \\
      python apps/eval-core-py/scripts/ingest_swe_rebench.py --n 10
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[3]
_PACKS = REPO / "evals" / "task-packs"
_DATASET = "nebius/SWE-rebench-V2"
_ROWS_URL = (
    f"https://datasets-server.huggingface.co/rows?dataset={_DATASET}&config=default&split=train"
)
_DATASET_URL = f"https://huggingface.co/datasets/{_DATASET}"
_DATASET_LICENSE = "CC-BY-4.0"  # dataset-level; per-row code license recorded separately

# SWE-rebench short language codes -> POLLMEVALS canonical language names.
_LANG_MAP = {
    "ts": "typescript",
    "tsx": "typescript",
    "js": "javascript",
    "jsx": "javascript",
    "py": "python",
    "python": "python",
    "go": "go",
    "rs": "rust",
    "rust": "rust",
    "java": "java",
    "kt": "kotlin",
    "kotlin": "kotlin",
    "rb": "ruby",
    "ruby": "ruby",
    "php": "php",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "cs": "csharp",
    "scala": "scala",
    "swift": "swift",
}

# Difficulty from patch size (modified lines), with byte-size fallback when the
# dataset leaves num_modified_lines null. easy/hard thresholds are conservative.
_EASY_MAX_LINES = 30
_HARD_MIN_LINES = 200
_EASY_MAX_BYTES = 2_000
_HARD_MIN_BYTES = 20_000
_PATCH_WARN_BYTES = 40_000  # note (don't skip) oversized gold patches


def _fetch_rows(n: int) -> list[dict[str, Any]]:
    """Fetch up to ``n`` rows, paging the datasets-server (100-row cap/page)."""
    out: list[dict[str, Any]] = []
    offset = 0
    while len(out) < n:
        length = min(100, n - len(out))
        url = f"{_ROWS_URL}&offset={offset}&length={length}"
        req = urllib.request.Request(url, headers={"User-Agent": "pollmevals-ingest"})
        with urllib.request.urlopen(req, timeout=90) as resp:  # trusted host
            payload = json.load(resp)
        batch = payload.get("rows", [])
        if not batch:
            break
        out.extend(item["row"] for item in batch)
        offset += length
    return out[:n]


def _sanitize(instance_id: str) -> str:
    """instance_id -> filesystem- and slug-safe token (lowercase, [a-z0-9-])."""
    s = instance_id.lower().replace("__", "-").replace("_", "-")
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def _language(code: str | None) -> str:
    return _LANG_MAP.get((code or "").lower(), (code or "unknown").lower())


def _difficulty(row: dict[str, Any]) -> str:
    """Infer easy/medium/hard from patch size; lines first, bytes as fallback."""
    meta = row.get("meta") or {}
    lines = meta.get("num_modified_lines")
    if isinstance(lines, int):
        if lines <= _EASY_MAX_LINES:
            return "easy"
        if lines >= _HARD_MIN_LINES:
            return "hard"
        return "medium"
    nbytes = len(row.get("patch") or "")
    if nbytes <= _EASY_MAX_BYTES:
        return "easy"
    if nbytes >= _HARD_MIN_BYTES:
        return "hard"
    return "medium"


def _slug(row: dict[str, Any], sanitized: str) -> str:
    """Short slug from repo basename + trailing issue/PR number of the id."""
    repo = (row.get("repo") or "").split("/")[-1].lower()
    repo = re.sub(r"[^a-z0-9]+", "-", repo).strip("-")
    m = re.search(r"(\d+)$", sanitized)
    num = m.group(1) if m else ""
    base = f"{repo}-{num}" if num else repo
    return f"swe-rebench-{base}".strip("-") or sanitized


def _prompt(row: dict[str, Any], language: str) -> str:
    """Candidate-facing 'fix this bug' prompt — issue only, never the gold."""
    repo = row.get("repo") or "the project"
    base_commit = row.get("base_commit") or "(unknown)"
    statement = (row.get("problem_statement") or "").strip()
    interface = (row.get("interface") or "").strip()
    iface_block = ""
    if interface and interface.lower() not in {"no new interfaces are introduced.", "none"}:
        iface_block = f"\nInterface / API notes:\n{interface}\n"
    return (
        f"# Bug fix: {repo}\n\n"
        f"You are fixing a real bug in the open-source repository `{repo}` "
        f"at commit `{base_commit}`.\n\n"
        "## Issue\n\n"
        f"{statement}\n"
        f"{iface_block}\n"
        "## Task\n\n"
        f"Modify the {language} source so the reported problem is resolved. Produce a "
        "patch against the repository at the given base commit that makes the failing "
        "tests pass without breaking the existing passing tests.\n\n"
        "Constraints:\n"
        "  - Change only what the fix requires; keep the diff minimal and focused.\n"
        "  - Do not edit the test files — they are the hidden acceptance criteria.\n"
        "  - Preserve the existing public API unless the issue explicitly requires a change.\n\n"
        "Output a unified diff (git patch) of your source changes.\n"
    )


def _description(row: dict[str, Any]) -> str:
    statement = (row.get("problem_statement") or "").strip()
    return statement or (row.get("pr_description") or "").strip() or "(no problem statement)"


def _task_yaml(row: dict[str, Any], task_id: str, sanitized: str) -> dict[str, Any]:
    language = _language(row.get("language"))
    code_license = str(row.get("license") or "UNKNOWN")
    install = row.get("install_config") or {}
    meta = row.get("meta") or {}
    llm = meta.get("llm_metadata") or {}
    return {
        "schema_version": "pollmevals.task.v1",
        "id": task_id,
        "slug": _slug(row, sanitized),
        "version": "1.0",
        "category": "bugfix",
        "difficulty": _difficulty(row),
        "language": language,
        "sourcing": "external",
        "license": {
            "code": code_license,
            "dataset": _DATASET_LICENSE,
        },
        "source": {
            "dataset": _DATASET,
            "instance_id": row.get("instance_id"),
            "repo": row.get("repo"),
            "base_commit": row.get("base_commit"),
            "image_name": row.get("image_name"),
            "test_cmd": install.get("test_cmd"),
            "dataset_url": _DATASET_URL,
            "meta_difficulty": llm.get("difficulty"),
            "pr_categories": llm.get("pr_categories") or [],
        },
        "description": _description(row),
        "prompt_template": _prompt(row, language),
        "success_criteria": [
            "All FAIL_TO_PASS tests in gold/expectations.json pass after the patch is applied.",
            "All PASS_TO_PASS tests continue to pass (no regression).",
            "Only source files are changed; test files are left untouched.",
        ],
        "execution_shape": "repo-checkout",  # NOT single-file; see NOTE.md
    }


def _rubric_yaml(task_id: str, language: str) -> dict[str, Any]:
    """Bugfix rubric. Correctness is gated by FAIL_TO_PASS/PASS_TO_PASS test sets;
    the judge criteria below assess the change's quality once tests are wired."""
    return {
        "schema_version": "pollmevals.rubric.v1",
        "task_id": task_id,
        "rubric_version": "1.0",
        "sourcing": "external",
        "language": language,
        "criteria": {
            "correctness": {
                "weight": 0.50,
                "description": (
                    "Does the patch make the FAIL_TO_PASS tests pass while keeping all "
                    "PASS_TO_PASS tests green? Primary signal is the objective test grid "
                    "(gold/expectations.json), not judge opinion."
                ),
                "anchors": {
                    0: "FAIL_TO_PASS tests still fail, or the patch breaks PASS_TO_PASS tests.",
                    5: "Resolves the reported issue on the happy path but regresses an edge "
                    "case or leaves one FAIL_TO_PASS test failing.",
                    10: "All FAIL_TO_PASS pass and no PASS_TO_PASS regress; the fix matches "
                    "the intent of the reported issue.",
                },
            },
            "minimalism": {
                "weight": 0.20,
                "description": (
                    "Is the diff scoped to the fix? No drive-by refactors, no unrelated "
                    "file churn, no edits to test files."
                ),
                "anchors": {
                    0: "Large unrelated rewrite, or edits the test files to force a pass.",
                    5: "Mostly focused but includes some incidental, unrelated changes.",
                    10: "Tight, minimal diff touching only what the fix requires.",
                },
            },
            "root_cause": {
                "weight": 0.20,
                "description": (
                    "Does the change address the underlying cause rather than masking the "
                    "symptom (e.g. swallowing an error or special-casing the test input)?"
                ),
                "anchors": {
                    0: "Hard-codes the expected test output or suppresses the symptom.",
                    5: "Plausible fix but narrow; may not generalise beyond the test case.",
                    10: "Addresses the root cause; the fix generalises to the whole bug class.",
                },
            },
            "code_clarity": {
                "weight": 0.10,
                "description": (
                    "Does the patch read like idiomatic, maintainable code for this "
                    "language and repository? Clear names, no dead code, consistent style."
                ),
                "anchors": {
                    0: "Obfuscated or inconsistent with the surrounding code.",
                    5: "Acceptable but with minor style or naming issues.",
                    10: "Idiomatic and consistent with the repository's conventions.",
                },
            },
        },
        "output_schema": {
            "rubric_scores": {
                "correctness": "0..10",
                "minimalism": "0..10",
                "root_cause": "0..10",
                "code_clarity": "0..10",
            },
            "total_score": "0..10",
            "reasoning": "Free-text, cite evidence from the candidate diff.",
        },
    }


def _note_md(row: dict[str, Any], task_id: str) -> str:
    install = row.get("install_config") or {}
    patch_bytes = len(row.get("patch") or "")
    oversized = (
        f"\n> **Oversized gold patch**: {patch_bytes / 1024:.1f} KB "
        f"(> {_PATCH_WARN_BYTES // 1024} KB). Saved verbatim regardless.\n"
        if patch_bytes > _PATCH_WARN_BYTES
        else ""
    )
    return (
        f"# Execution shape — {task_id} ({row.get('instance_id')})\n\n"
        "**Status: CATALOGUE entry (not yet runnable).**\n"
        f"{oversized}\n"
        "## Why this is not runnable today\n\n"
        "This pack was ingested from `nebius/SWE-rebench-V2`. Unlike the single-file "
        "reference task `be_01_jwt_auth` (one `solution.ts` graded by a Dockerised "
        "vitest run), a SWE-rebench instance is a **repository-level** task:\n\n"
        f"  - it needs a full checkout of `{row.get('repo')}` at base commit "
        f"`{row.get('base_commit')}`;\n"
        f"  - it runs inside the prebuilt Docker image `{row.get('image_name')}`;\n"
        f"  - the gold fix is a multi-file diff applied to that working tree;\n"
        f"  - correctness is decided by a test command "
        f"(`{install.get('test_cmd') or 'see install_config'}`) parsing FAIL_TO_PASS / "
        "PASS_TO_PASS results.\n\n"
        "Our current executor only does **single-file** submissions, so this pack is a "
        "catalogue entry: the prompt, gold patch, test patch, and expectations are stored "
        "verbatim and become runnable once the executor supports repo-based tasks "
        "(checkout at base_commit + image pull + apply test patch + run test_cmd + parse).\n\n"
        "## What is stored here\n\n"
        "| File | Contents |\n"
        "|---|---|\n"
        "| `gold/gold.patch` | reference fix (the `patch` field) — verbatim |\n"
        "| `gold/test.patch` | the test diff (the `test_patch` field) — verbatim |\n"
        "| `gold/expectations.json` | FAIL_TO_PASS + PASS_TO_PASS test name lists |\n"
        "| `task.yaml` | metadata, source provenance, candidate prompt |\n"
        "| `rubric.yaml` | bugfix judge rubric (correctness gated by the test grid) |\n\n"
        "## Provenance / licensing caveat\n\n"
        f"Dataset license: **{_DATASET_LICENSE}** (per-instance code license: "
        f"**{row.get('license')}**, recorded in `task.yaml`). NOTE: ADR-007's Tier-2 "
        "import allowlist (MIT / Apache-2.0 / BSD) and eligible-source list do **not** yet "
        "cover SWE-rebench-V2 or CC-BY-4.0. These packs are staged as `sourcing: external` "
        "for cataloguing; promotion to a scored run needs an ADR-007 amendment plus the G4 "
        "contamination gate.\n"
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _yaml_dump(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def _write_pack(row: dict[str, Any], task_id: str) -> tuple[str, str]:
    """Write one pack; return (pack_dir_path, instance_id)."""
    sanitized = _sanitize(row.get("instance_id") or task_id)
    pack = _PACKS / f"swe-{sanitized}"
    language = _language(row.get("language"))

    header = (
        f"# source: {_DATASET} instance {row.get('instance_id')} "
        f"(code license: {row.get('license')}, dataset license: {_DATASET_LICENSE}, "
        f"url: {_DATASET_URL})\n"
    )
    _write(pack / "task.yaml", header + _yaml_dump(_task_yaml(row, task_id, sanitized)))
    _write(pack / "rubric.yaml", header + _yaml_dump(_rubric_yaml(task_id, language)))
    _write(pack / "prompt.md", _prompt(row, language))
    _write(pack / "NOTE.md", _note_md(row, task_id))

    # Gold artefacts — preserve verbatim so correctness stays checkable later.
    _write(pack / "gold" / "gold.patch", row.get("patch") or "")
    _write(pack / "gold" / "test.patch", row.get("test_patch") or "")
    expectations = {
        "instance_id": row.get("instance_id"),
        "repo": row.get("repo"),
        "base_commit": row.get("base_commit"),
        "FAIL_TO_PASS": row.get("FAIL_TO_PASS") or [],
        "PASS_TO_PASS": row.get("PASS_TO_PASS") or [],
    }
    _write(pack / "gold" / "expectations.json", json.dumps(expectations, indent=2) + "\n")
    return str(pack), str(row.get("instance_id"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest SWE-rebench-V2 into task packs.")
    ap.add_argument("--n", type=int, default=10, help="number of instances (default 10)")
    args = ap.parse_args()

    os.chdir(REPO)  # repo-rooted relative paths, matching sibling scripts
    print(f"chdir {REPO}")
    print(f"Fetching {args.n} rows from {_DATASET} ...")
    rows = _fetch_rows(args.n)
    if not rows:
        print("ERROR: no rows fetched", file=sys.stderr)
        return 1

    created: list[tuple[str, str]] = []
    for i, row in enumerate(rows):
        task_id = f"swe_{i + 1:03d}"
        pack_dir, instance_id = _write_pack(row, task_id)
        created.append((pack_dir, instance_id))
        rel = Path(pack_dir).relative_to(REPO)
        print(f"  {task_id}  {instance_id:<40}  {rel}")

    print(f"\nWrote {len(created)} packs under {_PACKS.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
