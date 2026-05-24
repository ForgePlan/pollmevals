---
depth: standard
id: EVID-009
kind: evidence
last_modified_at: 2026-05-24T07:27:17.782425+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
status: active
title: 'Wave 1 (sprint phase-2A): PRD-001 FR-001+FR-002 resolved via validators rewrite'
---

# EVID-009: Wave 1 — PRD-001 FR-001+FR-002 resolved via validators rewrite

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "how to satisfy FR-001 + FR-002?")

- **H1**: Existing `infra/scripts/validate-task-specs.py` works as-is; FR-001 already covered, just no FR-002 yet — minimal addition needed (single new script, no rewrite).
- **H2**: Existing script broken (orphan import on a non-existent module `pollmevals_eval_core.registry`) → full rewrite needed, plus a NEW separate script for FR-002 (stack validation).
- **H3**: Both validators should be merged into a single CLI tool with `--task` / `--stack` modes — cleaner UX, less duplication.

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 | `python infra/scripts/validate-task-specs.py` exits 0 against existing task packs | Run the script as-is, observe exit code |
| H2 | `python infra/scripts/validate-task-specs.py` raises `ImportError` (orphan import) → broken in runtime → rewrite required | Run the script; observe traceback containing `ModuleNotFoundError: pollmevals_eval_core` |
| H3 | Two separate scripts have ~80% duplicated logic; single tool with mode flag would be DRYer | Count lines of duplication; compare maintainability |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 | `cat infra/scripts/validate-task-specs.py \| head -10` shows `from pollmevals_eval_core.registry import load_task_specs`; running the script would `ImportError` (this module never existed; cloc reports 1 Python file 12 LOC across whole project before this sprint) | Module absent — script broken at import time | **H1 REFUTED** |
| Y2 | After rewrite (pure stdlib + jsonschema): `uv run --with pyyaml --with jsonschema python infra/scripts/validate-task-specs.py` → exit 0, prints `3/3 task specs valid` (be_01_jwt_auth, doc_01_cli_readme, fe_01_multistep_form) | Both scripts work, both exit 0, both validate cleanly | **H2 SUPPORTED** |
| Y3 | Two scripts have ~50 lines of shared scaffolding (path resolution, YAML loading, jsonschema invocation) but each has distinct subject (task vs stack schema). Sharing would create a meta-validator harder to read for a single-task purpose. Cost > benefit. | Tested by agent in implementation; chose 2 separate scripts | **H3 REJECTED** (valid but not chosen — separation preserves clarity per CLAUDE.md "no premature abstraction") |

**Surviving hypothesis**: H2 — full rewrite of task validator + new stack validator. Matches shipped implementation.

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| Orphan import broke FR-001 coverage pre-sprint | 8 | 9 | 9 | 26/27 | F: explicit module name + line number citation. G: precise (file:line of the import statement). R: confirmed by `cloc` report (architect EVID-007) + direct inspection. |
| Rewritten task validator: 3/3 task specs PASS | 8 | 9 | 8 | 25/27 | F: explicit exit code + count. G: 3/3 enumerated (be_01, fe_01, doc_01). R: `pytest`-equivalent reproducible CLI invocation. Drops 1 on R because not yet in CI gate. |
| New stack validator: 3/3 stack specs PASS | 8 | 9 | 8 | 25/27 | Same as above for stacks (raw-llm, claude-code-basic, forgeplan-framework). |
| mypy --strict 0 issues on both scripts | 9 | 8 | 9 | 26/27 | F: mypy with `--strict` is the most formal Python type check. G: explicit "0 issues" count. R: deterministic tool output. |
| No schema mismatches in existing YAML data | 7 | 7 | 6 | 20/27 | F: stated by agent without showing every field. G: aggregate "0 mismatches" claim. R: single test run; would need re-run after any schema bump to revalidate. |

**Decision strength**: average sum = 24.4/27 (90%). All ≥ 12. No follow-up evidence needed for the core claim; "no schema mismatches" benefits from re-run in CI after every schema bump.

## Wave summary

- **Sprint**: phase-2A (`apps/eval-core-py/` foundation), **Wave**: 1 of 5
- **Worker**: `validators-fix` (agents-core:coder)
- **Files** (~365 LOC): MODIFY `infra/scripts/validate-task-specs.py` (~180 LOC rewrite), NEW `infra/scripts/validate-stack-specs.py` (~185 LOC)
- **Pipeline gates**: mypy --strict ✓ (0 issues), exit 0 on 3/3 task + 3/3 stack specs, both scripts importable as modules

## Acceptance criteria validation

- ✓ **PRD-001 FR-001**: validate task specs against JSON Schema via single CLI command
- ✓ **PRD-001 FR-002**: validate stack specs against contract
- ✓ **Architect finding #9 (LOW)**: orphan import resolved
- ✓ **Architect finding #7 (MEDIUM)**: FR-002 now has implementation locus
- ✓ GitHub issues #1 + #2 directly closed by this work

## Conclusions

- **Surviving hypothesis**: H2 (rewrite + separate stack validator)
- **Decision strength**: 90%
- **Follow-up evidence needed**: add `pyyaml`+`jsonschema` to a root infra-requirements or pyproject extras (so `moon run :lint` doesn't need `--with` flags). Currently a friction point but not a correctness gap.

## Related Artifacts

- PRD-001 (informs — auto-linked)
- RFC-001 impl task 14 (covered)
- GitHub issues #1, #2 (close-eligible after merge)
- EVID-007 (architect finding #9 source — closes the loop)
- NOTE-002 (Evidence Quality Standard — this is a retrofit)


