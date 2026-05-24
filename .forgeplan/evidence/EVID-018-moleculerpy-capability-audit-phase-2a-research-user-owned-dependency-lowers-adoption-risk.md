---
depth: standard
id: EVID-018
kind: evidence
last_modified_at: 2026-05-24T08:32:14.991731+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-003
  relation: informs
- target: ADR-004
  relation: informs
status: active
title: MoleculerPy capability audit — Phase 2A research; user-owned dependency lowers adoption risk
---

# EVID-018: MoleculerPy capability audit — Phase 2A research; user-owned dependency lowers adoption risk

## Structured Fields

verdict: supports
congruence_level: 2
evidence_type: audit

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "is MoleculerPy fit for PRD-003 distributed orchestrator?")

- **H1**: MoleculerPy is a **toy/early prototype** — adoption is risky 3rd-party dependency; POLLMEVALS should build on Celery+Redis (industry-standard) or wait for MoleculerPy v1.0 maturity.
- **H2**: MoleculerPy is **young (4 months) but production-disciplined**, AND **owned by POLLMEVALS maintainer (gogocat)** — bug-fix path is in-house, not 3rd-party blocked. Native Python fit, built-in primitives match POLLMEVALS needs (bulkhead, circuit breaker, NATS transport — already in POLLMEVALS Makefile). Reasonable bet for Phase 3+.
- **H3**: MoleculerPy is sufficient AND **POLLMEVALS being its first production user creates ecosystem flywheel** — POLLMEVALS gains battle-tested primitives, MoleculerPy gains credibility + real-world feature pressure. Mutual benefit.

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 | MoleculerPy repo: <500 LOC, no tests, no CI, no docs, no examples, archived/stale | `gh api` inspection of org repos |
| H2 | MoleculerPy: 1500+ LOC, CI/codecov, pre-commit, docker-compose, examples/, docs/, recent commits, 0 open issues, owned by user with explicit "I will fix issues fast" commitment | Same inspection + user direct statement |
| H3 | MoleculerPy is small (no big users yet); adopting POLLMEVALS as flagship is feasible AND would surface real-world API gaps quickly | Repo size + age + zero declared production users |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (toy prototype) | `gh api repos/MoleculerPy/moleculerpy` returns: 1850 KB, MIT license, Python, default branch `main`, **0 open issues**, has CHANGELOG.md (28 KB — substantial version history), KNOWN-ISSUES.md (9 KB — honest documentation of known gaps), examples/, docs/, tests/, scripts/, pre-commit-config.yaml, codecov.yml, security.md, docker-compose.yml, AGENTS.md + CLAUDE.md (uses agentic workflow), Russian + English READMEs (10 + 7 KB). | Production-shaped repo, NOT a toy | **H1 REFUTED** |
| Y2 (young but disciplined + owned) | All Y1 evidence + explicit user statement (2026-05-24): "я владелец Py версии … если что сам починю и это будет быстро и это в + к весу". User direction: bump Reliability axis for MoleculerPy-dependent decisions. POLLMEVALS architecture vision already commits MoleculerPy in MASTER.md ("Eval plane → Python 3.12+ + MoleculerPy", "MoleculerPy services: orchestrator, worker, judge, stats"). | Exactly as predicted | **H2 SUPPORTED** |
| Y3 (ecosystem flywheel) | MoleculerPy public_repos=4, all created 2026-Q1-Q2, 0 stars, 0 declared production users in README. POLLMEVALS becoming first production user would be measurable contribution. | True — first-mover position confirmed | **H3 SUPPORTED** (compatible with H2) |

**Surviving hypothesis**: H2 + H3 jointly — MoleculerPy is fit-for-purpose for PRD-003 with low adoption risk (owner-mediated fix path), AND POLLMEVALS adoption creates mutual ecosystem benefit.

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| MoleculerPy core repo: 1850 KB Python, MIT, 0 open issues | 9 | 9 | 9 | 27/27 | F: explicit. G: precise size. R: `gh api` first-party authoritative. |
| Production discipline: CI, codecov, pre-commit, docker-compose, security policy, KNOWN-ISSUES.md (9 KB) | 9 | 9 | 9 | 27/27 | F: file presence verifiable. G: file sizes precise. R: direct repo inspection. |
| Built-in bulkhead + circuit breaker + service discovery (Moleculer.js feature parity) | 8 | 8 | 7 | 23/27 | F: documented in Moleculer.js docs (MoleculerPy claims port). G: feature names precise. R: Moleculer.js docs authoritative; MoleculerPy parity NOT yet independently verified via direct test — assumed port-completeness. **Bumps to R=9 once first POLLMEVALS integration test exercises these primitives — until then R=7.** |
| User is owner of MoleculerPy org (`github.com/MoleculerPy`) → fix path in-house | 9 | 9 | 9 | 27/27 | F: explicit user statement + `gh api user/orgs` shows MoleculerPy in user's list. G: precise org name. R: GitHub API authoritative + direct user statement during this session. **This is the key F+G+R uplift** — typical 3rd-party deps would be R=6-7; ownership bumps to R=9. |
| User commitment: "если что сам починю и это будет быстро" (will fix issues fast) | 8 | 7 | 9 | 24/27 | F: direct quote. G: subjective ("fast" not defined as SLA). R: user-stated intent. Lower G because no formal SLA, but acceptable for v0.1 scope. |
| POLLMEVALS MASTER.md already commits MoleculerPy in vision | 9 | 9 | 9 | 27/27 | F: explicit quotes from MASTER.md. G: precise (multiple lines named). R: POLLMEVALS own doc. |
| NATS transport already planned in POLLMEVALS Makefile (`docker-up` includes NATS) | 9 | 9 | 9 | 27/27 | F: Makefile explicit. G: file:line. R: POLLMEVALS own infrastructure. |
| Phase 2A `EvalCaller` Protocol (EVID-015) provides clean migration seam to MoleculerPy action | 9 | 8 | 9 | 26/27 | F: Protocol explicit. G: seam well-defined. R: architect finding #4 + EVID-015 verified Protocol conformance. |
| MoleculerPy is 4 months old (Jan 2026); first production user (POLLMEVALS) would create flywheel | 8 | 8 | 8 | 24/27 | F: explicit creation date. G: precise age. R: `gh api` confirms; flywheel claim is reasonable inference (no peer-reviewed source for "first-user ecosystem effect" magnitude). |
| `gh api orgs/MoleculerPy/repos` confirms 4 repos all Python, all updated 2026-04 (recent) | 9 | 9 | 9 | 27/27 | F: explicit. G: precise repo list + dates. R: GitHub API authoritative. |

**Decision strength**: average sum = 25.9/27 (96%). 6 claims at 27/27. Weakest: built-in primitives parity (23/27) — explicitly flagged for measurement in first POLLMEVALS integration test (Phase 3 entry criterion). User-ownership claim (27/27) is the F+G+R uplift that distinguishes this adoption from a typical 3rd-party dependency decision.

## What we audited (sources)

1. `gh api orgs/MoleculerPy/repos --jq '.[] | {name, description, language, stars, updated, archived, fork}'` — 4 repos, all Python, all recent (Apr 2026)
2. `gh api orgs/MoleculerPy --jq '{name, description, public_repos, blog, location, created_at}'` — org Jan 2026, 4 public repos, blog at moleculerpy.services
3. `gh api repos/MoleculerPy/moleculerpy --jq '{size_kb, default_branch, language, license, topics, has_issues, has_wiki, open_issues}'` — 1850 KB, MIT, main, Python, 0 open issues
4. `gh api repos/MoleculerPy/moleculerpy/contents` — verified presence of: `CHANGELOG.md` (28 KB), `KNOWN-ISSUES.md` (9 KB), `examples/`, `docs/`, `tests/`, `scripts/`, `pre-commit-config.yaml`, `codecov.yml`, `Dockerfile`, `docker-compose.yml`, `AGENTS.md`, `CLAUDE.md`, `README.md` + `README.ru.md`
5. Moleculer.js docs (https://moleculer.services/docs/0.14/) — feature parity reference for MoleculerPy port
6. POLLMEVALS `MASTER.md` `grep -i moleculer` — 10 explicit mentions confirming vision-level commitment
7. POLLMEVALS `Makefile` `docker-up` target — NATS already planned in infrastructure
8. Direct user statement (2026-05-24): "я владелец Py версии … если что сам починю и это будет быстро"
9. `gh api user/orgs --jq '.[].login'` confirms `MoleculerPy` in user's org membership list

## Conclusions

- **Surviving hypothesis**: H2 + H3 (MoleculerPy fit, owner-mediated fix path, mutual ecosystem benefit)
- **Decision strength**: 96% (6 claims at 27/27; one strategic F+G+R uplift via ownership)
- **POLLMEVALS implication**: ADR-004 records the architectural decision to adopt MoleculerPy for PRD-003+; Phase 2A `EvalCaller` Protocol already provides migration seam
- **MoleculerPy implication**: POLLMEVALS becomes first production user; creates feedback pressure that surfaces real-world API gaps quickly (which user can fix in-house, accelerating MoleculerPy maturation)
- **Follow-up evidence needed**:
  - First Phase 3 integration test of bulkhead + circuit breaker against real provider failures → raises primitives-parity claim from 23/27 to 27/27
  - Track time-to-fix for any MoleculerPy issues found during POLLMEVALS Phase 3 (validates user "fast fix" commitment)

## Related Artifacts

- PRD-003 (informs — auto-linked at create; this audit informs weekly cadence design)
- ADR-004 (informs — provides decision rationale)
- EPIC-001 (PRD-003 is child; architecture decision affects EPIC phase planning)
- EVID-015 (Wave 4 EvalCaller Protocol — migration seam ready for MoleculerPy action wrap)
- EVID-016 (Wave 5 GridRunner — single-process baseline that MoleculerPy will distribute)
- NOTE-002 (Evidence Quality Standard — applied)
- Future EVID (Phase 3 first MoleculerPy integration measurement)



