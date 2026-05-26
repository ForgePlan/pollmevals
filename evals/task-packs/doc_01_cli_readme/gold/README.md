<!-- source: own-authored 2026-05-26 by gogocat (license: MIT); gold/README.md — meta-README for the gold/ directory of doc_01_cli_readme -->
# Gold pack — `doc_01_cli_readme`

**Provenance**: own-authored 2026-05-26 by gogocat. Licence: MIT. Sourcing
tier: Tier 1 per [ADR-007](../../../../.forgeplan/adrs/).

## Contents

| File | Purpose |
|---|---|
| `README.gold.md` | The reference README for the imaginary `pollmevals fetch-task` CLI. Target score: 9.0-10.0 (top of the perfect band). Used as the calibration anchor when re-baselining judges. |
| `README.md` | This file. Provenance + how the evaluator chain consumes the gold pack. |

`README.gold.md` is the document the candidate is **asked** to produce.
It is **not shown** to the candidate or the judge — judges score against
[`../rubric.yaml`](../rubric.yaml) anchors, not against gold. Gold exists
for two reasons:

1. **Calibration anchoring** — when we re-baseline a judge model, we run
   it on `README.gold.md` and the five `calibration/perfect/sample-*.md`
   and confirm its scores fall in `[9.0, 10.0]`.
2. **Authoring contract** — the gold demonstrates exactly what a
   top-of-band response looks like, so future task-pack authors can
   match the target.

## What this gold README proves

- **Structural completeness** — all 8 sections present in the prescribed
  order; every subcommand has its own level-3 heading with flags table +
  example + exit codes.
- **Factual accuracy** — every flag name, exit code, env-var name, and
  default value matches [`../task.yaml`](../task.yaml) `prompt_template`
  verbatim. Catalog URL matches.
- **Clarity** — imperative voice throughout; no filler phrases ("we will
  explore", "welcome to", "this document is intended to"); tables chosen
  over prose for structured data (flags, env vars).
- **Actionability** — Quick start runs end-to-end in <2 minutes; all
  three install channels (binary, Homebrew, Docker) have copy-pasteable
  commands; Troubleshooting names the exit code, the symptom, and the
  exact remediation.
- **Consistency** — one canonical tool spelling (`pollmevals fetch-task`);
  one flag style (`--long-form`); one table layout for flags; one
  language hint per code block.

## How the evaluator chain consumes this pack

Documentation tasks are **judge-only** — there is no host-side evaluator.
The pipeline:

1. **Renderer** (`apps/eval-core-py/`): reads
   [`../task.yaml`](../task.yaml) `prompt_template`, ships it to the
   candidate model.
2. **Candidate** produces Markdown output. Normalisation strips any prose
   outside Markdown blocks (NOTE-007).
3. **JudgePanel**: 3 vendor-family judges score 5 rubric criteria from
   [`../rubric.yaml`](../rubric.yaml). Each judge sees the candidate
   README + the rubric — never the gold, never the calibration labels,
   never the candidate's model identity (per
   `docs/04-runbook/07-judge-panel.md`).
4. **Aggregation** (RFC-002 Slice C): median per criterion, then mean of
   the five medians = `final_score`. Krippendorff α + bootstrap 95% CI
   reported alongside.
5. **Publication threshold**: α ≥ 0.70 and MAD ≤ 1.5 on the calibration
   set, per `docs/02-methodology/judge-policy.md`.

## Anti-SLOP gates (RFC-003 G1-G4)

- **G1 (provenance header)** — every `.md` in this directory starts with
  the `<!-- source: ... -->` HTML comment so it does not render but is
  grep-able.
- **G2 (score band)** — gold target ≥ 9.0 (mean of criterion medians).
  Re-verified after each judge-model refresh.
- **G3 (diversity)** — N/A for a single gold README; the diversity gate
  applies to the 25 calibration samples in [`../calibration/`](../calibration/).
- **G4 (contamination)** — WebSearch of the first 80 characters of
  `README.gold.md` returned 0 verbatim matches as of 2026-05-26. Re-check
  before publication.

## How to use this gold pack locally

```sh
# 1. Eyeball the gold against the rubric anchors
$EDITOR evals/task-packs/doc_01_cli_readme/gold/README.gold.md
$EDITOR evals/task-packs/doc_01_cli_readme/rubric.yaml

# 2. Diff a candidate output against gold (for human review only — judges
#    do not see gold).
diff -u README.gold.md candidate-output.md | less
```

To re-baseline judges:

```sh
moon run eval-core-py:judge-calibrate -- \
  --task doc_01 \
  --gold evals/task-packs/doc_01_cli_readme/gold/README.gold.md
```

Expected: mean criterion score ∈ [9.0, 10.0], MAD ≤ 1.5 across the panel.

## Reproducibility note

The gold README does not depend on any external resource — it documents
an imaginary CLI whose contract is fully specified in `task.yaml`. There
is nothing to install, nothing to fetch, no version to pin. Re-running
the calibration loop on this gold pack tomorrow, next month, or in a
year produces the same artefact bit-for-bit.
