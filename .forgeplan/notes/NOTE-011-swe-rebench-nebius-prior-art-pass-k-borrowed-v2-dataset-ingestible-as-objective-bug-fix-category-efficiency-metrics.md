---
depth: standard
id: NOTE-011
kind: note
last_modified_at: 2026-06-01T22:47:54.978920+00:00
last_modified_by: claude-code/2.1.156
links:
- target: PRD-006
  relation: informs
- target: PRD-009
  relation: informs
status: draft
title: SWE-rebench (Nebius) prior-art — pass^k borrowed + V2 dataset ingestible as objective bug-fix category + efficiency metrics
---

# NOTE-011: SWE-rebench (Nebius) prior-art — borrowings

Nebius shipped a June-2026 SWE-rebench update (+110 tasks) that, unlike most benchmarks, **runs real Codex and Claude Code harnesses** next to raw models — independent validation of our "model × harness" axis. Their analytics also surface efficiency (tokens/steps/cost/cached%) and a reliability metric we should adopt.

Sources: swe-rebench.com · HF `nebius/SWE-rebench-V2` · arxiv 2602.23866.

## External validation of our thesis
- Leaderboard lists **Codex (#2, 60.4%)** and **Claude Code (#3, 59.6%)** as entries beside raw GPT-5.5/Opus.
- Key finding: **"Claude gets a much bigger quality boost from its native scaffold; GPT ~same"** = our thesis (scaffolding matters, and *differently per model*).
- Cost signal: Cursor/Composer 53% @ **$0.23/task, 98.7% cached** — cached% is a real cost lever to report.
- Sobering: Nebius is ahead of us on *execution at scale*; we differentiate on judged subjective axes + L0–L8 granularity + open methodology, NOT by cloning their leaderboard.

## Borrowing 1 — pass^k reliability metric (DONE)
Commit `ac47de5` (branch `feat/pass-k-reliability-metric`): `apps/eval-core-py/src/scoring/pass_k.py`.
- `pass_at_k` (ceiling, solved ≥1 of k) · `pass_hat_k` (reliability, solved ALL k) · `flaky_fraction` (= pass@k − pass^k, the "got-lucky" band) · `pass_at_k_estimator` (unbiased, Chen et al. 2021).
- Pairs with best-of-N (PRD-009): pass@k = capability ceiling, pass^k = reliability floor.
- 25 unit tests, ruff + mypy --strict clean. **Publish-policy + threshold belong to the methodology** (ADR + MethodologyVersion) — follow-up.

## Borrowing 2 — SWE-rebench-V2 as an OBJECTIVE task category
Verdict: **ingestible**, clean conceptual mapping.
- Their `repository_patch` model = EXACTLY our `stack.yaml execution.mode: repository_patch` → rides the same stack executor (dynamic-eval) we need anyway.
- `FAIL_TO_PASS` / `PASS_TO_PASS` test lists → our binary auto `requirements[]` (RFC-004); `component_score` = their pass-rate = resolved signal. **No judges needed** (objective) → complements our subjective judged categories (docs / frontend / review).
- License **CC-BY-4.0** + per-instance repo SPDX → ADR-007 "licensed import with attribution" path. Decontaminated via `created_at` → also addresses our Contamination concern.
- Integration cost: a SWE-bench-style Docker test-runner (pull `image_name`, run `install_config.install`, apply patch, run `test_cmd`, parse via `log_parser`) inside our sandbox. Subset from 32k instances (their 110-task benchmark, or filter by `meta.llm_metadata.difficulty` / `language`).

## Borrowing 3 — efficiency metrics first-class
tokens-per-task, steps-per-task, cost-per-task, **cached%** → the agent/harness telemetry initiative. Their presentation is the reference.

## Affects
- **PRD-006** (task-catalog expansion): SWE-rebench-V2 = a ready objective bug-fix category.
- **PRD-009** (best-of-N / reliability): pass^k is the reliability companion — already implemented.
- Scoring methodology: a future ADR formalises publishing pass@k + pass^k + flakiness.




