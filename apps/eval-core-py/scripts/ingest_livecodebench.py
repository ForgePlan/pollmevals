#!/usr/bin/env python
"""Ingest a sample of LiveCodeBench problems into POLLMEVALS task packs.

LiveCodeBench (https://livecodebench.github.io/) is a contamination-free,
time-windowed benchmark of competitive-programming problems from LeetCode,
AtCoder, and Codeforces. Each problem ships a problem statement, public
example tests, and a larger set of hidden tests — the tests ARE the objective
oracle (there is no reference solution in the dataset).

This script pulls the NEWEST release window (``release_v6`` -> ``test6.jsonl``,
problems dated 2025-01 onward) so the ingested sample sits past every current
model's training cutoff, and writes one pack per problem under
``evals/task-packs/lcb-<platform>-<question_id>/`` mirroring the structure of
``be_01_jwt_auth`` (task.yaml + prompt.md + gold/ + NOTE.md).

Dataset : livecodebench/code_generation_lite  (HF)
License : MIT (declared in the dataset loader ``_info().license``; the repo
          card front-matter tags it ``cc`` — we record MIT as primary per the
          loader + the upstream GitHub repo, and note the ``cc`` tag honestly).

Run from anywhere (the script chdir's to the repo root)::

    uv run --project apps/eval-core-py \\
        python apps/eval-core-py/scripts/ingest_livecodebench.py --n 10
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import pickle  # trusted LCB native encoding — see decode_test_cases() docstring
import re
import sys
import urllib.request
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]

DATASET = "livecodebench/code_generation_lite"
LICENSE_PRIMARY = "MIT"  # dataset loader _info().license == "MIT License"
LICENSE_CARD_TAG = "cc"  # HF repo-card front-matter (recorded for honesty)
HF_RESOLVE = "https://huggingface.co/datasets/{ds}/resolve/main/{f}"

# release_tag -> jsonl shard holding that window's NEW problems. The lite loader
# concatenates shards cumulatively; the highest shard is the most recent window.
WINDOW_FILE = {
    "release_v6": "test6.jsonl",  # 2025-01 onward (newest, default)
    "release_v5": "test5.jsonl",  # +2024-09..2025-01
    "release_v4": "test4.jsonl",  # +2024-07..2024-09
    "release_v3": "test3.jsonl",  # +2024-05..2024-07
}
WINDOW_NOTE = {
    "release_v6": "problems released 2025-01 onward (post-2024 cutoff)",
    "release_v5": "problems released 2024-09 through 2025-01",
    "release_v4": "problems released 2024-07 through 2024-09",
    "release_v3": "problems released 2024-05 through 2024-07",
}

_PLATFORM_EXT = {"leetcode": "py", "atcoder": "py", "codeforces": "py"}
_DIFFICULTY_OK = {"easy", "medium", "hard"}
_CHUNK = 1 << 18  # 256 KiB streaming reads


def decode_test_cases(blob: str) -> list[dict[str, Any]]:
    """Decode a LiveCodeBench test-case blob into ``[{input, output, testtype}]``.

    ``public_test_cases`` is plain JSON. ``private_test_cases`` (when large) is
    encoded as ``base64(zlib(pickle(json_string)))`` — the exact round-trip the
    official LiveCodeBench harness uses to (de)serialise its hidden tests. We
    therefore ``pickle.loads`` a JSON *string* and parse it. This is the
    dataset's native on-disk format, not arbitrary third-party input; the bytes
    come straight from the canonical HF dataset over HTTPS.
    """
    if not blob:
        return []
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        raw = zlib.decompress(base64.b64decode(blob))
        obj: Any = pickle.loads(raw)  # trusted: LCB dataset's own native encoding
        if isinstance(obj, (bytes, bytearray)):
            obj = obj.decode("utf-8")
        if isinstance(obj, str):
            obj = json.loads(obj)
        return obj


def stream_rows(version_tag: str, n: int) -> list[dict[str, Any]]:
    """Stream the first ``n`` JSONL records of a release window without
    downloading the whole (100s of MB) shard."""
    shard = WINDOW_FILE[version_tag]
    url = HF_RESOLVE.format(ds=DATASET, f=shard)
    req = urllib.request.Request(url, headers={"User-Agent": "pollmevals-ingest/0.1"})
    rows: list[dict[str, Any]] = []
    buf = b""
    with urllib.request.urlopen(req, timeout=180) as resp:  # fixed HF https URL
        while len(rows) < n:
            chunk = resp.read(_CHUNK)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf and len(rows) < n:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if line:
                    rows.append(json.loads(line.decode("utf-8")))
    return rows


def sanitize(value: str) -> str:
    """Lowercase, keep [a-z0-9-], collapse runs of separators."""
    out = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-{2,}", "-", out) or "x"


def slug_from_title(title: str) -> str:
    words = sanitize(title).split("-")
    return "-".join(w for w in words if w)[:60] or "lcb-problem"


def normalize_difficulty(raw: str) -> str:
    d = (raw or "").strip().lower()
    return d if d in _DIFFICULTY_OK else "medium"


def parse_contest_date(raw: str) -> str:
    """Return an ISO date (YYYY-MM-DD) from the row's contest_date timestamp."""
    if not raw:
        return "unknown"
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return raw[:10]


def build_prompt(content: str, starter: str, has_starter: bool) -> str:
    """Render the candidate-facing prompt (problem statement + I/O contract)."""
    lines = [content.rstrip(), ""]
    if has_starter:
        lines += [
            "## Starter code",
            "",
            "Complete the following; keep the given signature.",
            "",
            "```python",
            starter.rstrip(),
            "```",
            "",
            "Output only the completed solution code. No prose, no markdown fences.",
        ]
    else:
        lines += [
            "## I/O contract",
            "",
            "Read all input from standard input and write the answer to standard "
            "output, matching the formats shown in the examples above.",
            "",
            "Output only a single self-contained program. No prose, no markdown fences.",
        ]
    return "\n".join(lines) + "\n"


def render_task_yaml(
    *,
    pack_num: int,
    slug: str,
    difficulty: str,
    description: str,
    prompt_template: str,
    version_tag: str,
    row: dict[str, Any],
    has_starter: bool,
    n_public: int,
    n_private: int,
) -> str:
    """Build the task.yaml text, matching the be_01 field structure."""
    pid = f"lcb_{pack_num:03d}"
    date_iso = parse_contest_date(row.get("contest_date", ""))
    platform = row.get("platform", "unknown")
    oracle = "function-completion tests" if has_starter else "stdin/stdout tests"
    header = (
        f"# source: livecodebench/code_generation_lite ({version_tag}) — "
        f"ingested {datetime.now(UTC).date().isoformat()} (license: {LICENSE_PRIMARY})\n"
    )
    return header + (
        f"schema_version: pollmevals.task.v1\n"
        f"id: {pid}\n"
        f"slug: {slug}\n"
        f'version: "1.0"\n'
        f"category: algo\n"
        f"difficulty: {difficulty}\n"
        f"language: python\n"
        f"\n"
        f"# Sourcing tier per ADR-007: external = ingested from a third-party\n"
        f"# benchmark, kept under its upstream license, never edited in place.\n"
        f"sourcing: external\n"
        f"\n"
        f"description: |\n"
        f"{_indent(description, 2)}\n"
        f"\n"
        f"prompt_template: |\n"
        f"{_indent(prompt_template, 2)}\n"
        f"\n"
        f"success_criteria:\n"
        f"  - Program is accepted by every gold test in gold/tests.json "
        f"({n_public} public + {n_private} private input/output pairs).\n"
        f"  - Output matches the expected output exactly (after trailing-"
        f"whitespace normalisation) for each test.\n"
        f"  - Solution runs within the contest time/memory limits.\n"
        f"\n"
        f"# The objective oracle is the test set (no reference solution ships\n"
        f"# with LiveCodeBench). Execution needs a {oracle} runner — see NOTE.md.\n"
        f"oracle: tests\n"
        f"\n"
        f"license:\n"
        f"  primary: {LICENSE_PRIMARY}\n"
        f"  hf_card_tag: {LICENSE_CARD_TAG}\n"
        f"\n"
        f"source:\n"
        f"  dataset: {DATASET}\n"
        f"  version_tag: {version_tag}\n"
        f"  platform: {platform}\n"
        f"  question_id: {row.get('question_id', '')}\n"
        f"  contest_id: {row.get('contest_id', '')}\n"
        f"  contest_date: {date_iso}\n"
        f"\n"
        f"# Score weights per docs/02-methodology/scoring.md coding-task formula.\n"
        f"# For an objective algo task, correctness (test pass-rate) dominates;\n"
        f"# style/complexity components are recorded but secondary.\n"
        f"weight_components:\n"
        f"  correctness: 0.70\n"
        f"  complexity: 0.10\n"
        f"  linter: 0.10\n"
        f"  pattern_match: 0.10\n"
    )


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + ln if ln else pad.rstrip() for ln in text.rstrip().splitlines())


def render_note(
    *, slug: str, has_starter: bool, version_tag: str, n_public: int, n_private: int
) -> str:
    window = WINDOW_NOTE.get(version_tag, version_tag)
    shape = "function-completion" if has_starter else "stdin/stdout"
    runnable = (
        "Functional (LeetCode-style) problem: the candidate completes a given "
        "function signature. A test runner must import the solution and call the "
        "function with each test input, comparing the return value."
        if has_starter
        else "Self-contained stdin/stdout problem: the candidate writes a whole "
        "program that reads stdin and writes stdout. A test runner must pipe "
        "each test `input` into the program and diff its stdout against `output`."
    )
    return (
        f"# Execution shape — {slug}\n"
        f"\n"
        f"**Source**: `{DATASET}` ({version_tag}, {window}). License: "
        f"{LICENSE_PRIMARY}.\n"
        f"\n"
        f"**Oracle**: the test cases in `gold/tests.json` "
        f"({n_public} public + {n_private} private input/output pairs). "
        f"LiveCodeBench ships **no reference solution** — the hidden tests are "
        f"the sole objective oracle.\n"
        f"\n"
        f"**Problem type**: {shape}.\n"
        f"\n"
        f"{runnable}\n"
        f"\n"
        f"## Runnable now?\n"
        f"\n"
        f"**Needs a test-runner.** The current executor (see `be_01_jwt_auth`) "
        f"does a single-file write + a framework test command (vitest/pytest "
        f"against a fixed spec). These LCB problems instead need a generic "
        f"**{shape} harness** that feeds each `gold/tests.json` case to the "
        f"candidate program and compares output. That harness does not exist in "
        f"the executor yet, so these packs are **ingested-but-not-yet-runnable** "
        f"until a `tests.json` runner is added.\n"
        f"\n"
        f"They are *closer* to runnable than repo-based tasks (no git apply, no "
        f"multi-file project, no dependency install — just a script + I/O pairs), "
        f"so wiring the runner is a small, well-scoped follow-up.\n"
    )


def write_pack(out_root: Path, pack_num: int, row: dict[str, Any], version_tag: str) -> Path:
    platform = sanitize(row.get("platform", "lcb"))
    qid = sanitize(row.get("question_id", f"q{pack_num}"))
    pack_dir = out_root / f"lcb-{platform}-{qid}"
    gold = pack_dir / "gold"
    gold.mkdir(parents=True, exist_ok=True)

    title = row.get("question_title") or row.get("question_id") or "problem"
    slug = slug_from_title(title)
    difficulty = normalize_difficulty(row.get("difficulty", ""))
    content = (row.get("question_content") or "").strip()
    starter = row.get("starter_code") or ""
    has_starter = bool(starter.strip())

    public = decode_test_cases(row.get("public_test_cases", ""))
    private = decode_test_cases(row.get("private_test_cases", ""))

    # gold/tests.json — the objective oracle (public + private I/O pairs).
    tests = {
        "source": DATASET,
        "version_tag": version_tag,
        "question_id": row.get("question_id", ""),
        "oracle": "tests",
        "public": public,
        "private": private,
    }
    (gold / "tests.json").write_text(json.dumps(tests, indent=2) + "\n", encoding="utf-8")

    if has_starter:
        ext = _PLATFORM_EXT.get(row.get("platform", ""), "py")
        (gold / f"starter_code.{ext}").write_text(starter, encoding="utf-8")

    description = content if len(content) <= 600 else content[:597].rstrip() + "..."
    prompt = build_prompt(content, starter, has_starter)
    (pack_dir / "prompt.md").write_text(
        f"<!-- source: {DATASET} ({version_tag}) — license {LICENSE_PRIMARY} -->\n"
        f"# {title}\n\n{prompt}",
        encoding="utf-8",
    )
    (pack_dir / "task.yaml").write_text(
        render_task_yaml(
            pack_num=pack_num,
            slug=slug,
            difficulty=difficulty,
            description=description,
            prompt_template=prompt,
            version_tag=version_tag,
            row=row,
            has_starter=has_starter,
            n_public=len(public),
            n_private=len(private),
        ),
        encoding="utf-8",
    )
    (pack_dir / "NOTE.md").write_text(
        render_note(
            slug=slug,
            has_starter=has_starter,
            version_tag=version_tag,
            n_public=len(public),
            n_private=len(private),
        ),
        encoding="utf-8",
    )
    return pack_dir


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest LiveCodeBench into task packs.")
    ap.add_argument("--n", type=int, default=10, help="number of packs (default 10)")
    ap.add_argument(
        "--version-tag",
        default="release_v6",
        choices=sorted(WINDOW_FILE),
        help="release window; newest (release_v6) is the most decontaminated",
    )
    ap.add_argument(
        "--out-root",
        default="evals/task-packs",
        help="destination root for packs (default evals/task-packs)",
    )
    ap.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="first lcb_NNN id number (default 1)",
    )
    args = ap.parse_args()

    os.chdir(REPO)
    out_root = (REPO / args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"Streaming {args.n} problems from {DATASET} [{args.version_tag}] ...")
    rows = stream_rows(args.version_tag, args.n)
    if len(rows) < args.n:
        print(f"WARN: only {len(rows)} rows available in window", file=sys.stderr)

    created: list[Path] = []
    dist: dict[str, int] = {}
    for i, row in enumerate(rows):
        pack = write_pack(out_root, args.start_index + i, row, args.version_tag)
        created.append(pack)
        diff = normalize_difficulty(row.get("difficulty", ""))
        dist[diff] = dist.get(diff, 0) + 1
        print(
            f"  [{args.start_index + i:>3}] {pack.name:40} "
            f"{diff:7} {row.get('contest_date', '')[:10]}"
        )

    print(f"\nCreated {len(created)} packs under {out_root}")
    print(f"Difficulty distribution: {dict(sorted(dist.items()))}")
    print(f"License: {LICENSE_PRIMARY} (HF card tag: {LICENSE_CARD_TAG})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
