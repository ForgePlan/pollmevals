---
depth: standard
id: ADR-015
kind: adr
last_modified_at: 2026-06-03T21:00:08.397322+00:00
last_modified_by: claude-code/2.1.156
links:
- target: PRD-002
  relation: refines
status: draft
title: Methodology v0.2 — 5-frontier judge panel; deterministic lint+typing, judges score subjective axes only
---

## Status

Draft (proposed 2026-06-03). Refines PRD-002 (judge-panel methodology) and ADR-005 (median + bootstrap-CI publication gate). Awaiting review before activation.

## Context and Problem Statement

The v0.1 judge panel runs 3 routes in practice (`claude-sonnet-4-6-judge`, `gpt-5-mini-judge`, and an un-isolated `gemini-3-flash`), with only 2 properly billing-isolated `-judge` aliases. Observed inter-judge agreement is low: Krippendorff α = 0.187 (EVID-047) → 0.358 after the reasoning-cap fix (EVID-048/050), still below the 0.70 publication gate. Two problems compound it:

1. **Weak/undersized panel.** Mini-class judges are less self-consistent and a 2-judge panel has no tie-break. The user directs us to judge on the most powerful June-2026 models.
2. **Dual-path double-count.** The `be_01` rubric scores `type_safety` as a judge criterion (weight 0.15) while `scoring.md` also scores a deterministic `type_safety_score` (tsc, weight 0.10) — the same signal counted twice. Lint has the analogous risk.

## Decision Drivers

- Raise inter-judge agreement toward the α ≥ 0.70 gate without inventing scores.
- Judge **diversity** (uncorrelated vendor families) over raw count — prior-art: frontier judges reach α 0.80–0.91; family diversity de-biases more than a 4th same-family judge.
- No double-count: a signal a compiler can decide must not also be judged.
- Preserve run immutability (ADR-0002) and the median + bootstrap-CI gate (ADR-005).
- Cost-awareness: judge calls dominate spend.

## Considered Options

- **A — Status quo** (2–3 mixed judges, deterministic lint/tsc, `type_safety` also judged).
- **B — 5 strong judges that ALSO grade lint/typing** (keeps the double-count).
- **C — 5 frontier judges, 5 families; lint/typing DETERMINISTIC only; judges score subjective axes only.** ← chosen.
- **D — Defer to v0.3.**

## Decision Outcome

Chosen: **Option C.**

**Judge panel** = the 5 most powerful June-2026 models, 5 distinct families (user decision 2026-06-03): Claude Opus 4.8 · GPT-5.5 · Gemini 3.1 Pro · Grok 4 · DeepSeek V4 Pro. Wired as `-judge` aliases in `infra/litellm-config.yaml`, billed to `OPENROUTER_API_KEY_JUDGE` (NFR-005), `reasoning_effort=low` so the rubric JSON fits the 2048-tok cap (EVID-050 pattern).

**Lint + typing are DETERMINISTIC** (eslint/ruff + tsc), 0.10 each in the frozen coding formula, computed by `auto_metrics.py` on the harness's real file tree. The judge rubric's `type_safety` criterion becomes `design_appropriateness` (subjective: composition, idioms, boundaries — what a compiler can't decide). `rubric_version` → 2.0.

**Evidence-backed levers** folded in (Research-B prior-art): chain-of-thought in the judge prompt, forced per-criterion scoring, calibration few-shot anchors, rubric criteria kept orthogonal to deterministic metrics.

**Self-judging:** `_FAMILY_ALIASES` gains xai/deepseek/minimax so the guard normalises grok-4 / deepseek-* correctly. Until per-eval exclusion lands, the 5 frontier models are the **reference/judge tier** and the scored candidate roster excludes those families.

### Consequences

- New **MethodologyVersion v0.2.0**. Per ADR-0002, published v0.1.0 runs are NOT re-scored in place; new runs reference v0.2.0 with a `supersedes: methodology-v0.1.0` manifest link. The existing board is re-scored as a NEW run.
- **Refines** PRD-002 + ADR-005 — same median reducer + CI-lower-bound ≥ 0.70 gate, expanded roster + criteria clean-up. Not a supersede.
- Cost ≈ $0.10/eval (5 frontier judges @ ~3k in / 600 out); the current 45-cell board re-scores for ~$5–15. Tiering (strong panel on calibration only) is unnecessary at this scale; revisit when the grid grows.
- Follow-up: per-eval self-judging exclusion to re-admit grok-4 / deepseek-* as candidates; live route ping pending a funded key.

## More Information

Implemented in PR #59 (`feat/v0.2-infra-wave`): litellm-config 5 judge routes, judge_panel `_FAMILY_ALIASES`, build_real_board `_JUDGES`, be_01 rubric, `auto_metrics.py`. 766 tests green. Evidence: EVID-047/048 (α + cap fix), EVID-049/050 (gpt-5-mini reasoning fix). Prior-art: GPT-4o judge α 0.908 vs 70B 0.806 (arXiv 2506.13639); CoT +7–13pp (arXiv 2604.23178); structured per-criterion 31.5% SPB reduction (arXiv 2604.22891); 3-diverse-family panel beats single large judge at 7× lower cost (Verga et al.).

