---
depth: standard
id: EVID-003
kind: evidence
last_modified_at: 2026-05-24T07:39:24.295152+00:00
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

## ADI cycle (per NOTE-002 — retrofit)

### Abduction — research questions framed as hypotheses

- **H1**: lm-eval-harness uses content-addressed task versioning (hash-based, like POLLMEVALS plans) — silent task edits would invalidate previous results.
- **H2**: lm-eval-harness uses manual integer versioning — task authors bump `version: N` when behavior changes; reproducibility relies on (YAML file + git commit) tuple.
- **H3**: lm-eval-harness has a working solution for contamination detection that POLLMEVALS could adopt.

### Induction — verification per hypothesis

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (content-addressed) | docs/task_guide.md: `version:` is an integer field manually bumped; no hash-based change detection | False | **H1 REFUTED** |
| Y2 (manual integer + git pinning) | Same docs + v0.4.0 release notes: YAML registry + git commit hash is the recommended reproducibility contract; `--use_cache /path/to/sqlite_` for output replay | Confirmed exactly | **H2 SUPPORTED** — POLLMEVALS deliberately DIVERGES (content-addressed task_pack_sha256 in SPEC-001) |
| Y3 (contamination solved) | Open LLM Leaderboard discussion #472 closed March 2025: detection tool `detect-pretrain-code` (perplexity-based) used; contaminated models flagged but NOT removed; merged models show ~5-8pt inflation with no remedy | Unsolved | **H3 REFUTED** — POLLMEVALS shouldn't promise to solve in v0.1 |

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| `--use_cache` SQLite mechanism = direct precedent for ADR-002 evaluator-only reproduce | 9 | 9 | 9 | 27/27 | F: documented mechanism with exact flag. G: SQLite per-rank DB, specific behavior (skip already-completed). R: lm-eval-harness official docs + issue thread #2548 confirming semantics. |
| Task versioning is manual integer (`version: N`) — NOT content-addressed | 9 | 8 | 9 | 26/27 | F: explicit doc quotation. G: precise scheme. R: official docs (task_guide.md). |
| Open LLM Leaderboard contamination unsolved as of March 2025 | 8 | 8 | 8 | 24/27 | F: official discussion thread closed without resolution. G: specific date + tools named. R: HF Space discussion (authoritative for that leaderboard). |
| v0.4 rewrite (2024) replaced static Python registration with YAML registry | 8 | 8 | 9 | 25/27 | F: release notes. G: specific version + change description. R: GitHub release notes (authoritative). |
| Merged-model inflation ~5-8 percentage points (DPO + merging) | 7 | 8 | 7 | 22/27 | F: stated as range. G: pct range. R: discussion thread analysis, not peer-reviewed paper. |
| lm-eval-harness does NOT evaluate stacks (model-only) | 8 | 8 | 9 | 25/27 | F: explicit doc & architecture analysis. G: confirmed by no agent/multi-turn primitives. R: official repo. |

**Decision strength**: average sum = 24.8/27 (92%). One 27/27 claim (`--use_cache` precedent — load-bearing for ADR-002). Weakest: merged-model inflation range (22/27).

## Key Findings (preserved)

### Task versioning — manual integer (POLLMEVALS DIVERGES)

`version:` integer field, manually bumped. Contract: (YAML file + git commit hash). NO automatic hash-based detection.

POLLMEVALS divergence: SPEC-001 `task_pack_sha256 = sha256(prompt + evaluator + gold)` — content-addressed. Closes silent-bug-fix gap.

Source: <https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/task_guide.md>.

### `--use_cache` SQLite — DIRECT PRECEDENT for ADR-002

`--use_cache /path/to/sqlite_` stores model completions in per-rank SQLite DB; on re-run, evaluator skips already-completed samples, re-scores from cache — model API NOT called. Intended workflow for metric-formula changes.

Sources: <https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/interface.md>, <https://github.com/EleutherAI/lm-evaluation-harness/issues/2548>.

### Contamination — unresolved (validates EPIC-001 ER-5)

Open LLM Leaderboard discussion #472 closed March 2025 without definitive solution. `detect-pretrain-code` (Shi et al. 2023) flags but doesn't remove contaminated models. Merged models accumulate ~5-8pt inflation.

Source: <https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard/discussions/472>.

### v0.4 rewrite (2024) — YAML-declared task registry

Replaced static Python registration with YAML configs + dynamic runtime registry. POLLMEVALS pattern alignment: `evals/task-packs/<slug>/task.yaml`.

## Conclusions

- **Surviving hypothesis**: H2 (manual integer + git pinning) — POLLMEVALS deliberately DIVERGES via content-addressed `task_pack_sha256`
- **Decision strength**: 92% (one 27/27 — `--use_cache` precedent)
- **POLLMEVALS implication**: ADR-002 has direct precedent (validation); SPEC-001 task pinning is STRONGER than lm-eval-harness (closes silent-bug gap)
- **Contamination follow-up**: lightweight n-gram overlap monthly check on `evals/task-packs/` against public datasets in v0.1; defer neural detection to v1.0+

## Sources

1. <https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/task_guide.md>
2. <https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/interface.md>
3. <https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.0>
4. <https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard/discussions/472>
5. <https://github.com/EleutherAI/lm-evaluation-harness/issues/2548>

## Related Artifacts

- PRD-001 (informs — auto-linked)
- ADR-002 (reproduce semantics — direct precedent)
- SPEC-001 (`task_pack_sha256` — POLLMEVALS divergence from integer versioning)
- EPIC-001 ER-5 (contamination risk confirmed industry-wide)
- Future Note: monthly n-gram contamination check for `evals/task-packs/`
- NOTE-002 (Evidence Quality Standard — retrofit)

