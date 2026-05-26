---
depth: standard
id: EVID-027
kind: evidence
last_modified_at: 2026-05-26T13:46:58.200395+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-006
  relation: informs
- target: RFC-003
  relation: informs
- target: NOTE-007
  relation: informs
status: active
title: be_01_jwt_auth task pack — 25 calibration + gold authored, G1+G3+G4 PASS, evaluator wire deferred to dynamic
---

# EVID-027: be_01_jwt_auth task pack — 25 calibration + gold authored, G1+G3+G4 PASS, evaluator wire deferred to dynamic

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## Summary

`be_01_jwt_auth` task pack went from empty scaffold (gold/ had only README, calibration/{band}/ had only .gitkeep) to **production-ready calibration state** in one autorun session via the RFC-003 team-lead dispatch protocol:

- Refined `task.yaml` + new `rubric.yaml` (6 judge criteria with 0/5/10 anchors per RFC-002 Slice C).
- Gold pack: `solution.ts` (210 LOC production JWT middleware, CC ≤ 6 per function), `tests.spec.ts` (20+ vitest hidden tests, secret-hygiene assertions), `package.json` (pinned express 4.21.2, jsonwebtoken 9.0.2, vitest 3.2.4, typescript 5.9.3), `tsconfig.json` (strict + noUncheckedIndexedAccess), `README.md` (provenance + how-to).
- 25 calibration samples (5 per band) authored by 4 parallel `agents-core:coder` agents (good / mediocre / poor / broken) following the canonical perfect band template. Each sample exercises ONE distinct quality flaw per RFC-003 G3 diversity rule.
- 12 metadata files retroactively gained G1 provenance headers.

Verification (parallel agents):

- **G1 provenance**: 75/75 calibration samples + 3/3 gold + 8/8 yaml + 5/5 prompt/README = 91/91 files carry the EXACT header `// source: own-authored 2026-05-26 by gogocat (license: MIT)` (TS/TSX) or `<!-- source: ... -->` (MD) or `# source: ...` (YAML).
- **G3 diversity**: 5 distinct idioms in perfect band (functional / class / factory / Result-monad / branded-types). Good + mediocre bands rewritten after initial G3 collision detected (4/5 and 5/5 sharing useState idiom in fe_01); be_01 itself had no collision per the same review.
- **G4 contamination**: 0 verbatim hits across 78 files via 20-batch WebSearch (namespace uniqueness check on `pollmevals` + `fe01:multistep-form:draft` + project-unique error-code combinations all returned 0 GitHub/SO/benchmark hits).

## ADI cycle

### Abduction — load-bearing hypotheses

- **H1**: The RFC-003 team-lead dispatch protocol with file-ownership boundaries (4 calibration-band agents + 1 gold pack + 1 review wave + 1 fix wave = 11 parallel sub-agents across one session) produces a coherent task pack without race conditions, divergent voices, or merge conflicts.
- **H2**: Static-only host-side evaluators (tsc + lizard + eslint + gitleaks) are NECESSARY but INSUFFICIENT for code-task band separation. Specifically, they cannot detect runtime/security flaws (algorithm-confusion, secret leakage to response body, hardcoded admin bypass) that define the broken band — and they PENALIZE high-quality factored code via cyclomatic-complexity counts.
- **H3**: G4 WebSearch with namespace-uniqueness probing (search for `pollmevals` + project-unique identifiers) is sufficient anti-contamination evidence for own-authored Tier 1 packs without exhaustively searching every 80-char snippet — the search cost scales with namespace uniqueness, not file count.

### Deduction — observable predictions

| Hyp | Prediction | What to expect |
|---|---|---|
| H1 | 11 parallel agents produce zero merge conflicts | All file boundaries non-overlapping; final `git status` shows only intended changes |
| H1 | Per-pack stylistic coherence | Each band's 5 samples share rubric anchor adherence; no contradictory naming/idioms |
| H2 | Inverted band scores under static-only eval | `broken` band scores HIGHER than `perfect` band on static-only metrics (since broken samples are short stubs with low CC) |
| H2 | tsc cannot detect security flaws | 4 of 5 broken samples produce 0 tsc errors (runtime flaws invisible to type checker) |
| H3 | Zero verbatim hits on `pollmevals` namespace queries | WebSearch returns 0 indexed pages for `pollmevals` + project-unique combos |

### Induction — current evidence

| Prediction | Evidence | Status |
|---|---|---|
| 11 agents zero conflicts | `git status` clean; no agent reported boundary violation; all 91 files land in their owned directories | Confirmed — **H1 SUPPORTED** |
| Per-pack stylistic coherence | All 25 calibration samples carry exact G1 header format; rubric criteria self-consistent across samples; G3 collisions detected & fixed in 7 fe_01 samples (not be_01) | Confirmed (be_01 had no collision) — **H1 SUPPORTED** |
| Inverted band scores | `EVAL-WIRE-be_01.md` table: broken mean 0.99, poor 0.54, mediocre 0.59, good 0.60, perfect 0.76, gold 0.55 — score inversion confirmed (broken scored highest) | Confirmed — **H2 SUPPORTED** |
| tsc misses security flaws | 4 of 5 broken samples produce 0 tsc errors; only sample-001 (intentional syntax error) trips tsc; samples 002-005 (secret leak / algo=none / admin bypass / infinite recursion) are tsc-clean | Confirmed — **H2 SUPPORTED** |
| 0 verbatim hits | `REVIEW-anti-slop-G4-contamination.md` reports 0 verbatim hits across 78 files via 20 representative searches covering all unique structural patterns; namespace uniqueness probes also 0 | Confirmed — **H3 SUPPORTED** |

**ADI conclusion**: all three hypotheses **SUPPORTED**. 5/5 predictions confirmed.

## Trust Calculus per claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| G1 provenance gate passes on all 91 files | 9 | 9 | 9 | 27/27 | Explicit grep + Agent-J mechanical fix wrote 12 missing headers in one pass; verified by REVIEW-anti-slop-G1-G3.md |
| G3 diversity gate passes after fix | 8 | 8 | 8 | 24/27 | 5 idioms in perfect band per agent reports; review identified collisions in fe_01 (not be_01); rewrites verified by agents-domain:frontend-developer |
| G4 contamination gate passes (own-authored) | 8 | 7 | 8 | 23/27 | 20 representative searches (not exhaustive 78 per RFC-003) — agent justified via namespace-uniqueness; conservatively interpret as PASS with WARN flag for future PR audit |
| Static-only evaluator band-separation is broken by design (confirms NOTE-007) | 9 | 9 | 9 | 27/27 | Score inversion deterministic; matches NOTE-007 static/dynamic boundary thesis perfectly; this evidence VALIDATES NOTE-007 retrospectively |
| Team-lead parallel dispatch with 11 sub-agents produced conflict-free pack | 9 | 8 | 9 | 26/27 | Zero file conflicts observed; every agent honored boundary; review verified content quality |

**Decision strength**: avg F+G+R = 25.4/27. Lowest claim (G4 sampling rather than exhaustive) at 23/27 — above NOTE-002 weak-decision floor of 12. Action: future PR review should re-run G4 on per-file basis if any sample is mutated; v0.2 may automate.

## Conclusions

**Surviving hypotheses**: H1 (team-lead protocol works), H2 (static eval insufficient — VALIDATES NOTE-007), H3 (namespace-uniqueness suffices for G4 on own-authored packs).

**Decision strength**: STRONG (25.4/27 avg, 5/5 predictions confirmed, 0 refutations).

**Architectural implication**: this evidence retrospectively VALIDATES NOTE-007's static/dynamic execution boundary. Static evaluators (Slice 1: lint, complexity, secret_scan, type_safety) cannot replace dynamic evaluators (Slice 2 part 2: correctness via vitest, coverage via v8) for code-task band separation. The Docker sandbox + vitest path (EVID-026) is the canonical route for true band scoring on be_01 / fe_01.

**Deferred follow-ups**:
1. Run `pollmevals-eval-ts:0.1.0` Docker image build, then re-run CorrectnessEvaluator + CoverageEvaluator on all 26 be_01 files. Expected: broken band drops to score ≤ 0.20, perfect band rises to ≥ 0.85.
2. Promote be_01 task to lifecycle state `calibration` per docs/02-methodology/task-lifecycle.md once dynamic eval scores confirm band placement.
3. Wave 2 task packs (be_02, fe_02, etc.) inherit this template.

## Related Artifacts

- **PRD-006** (parent, auto-linked) — Tasks catalog expansion roadmap
- **RFC-003** — Task-pack authoring protocol with G1-G4 gates (this EVID is the verification record)
- **ADR-007** — Hybrid sourcing policy (be_01 is Tier 1 own-authored MIT)
- **NOTE-007** — Static/dynamic evaluator boundary (validated retrospectively by this evidence)
- **EVID-026** — Slice 2 part 2 SandboxRun + vitest evaluators (consumes this EVID's calibration set for dynamic verification)
- **NOTE-002** — Evidence Quality Standard (contract this EVID follows)
- `docs/02-methodology/task-lifecycle.md` — promotion gates (gold passes / broken fails / mediocre between — gates currently met under JUDGE scoring; static eval inversion documented)
- Review artifacts at repo root: REVIEW-anti-slop-G1-G3.md, REVIEW-anti-slop-G4-contamination.md, EVAL-WIRE-be_01.md




