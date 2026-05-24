---
depth: standard
id: NOTE-002
kind: note
last_modified_at: 2026-05-24T07:25:05.166139+00:00
last_modified_by: claude-code/2.1.150
links:
- target: EPIC-001
  relation: informs
status: active
title: Evidence Quality Standard — ADI cycle + Trust Calculus F/G/R for all POLLMEVALS EVIDs
---

# NOTE-002: Evidence Quality Standard — ADI cycle + Trust Calculus F/G/R

## Context

**Established 2026-05-24** after user (gogocat) flagged that EVID-009..013 (Wave 1-3 sprint outputs) were descriptive but lacked formal ADI structure and Trust Calculus scoring. This Note is the **mandatory contract** for all subsequent POLLMEVALS Evidence artifacts. Pre-existing EVID-001..013 are retrofitted in the same revision to comply.

This is the methodology layer above forgeplan's automatic `formality / granularity / reliability` scoring — explicit values prevent the parser from guessing.

## The two concepts (binding)

### 1. ADI cycle (Abduction → Deduction → Induction)

Every EVID body MUST contain three sections in order:

**Hypotheses** (minimum 3): each is a distinct candidate explanation for the underlying claim. Two hypotheses risk false dichotomy ("Redis vs Postgres"); the third often breaks the dichotomy ("in-process LRU, no network at all"). Label H1, H2, H3.

**Deductive predictions**: for each hypothesis, formulate "if H_i is true, then observable Y_i must hold". Word "observable" is load-bearing. If no prediction can be checked → it's a phrase, not a hypothesis. Format: `H1 → predicts Y1 (measurable as Z1)`.

**Inductive verification**: each prediction is paired with a concrete measurement / benchmark / test / doc reference / production data. Format: `Y1 verified by <evidence>; result <outcome>; hypothesis H1 <SUPPORTED|REFUTED|INCONCLUSIVE>`.

The verdict (`supports / weakens / refutes`) on the EVID's structured fields is computed from the inductive verification: which hypothesis survived.

### 2. Trust Calculus (F + G + R)

Each load-bearing claim inside an EVID gets a triple `(F, G, R)`, each axis on 0-9 scale, independent:

- **F (Formality)** — how rigorously stated:
  - 0: "I think" / vibes
  - 5: explicit statement with conditions ("under load X, metric Y holds")
  - 9: formal specification or proof

- **G (Granularity)** — how concrete:
  - 0: "it's slow"
  - 5: "15% faster"
  - 9: "p99 = 47ms at 10k RPS, payload 1KB, setup described"

- **R (Reliability)** — source quality:
  - 0: Slack anecdote
  - 5: multiple independent sources
  - 9: peer-reviewed paper OR our own production benchmark with reproducible script

**Axes are independent.** A vendor marketing whitepaper might be F7 G8 R2 — formal, detailed, but the source is selling you. A Slack screenshot with a reproducible bench script can be F2 G8 R7 — informal but real and replicable.

**Rule of thumb**: if a decision rests on claims with F+G+R sum < 12 → it is a weak decision and more evidence should be gathered before committing. The goal is not perfectionism but honesty with self.

## Mandatory EVID body template (binding)

```markdown
# EVID-NNN: <title>

## Structured Fields

verdict: supports | weakens | refutes
congruence_level: 0 | 1 | 2 | 3
evidence_type: measurement | test | benchmark | audit | research

## ADI cycle

### Abduction — hypotheses (≥3)

- **H1**: <distinct explanation 1>
- **H2**: <distinct explanation 2>
- **H3**: <distinct explanation 3 — often the dichotomy-breaker>

### Deduction — observable predictions

- **H1 → Y1**: if H1 holds, we should observe <concrete observable>; measurable as <specific check>
- **H2 → Y2**: ...
- **H3 → Y3**: ...

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 | <bench / test name / doc URL / measurement> | <pass/fail/value> | SUPPORTED / REFUTED / INCONCLUSIVE |
| Y2 | ... | ... | ... |
| Y3 | ... | ... | ... |

## Trust Calculus per claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| <load-bearing claim 1> | 0-9 | 0-9 | 0-9 | x/27 | <source / caveats> |
| <load-bearing claim 2> | ... | ... | ... | ... | ... |

**Decision strength**: sum of all claim F+G+R averages. If any single load-bearing claim has sum < 12 → flag in conclusions for follow-up evidence gathering.

## Wave summary (sprint context, if applicable)

<existing wave summary fields: sprint, wave, workers, files, LOC, pipeline gates>

## Acceptance criteria validation (if applicable)

<as before>

## Related Artifacts

<as before>

## Conclusions

- Surviving hypothesis: <which H_i is best supported by evidence>
- Strength: <decision-strength summary>
- Follow-up evidence needed (if any): <list claims with low F+G+R that warrant more data>
```

## Why now

Without this standard:
- Evidence "decay" goes undetected — old benchmarks treated as still valid (Redis 6.x bench for Redis 7.4 question)
- Decisions get committed on F2 G2 R2 ("colleague said") claims without anyone realizing
- Future contributors can't tell which claims in an EVID are load-bearing vs incidental color
- `forgeplan score` falls back to keyword-guessed F/G/R values instead of explicit ones

## Retrofit scope (this same revision)

EVID-001..008 are external research / audit and largely satisfy this standard implicitly (each has source URLs + verdict). They will get an explicit `## Trust Calculus` table appended but no ADI restructure (their ADI is implicit in the research-question format).

EVID-009..013 (Wave 1-3 sprint outputs) are **fully retrofitted** with explicit ADI sections + Trust Calculus tables.

EVID-014+ (Wave 4-5 + sprint close) created with the new template from the start.

## Compliance

- Lefthook `forgeplan-validate` will be extended (separate Tactical task) to fail if a new EVID lacks `## ADI cycle` or `## Trust Calculus` H2 sections — making this contract enforced, not aspirational.
- This NOTE-002 is itself NOT an EVID (no claims about external state) — Notes don't need ADI structure. But it IS the contract referenced by every future EVID.

## Related

- EVID-007 (architect-reviewer audit) — first EVID retrofitted as proof of concept (CL=3, structured fields already present)
- EVID-008 (Guardian gate-2 PASS) — same
- EVID-009..013 — retrofitted in this revision
- `.forgeplan/config.yaml` § FPF Engine — F/G/R thresholds will be tuned after first sprint with explicit scoring (currently commented out, defaults: explore_reff=0.01, investigate_reff=0.5, exploit_reff=0.7)
- `forgeplan_score` — auto-aggregates F/G/R per artifact; explicit scoring eliminates parser guessing




