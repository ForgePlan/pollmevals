#!/usr/bin/env python
"""Ingest BigCodeBench tasks into POLLMEVALS task-pack format (ADR-007 Tier 2).

BigCodeBench (https://huggingface.co/datasets/bigcode/bigcodebench, Apache-2.0)
is a benchmark of self-contained, function-level Python tasks with diverse
library calls and rigorous ``unittest`` test cases. Each row carries a natural-
language instruction (``instruct_prompt``), the gold function body
(``canonical_solution``), and a ``unittest.TestCase`` suite (``test``).

This script discovers rows via the HuggingFace **datasets-server REST API**
(no auth, plain HTTPS + JSON) and writes one task pack per row under
``evals/task-packs/bcb-<sanitized_task_id>/`` mirroring the be_01_jwt_auth
reference layout:

    bcb-<id>/
      task.yaml          # pollmevals.task.v1 contract
      prompt.md          # candidate-facing prompt (the instruct_prompt)
      gold/solution.py   # runnable: complete_prompt (sig+docstring) + body
      gold/test.py       # the verbatim unittest suite
      gold/meta.json     # entry_point + provenance
      NOTE.md            # honest execution-shape note
      LICENSE.md         # ADR-007 Tier 2 attribution (required for sourced packs)

Per ADR-007 these are **Tier 2 (sourced)** packs: license is Apache-2.0, the
``sourcing:`` field is ``hybrid`` (the ADR's enum is ``own | hybrid`` — there is
no ``external`` value), and every artefact carries a provenance header.

Usage (run from anywhere — the script chdir's to the repo root)::

    uv run --project apps/eval-core-py \\
        python apps/eval-core-py/scripts/ingest_bigcodebench.py --n 10

    # BCB-Hard subset (difficulty: hard):
    uv run --project apps/eval-core-py \\
        python apps/eval-core-py/scripts/ingest_bigcodebench.py \\
        --dataset bigcode/bigcodebench-hard --n 10

    # dry run — inspect what would be written, touch nothing:
    python apps/eval-core-py/scripts/ingest_bigcodebench.py --n 10 --dry-run
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]

# datasets-server REST endpoints (no auth required for public datasets).
_ROWS_URL = "https://datasets-server.huggingface.co/rows"
_SPLITS_URL = "https://datasets-server.huggingface.co/splits"

# A row's `test` references the entry-point function as a bare free name with no
# import and no __main__ runner; a python test-runner must inject the solution
# into the test namespace (or prepend it). See each pack's NOTE.md.
_DEFAULT_SPLIT = "v0.1.4"

# Map dataset -> POLLMEVALS difficulty (BCB = medium, BCB-Hard = hard).
_DIFFICULTY_BY_DATASET = {
    "bigcode/bigcodebench": "medium",
    "bigcode/bigcodebench-hard": "hard",
}

# Standard "coding task" weight formula (docs/02-methodology/scoring.md).
# Σ == 1.0 (validate-task-specs.py MUST-5).
_WEIGHT_COMPONENTS = {
    "correctness": 0.40,
    "test_coverage": 0.15,
    "complexity": 0.10,
    "linter": 0.10,
    "type_safety": 0.10,
    "pattern_match": 0.15,
}


def _http_get_json(url: str, params: dict[str, str | int], timeout: float = 60.0) -> dict[str, Any]:
    """GET *url* with query *params* and parse the JSON body."""
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{query}", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover - network failure path
        body = exc.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"ERROR: HTTP {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network failure path
        raise SystemExit(f"ERROR: cannot reach {url}: {exc.reason}") from exc


def _resolve_split(dataset: str, config: str, requested: str) -> str:
    """Confirm *requested* split exists; otherwise fall back to the last listed."""
    data = _http_get_json(_SPLITS_URL, {"dataset": dataset})
    splits = [s["split"] for s in data.get("splits", []) if s.get("config") == config]
    if not splits:
        raise SystemExit(f"ERROR: no splits for {dataset} (config={config})")
    if requested in splits:
        return requested
    print(
        f"WARN: split {requested!r} not found for {dataset}; "
        f"using {splits[-1]!r} (available: {splits})",
        file=sys.stderr,
    )
    return splits[-1]


def _fetch_rows(dataset: str, config: str, split: str, offset: int, n: int) -> list[dict[str, Any]]:
    """Fetch up to *n* rows starting at *offset* via the datasets-server."""
    data = _http_get_json(
        _ROWS_URL,
        {"dataset": dataset, "config": config, "split": split, "offset": offset, "length": n},
    )
    return [item["row"] for item in data.get("rows", [])]


def _sanitize_task_id(task_id: str) -> str:
    """`BigCodeBench/0` -> `0000`; keep ids zero-padded + sortable.

    Falls back to a slugified form if the id is not the `Prefix/N` shape.
    """
    tail = task_id.rsplit("/", 1)[-1]
    if tail.isdigit():
        return tail.zfill(4)
    return re.sub(r"[^a-z0-9]+", "-", tail.lower()).strip("-") or "unknown"


def _parse_libs(libs_raw: str) -> list[str]:
    """`libs` arrives as a stringified Python list; parse it safely."""
    if not libs_raw:
        return []
    try:
        parsed = ast.literal_eval(libs_raw)
    except (ValueError, SyntaxError):
        return []
    if isinstance(parsed, (list, tuple)):
        return [str(x) for x in parsed]
    return []


def _build_solution(row: dict[str, Any]) -> str:
    """Assemble a RUNNABLE solution.py from the row.

    ``canonical_solution`` is only the function *body* (indented, no ``def``
    line). The signature + imports + docstring live in ``complete_prompt`` (or
    the leaner ``code_prompt``). Concatenating the two yields a complete module
    that defines the entry-point function. Preserve both parts verbatim.
    """
    scaffold = row.get("complete_prompt") or row.get("code_prompt") or ""
    body = row.get("canonical_solution") or ""
    scaffold = scaffold.rstrip("\n") + "\n"
    return scaffold + body.rstrip("\n") + "\n"


def _provenance_header(dataset: str, task_id: str, retrieved: str, comment: str) -> str:
    """ADR-007 Tier 2 provenance header in the file's comment syntax."""
    url = f"https://huggingface.co/datasets/{dataset}"
    return (
        f"{comment} source: BigCodeBench task #{task_id} "
        f"(license: Apache-2.0, retrieved {retrieved}, url: {url})\n"
    )


def _render_task_yaml(
    *,
    pack_id: str,
    slug: str,
    difficulty: str,
    dataset: str,
    task_id: str,
    libs: list[str],
    entry_point: str,
    instruction: str,
    retrieved: str,
) -> str:
    """Render task.yaml for one pack.

    NOTE: ``requirements[]`` is intentionally omitted. It is optional in
    task.schema.json, and emitting it would force the RFC-004 MUST rules
    (per-item prompt_ref + maps_to bindings) which cannot be derived faithfully
    from an imported function task without fabricating mappings.
    """
    header = (
        f"# source: BigCodeBench task #{task_id} (license: Apache-2.0, "
        f"retrieved {retrieved}, url: https://huggingface.co/datasets/{dataset})"
    )
    indented_desc = "\n".join("  " + ln if ln else "" for ln in instruction.splitlines())
    libs_yaml = "[" + ", ".join(json.dumps(x) for x in libs) + "]"
    lines = [
        header,
        "schema_version: pollmevals.task.v1",
        f"id: {pack_id}",
        f"slug: {slug}",
        'version: "1.0"',
        # entry_point task_func is pure compute (no I/O contract) → algo, else backend.
        f"category: {_category_for(libs)}",
        f"difficulty: {difficulty}",
        "language: python",
        "",
        "# ADR-007 Tier 2 (sourced with attribution). The ADR's sourcing enum is",
        "# `own | hybrid`; there is no `external` value, so a fully-imported pack",
        "# is `hybrid`. License + provenance recorded below and in LICENSE.md.",
        "sourcing: hybrid",
        "license:",
        "  spec: Apache-2.0",
        "  code: Apache-2.0",
        "",
        "source:",
        f"  dataset: {dataset}",
        f'  task_id: "{task_id}"',
        f"  entry_point: {entry_point}",
        f"  libs: {libs_yaml}",
        f"  retrieved: {retrieved}",
        "",
        "description: |",
        indented_desc,
        "",
        "prompt_template: |",
        indented_desc,
        "",
        "success_criteria:",
        f"  - All hidden unittest cases in gold/test.py pass for `{entry_point}`.",
        "  - The solution is a single self-contained Python module.",
        "  - Only the listed standard/third-party libraries are imported.",
        "",
        "# Standard coding-task formula (docs/02-methodology/scoring.md). Σ == 1.0.",
        "weight_components:",
    ]
    lines += [f"  {k}: {v}" for k, v in _WEIGHT_COMPONENTS.items()]
    return "\n".join(lines) + "\n"


def _category_for(libs: list[str]) -> str:
    """`backend` if the task touches I/O-ish libs, else `algo` (pure compute)."""
    io_markers = {
        "os",
        "sys",
        "subprocess",
        "socket",
        "ftplib",
        "smtplib",
        "requests",
        "urllib",
        "http",
        "flask",
        "django",
        "sqlite3",
        "shutil",
        "pathlib",
        "ssl",
        "email",
        "json",
        "csv",
        "logging",
    }
    return "backend" if any(lib.split(".")[0] in io_markers for lib in libs) else "algo"


def _render_note_md(
    *, pack_id: str, entry_point: str, dataset: str, task_id: str, retrieved: str
) -> str:
    """Honest execution-shape note (how close to runnable vs be_01)."""
    return f"""<!-- {_provenance_header(dataset, task_id, retrieved, "").strip()} -->
# Execution shape — {pack_id}

**Source**: BigCodeBench `{task_id}` ({dataset}), entry point `{entry_point}`.

## What this pack is

A self-contained Python function task. Unlike `be_01_jwt_auth` (TypeScript +
vitest + a full `node_modules`/Docker toolchain), this is a single pure-Python
module scored by a `unittest.TestCase` suite. It is **close to runnable** — no
build step, no package install beyond the task's own libraries.

## Files

- `gold/solution.py` — a **runnable** reference module. Assembled verbatim from
  the dataset's `complete_prompt` (imports + `def {entry_point}(...)` signature +
  docstring) followed by `canonical_solution` (the function body). The body
  alone is NOT a complete function — this is the key schema gotcha.
- `gold/test.py` — the verbatim BigCodeBench `unittest` suite.
- `gold/meta.json` — `entry_point` + provenance.

## Can our executor run this today?

**Not with the current single-file TypeScript/vitest executor** (that path is
hard-wired to `npx vitest` inside the `eval-ts` image). These packs need a
**Python test-runner** instead. The gap is small and mechanical:

1. Write the candidate's answer to `solution.py`.
2. Make the entry-point visible to the test module. `gold/test.py` calls
   `{entry_point}(...)` as a **bare free name** — there is no `import` line and
   no `if __name__ == "__main__"` block. The runner must either:
   - prepend `solution.py` into the test module's namespace, or
   - inject `from solution import {entry_point}` at the top of the test, or
   - run via `python -m unittest` with both files in one namespace.
3. Execute `python -m unittest` (or `pytest`) in the task's venv and parse the
   pass/fail/error counts into the `correctness` component.

Some suites use `unittest.mock.patch` and seeded `random`/`subprocess`; they run
in-process and need the task's third-party libs installed (see `source.libs` in
`task.yaml`). Sandbox parity with the frozen policy
(`docs/04-runbook/09-sandbox-security.md`) is a follow-up: BigCodeBench tasks
that touch the network or filesystem must run network-off with a tmpfs CWD.

**Verdict**: runnable-now for a human (`python -m unittest`); needs a small
Python test-runner adapter to wire into the POLLMEVALS evaluator chain.
"""


def _render_license_md(packs: list[tuple[str, str]], dataset: str, retrieved: str) -> str:
    """Per-pack LICENSE.md (ADR-007 Tier 2 attribution table)."""
    rows = "\n".join(f"| `{pid}` | {tid} |" for pid, tid in packs)
    return f"""# License & attribution (ADR-007 Tier 2)

This task pack is **sourced** from BigCodeBench, not own-authored.

- **Source dataset**: {dataset}
- **URL**: https://huggingface.co/datasets/{dataset}
- **License**: Apache-2.0 (SPDX: `Apache-2.0`)
- **Retrieved**: {retrieved}

The gold solution (`gold/solution.py`) and test suite (`gold/test.py`) are
imported verbatim from BigCodeBench and remain under Apache-2.0. Per ADR-007
invariant #3 (no license downgrade), this attribution is preserved.

| pack id | BigCodeBench task_id |
|---|---|
{rows}
"""


def _write(path: Path, content: str, *, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] would write {path.relative_to(REPO)} ({len(content)} bytes)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _ingest_row(row: dict[str, Any], dataset: str, retrieved: str, *, dry_run: bool) -> str | None:
    """Write one task pack for *row*; return the pack id (or None on skip)."""
    task_id = str(row.get("task_id", "")).strip()
    if not task_id:
        print("WARN: row has no task_id; skipping", file=sys.stderr)
        return None

    sanitized = _sanitize_task_id(task_id)
    pack_dirname = f"bcb-{sanitized}"
    pack_id = f"bcb_{sanitized}"
    entry_point = str(row.get("entry_point") or "task_func")
    libs = _parse_libs(str(row.get("libs", "")))
    instruction = str(row.get("instruct_prompt") or "").strip()
    difficulty = _DIFFICULTY_BY_DATASET.get(dataset, "medium")

    # Use the entry-point name in the slug; it disambiguates and is descriptive.
    slug = f"bcb-{sanitized}-{re.sub(r'[^a-z0-9]+', '-', entry_point.lower()).strip('-')}"

    pack_dir = REPO / "evals" / "task-packs" / pack_dirname
    gold_dir = pack_dir / "gold"

    task_yaml = _render_task_yaml(
        pack_id=pack_id,
        slug=slug,
        difficulty=difficulty,
        dataset=dataset,
        task_id=task_id,
        libs=libs,
        entry_point=entry_point,
        instruction=instruction,
        retrieved=retrieved,
    )
    prompt_md = (
        f"<!-- {_provenance_header(dataset, task_id, retrieved, '').strip()} -->\n"
        f"# Prompt for {pack_id}\n\n{instruction}\n"
    )
    solution_py = _provenance_header(dataset, task_id, retrieved, "#") + _build_solution(row)
    test_py = (
        _provenance_header(dataset, task_id, retrieved, "#")
        + str(row.get("test") or "").rstrip("\n")
        + "\n"
    )
    meta_json = (
        json.dumps(
            {
                "entry_point": entry_point,
                "source": {
                    "dataset": dataset,
                    "task_id": task_id,
                    "libs": libs,
                    "license": "Apache-2.0",
                    "retrieved": retrieved,
                    "url": f"https://huggingface.co/datasets/{dataset}",
                },
            },
            indent=2,
        )
        + "\n"
    )
    note_md = _render_note_md(
        pack_id=pack_id,
        entry_point=entry_point,
        dataset=dataset,
        task_id=task_id,
        retrieved=retrieved,
    )
    license_md = _render_license_md([(pack_id, task_id)], dataset, retrieved)

    _write(pack_dir / "task.yaml", task_yaml, dry_run=dry_run)
    _write(pack_dir / "prompt.md", prompt_md, dry_run=dry_run)
    _write(gold_dir / "solution.py", solution_py, dry_run=dry_run)
    _write(gold_dir / "test.py", test_py, dry_run=dry_run)
    _write(gold_dir / "meta.json", meta_json, dry_run=dry_run)
    _write(pack_dir / "NOTE.md", note_md, dry_run=dry_run)
    _write(pack_dir / "LICENSE.md", license_md, dry_run=dry_run)
    return pack_id


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest BigCodeBench tasks into POLLMEVALS task-pack format.",
    )
    parser.add_argument("--n", type=int, default=10, help="number of tasks to ingest (default 10)")
    parser.add_argument(
        "--dataset",
        default="bigcode/bigcodebench",
        choices=sorted(_DIFFICULTY_BY_DATASET),
        help="source dataset (bigcodebench=medium, bigcodebench-hard=hard)",
    )
    parser.add_argument("--config", default="default", help="dataset config (default 'default')")
    parser.add_argument(
        "--split", default=_DEFAULT_SPLIT, help=f"dataset split (default {_DEFAULT_SPLIT})"
    )
    parser.add_argument("--offset", type=int, default=0, help="row offset into the split")
    parser.add_argument(
        "--dry-run", action="store_true", help="print what would be written, touch nothing"
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    # chdir so relative paths (evals/task-packs/...) resolve at the repo root.
    os.chdir(REPO)

    if args.n <= 0:
        print("ERROR: --n must be positive", file=sys.stderr)
        return 2

    retrieved = date.today().isoformat()
    split = _resolve_split(args.dataset, args.config, args.split)
    rows = _fetch_rows(args.dataset, args.config, split, args.offset, args.n)
    if not rows:
        print("ERROR: datasets-server returned 0 rows", file=sys.stderr)
        return 1

    print(
        f"Ingesting {len(rows)} BigCodeBench task(s) from {args.dataset} "
        f"[{args.config}/{split}] offset={args.offset}" + ("  (DRY RUN)" if args.dry_run else "")
    )
    created: list[str] = []
    for row in rows:
        pack_id = _ingest_row(row, args.dataset, retrieved, dry_run=args.dry_run)
        if pack_id:
            created.append(pack_id)
            print(f"  ✓ {pack_id}")

    print(f"\n{len(created)} pack(s) {'planned' if args.dry_run else 'written'}.")
    if not args.dry_run and created:
        print("Validate: python infra/scripts/validate-task-specs.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
