<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); README — pack-level meta-README for doc_01_cli_readme -->
# doc_01_cli_readme

POLLMEVALS task pack — documentation task. The candidate is asked to
write a production-grade `README.md` for an imaginary CLI tool called
`pollmevals fetch-task`.

## Sourcing

**Tier 1 (own-authored)** per [ADR-007](../../../.forgeplan/adrs/).
Provenance: 2026-05-26 by gogocat. Content licence: MIT. Spec licence:
CC-BY-SA-4.0.

## Contents

| Path | Purpose |
|---|---|
| `task.yaml` | Task spec — schema, prompt, weight components, calibration band ranges. Render this via `apps/eval-core-py/` to produce the candidate prompt. |
| `rubric.yaml` | Judge rubric — 5 equal-weight criteria with 0/5/10 anchors. Documentation tasks are judge-only; no host-side evaluator. |
| `prompt.md` | Human-readable mirror of `task.yaml#prompt_template` plus authoring notes (not shown to candidates or judges). |
| `gold/README.gold.md` | Reference README at the top of the perfect band (expected score 9.0-10.0). Used for judge re-baselining, not shown to candidates. |
| `gold/README.md` | Meta-README for the gold pack — provenance + how the evaluator chain consumes it. |
| `calibration/<band>/sample-{001..005}.md` | 25 hand-authored READMEs across 5 bands (perfect / good / mediocre / poor / broken) for judge calibration. |

## Scoring

Documentation tasks use the formula in
[`docs/02-methodology/scoring.md`](../../../docs/02-methodology/scoring.md):

```
final_score = mean(median_per_criterion)
```

across the five rubric criteria:
`structural_completeness`, `factual_accuracy`, `clarity`, `actionability`,
`consistency`. Each weighted 0.20.

## Calibration band design

| Band | Range | Distinguishing feature |
|---|---|---|
| perfect | 9.0-10.0 | All 8 sections present, every fact correct, voice is reference-grade. 5 distinct authorial styles. |
| good | 7.0-8.5 | All sections present; exactly one minor flaw per sample (wrong flag, stale path, wrong env default, slight ambiguity, factual slip on one exit code). |
| mediocre | 4.5-6.5 | Missing one or two required sections, OR factually wrong on one whole subcommand. |
| poor | 2.0-4.0 | Large structural gaps — no Commands, no Installation, hallucinated subcommands, or wrong tool entirely. |
| broken | 0.0-1.5 | Garbage — truncated mid-sentence, irrelevant topic, content-free SLOP, lorem-ipsum, one-line TODO stub. |

## Anti-SLOP gates (RFC-003)

- **G1 (provenance)** — every `.md` in this pack starts with the
  canonical `<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); ... -->`
  comment. Verified via `grep -L`.
- **G2 (score band)** — to be verified after judge wiring lands; each
  sample's empirical score should fall in its band's range.
- **G3 (diversity)** — perfect band uses 5 distinct authorial styles
  (terse-formal man-page, tutorial walkthrough, FAQ, reference grammar,
  narrative engineer's notes). Other bands use distinct failure modes
  per sample to avoid sibling collisions.
- **G4 (contamination)** — to be re-verified before publication via
  WebSearch on first 80 characters of each sample.

## v0.2 scope bump

`n_samples_per_level` is 5 in v0.1 (25 total). The PRD-002 § Q4
stability target (judge MAD < 1.5) calls for 10 per level (50 total);
that scope bump lands in v0.2 alongside the parallel bump on
`be_01_jwt_auth`. See [`task.yaml`](./task.yaml) `calibration.v0_2_target_per_level`.

## How the evaluator chain consumes this pack

1. **Renderer** reads `task.yaml#prompt_template`, ships it to the
   candidate model verbatim.
2. **Candidate** produces Markdown. Normalisation (NOTE-007) strips
   anything outside Markdown blocks.
3. **JudgePanel** scores the candidate output against `rubric.yaml`.
   Judges never see `gold/` or `calibration/` contents.
4. **Aggregation** (RFC-002 Slice C): median per criterion, then mean
   of the five medians = `final_score`. Krippendorff α and bootstrap
   95% CI reported alongside.

## Reproduce locally

```sh
moon run eval-core-py:judge-calibrate -- --task doc_01
```

Expected: judge MAD ≤ 1.5 across the 25 calibration samples once the
judge wiring lands.
