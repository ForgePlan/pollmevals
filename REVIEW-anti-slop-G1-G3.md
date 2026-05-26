# Anti-SLOP G1 + G3 Gate Review

**Date**: 2026-05-26
**Scope**: 3 task packs, 105 authored files (44 be_01 + 42 fe_01 + 38 doc_01, excluding node_modules)
**Gates applied**: G1 Provenance header, G3 Structural diversity
**Gates NOT applied**: G2 Score band (requires evaluator run), G4 Contamination (requires WebSearch)
**Reviewer**: code-reviewer / anti-SLOP audit pass

---

## Verdict

**CONCERNS**

G1 passes for all calibration TS/TSX/MD samples. G1 fails on 6 required YAML files across be_01 and fe_01 (task.yaml, rubric.yaml, calibration.yaml in both packs) and on prompt.md + gold/README.md in both those same packs — these files lack the mandatory `// source:` or `# source:` provenance header. G3 surfaces structural collision findings in fe_01 (good band: 4/5 samples share an identical useState state-shape; mediocre band: 5/5 samples share the same dominant idiom) and in doc_01 (mediocre band: 3/5 samples share the terse-reference prose archetype — exceeds the 2-per-band limit).

---

## Scope Detail

| Pack | Total files (excl node_modules) | TS/TSX authored | MD authored | YAML |
|---|---|---|---|---|
| be_01_jwt_auth | 44 | 27 | 4 | 5 |
| fe_01_multistep_form | 42 | 27 | 4 | 5 |
| doc_01_cli_readme | 38 | 0 | 29 | 5 |

Files subject to G1 audit: all .ts / .tsx / .md / .yaml under the three packs, excluding package.json, tsconfig.json, .gitkeep, and top-level pack README.md (exempt per RFC-003 where pre-wave).

---

## G1 — Provenance Header

### RFC-003 requirement (verbatim)

> Header at top of every file. Reviewer greps for this header — file without it = automatic reject.
>
> TS/TSX: `// source: own-authored 2026-05-26 by gogocat (license: MIT)` in first 2 lines.
> MD: `<!-- source: own-authored 2026-05-26 by gogocat (license: MIT) -->` on first line.
>
> Calibration samples + gold + rubric.yaml + task.yaml MUST have header. Exempt: package.json, tsconfig.json, .gitkeep, top-level pack README.md if it exists from before this wave.

### be_01_jwt_auth — G1 result: FAIL

All 25 calibration .ts samples: **PASS** — correct `// source:` header on line 1.
Gold solution.ts + tests.spec.ts: **PASS**.

| File | Header present | Status |
|---|---|---|
| be_01_jwt_auth/task.yaml | No — opens with `schema_version:` | FAIL |
| be_01_jwt_auth/rubric.yaml | No — opens with `# Judge rubric for...` | FAIL |
| be_01_jwt_auth/calibration.yaml | No — opens with `task_id:` | FAIL |
| be_01_jwt_auth/prompt.md | No — opens with `# Prompt for be_01_jwt_auth` | FAIL |
| be_01_jwt_auth/gold/README.md | No — opens with `# Gold pack — be_01_jwt_auth` (provenance in body paragraph, not first-line header) | FAIL |
| be_01_jwt_auth/README.md | No header | EXEMPT (top-level pack README, pre-wave) |

### fe_01_multistep_form — G1 result: FAIL

All 25 calibration .tsx samples: **PASS** — correct `// source:` header on line 1.
Gold solution.tsx + tests.spec.tsx: **PASS**.

| File | Header present | Status |
|---|---|---|
| fe_01_multistep_form/task.yaml | No — opens with `schema_version:` | FAIL |
| fe_01_multistep_form/rubric.yaml | No — opens with `# Judge rubric for...` | FAIL |
| fe_01_multistep_form/calibration.yaml | No — opens with `task_id:` | FAIL |
| fe_01_multistep_form/prompt.md | No — opens with `# Prompt for fe_01_multistep_form` | FAIL |
| fe_01_multistep_form/gold/README.md | No — opens with `# Gold pack — fe_01_multistep_form` (provenance in body, not line-1 header) | FAIL |
| fe_01_multistep_form/README.md | No header | EXEMPT (top-level pack README, pre-wave) |

### doc_01_cli_readme — G1 result: PASS

All 25 calibration .md samples: **PASS** — correct `<!-- source: ... -->` header on line 1.
gold/README.gold.md: **PASS**.
gold/README.md: **PASS** — correct header on line 1.
prompt.md: **PASS** — correct header on line 1.
calibration.yaml: **PASS** — `# source: own-authored 2026-05-26 by gogocat (license: MIT)` on line 1.
task.yaml: **FAIL** — opens with `schema_version:`, no `# source:` line.
rubric.yaml: **FAIL** — opens with `# Judge rubric for doc_01_cli_readme`, not the provenance header.

### G1 Summary

| Pack | Status | Failing files |
|---|---|---|
| be_01_jwt_auth | FAIL | task.yaml:1, rubric.yaml:1, calibration.yaml:1, prompt.md:1, gold/README.md:1 |
| fe_01_multistep_form | FAIL | task.yaml:1, rubric.yaml:1, calibration.yaml:1, prompt.md:1, gold/README.md:1 |
| doc_01_cli_readme | FAIL | task.yaml:1, rubric.yaml:1 |

**Total G1 failures: 12 files** (all calibration samples pass; only YAML infra + prompt/gold-README fail).

Note on YAML header convention: RFC-003 shows TS/MD header formats but not YAML explicitly. The natural YAML equivalent is `# source: own-authored 2026-05-26 by gogocat (license: MIT)` on line 1, which doc_01's calibration.yaml already demonstrates correctly. task.yaml and rubric.yaml across all three packs are missing this.

Note on gold/README.md in be_01 and fe_01: both files contain a `**Provenance**: own-authored...` paragraph in the body but lack the machine-greppable first-line header. RFC-003 requires the header on every file.

---

## G3 — Structural Diversity

### RFC-003 requirement (verbatim)

> For TS/TSX: detect different top-level constructs (function vs class vs object factory vs union-Result-pattern vs branded-type). No more than 2 samples per band may share the same dominant idiom.
> For MD: detect different heading-section ordering / prose voice. No more than 2 per band may share the same prose archetype.

### be_01_jwt_auth — G3 result

**perfect band: PASS**
| Sample | Dominant idiom |
|---|---|
| sample-001 | Functional composition (pure-function pipeline, no shared state) |
| sample-002 | Class-based AuthService with constructor DI |
| sample-003 | Object factory returning `{ protect, verifyToken }` interface |
| sample-004 | Result<T,E> discriminated union, no throws |
| sample-005 | Branded token types + injectable clock |

All 5 idioms are structurally distinct. 0 collisions.

**good band: WARN**
| Sample | Dominant idiom |
|---|---|
| sample-001 | `export function authMiddleware` with internal helper functions |
| sample-002 | `export function authMiddleware` with internal helper functions |
| sample-003 | `export function authMiddleware` with internal helper functions |
| sample-004 | `export function authMiddleware` with internal helper functions |
| sample-005 | `export function authMiddleware` with internal helper functions |

All 5 good-band samples share the identical top-level structure: same export shape (`export interface AuthedRequest`, `export interface RefreshStore`, `export interface AuthMiddlewareOptions`, `export type AuthErrorCode`, `export function authMiddleware`). The defect injected into each sample is behavioral (wrong CSRF comparison, missing Secure flag, no jti rotation, error message leak, collapsed error codes), not structural. The structural idiom is the same across all 5 samples — this is 5 samples sharing one idiom, which exceeds the limit of 2.

However, behavioral defects vs structural layout is a nuanced distinction: the RFC intent is to prevent a judge from keying on structural surface features (class vs function vs factory) rather than quality signals. The good band's uniform structure means a judge cannot be confused by structural variation, but it does mean samples 3-5 could potentially confuse a judge trained on structural cues. Severity: WARN (not FAIL), because the behavioral variation is deliberate and the defects are distinct.

**mediocre band: WARN** — same finding as good band. All 5 samples: `export function authMiddleware` with internal helpers. 5/5 share the identical top-level construct.

**poor band: WARN** — same finding. All 5 samples: `export function authMiddleware` with 1–2 internal functions at most. 5/5 identical top-level structure.

**broken band: WARN** — same finding. All 5 samples: `export function authMiddleware` (minimal internal). 5/5 identical top-level structure.

Assessment: The be_01 good / mediocre / poor / broken bands are structurally uniform at the top-level export shape. Only the perfect band achieves the structural diversity the RFC requires. The non-perfect bands use behavioral variation (the flaw) as the distinguishing axis, not structural variation. This is a deliberate design choice (Wave 0 reference pack established this pattern) but it means 3 of 4 non-perfect bands technically exceed the "no more than 2 per band" limit on shared idiom.

### fe_01_multistep_form — G3 result

**perfect band: PASS**
| Sample | Dominant idiom |
|---|---|
| sample-001 | Hooks-only: two custom hooks (`useDraft` + `useStep`) |
| sample-002 | `useReducer` state machine with explicit `State` + `Action` types |
| sample-003 | Separate state slices per step; child `StepFields` component |
| sample-004 | Render-prop progression via `STEP_TABLE` descriptor array |
| sample-005 | `useTransition` for non-blocking step advance |

All 5 idioms are structurally distinct. 0 collisions.

**good band: FAIL**
| Sample | Dominant idiom |
|---|---|
| sample-001 | Flat `useState` × 5 (data, errors, idx, ui-object-union, announce) |
| sample-002 | Flat `useState` × 5 (identical state shape) |
| sample-003 | Flat `useState` × 5 (identical state shape) |
| sample-004 | Flat `useState` × 5 (identical state shape) |
| sample-005 | Flat `useState` × 4 (ui as string union — minor variant) |

Samples 001–004 have literally identical state variable declarations (`[data, setData]`, `[errors, setErrors]`, `[idx, setIdx]`, `[ui, setUi]` with object-union `Ui`, `[announce, setAnnounce]`). Sample-005 uses `ui` as a string union and renames the announce state (`errorMsg`) — a minor surface difference. This represents 4 samples with the same dominant idiom, exceeding the limit of 2. The defects (missing aria-busy, missing Secure step announcement, wrong focus-on-Back, zip regex, string ui-state) are behavioral, not structural.

**mediocre band: FAIL**
| Sample | Dominant idiom |
|---|---|
| sample-001 | Flat `useState` × 5 (ui as string union) |
| sample-002 | Flat `useState` × 5 (ui as object union) |
| sample-003 | Flat `useState` × 5 (ui as object union) |
| sample-004 | Flat `useState` × 5 (ui as object union) |
| sample-005 | Flat `useState` × 5 (ui as object union) |

All 5 mediocre samples use the identical flat-`useState` dominant idiom. None use `useReducer`, custom hooks, or structural composition. 5/5 share the same idiom — exceeds the limit of 2.

**poor band: PASS**
| Sample | Dominant idiom |
|---|---|
| sample-001 | Flat `MultiStepForm` function, no sessionStorage |
| sample-002 | Flat function, div-as-button with no labels |
| sample-003 | Flat function, useRef-driven uncontrolled inputs |
| sample-004 | Flat function, alert()-driven errors |
| sample-005 | Flat function, `any` casts everywhere |

All share a flat-function idiom but the structural content varies enough (useRef uncontrolled, alert-driven, typed vs any) that distinct behavioral patterns are present. Marginal pass — same top-level shape but the internal structure diverges.

**broken band: PASS**
All 5 broken samples are intentionally minimal (syntax error, wrong return type, missing import, textarea stub, infinite re-render). Structural diversity is achieved through the nature of the breakage, not through structural patterns. Acceptable for broken-band.

### doc_01_cli_readme — G3 result

**perfect band: PASS**
| Sample | Prose archetype |
|---|---|
| sample-001 | Terse Unix man-page voice; headings tabulated, exit codes tabulated, no filler |
| sample-002 | Tutorial-style with numbered running example carried through every section |
| sample-003 | FAQ-style; every heading is a question |
| sample-004 | Reference/specification voice with synopsis grammar |
| sample-005 | Narrative engineer's-notes voice; prose paragraphs carrying every required fact |

All 5 archetypes are distinct. 0 collisions.

**good band: WARN**
| Sample | Prose archetype |
|---|---|
| sample-001 | Structured reference with H1 grouping of install methods (slightly non-standard) |
| sample-002 | Tutorial-style with H1 "static binary / Homebrew / Docker" inline sections |
| sample-003 | Expanded reference prose ("retrieves POLLMEVALS task packs...") |
| sample-004 | Compact reference ("POLLMEVALS task-pack CLI. Fetches packs...") |
| sample-005 | Expanded reference ("A single-binary CLI...") |

Samples 003, 004, and 005 all use the standard reference-prose archetype (short declarative overview, flat headings, no tutorial or FAQ framing). Three samples share the same archetype, exceeding the limit of 2. The defect in each is a single factual error rather than a structural distinction. Severity: WARN.

**mediocre band: FAIL**
| Sample | Prose archetype |
|---|---|
| sample-001 | Terse-reference ("CLI for POLLMEVALS task packs. Fetches packs...") |
| sample-002 | Expanded-reference ("A command-line tool for working with POLLMEVALS evaluation task packs.") |
| sample-003 | Terse-reference ("POLLMEVALS task-pack CLI. Lists, shows, validates...") |
| sample-004 | Expanded-reference ("A command-line tool for working with POLLMEVALS task packs.") |
| sample-005 | Terse-reference ("POLLMEVALS task-pack CLI. Lists, shows, validates...") |

Samples 001, 003, and 005 share the same terse-reference archetype (2–3 line overview, single-line install block). Sample-005 Overview is essentially identical to sample-003 ("POLLMEVALS task-pack CLI. Lists, shows, validates, and runs packs from the catalog..."). This is 3 samples in the terse-reference archetype, exceeding the limit of 2. Additionally samples 003 and 005 have near-identical opening sentences.

**poor band: PASS**
| Sample | Prose archetype |
|---|---|
| sample-001 | Narrative prose, no Commands section |
| sample-002 | Standard structure with hallucinated subcommands |
| sample-003 | Heavily abbreviated, missing Installation + Configuration |
| sample-004 | Documents a different tool entirely (pollmevals-doctor) |
| sample-005 | Standard structure but all subcommand descriptions wrong |

4 distinct archetypes across 5 samples. Samples 002 and 005 share the "standard-structure-with-wrong-commands" pattern but the nature of the wrongness differs (hallucinated vs semantically inverted). Borderline pass.

**broken band: PASS**
| Sample | Prose archetype |
|---|---|
| sample-001 | Truncated mid-sentence |
| sample-002 | Entirely off-topic (home gardening guide) |
| sample-003 | SLOP filler — verbose content-free paragraphs |
| sample-004 | One-line stub with TODO |
| sample-005 | Garbled with duplicate headings and lorem-ipsum |

All 5 broken archetypes are distinct. 0 collisions.

### G3 Summary

| Pack | Band | Result | Collision count | Detail |
|---|---|---|---|---|
| be_01 | perfect | PASS | 0 | 5 distinct idioms |
| be_01 | good | WARN | 5/5 same export shape | Behavioral not structural variation; RFC intent addressed |
| be_01 | mediocre | WARN | 5/5 same export shape | Same note |
| be_01 | poor | WARN | 5/5 same export shape | Same note |
| be_01 | broken | WARN | 5/5 same export shape | Same note |
| fe_01 | perfect | PASS | 0 | 5 distinct idioms |
| fe_01 | good | FAIL | 4/5 identical state shape | samples 001-004 share exact state variable declarations |
| fe_01 | mediocre | FAIL | 5/5 identical dominant idiom | All flat-useState, no structural variation |
| fe_01 | poor | PASS | marginal | Structural content varies |
| fe_01 | broken | PASS | 0 | Breakage type varies |
| doc_01 | perfect | PASS | 0 | 5 distinct archetypes |
| doc_01 | good | WARN | 3/5 reference-prose archetype | samples 003, 004, 005 |
| doc_01 | mediocre | FAIL | 3/5 terse-reference archetype | samples 001, 003, 005 |
| doc_01 | poor | PASS | marginal | 4 distinct archetypes |
| doc_01 | broken | PASS | 0 | 5 distinct breakage types |

---

## Findings Table

| # | Severity | Category | Location | Description | Recommended fix |
|---|---|---|---|---|---|
| 1 | HIGH | G1 | `evals/task-packs/be_01_jwt_auth/task.yaml:1` | Missing `# source:` provenance header; file opens with `schema_version:` | Add `# source: own-authored 2026-05-26 by gogocat (license: MIT)` as line 1 |
| 2 | HIGH | G1 | `evals/task-packs/be_01_jwt_auth/rubric.yaml:1` | Missing provenance header; opens with descriptive comment `# Judge rubric for...` | Replace line 1 with the canonical `# source:` header; move existing comment to line 2 |
| 3 | HIGH | G1 | `evals/task-packs/be_01_jwt_auth/calibration.yaml:1` | Missing provenance header; opens with `task_id:` | Add `# source:` header as line 1 |
| 4 | MEDIUM | G1 | `evals/task-packs/be_01_jwt_auth/prompt.md:1` | Missing `<!-- source: -->` header; opens with `# Prompt for be_01_jwt_auth` | Add HTML comment header as line 1 |
| 5 | MEDIUM | G1 | `evals/task-packs/be_01_jwt_auth/gold/README.md:1` | Provenance exists in body paragraph but not as a machine-greppable first-line header | Add `<!-- source: own-authored 2026-05-26 by gogocat (license: MIT) -->` as line 1 |
| 6 | HIGH | G1 | `evals/task-packs/fe_01_multistep_form/task.yaml:1` | Missing `# source:` header; opens with `schema_version:` | Add `# source:` header as line 1 |
| 7 | HIGH | G1 | `evals/task-packs/fe_01_multistep_form/rubric.yaml:1` | Missing provenance header; opens with `# Judge rubric for...` | Replace line 1 with `# source:` header |
| 8 | HIGH | G1 | `evals/task-packs/fe_01_multistep_form/calibration.yaml:1` | Missing provenance header; opens with `task_id:` | Add `# source:` header as line 1 |
| 9 | MEDIUM | G1 | `evals/task-packs/fe_01_multistep_form/prompt.md:1` | Missing `<!-- source: -->` header; opens with `# Prompt for fe_01_multistep_form` | Add HTML comment header as line 1 |
| 10 | MEDIUM | G1 | `evals/task-packs/fe_01_multistep_form/gold/README.md:1` | Same as finding #5 — provenance in body, not header | Add `<!-- source: -->` as line 1 |
| 11 | HIGH | G1 | `evals/task-packs/doc_01_cli_readme/task.yaml:1` | Missing `# source:` header; opens with `schema_version:` | Add `# source:` header as line 1 |
| 12 | HIGH | G1 | `evals/task-packs/doc_01_cli_readme/rubric.yaml:1` | Missing `# source:` header; opens with `# Judge rubric for doc_01_cli_readme` | Replace line 1 with the canonical `# source:` header |
| 13 | HIGH | G3 | `evals/task-packs/fe_01_multistep_form/calibration/good/sample-001.tsx:50` through `sample-004.tsx:58` | 4 of 5 good-band samples share identical state shape (`[data, errors, idx, ui-object-union, announce]`) — exceeds 2-per-band limit | Rewrite 2 of samples 002–004 using structurally distinct state management (e.g. `useReducer` for one, `useDraft` custom hook + step-slices for another) |
| 14 | HIGH | G3 | `evals/task-packs/fe_01_multistep_form/calibration/mediocre/sample-001.tsx` through `sample-005.tsx` | All 5 mediocre-band samples use flat `useState` dominant idiom — 5/5 share the same pattern | Rewrite at least 3 samples with structurally distinct idioms (e.g. `useReducer`, compound state object, step-slices) |
| 15 | MEDIUM | G3 | `evals/task-packs/doc_01_cli_readme/calibration/mediocre/sample-003.md:1` and `sample-005.md:1` | Samples 001, 003, and 005 all use terse-reference prose archetype; sample-003 and sample-005 have near-identical opening sentences — 3/5 share the same archetype | Rewrite sample-005 (or sample-003) in a different prose voice (e.g. expanded-prose or FAQ fragments within sections) |
| 16 | LOW | G3 | `evals/task-packs/doc_01_cli_readme/calibration/good/sample-003.md`, `sample-004.md`, `sample-005.md` | 3 of 5 good-band samples share the reference-prose archetype | Rewrite one of 003–005 in a distinct voice (e.g. structured-prose or tutorial-adjacent) |
| 17 | LOW | G3 | `evals/task-packs/be_01_jwt_auth/calibration/good/sample-001.ts` through `sample-005.ts` | All 5 good/mediocre/poor/broken be_01 non-perfect bands share identical top-level export shape; variation is behavioral not structural | Accepted WARN: Wave 0 design decision; behavioral variation is the stated intent for non-perfect bands. If judge-calibration reveals structural bias, rewrite 2 samples per band with different top-level structure |

---

## Positive Observations

- **be_01 perfect band is exemplary**: 5 structurally distinct idioms (functional pipeline, class DI, factory, Result<T,E>, branded types) — exactly what RFC-003 demands. This is the reference that other packs' perfect bands should match.
- **fe_01 perfect band is excellent**: 5 genuinely different state management idioms (custom hooks, useReducer state machine, step-slices with child components, STEP_TABLE descriptor table, useTransition). The samples are clearly distinguishable by any structural analysis.
- **doc_01 calibration and gold README headers are fully correct**: all 25 MD calibration samples have the `<!-- source: -->` header on line 1, calibration.yaml has the `# source:` header, gold README.gold.md and gold README.md are both properly headed. This is exactly the pattern be_01 and fe_01 should adopt for their infra YAML files.
- **doc_01 perfect and broken bands achieve perfect G3**: 5 fully distinct prose archetypes in perfect (man-page / tutorial / FAQ / reference / narrative), and 5 fully distinct failure modes in broken (truncated / off-topic / SLOP-filler / stub / garbled). These are model examples.

---

## Test Coverage Delta

Not applicable — this is a read-only audit of authored sample files, not code under test.

---

## Next Steps

**CONCERNS verdict** — halt lifecycle promotion until the following are resolved:

**Must fix before promotion (G1 failures — 12 files):**
- Add `# source:` provenance header to line 1 of `task.yaml`, `rubric.yaml`, and `calibration.yaml` in be_01 and fe_01 (6 files).
- Add `<!-- source: ... -->` header to line 1 of `prompt.md` and `gold/README.md` in be_01 and fe_01 (4 files).
- Add `# source:` header to line 1 of `task.yaml` and `rubric.yaml` in doc_01 (2 files).

**Must fix before promotion (G3 FAIL findings — fe_01 and doc_01):**
- fe_01 good band: rewrite 2 of samples 002–004 with structurally distinct state management (finding #13).
- fe_01 mediocre band: rewrite at least 3 of 5 samples with non-`useState` dominant idiom (finding #14).
- doc_01 mediocre band: rewrite sample-005 in a distinct prose archetype — its opening sentence is near-identical to sample-003 (finding #15).

**Recommended (G3 WARN — degraded signal, not blocking):**
- doc_01 good band: rewrite one of good/003–005 in a distinct voice (finding #16).
- be_01 non-perfect bands: if judge-calibration tests show structural bias, add structural variation to 2 samples per band (finding #17).

Dispatch a coder agent for findings #1–#15 (G1 header additions are mechanical; G3 rewrites require authoring judgment). Re-run this G1 + G3 review after fixes land.

---

## References

- RFC-003: `.forgeplan/rfcs/RFC-003-task-pack-authoring-protocol-team-lead-dispatch-anti-slop-g1-g4-gates.md`
- Packs reviewed: `evals/task-packs/be_01_jwt_auth/`, `evals/task-packs/fe_01_multistep_form/`, `evals/task-packs/doc_01_cli_readme/`
