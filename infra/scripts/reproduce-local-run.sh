#!/usr/bin/env bash
set -euo pipefail
python -m pollmevals_eval_core.demo_run --tasks evals/tasks --stacks stacks --output artifacts --seeds 3
