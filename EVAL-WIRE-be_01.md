# EVAL-WIRE-be_01 — Static Evaluator Verification Report

**Task pack**: `be_01_jwt_auth`  
**Date**: 2026-05-26  
**Agent**: claude-code/claude-sonnet-4-6/tester-task-23  
**Overall verdict**: **BLOCKER** (see §4 for root cause)

---

## §1 Tool availability

| Evaluator | Tool | Status | Version |
|---|---|---|---|
| TypeSafetyEvaluator | `tsc` | AVAILABLE (local) | TypeScript 5.9.3 (gold pack node_modules) |
| LintEvaluator | `eslint` | **SKIPPED** | eslint v8.36.0 (global) — `@typescript-eslint/parser` not installed anywhere in workspace; cannot parse `.ts` files |
| ComplexityEvaluator | `lizard` | AVAILABLE | lizard 1.22.1 (via `uv run`) |
| SecretScanEvaluator | `gitleaks` | **SKIPPED** | gitleaks not on PATH; not in brew |

**Active evaluators for scoring**: `tsc` + `lizard` only (2 of 4).  
**Score formula per evaluator**: `1.0 - min(1.0, errors / 10)` (tsc, lint); `1.0 if max_cc≤8 else max(0.0, 1.0-(max_cc-8)/10)` (lizard).  
**Composite score**: average of applicable evaluators = `(tsc_score + lizard_score) / 2`.

### tsc invocation detail

The gold pack `tsconfig.json` uses `moduleResolution: Bundler` and `allowImportingTsExtensions: true` — both TypeScript 5.x-only features. The global `tsc` is v4.9.5 and rejected the tsconfig. The gold pack's devDependency `typescript: 5.9.3` was installed via `npm install --ignore-scripts` into `evals/task-packs/be_01_jwt_auth/gold/node_modules/`.

Commands run:

```bash
# Gold (tsconfig mode — honours noUncheckedIndexedAccess and all 5.x options)
cd evals/task-packs/be_01_jwt_auth/gold
./node_modules/.bin/tsc -p tsconfig.json --noEmit --pretty false
# EXIT=2

# Calibration (file mode — esModuleInterop + skipLibCheck to neutralise import-style false positives)
./node_modules/.bin/tsc --noEmit --strict --pretty false \
  --target ES2022 --lib ES2022 \
  --moduleResolution node \
  --esModuleInterop --skipLibCheck \
  --typeRoots ./node_modules/@types \
  <file>
```

**Note on calibration tsc flags**: without `--esModuleInterop`, all non-broken samples accumulate 1 uniform `TS1192: Module 'jsonwebtoken' has no default export` error (caused by `import jwt from 'jsonwebtoken'` against CJS types). This is a false positive from import style, not a functional type error. Adding `--esModuleInterop` (which the gold tsconfig enables) eliminates it. The reported tsc errors below use the `esModuleInterop` baseline.

---

## §2 Per-file table

### Gold solution

| File | TSC errors | TSC score | Max CC | Lizard score | Avg score | Expected | Verdict |
|---|---|---|---|---|---|---|---|
| `gold/solution.ts` | 2 | 0.8000 | 15 | 0.3000 | **0.5500** | ≥0.85 | **OUT_OF_BAND** |

**tsc errors (gold, via tsconfig.json):**
- `solution.ts(55,14): error TS2322: Type 'string | undefined' is not assignable to type 'string | null'` — caused by `noUncheckedIndexedAccess: true` treating regex match group `m[1]` as `string | undefined` instead of `string`.  
- `tests.spec.ts(100,33): error TS2322: Type 'number' is not assignable to type 'string | (() => string) | undefined'` — in the test file, not the solution.

**lizard CC breakdown (gold solution.ts):**
- `handler`: CC=15, `randomJti`: CC=15, `narrowAccessClaims`: CC=8, `narrowRefreshClaims`: CC=7, `authMiddleware`: CC=4, `extractBearer`: CC=3, `isStateChanging`: CC=3

### Calibration samples

| File | TSC errors | TSC score | Max CC | CC score | Avg score | Band expected | Verdict |
|---|---|---|---|---|---|---|---|
| `perfect/sample-001` | 0 | 1.0000 | 10 | 0.8000 | **0.9000** | 0.85–1.00 | IN_BAND |
| `perfect/sample-002` | 0 | 1.0000 | 21 | 0.0000 | **0.5000** | 0.85–1.00 | OUT_OF_BAND |
| `perfect/sample-003` | 0 | 1.0000 | 11 | 0.7000 | **0.8500** | 0.85–1.00 | IN_BAND |
| `perfect/sample-004` | 0 | 1.0000 | 11 | 0.7000 | **0.8500** | 0.85–1.00 | IN_BAND |
| `perfect/sample-005` | 0 | 1.0000 | 14 | 0.4000 | **0.7000** | 0.85–1.00 | OUT_OF_BAND |
| `good/sample-001` | 0 | 1.0000 | 14 | 0.4000 | **0.7000** | 0.70–0.85 | IN_BAND |
| `good/sample-002` | 0 | 1.0000 | 23 | 0.0000 | **0.5000** | 0.70–0.85 | OUT_OF_BAND |
| `good/sample-003` | 0 | 1.0000 | 15 | 0.3000 | **0.6500** | 0.70–0.85 | OUT_OF_BAND |
| `good/sample-004` | 0 | 1.0000 | 23 | 0.0000 | **0.5000** | 0.70–0.85 | OUT_OF_BAND |
| `good/sample-005` | 0 | 1.0000 | 15 | 0.3000 | **0.6500** | 0.70–0.85 | OUT_OF_BAND |
| `mediocre/sample-001` | 0 | 1.0000 | 19 | 0.0000 | **0.5000** | 0.45–0.65 | IN_BAND |
| `mediocre/sample-002` | 0 | 1.0000 | 19 | 0.0000 | **0.5000** | 0.45–0.65 | IN_BAND |
| `mediocre/sample-003` | 0 | 1.0000 | 9 | 0.9000 | **0.9500** | 0.45–0.65 | OUT_OF_BAND |
| `mediocre/sample-004` | 0 | 1.0000 | 21 | 0.0000 | **0.5000** | 0.45–0.65 | IN_BAND |
| `mediocre/sample-005` | 0 | 1.0000 | 22 | 0.0000 | **0.5000** | 0.45–0.65 | IN_BAND |
| `poor/sample-001` | 0 | 1.0000 | 14 | 0.4000 | **0.7000** | 0.20–0.40 | OUT_OF_BAND |
| `poor/sample-002` | 0 | 1.0000 | 22 | 0.0000 | **0.5000** | 0.20–0.40 | OUT_OF_BAND |
| `poor/sample-003` | 0 | 1.0000 | 23 | 0.0000 | **0.5000** | 0.20–0.40 | OUT_OF_BAND |
| `poor/sample-004` | 0 | 1.0000 | 20 | 0.0000 | **0.5000** | 0.20–0.40 | OUT_OF_BAND |
| `poor/sample-005` | 0 | 1.0000 | 24 | 0.0000 | **0.5000** | 0.20–0.40 | OUT_OF_BAND |
| `broken/sample-001` | 1 | 0.9000 | 4 | 1.0000 | **0.9500** | 0.00–0.20 | OUT_OF_BAND |
| `broken/sample-002` | 0 | 1.0000 | 4 | 1.0000 | **1.0000** | 0.00–0.20 | OUT_OF_BAND |
| `broken/sample-003` | 0 | 1.0000 | 4 | 1.0000 | **1.0000** | 0.00–0.20 | OUT_OF_BAND |
| `broken/sample-004` | 0 | 1.0000 | 6 | 1.0000 | **1.0000** | 0.00–0.20 | OUT_OF_BAND |
| `broken/sample-005` | 0 | 1.0000 | 4 | 1.0000 | **1.0000** | 0.00–0.20 | OUT_OF_BAND |

---

## §3 Per-band statistics

| Band | Mean score | Std dev | IN_BAND | OUT_OF_BAND | Count | Status |
|---|---|---|---|---|---|---|
| perfect | 0.7600 | 0.1636 | 3 | 2 | 5 | FAIL (mean 0.76 below expected 0.85–1.00) |
| good | 0.6000 | 0.0935 | 1 | 4 | 5 | FAIL (mean 0.60 below expected 0.70–0.85) |
| mediocre | 0.5900 | 0.2012 | 4 | 1 | 5 | PASS (mean 0.59 within 0.45–0.65) |
| poor | 0.5400 | 0.0894 | 0 | 5 | 5 | FAIL (mean 0.54 above expected 0.20–0.40) |
| broken | 0.9900 | 0.0224 | 0 | 5 | 5 | FAIL (mean 0.99 far above expected 0.00–0.20) |

---

## §4 Root cause analysis — why the bands are inverted

The static evaluators (tsc + lizard) measure **structural** properties of code, not **semantic correctness**. The `be_01_jwt_auth` calibration band quality is defined by **JWT security logic**, not code structure. This creates a systematic inversion:

### Lizard (max cyclomatic complexity) is anti-correlated with band quality

The `perfect` samples implement the task correctly using **multiple small well-named functions** (each with CC ≤ 10–14) to express a full JWT + CSRF pipeline. The `poor` and `mediocre` samples concentrate all logic in a **single monolithic `handler` function** with CC 14–24 — high CC is a structural smell, but in calibration terms it means *more* of the required logic is present (even if implemented poorly). The `broken` samples are minimal stubs (4–6 lines of logic per function, CC ≤ 6) — they score 1.0 on lizard because there's almost no logic to measure.

| Band | Avg max CC | Lizard mean score |
|---|---|---|
| perfect | 13.4 | 0.52 |
| good | 18.0 | 0.20 |
| mediocre | 18.0 | 0.18 |
| poor | 20.6 | 0.08 |
| broken | 4.4 | **1.00** |

### tsc cannot detect the broken band's defects

4 of 5 broken samples have 0 tsc errors. Their defects are runtime/security bugs that tsc cannot catch:
- `broken/sample-001`: syntax error (missing `}`) — tsc catches this (1 error) ✓
- `broken/sample-002`: JWT secret leaked into HTTP response body — tsc sees no type violation
- `broken/sample-003`: accepts `algorithms: ['none']` — tsc sees valid `jwt.verify()` call
- `broken/sample-004`: hardcoded `"admin"` bypass skips JWT verification — tsc sees no type violation
- `broken/sample-005`: infinite recursion — tsc sees no type violation

### Gold solution type error

The gold `solution.ts` has 2 tsc errors in `tsconfig.json` mode:
1. `solution.ts:55` — `noUncheckedIndexedAccess` triggers on `m[1]` (regex group) — strict mode false positive; the preceding `if (!m)` guard establishes `m` is non-null but the index access `m[1]` is still typed as `string | undefined` under `noUncheckedIndexedAccess`.
2. `tests.spec.ts:100` — type error is in the test file, not `solution.ts`. The gold `tsconfig.json` includes `tests.spec.ts`, so it appears in the tsconfig-mode count. Solution-file-only errors = 1.

**Max CC 15** on `gold/solution.ts` — two functions at CC=15: `handler` (the main JWT middleware body) and `randomJti` (a random-bytes helper with base64url encoding). The `handler` function CC=15 is expected for a production-quality JWT middleware that handles multiple token states, CSRF checking, and error codes.

---

## §5 Gold solution verdict

| Evaluator | Score | Threshold | Pass? |
|---|---|---|---|
| tsc (tsconfig mode, solution.ts only errors) | 0.9000 | ≥0.85 | PASS |
| tsc (tsconfig mode, all files including tests.spec.ts) | 0.8000 | ≥0.85 | FAIL |
| lizard (max CC = 15) | 0.3000 | ≥0.85 | FAIL |
| Composite (tsc+lizard, all errors) | **0.5500** | ≥0.85 | **FAIL** |
| eslint | skipped | — | n/a |
| gitleaks | skipped | — | n/a |

**Gold solution is OUT_OF_BAND on composite score (0.55 vs required ≥0.85).**

The lizard score of 0.30 is the primary driver. At CC=15 the formula gives `max(0.0, 1.0-(15-8)/10) = 0.30`. The gold solution's complexity is characteristic of a correct, production-grade JWT+CSRF handler. The CC=8 threshold is too strict for the `be_01_jwt_auth` task domain.

---

## §6 Skipped evaluators — impact assessment

### ESLint (skipped)
If ESLint were available with `@typescript-eslint/parser` configured, it would likely:
- Find no errors on `perfect` samples (well-structured, standard patterns)
- Find some warnings on `poor` samples (missing error handling patterns, unused vars)
- Find 0 errors on `broken` samples (small files, no obvious lint violations)
- **Conclusion**: ESLint would not resolve the band-inversion problem for `broken` vs `perfect`

### gitleaks (skipped)
`broken/sample-002` includes `process.env.JWT_SECRET` and `opts.accessSecret` leaked into HTTP response bodies. `broken/sample-004` uses string `"admin"` as a bypass token. Neither of these is a static secret string that gitleaks would flag (gitleaks detects literal credential values like `password = "abc123"`, not env var references or program logic). **gitleaks would not differentiate the broken band from others** even if installed.

---

## §7 Overall verdict: BLOCKER

The two available static evaluators (tsc + lizard) **cannot differentiate the calibration bands** for this task pack. Specifically:

1. **broken band scores 0.95–1.00** (should be ≤0.20) — the broken samples are stubs or have runtime/security bugs invisible to static analysis
2. **poor band scores 0.50–0.70** (should be 0.20–0.40) — poor implementations are syntactically valid and pass tsc
3. **perfect band scores 0.50–0.90** (should be ≥0.85) — comprehensive implementations have higher CC which lizard penalises
4. **gold solution scores 0.55** (should be ≥0.85) — same CC penalty

The host-side static evaluators are **wired and functional** (tools execute, parsers work, scores compute). The problem is **calibration band misalignment with static metrics**: the `be_01_jwt_auth` task tests JWT security logic, which is invisible to tsc and lizard.

---

## §8 Next steps

**BLOCKER — hand to coder (task #23)**:

1. **Fix gold solution tsc error**: `solution.ts:55` — replace `m[1]` with `m[1] ?? null` or cast `m[1] as string` (the preceding guard establishes non-null, `noUncheckedIndexedAccess` is a false positive here). This unblocks the gold score from 0.80 → 1.00 on tsc.

2. **Raise CC threshold OR use sum-of-functions metric**: The CC=8 threshold rejects production-quality JWT implementations. Options:
   - Raise the threshold to CC ≤ 20 for `be_01_jwt_auth` specifically (task-level override in `task.yaml`).
   - Switch from `max_cc` to `avg_cc` or `functions_over_threshold_count / total_functions` to reward factored implementations.
   - Both changes needed before calibration bands are representative.

3. **Static evaluators alone are insufficient for band differentiation on this task**: The primary differentiators for `be_01_jwt_auth` bands are runtime-only: JWT expiry handling, algorithm pinning, CSRF validation, secret leak prevention. These require the dynamic evaluators (correctness/coverage via vitest in sandbox) — the host-side static analysis is a *necessary but not sufficient* gate for this task.

4. **Install ESLint with TypeScript support** before the next evaluator wiring run:
   ```bash
   npm install -g @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint
   ```
   This will allow the lint evaluator to run. Expected to add signal for `poor/broken` bands (unused imports, missing return types, `any` usage).

5. **Do not promote to calibration state** (`task #25`) until items 1–3 are resolved. The calibration YAML uses these scores as ground truth — inverted scores would poison judge calibration.

---

## §9 Commands run (audit trail)

```bash
# Install gold pack deps for tsc 5.9.3
cd evals/task-packs/be_01_jwt_auth/gold && npm install --ignore-scripts
# EXIT=0

# tsc on gold solution (tsconfig mode)
./node_modules/.bin/tsc -p tsconfig.json --noEmit --pretty false
# EXIT=2 — 2 errors (solution.ts:55 + tests.spec.ts:100)

# tsc on each calibration sample (25 files, file mode)
./node_modules/.bin/tsc --noEmit --strict --pretty false \
  --target ES2022 --lib ES2022 --moduleResolution node \
  --esModuleInterop --skipLibCheck \
  --typeRoots ./node_modules/@types \
  <file>
# EXIT=0 for 24/25 files; EXIT=2 for broken/sample-001 (1 error: TS1005)

# lizard on all 26 files (via uv run)
uv run python3 -c "import lizard; fi=lizard.analyze_file('<file>'); ..."
# EXIT=0 all files

# eslint (attempted)
eslint --no-eslintrc --parser-options 'ecmaVersion:2022,sourceType:module' <file>
# RESULT: "Parsing error: Unexpected token {" — @typescript-eslint/parser not available

# gitleaks (attempted)
which gitleaks
# RESULT: not found
```

---

*Report written by: claude-code/claude-sonnet-4-6/tester-task-23*  
*Files evaluated: 26 (1 gold + 25 calibration)*  
*Evaluators active: 2/4 (tsc ✓, lizard ✓, eslint skipped, gitleaks skipped)*
