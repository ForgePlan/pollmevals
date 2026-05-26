# EVAL-WIRE — doc_01_cli_readme calibration audit

**Audited:** 2026-05-26
**Auditor:** Documentation Engineer (structured heuristic, substituting for absent numerical evaluator)
**Reference rubric:** `evals/task-packs/doc_01_cli_readme/rubric.yaml` (v1.0)
**Reference prompt:** `evals/task-packs/doc_01_cli_readme/prompt.md`
**Reference gold:** `evals/task-packs/doc_01_cli_readme/gold/README.gold.md`
**Scoring:** 5 criteria, equal weight, mean of criterion scores → /10 → /10 = [0,1].

## Methodology

For each file, every criterion was scored 0-10 against rubric anchors:

- **structural_completeness** — presence/order/depth of the 8 required sections (Overview, Installation, Quick start, Commands, Configuration, Troubleshooting, Contributing, Licence) and the 4 subcommands (`list`, `show`, `validate`, `run`) under `Commands` with flags + examples + exit codes.
- **factual_accuracy** — alignment with `prompt.md` contract (flag names, exit codes, env-var names + defaults, catalog URL, paths). Hallucinations penalised heavily.
- **clarity** — scannability, imperative voice, absence of filler, useful headings, examples with expected output.
- **actionability** — copy-paste-runnable quick start, all three install channels, concrete troubleshooting with symptom + fix.
- **consistency** — uniform tool name, flag style, heading capitalisation, code-block language hints.

Final score = mean(5 criteria) / 10 — gives [0, 1].

---

## Gold reference score

| File | structural | factual | clarity | actionability | consistency | mean/10 | final [0,1] | gate (≥0.85) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `gold/README.gold.md` | 10 | 10 | 9 | 10 | 10 | 9.8 | **0.98** | PASS |

The gold README hits every anchor at the 10-point line: all 8 sections in prescribed order, every subcommand with flags+exit codes+example, all three install channels copy-pasteable, troubleshooting indexed by exit code with concrete fix, one canonical tool spelling, one flag style, consistent code-block language hints. Minor clarity nick (9 not 10) for two prose-heavy paragraphs in Overview and Run that the terse `perfect/sample-001` improves on.

---

## Per-file calibration scores

### `perfect/` (target band: ≥ 0.85)

| File | structural | factual | clarity | actionability | consistency | mean/10 | final | expected | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `perfect/sample-001.md` (terse Unix man-page) | 10 | 10 | 10 | 9 | 10 | 9.8 | 0.98 | ≥0.85 | IN_BAND |
| `perfect/sample-002.md` (tutorial, numbered steps) | 10 | 10 | 9 | 10 | 9 | 9.6 | 0.96 | ≥0.85 | IN_BAND |
| `perfect/sample-003.md` (FAQ-style) | 10 | 10 | 9 | 9 | 9 | 9.4 | 0.94 | ≥0.85 | IN_BAND |
| `perfect/sample-004.md` (reference / synopsis) | 10 | 10 | 10 | 10 | 10 | 10.0 | 1.00 | ≥0.85 | IN_BAND |
| `perfect/sample-005.md` (narrative engineer's-notes) | 10 | 10 | 8 | 9 | 9 | 9.2 | 0.92 | ≥0.85 | IN_BAND |

Notes:
- All five style variants prove the rubric rewards substance over form (man-page / tutorial / FAQ / reference / narrative all score ≥0.92).
- 005 takes the smallest clarity hit (-2) for prose-heavy paragraphs that work but are less scannable than tables.
- Zero factual errors across the perfect band — all `--category`, exit code, env-var defaults match the contract verbatim.

### `good/` (target band: 0.70 - 0.85)

| File | structural | factual | clarity | actionability | consistency | mean/10 | final | expected | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `good/sample-001.md` (`--cat` instead of `--category`) | 10 | 6 | 8 | 8 | 9 | 8.2 | 0.82 | 0.70-0.85 | IN_BAND |
| `good/sample-002.md` (exit 10 → "general failure") | 10 | 7 | 8 | 8 | 9 | 8.4 | 0.84 | 0.70-0.85 | IN_BAND |
| `good/sample-003.md` (`POLLMEVALS_LOG_LEVEL` default `warn`) | 10 | 7 | 8 | 8 | 9 | 8.4 | 0.84 | 0.70-0.85 | IN_BAND |
| `good/sample-004.md` (stale path `./tasks/be_01`) | 10 | 7 | 8 | 8 | 9 | 8.4 | 0.84 | 0.70-0.85 | IN_BAND |
| `good/sample-005.md` (conflates exit 9/10 in troubleshooting) | 10 | 7 | 8 | 7 | 9 | 8.2 | 0.82 | 0.70-0.85 | IN_BAND |

Notes:
- Each "good" sample carries exactly one factual slip per the rubric's 5-point anchor — judges should score factual ~5-7 here.
- 001 takes the deepest factual hit (-4) because the wrong flag name is repeated in three places (Quick start, list signature, example output), so it acts like multiple errors propagating from one source.
- All other criteria stay high — structure perfect, install channels intact, no hallucinations.

### `mediocre/` (target band: 0.45 - 0.65)

| File | structural | factual | clarity | actionability | consistency | mean/10 | final | expected | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `mediocre/sample-001.md` (Troubleshooting missing) | 6 | 9 | 7 | 4 | 9 | 7.0 | 0.70 | 0.45-0.65 | OUT_OF_BAND (high) |
| `mediocre/sample-002.md` (Configuration missing) | 6 | 9 | 7 | 5 | 9 | 7.2 | 0.72 | 0.45-0.65 | OUT_OF_BAND (high) |
| `mediocre/sample-003.md` (`run` invented `--profile`/`--retries`) | 8 | 3 | 7 | 4 | 6 | 5.6 | 0.56 | 0.45-0.65 | IN_BAND |
| `mediocre/sample-004.md` (Quick start AND Troubleshooting missing) | 5 | 9 | 7 | 3 | 9 | 6.6 | 0.66 | 0.45-0.65 | OUT_OF_BAND (high) |
| `mediocre/sample-005.md` (`validate` end-to-end wrong) | 8 | 3 | 7 | 4 | 6 | 5.6 | 0.56 | 0.45-0.65 | IN_BAND |

**Calibration concern in this band.** Three of five "mediocre" samples (001, 002, 004) score 0.66-0.72, which sits inside the **good** band (0.70-0.85), not mediocre. Root cause: a single missing section drops `structural_completeness` to ~6 and `actionability` to 3-5, but the remaining four criteria stay high because the rest of the content is accurate. The rubric's structural-completeness anchor at 5 says "Six or seven of the eight sections present" → a 7/8 sample legitimately scores 5-6 there, not below.

If the intent is to floor the band at 0.45-0.65, the "mediocre" samples need either (a) two missing sections (like 004 + something else), or (b) the missing-section flaw combined with a factual error (the way 003 and 005 land genuinely inside band by combining structural + factual hits).

Recommendation: keep 003 and 005 (in-band by design); rebuild 001/002/004 to compound a missing section with a factual slip in another section.

### `poor/` (target band: 0.20 - 0.40)

| File | structural | factual | clarity | actionability | consistency | mean/10 | final | expected | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `poor/sample-001.md` (no Commands section) | 3 | 6 | 6 | 3 | 8 | 5.2 | 0.52 | 0.20-0.40 | OUT_OF_BAND (high) |
| `poor/sample-002.md` (hallucinated init/sync/audit) | 5 | 0 | 5 | 2 | 7 | 3.8 | 0.38 | 0.20-0.40 | IN_BAND |
| `poor/sample-003.md` (no Install, no Config; abbreviated) | 5 | 7 | 4 | 3 | 7 | 5.2 | 0.52 | 0.20-0.40 | OUT_OF_BAND (high) |
| `poor/sample-004.md` (different tool `pollmevals-doctor`) | 6 | 0 | 6 | 4 | 8 | 4.8 | 0.48 | 0.20-0.40 | OUT_OF_BAND (high) |
| `poor/sample-005.md` (all subcommand descriptions wrong) | 6 | 0 | 5 | 2 | 7 | 4.0 | 0.40 | 0.20-0.40 | IN_BAND (edge) |

**Calibration concern in this band.** Three of five "poor" samples (001, 003, 004) land at 0.48-0.52 — top of poor or even into mediocre territory. Root causes:
- 001: drops Commands entirely (structural=3, actionability=3), but is otherwise coherent prose with accurate env-var list → drags mean back up.
- 003: missing two sections (Install, Config) but the parts present are factually clean → factual=7, consistency=7.
- 004: factual_accuracy=0 by rubric definition ("documents a different tool"), but `pollmevals-doctor` is internally coherent → structural/clarity/consistency hold up.

The rubric anchors for 0-point factual ("Multiple invented subcommands… wrong default catalog URL… two or more contradictions") fire here, but the other four criteria don't compound the damage enough. To force these into the 0.20-0.40 band, the "poor" samples need additional defects — e.g. broken-formatting + filler-text on top of the structural/factual collapse.

002 and 005 (where the contract is contradicted AND the prose is degraded) land in band correctly.

### `broken/` (target band: ≤ 0.20)

| File | structural | factual | clarity | actionability | consistency | mean/10 | final | expected | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `broken/sample-001.md` (truncated mid-sentence) | 1 | 0 | 1 | 0 | 0 | 0.4 | 0.04 | ≤0.20 | IN_BAND |
| `broken/sample-002.md` (off-task: gardening guide) | 0 | 0 | 6 | 0 | 6 | 2.4 | 0.24 | ≤0.20 | OUT_OF_BAND (high, edge) |
| `broken/sample-003.md` (SLOP filler everywhere) | 7 | 1 | 1 | 1 | 5 | 3.0 | 0.30 | ≤0.20 | OUT_OF_BAND (high) |
| `broken/sample-004.md` (one-line TODO stub) | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.00 | ≤0.20 | IN_BAND |
| `broken/sample-005.md` (lorem-ipsum + duplicate headings) | 2 | 0 | 1 | 0 | 1 | 0.8 | 0.08 | ≤0.20 | IN_BAND |

**Calibration concern in this band.** Two of five "broken" samples land just over the 0.20 ceiling:
- 002 (gardening guide): factual_accuracy collapses to 0 and structural to 0 (none of the required sections exist), but the **gardening prose itself is well-written**, so a literal-minded judge scoring clarity on prose quality alone could land at 6/10. A judge who reads clarity as "scannable docs prose **for the documented tool**" would score 0-1. The rubric anchor for clarity does not explicitly couple clarity to relevance — that coupling is implicit. Worth tightening the anchor.
- 003 (SLOP): all 8 section headings present (structural=7) but every body is content-free filler. Judges who score on heading presence alone would over-reward this. Re-reading rubric anchors, "non-trivial" is part of structural_completeness's 10-point definition; a strict reading drops structural to ~3-4, which would put 003 at ~0.18 — in band. My score of 7 is generous; a strict-reading judge should give 3-4.

Recommendation: tighten the rubric's structural_completeness 10-point anchor to require "non-trivial" content per section (already in the description; reinforce in anchor text), and add a clarity clause that ties clarity to documenting **this tool's contract** specifically.

---

## Per-band statistics

| Band | n | min | max | mean | median | expected range | in-band count | pass |
|---|---:|---:|---:|---:|---:|---|---:|---|
| perfect | 5 | 0.92 | 1.00 | 0.96 | 0.96 | ≥ 0.85 | 5/5 | YES |
| good | 5 | 0.82 | 0.84 | 0.832 | 0.84 | 0.70-0.85 | 5/5 | YES |
| mediocre | 5 | 0.56 | 0.72 | 0.640 | 0.66 | 0.45-0.65 | 2/5 | NO (3 land too high) |
| poor | 5 | 0.38 | 0.52 | 0.460 | 0.48 | 0.20-0.40 | 2/5 | NO (3 land too high) |
| broken | 5 | 0.00 | 0.30 | 0.132 | 0.08 | ≤ 0.20 | 3/5 | NO (2 land just over) |
| **overall** | 25 | 0.00 | 1.00 | 0.605 | 0.66 | monotonic | 17/25 | partial |

Monotonicity holds at the **median** level (0.96 > 0.84 > 0.66 > 0.48 > 0.08) and at the **mean** level (0.96 > 0.83 > 0.64 > 0.46 > 0.13). Band separation is preserved by ordering, even where individual samples drift into adjacent bands.

---

## Overall verdict

**STATUS: PARTIAL PASS**

What works:
- Perfect band is rock-solid (5/5, range 0.92-1.00). Five distinct stylistic voices (terse-formal / tutorial / FAQ / reference / narrative) all clear the 0.85 threshold, validating that the rubric rewards substance over style.
- Good band is rock-solid (5/5, range 0.82-0.84). The "single factual slip" design yields the intended drop of ~0.12-0.16 below perfect, and judges can be expected to spot each slip from the contract.
- Gold scores 0.98 — well clear of its own published bar (≥ 0.85), with headroom for inter-judge variance.
- Monotonicity holds at mean and median across all five bands.

What needs work (sample re-engineering, not rubric change):
- **`mediocre/{001,002,004}`** score 0.66-0.72 — inside the good band. The "one missing section" defect alone isn't enough to drop into 0.45-0.65; compound it with a factual error elsewhere (as 003 and 005 already do, which land correctly).
- **`poor/{001,003,004}`** score 0.48-0.52 — at the top of poor or into mediocre. Need to compound structural/factual collapse with clarity/consistency degradation. 002 and 005 land in band because they degrade on multiple axes simultaneously.
- **`broken/{002,003}`** score 0.24 / 0.30 — over the 0.20 ceiling. Two paths: tighten judge interpretation via the rubric anchors (`clarity` must be relative to documenting **this** tool; `structural_completeness` at 10-point must require non-trivial content), or rewrite 002/003 to additionally break clarity/structure (gardening guide should also be terse/garbled; SLOP sample should drop the perfect 8-section structure).

What does NOT need to change:
- The rubric itself is sound. The 5-criterion equal-weight scheme with the stated anchors produces correct rank ordering. The mediocre/poor/broken drift is in **sample construction**, not in rubric design.
- The gold gate (≥ 0.85) is appropriate — gold scored 0.98 leaves judge-disagreement headroom without ambiguity.
- All five `perfect/` and all five `good/` samples can ship as-is.

## Next actions

1. **Keep gold and all 10 `perfect/`+`good/` samples** — calibration-ready.
2. **Re-engineer 3 mediocre + 3 poor samples** to compound defects (missing section + factual error, or hallucination + format degradation). Target: each affected sample drops 0.10-0.20 to land squarely in band.
3. **Tighten two rubric anchors** in `rubric.yaml`:
   - `structural_completeness` 10-point anchor: explicit "non-trivial content per section" (close the SLOP loophole).
   - `clarity` description: explicit "clarity in documenting **this tool's contract**" (close the off-task-but-polished-prose loophole).
4. **Re-run this audit** after sample changes, target 25/25 IN_BAND verdicts before judge calibration.

---

## Relevant absolute paths

- `/Users/explosovebit/Work/pollmevals/evals/task-packs/doc_01_cli_readme/rubric.yaml`
- `/Users/explosovebit/Work/pollmevals/evals/task-packs/doc_01_cli_readme/prompt.md`
- `/Users/explosovebit/Work/pollmevals/evals/task-packs/doc_01_cli_readme/gold/README.gold.md`
- `/Users/explosovebit/Work/pollmevals/evals/task-packs/doc_01_cli_readme/calibration/perfect/sample-{001..005}.md`
- `/Users/explosovebit/Work/pollmevals/evals/task-packs/doc_01_cli_readme/calibration/good/sample-{001..005}.md`
- `/Users/explosovebit/Work/pollmevals/evals/task-packs/doc_01_cli_readme/calibration/mediocre/sample-{001..005}.md`
- `/Users/explosovebit/Work/pollmevals/evals/task-packs/doc_01_cli_readme/calibration/poor/sample-{001..005}.md`
- `/Users/explosovebit/Work/pollmevals/evals/task-packs/doc_01_cli_readme/calibration/broken/sample-{001..005}.md`
