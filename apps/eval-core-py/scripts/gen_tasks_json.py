#!/usr/bin/env python
"""Generate apps/site/public/tasks.json from the eval task packs.

RFC-006 Phase 4c — transparency. The leaderboard shows scores but the site never
said WHAT is being tested. This emits the task catalogue (id, category,
difficulty, what's asked, what's judged, link to the full spec in the repo) so a
viewer can see the tasks and verify them.

Run from anywhere (chdirs to the repo root):
  uv run --project apps/eval-core-py python apps/eval-core-py/scripts/gen_tasks_json.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
_PACKS = REPO / "evals" / "task-packs"
_OUT = REPO / "apps" / "site" / "public" / "tasks.json"
_REPO_URL = "https://github.com/ForgePlan/pollmevals/tree/main/evals/task-packs"


def _summary(description: str) -> str:
    """First 1-2 sentences of the task description, single-spaced."""
    text = " ".join(description.split())
    cut = text[:240]
    dot = cut.rfind(". ")
    return (cut[: dot + 1] if dot > 80 else cut).strip()


def _criteria(pack: Path) -> list[dict[str, object]]:
    rubric_path = pack / "rubric.yaml"
    if not rubric_path.exists():
        return []
    data = yaml.safe_load(rubric_path.read_text(encoding="utf-8"))
    crit = data.get("criteria", {}) if isinstance(data, dict) else {}
    out: list[dict[str, object]] = []
    if isinstance(crit, dict):
        for name, body in crit.items():
            weight = body.get("weight") if isinstance(body, dict) else None
            out.append({"name": str(name), "weight": weight})
    return out


def main() -> int:
    os.chdir(REPO)
    tasks: list[dict[str, object]] = []
    for pack in sorted(p for p in _PACKS.iterdir() if p.is_dir()):
        task_yaml = pack / "task.yaml"
        if not task_yaml.exists():
            continue
        d = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            continue
        tasks.append(
            {
                "id": str(d.get("id", pack.name)),
                "task_id": pack.name,
                "slug": str(d.get("slug", pack.name)),
                "category": str(d.get("category", "")),
                "difficulty": str(d.get("difficulty", "")),
                "language": str(d.get("language", "")),
                "summary": _summary(str(d.get("description", ""))),
                "criteria": _criteria(pack),
                "repo_url": f"{_REPO_URL}/{pack.name}",
            }
        )

    payload = {"generated_from": "evals/task-packs", "tasks": tasks}
    _OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {_OUT} ({len(tasks)} tasks)")
    for t in tasks:
        print(f"  {t['id']:<7} {t['category']:<9} {t['difficulty']:<7} {t['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
