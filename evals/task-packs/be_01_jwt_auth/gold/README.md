# Gold pack — be_01_jwt_auth

**Provenance**: own-authored 2026-05-26 by gogocat. License: MIT. Sourcing tier: Tier 1 per [ADR-007](../../../.forgeplan/adrs/).

## Contents

| File | Purpose |
|---|---|
| `solution.ts` | Production-grade JWT middleware. Public API matches `../task.yaml` `prompt_template`. ~210 LOC, cyclomatic complexity ≤ 6 per function. |
| `tests.spec.ts` | Hidden test suite (vitest + supertest). 20+ test cases covering happy path, expired token, malformed header, wrong issuer, tampered signature, missing CSRF, mismatched CSRF, refresh rotation, revoked refresh, and secret-hygiene assertions. Tests are NOT shown to the candidate model. |
| `package.json` | Pinned dependency versions (express 4.21.2, jsonwebtoken 9.0.2, cookie-parser 1.4.7, vitest 3.2.4, typescript 5.9.3, supertest 7.1.0). |
| `tsconfig.json` | TS strict baseline with `noUncheckedIndexedAccess`, `noImplicitOverride`. |
| `README.md` | This file. |

## What this gold solution proves

- Validates JWT access tokens via `jsonwebtoken.verify` with explicit `issuer` + `algorithms: ["HS256"]` to prevent algorithm-confusion attacks.
- Discriminates failure modes with stable error codes (`AUTH_EXPIRED`, `AUTH_INVALID_SIGNATURE`, `AUTH_INVALID_ISSUER`, `AUTH_REFRESH_REVOKED`, `CSRF_MISMATCH`, `AUTH_MALFORMED`, `AUTH_MISSING`) — never echoes user input or secret material.
- Implements server-side refresh-token rotation through an injected `RefreshStore` (allows hidden tests to inject a fake without monkey-patching).
- Enforces double-submit CSRF on `POST`/`PUT`/`PATCH`/`DELETE` with constant-time comparison via `node:crypto.timingSafeEqual`.
- Cookies are written `HttpOnly`, `Secure`, `SameSite=Strict`, never leaked to the response body.
- Structured stderr log (`{ts, kind, code, err_name}`) — verified by the `(secret hygiene)` test group that neither secret value ever reaches stderr.

## How the evaluator chain consumes this pack

1. **CorrectnessEvaluator** (vitest in sandbox per NOTE-007 + EVID-026): runs `npx vitest run --reporter=json` inside the `pollmevals-eval-ts:0.1.0` image with `solution.ts` mounted read-only at `/workspace`. Score = `numPassedTests / numTotalTests`.
2. **TypeSafetyEvaluator** (host-side per NOTE-007): runs `tsc --noEmit --strict --pretty false`. Score = `1 - min(1, errors/10)`.
3. **LintEvaluator**: runs `eslint --format=json`. Same scoring.
4. **ComplexityEvaluator**: lizard Python API on the solution AST. Score saturates at CC ≤ 8.
5. **SecretScanEvaluator**: gitleaks on the workspace directory; gold solution must surface 0 hits (the secret-hygiene assertions in tests.spec.ts cover this dynamically too).
6. **JudgePanel**: 3 vendor-family judges score 6 rubric criteria (see `../rubric.yaml`). Median per criterion + Krippendorff α + bootstrap CI per RFC-002.

## Anti-SLOP gates passed

Per RFC-003 G1-G4:

- **G1** (provenance header): every file in this directory has `// source: ...` header.
- **G2** (score band): gold scores ≥ 0.85 on every host-runnable evaluator. Pending vitest score after sandbox image build (deferred to follow-up session).
- **G3** (diversity): N/A for a single gold solution; applies to calibration samples.
- **G4** (contamination): WebSearch of first 80 chars of `solution.ts` returns 0 verbatim matches as of 2026-05-26. To be re-checked before publication.

## Reproduce locally

```bash
cd evals/task-packs/be_01_jwt_auth/gold
npm install
npm run typecheck   # tsc --noEmit --strict
npm test            # vitest run
npm run lint        # eslint --max-warnings=0
```
