# EVAL-WIRE — fe_01_multistep_form static evaluator verification

**Audited:** 2026-05-26  
**Auditor:** Tester agent (host-side static analysis)  
**Task pack:** `evals/task-packs/fe_01_multistep_form/`  
**Evaluators exercised:** TypeSafety (tsc 5.9.3), Lint (eslint 8.36.0 — skipped, see §Lint note), Complexity (lizard 1.22.1 via uv)  
**Files evaluated:** 26 total — 1 gold + 5 bands × 5 samples  
**Score formula:** `1.0 − min(1.0, findings_count / 10)` where `findings_count = tsc_errors + lint_findings + cc_over8_count`

---

## Tool availability

| Tool | Status | Version | Notes |
|---|---|---|---|
| `tsc` | Available | 5.9.3 (project-local via `node_modules/.bin/tsc`) | System `tsc` was 4.9.5 — too old for `Bundler` moduleResolution + `allowImportingTsExtensions`. Used gold pack's locally installed tsc throughout. |
| `eslint` | Partially available | 8.36.0 (global via pnpm) | **Skipped for all files.** No project eslint config exists for the `evals/` subtree, and `@typescript-eslint/parser` is not installed globally. Without the TS parser, eslint throws a fatal parse error on every `.tsx` file. Counting parse errors as lint findings would be misleading. Lint column = `N/A` for all 26 files. |
| `lizard` | Available | 1.22.1 (via `uv run python -c "import lizard"`) | Runs as Python API; no PATH dependency. Supports TSX. |

**tsc invocation (file mode — calibration samples have no tsconfig):**
```bash
/path/to/gold/node_modules/.bin/tsc --noEmit --strict --pretty false \
  --target ES2022 --module ESNext --moduleResolution Bundler \
  --lib ES2022,DOM,DOM.Iterable --jsx react-jsx \
  --esModuleInterop true --skipLibCheck true --isolatedModules \
  --noUncheckedIndexedAccess --noImplicitOverride \
  --typeRoots evals/task-packs/fe_01_multistep_form/gold/node_modules/@types \
  <file.tsx>
```
Flags mirror the gold `tsconfig.json` (react-jsx, strict, Bundler resolution) minus `types:vitest/globals` which is test-only.

**tsc invocation (gold — project mode):** same flags but via file mode pointing only at `solution.tsx` (excluding `tests.spec.tsx` which has a testing-library version mismatch unrelated to the solution quality).

---

## Per-file results

### Gold solution

| File | tsc errors | lint | CC>8 count | max CC | findings | score | gate (≥0.85) | verdict |
|---|---:|---|---:|---:|---:|---:|---|---|
| `gold/solution.tsx` | 0 | N/A | 1 | 17 | 1 | **0.90** | ≥0.85 | **PASS** |

**CC detail:** `validateField` CC=17 (regex validation + field-specific logic). Exceeds CC>8 threshold but is a single short function.

---

### Perfect band (expected avg ≥0.85)

| File | tsc errors | lint | CC>8 count | max CC | findings | score | verdict |
|---|---:|---|---:|---:|---:|---:|---|
| `calibration/perfect/sample-001.tsx` | 0 | N/A | 1 | 10 | 1 | 0.90 | in-band |
| `calibration/perfect/sample-002.tsx` | 0 | N/A | 2 | 19 | 2 | 0.80 | **below expected** |
| `calibration/perfect/sample-003.tsx` | 0 | N/A | 1 | 11 | 1 | 0.90 | in-band |
| `calibration/perfect/sample-004.tsx` | 0 | N/A | 0 |  8 | 0 | 1.00 | in-band |
| `calibration/perfect/sample-005.tsx` | 0 | N/A | 1 |  9 | 1 | 0.90 | in-band |

**Band avg: 0.900** (expected ≥0.85) — **PASS**  
**CC detail:** sample-002 has `reducer` CC=19 + anonymous CC=9 (likely a switch-based reducer); sample-003 anonymous CC=11.

---

### Good band (expected avg 0.70–0.85)

| File | tsc errors | lint | CC>8 count | max CC | findings | score | verdict |
|---|---:|---|---:|---:|---:|---:|---|
| `calibration/good/sample-001.tsx` | 0 | N/A | 1 | 9 | 1 | 0.90 | **above expected** |
| `calibration/good/sample-002.tsx` | 0 | N/A | 1 | 10 | 1 | 0.90 | **above expected** |
| `calibration/good/sample-003.tsx` | 0 | N/A | 1 | 9 | 1 | 0.90 | **above expected** |
| `calibration/good/sample-004.tsx` | 0 | N/A | 1 | 9 | 1 | 0.90 | **above expected** |
| `calibration/good/sample-005.tsx` | 0 | N/A | 1 | 9 | 1 | 0.90 | **above expected** |

**Band avg: 0.900** (expected 0.70–0.85) — **OUT OF BAND (above ceiling)**  
All 5 samples score identically at 0.90.

---

### Mediocre band (expected avg 0.45–0.65)

| File | tsc errors | lint | CC>8 count | max CC | findings | score | verdict |
|---|---:|---|---:|---:|---:|---:|---|
| `calibration/mediocre/sample-001.tsx` | 0 | N/A | 0 |  8 | 0 | 1.00 | **above expected** |
| `calibration/mediocre/sample-002.tsx` | 0 | N/A | 1 |  9 | 1 | 0.90 | **above expected** |
| `calibration/mediocre/sample-003.tsx` | 0 | N/A | 1 | 11 | 1 | 0.90 | **above expected** |
| `calibration/mediocre/sample-004.tsx` | 0 | N/A | 1 |  9 | 1 | 0.90 | **above expected** |
| `calibration/mediocre/sample-005.tsx` | 0 | N/A | 1 | 10 | 1 | 0.90 | **above expected** |

**Band avg: 0.920** (expected 0.45–0.65) — **OUT OF BAND (massively above ceiling)**

---

### Poor band (expected avg 0.20–0.40)

| File | tsc errors | lint | CC>8 count | max CC | findings | score | verdict |
|---|---:|---|---:|---:|---:|---:|---|
| `calibration/poor/sample-001.tsx` | 0 | N/A | 0 |  8 | 0 | 1.00 | **above expected** |
| `calibration/poor/sample-002.tsx` | 0 | N/A | 0 |  7 | 0 | 1.00 | **above expected** |
| `calibration/poor/sample-003.tsx` | 0 | N/A | 2 | 22 | 2 | 0.80 | **above expected** |
| `calibration/poor/sample-004.tsx` | 0 | N/A | 0 |  8 | 0 | 1.00 | **above expected** |
| `calibration/poor/sample-005.tsx` | 0 | N/A | 0 |  4 | 0 | 1.00 | **above expected** |

**Band avg: 0.960** (expected 0.20–0.40) — **OUT OF BAND (massively above ceiling)**  
**CC detail (sample-003):** `MultiStepForm` CC=22, `submit` CC=16 — monolithic component.

---

### Broken band (expected avg ≤0.20)

| File | tsc errors | lint | CC>8 count | max CC | findings | score | tsc error | verdict |
|---|---:|---|---:|---:|---:|---:|---|---|
| `calibration/broken/sample-001.tsx` | 1 | N/A | 0 | 2 | 1 | 0.90 | TS1005: `'}'` expected (line 43) | **above expected** |
| `calibration/broken/sample-002.tsx` | 1 | N/A | 0 | 1 | 1 | 0.90 | TS2322: `string` not assignable to `Element` (line 17) | **above expected** |
| `calibration/broken/sample-003.tsx` | 1 | N/A | 0 | 1 | 1 | 0.90 | TS2304: Cannot find name `useState` (line 18) | **above expected** |
| `calibration/broken/sample-004.tsx` | 0 | N/A | 0 | 2 | 0 | 1.00 | — | **above expected** |
| `calibration/broken/sample-005.tsx` | 0 | N/A | 0 | 2 | 0 | 1.00 | — | **above expected** |

**Band avg: 0.940** (expected ≤0.20) — **OUT OF BAND (massively above ceiling)**  
Note: only 3 of 5 broken files have tsc-detectable errors. Broken-004 and broken-005 are type-correct at tsc level (their defects are runtime/logical, not structural).

---

## Per-band summary

| Band | Expected avg | Actual avg | Min | Max | Status |
|---|---|---|---|---|---|
| perfect | ≥0.85 | **0.900** | 0.80 | 1.00 | PASS |
| good | 0.70–0.85 | **0.900** | 0.90 | 0.90 | FAIL — above ceiling |
| mediocre | 0.45–0.65 | **0.920** | 0.90 | 1.00 | FAIL — massively above ceiling |
| poor | 0.20–0.40 | **0.960** | 0.80 | 1.00 | FAIL — massively above ceiling |
| broken | ≤0.20 | **0.940** | 0.90 | 1.00 | FAIL — massively above ceiling |

---

## Gold solution score

`gold/solution.tsx` scored **0.90** (tsc errors: 0, lint: N/A, CC>8 functions: 1 — `validateField` CC=17).  
Gate requirement: ≥0.85. **PASS.**

---

## Overall verdict

**CONCERNS** — host-side static evaluators (tsc + lizard) are wired correctly and produce correct per-file scores, but they lack the discriminatory power to separate quality bands for this task.

### Root cause analysis

1. **Band separation failure.** Static evaluators measure *structural correctness* (type safety, syntax validity, cyclomatic complexity), not *functional correctness* or *accessibility*. The fe_01 task bands were authored to reflect runtime and UX quality differences (missing validation, no accessibility, wrong step logic) which are invisible to `tsc --strict` and `lizard`. A type-clean file with zero CC violations can still be a mediocre or broken implementation.

2. **Lint skipped.** `eslint` is on PATH but `@typescript-eslint/parser` is not installed, making it unable to parse `.tsx`. Even if the parser were available, eslint without a project config would only catch basic JS issues, not React-specific quality gaps.

3. **CC threshold too coarse.** The CC>8 criterion penalises high-CC functions by 0.1 per violating function (capped at 10). Most samples stay within 1–2 violations → score 0.80–0.90. No sample has 10+ violations, so the floor is never reached.

4. **Two broken files (004, 005) are type-safe.** Their defects are logical (wrong data flow, missing steps) — invisible to the static analysis layer.

### What is working correctly

- tsc correctly catches the 3 structural/type errors in broken-001, broken-002, broken-003
- lizard correctly identifies high-CC functions (poor-003, perfect-002, gold)
- Gold solution passes its ≥0.85 gate
- Tool wiring is functional end-to-end (tsc 5.9.3, lizard 1.22.1, uv environment)

### Required actions before calibration state promotion

| Priority | Action | Owner |
|---|---|---|
| **BLOCKER** | Add dynamic evaluators (vitest correctness + accessibility via axe-core) to produce band-discriminating scores. Static evaluators alone cannot separate mediocre/poor/broken from perfect/good. | coder |
| **BLOCKER** | Install `@typescript-eslint/parser` + a project eslint config for `evals/` so lint evaluator runs on tsx. Without it, lint is permanently skipped. | coder |
| **CONCERN** | Consider whether `validateField` CC=17 in the gold solution should be refactored (extract per-field validators) to avoid the gold solution self-penalising the type_safety component. | coder (optional) |
| **INFO** | broken-004 and broken-005 have no static-detectable errors. Verify their intended defects are documented in `calibration.yaml` and are expected to fail only via dynamic evaluation. | content author |

---

## Appendix: raw command log

```
# tsc (gold — file mode, flags matching gold tsconfig)
.../gold/node_modules/.bin/tsc --noEmit --strict --pretty false \
  --target ES2022 --module ESNext --moduleResolution Bundler \
  --lib ES2022,DOM,DOM.Iterable --jsx react-jsx \
  --esModuleInterop true --skipLibCheck true --isolatedModules \
  --noUncheckedIndexedAccess --noImplicitOverride \
  --typeRoots .../gold/node_modules/@types \
  gold/solution.tsx
# exit code: 0

# eslint (all files — representative)
eslint --format json calibration/broken/sample-001.tsx
# result: fatal parse error (no @typescript-eslint/parser) — SKIPPED

# lizard (via uv python API — representative)
uv run python -c "import lizard; fi = lizard.analyze_file('gold/solution.tsx'); ..."
# lizard 1.22.1
```
