---
depth: standard
id: EVID-003
kind: evidence
last_modified_at: 2026-05-23T19:29:21.395517+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: ADR-002
  relation: informs
status: active
title: 'prior art: lm-evaluation-harness (EleutherAI) — --use_cache SQLite + integer task versioning'
---

# EVID-003: lm-evaluation-harness (EleutherAI) — --use_cache SQLite + integer task versioning

## Structured Fields

verdict: supports
congruence_level: 2
evidence_type: audit

## Summary

External prior art review of EleutherAI's lm-evaluation-harness v0.4+ (Gao et al. 2021 + 2024 rewrite). Directly validates ADR-002 (evaluator-only reproduce) via the `--use_cache` SQLite mechanism, and informs POLLMEVALS to diverge from integer task versioning in favor of content-addressing.

## Key Findings

### Task versioning — manual integer, not hash-based (POLLMEVALS DIVERGES)

Each YAML task config carries a plain `version:` integer field (e.g. `version: 3`). When a task is updated to fix a bug, maintainers manually increment the integer. The harness reports versions in result JSON so operators can detect mismatches between runs. There is **NO automatic hash-based change detection** — the recommended reproducibility contract is `(YAML file + git commit hash)`, not content-addressed task snapshots.

Source: <https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/task_guide.md>.

**POLLMEVALS divergence**: SPEC-001 uses `task_pack_sha256 = sha256(prompt + evaluator + gold)` — content-addressed. This closes the gap lm-eval-harness leaves open (silent bug fixes that re-use the same `version:` integer would be invisible to consumers).

### Reproducibility — `--use_cache` SQLite — DIRECT PRECEDENT for ADR-002

The harness supports **true output-replay mode**:

```
lm_eval --model openai --tasks mmlu --use_cache /path/to/sqlite_db
```

`--use_cache /path/to/sqlite_` stores model completions in a per-rank SQLite DB. On a re-run with the same cache path, the evaluator **skips already-completed samples and re-scores from the cache** — the model API is NOT called again. `--log_samples` additionally serialises every prompt+completion to JSON for post-hoc metric recomputation.

This means "re-run evaluator on cached outputs" IS possible and is the **intended workflow** for metric-formula changes.

Sources:
- <https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/interface.md>
- <https://github.com/EleutherAI/lm-evaluation-harness/issues/2548>

**POLLMEVALS direct precedent**: ADR-002's evaluator-only reproduce IS exactly this pattern, just with content-addressed file storage instead of SQLite.

### Contamination — unresolved problem (validates EPIC-001 ER-5 risk)

The Open LLM Leaderboard team (running on lm-eval-harness) treats contamination as an **unsolved problem** as of the official discussion thread closure in March 2025. Primary detection tool: `detect-pretrain-code` (Shi et al. 2023, perplexity-based). Confirmed contaminated models are **flagged but NOT removed** from the leaderboard. No automated hash-rotation of test sets is in place; private benchmarks were discussed but not shipped as of that date.

Merged models (DPO + merging) accumulate ~5-8pt inflation with no current systematic remedy.

Source: <https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard/discussions/472>.

### v0.4 rewrite (2024) — YAML-declared task registry

The v0.4 rewrite replaced static Python task registration with YAML-declared task configs and a dynamic runtime registry (`ALL_TASKS` no longer compiled statically). This decouples task-definition changes from framework releases and allows task packs to live in separate repos.

Source: <https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.0>.

**POLLMEVALS pattern alignment**: `evals/task-packs/<slug>/task.yaml` follows this approach — task definitions are data, not code.

## Implications for POLLMEVALS

1. **ADR-002 has direct precedent** — `--use_cache` is exactly the pattern. No methodological controversy.
2. **POLLMEVALS DIVERGES** from `version: <integer>` task versioning. Our content-addressed `task_pack_sha256` is structurally stronger.
3. **Contamination is an industry-wide unsolved problem** — POLLMEVALS v0.1 should not promise to solve it. Worth captured: monthly n-gram overlap checks on `evals/task-packs/` against public datasets as a lightweight gate, with neural detection deferred to v1.0+.
4. **lm-eval-harness does NOT evaluate stacks** — confirmed gap that POLLMEVALS fills. lm-eval-harness for raw model batch benchmarking; POLLMEVALS for stack evaluation.

## Sources

1. <https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/task_guide.md> — Task VERSION semantics, YAML+git-commit contract
2. <https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/interface.md> — `--use_cache`, `--log_samples`, `--seed` flags
3. <https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.0> — v0.4 rewrite: YAML registry, CachingLM
4. <https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard/discussions/472> — Official contamination discussion
5. <https://github.com/EleutherAI/lm-evaluation-harness/issues/2548> — `--use_cache` semantics confirmation

## Confidence

🟢 High for findings 1, 2, 4 (primary sources). 🟡 Medium for finding 3 (contamination state beyond March 2025 not confirmed; may have evolved).

## Open Questions

- Has Open LLM Leaderboard v2 shipped private rotating benchmarks post-March 2025? Not investigated.
- Does lm-eval-harness v0.4.9 have community extensions for agent-level eval (tool calls, multi-turn)? Not investigated.

## Related Artifacts

- PRD-001 (informs — auto-linked)
- ADR-002 (reproduce semantics — direct precedent)
- SPEC-001 (`task_pack_sha256` — POLLMEVALS divergence from integer versioning)
- EPIC-001 ER-5 (contamination risk — confirmed industry-wide)
- Future Note: monthly n-gram contamination check for `evals/task-packs/`



