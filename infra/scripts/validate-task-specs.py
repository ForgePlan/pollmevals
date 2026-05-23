#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/eval-core-py/src"))
from pollmevals_eval_core.registry import load_task_specs


def main() -> None:
    tasks = load_task_specs(Path("evals/tasks"))
    print(f"valid task specs: {len(tasks)}")
    for task in tasks:
        print(f"- {task.slug}@{task.version} [{task.category}]")


if __name__ == "__main__":
    main()
