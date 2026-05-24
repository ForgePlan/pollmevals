---
depth: standard
id: EVID-005
kind: evidence
last_modified_at: 2026-05-24T07:40:38.559767+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: RFC-001
  relation: informs
- target: SPEC-001
  relation: informs
status: active
title: 'prior art: SWE-bench (Princeton) — Docker harness + scaffolding attribution gap'
---

# EVID-005: SWE-bench (Princeton) — Docker harness + scaffolding attribution gap

## Structured Fields

verdict: supports
congruence_level: 2
evidence_type: audit

## ADI cycle (per NOTE-002 — retrofit)

### Abduction — research questions framed as hypotheses

- **H1**: SWE-bench has formal machine-readable scaffold-vs-model attribution in its submission schema.
- **H2**: SWE-bench uses naming-convention attribution only (`YYYYMMDD_<scaffold>_<model>` folder name); no schema field for `scaffold_id` separate from `model_name`. POLLMEVALS must close this gap if stack-eval thesis is to be expressible.
- **H3**: SWE-bench Docker images are digest-pinned for content-addressed reproducibility.

### Induction — verification per hypothesis

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (formal attribution) | sb-cli submit page: metadata.yaml requires only `name`, `oss` (bool), `site` URL; submission JSONL has `instance_id`, `model_name_or_path` (free-text label, no effect on scoring), `model_patch`. NO scaffold field. | False | **H1 REFUTED** |
| Y2 (folder convention only) | SWE-bench/experiments repo: `YYYYMMDD_sweagent_gpt4`-style folder names; leaderboard renders inconsistently ("SWE-agent + GPT-4" vs model-only); third-party morphllm analysis confirms inconsistency | Exactly as predicted | **H2 SUPPORTED** — POLLMEVALS deliberately adds `stack_pins[].stack_id` schema field |
| Y3 (digest pinning) | Docs reference DockerHub without specifying digest pinning vs tag; tag-pinning is the default | False — soft immutability | **H3 REFUTED** — POLLMEVALS pins by digest (verified in EVID-010) |

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| SWE-bench submission format: JSONL with 3 fields (`instance_id`, `model_name_or_path`, `model_patch`) | 9 | 9 | 9 | 27/27 | F: explicit. G: precise field names. R: official swebench.com guides/evaluation page. |
| `model_name_or_path` is "free-text label, no effect on scoring" | 9 | 8 | 9 | 26/27 | F: docs explicit. G: precise behavior. R: official guides. |
| Folder convention `YYYYMMDD_<scaffold>_<model>` is the only attribution | 8 | 8 | 8 | 24/27 | F: confirmed via SWE-bench/experiments repo browse. G: precise pattern. R: GitHub repo (authoritative for convention). |
| Docker pinning by TAG (not digest); tags mutable on DockerHub | 7 | 7 | 8 | 22/27 | F: stated as absence of digest pinning in docs. G: standard DockerHub behavior. R: derived (no explicit doc statement either way). |
| Leaderboard renders attribution inconsistently | 7 | 7 | 6 | 20/27 | F: stated by third-party analyst. G: examples given. R: morphllm.com analysis — not first-party (Princeton). |
| No cost or token reporting required in submission schema | 9 | 9 | 9 | 27/27 | F: schema explicit. G: precise absence of fields. R: official sb-cli docs. |
| $4/instance budget was agent-level (SWE-agent paper), not harness gate | 8 | 8 | 9 | 25/27 | F: paper explicit. G: precise wording (agent-level vs harness-level). R: NeurIPS 2024 paper (peer-reviewed). |
| SWE-bench-Live added 2M/20M token enforcement (not back-ported to Verified) | 7 | 7 | 7 | 21/27 | F: stated. G: precise numbers + variant scope. R: discussion sources, not yet verified against Verified's docs directly. |

**Decision strength**: average sum = 24.0/27 (89%). Two 27/27 claims (submission format + cost reporting absence — both load-bearing for POLLMEVALS divergence). Weakest: leaderboard rendering inconsistency (20/27, third-party source).

## Key Findings (preserved)

### Submission format — minimal JSONL contract

3 required fields: `instance_id`, `model_name_or_path` (free-text), `model_patch` (unified diff). Harness applies patch + runs repo's own test suite in Docker container per instance.

Sources: <https://www.swebench.com/SWE-bench/guides/evaluation/>, <https://www.swebench.com/SWE-bench/reference/harness/>.

### Docker pinning — by TAG (POLLMEVALS DIVERGES)

DockerHub images pre-built and pulled. Reproducibility = "only as immutable as the pinned Docker image tag" — tags are mutable.

POLLMEVALS divergence (improvement): SPEC-001 SHA256 content-addressing for ALL artifacts; RFC-001 RR-4 explicit "pin Docker image by digest (not tag)" for be_01 sandbox. **Verified in EVID-010 with real `docker inspect` digests.**

### Scaffolding attribution — naming convention only (POLLMEVALS CLOSES GAP)

`YYYYMMDD_<scaffold>_<model>` folder names (e.g. `20240415_sweagent_gpt4`). `metadata.yaml` requires only `name`, `oss`, `site` URL. NO machine-readable `scaffold_name` field separate from `model_name`. Leaderboard rendering inconsistent.

Sources: <https://www.swebench.com/sb-cli/submit-to-leaderboard/>, <https://github.com/SWE-bench/experiments>, <https://www.morphllm.com/swe-benchmark>.

POLLMEVALS direct improvement: SPEC-001 `stack_pins[].stack_id` is a first-class manifest field — machine-readable, content-addressed via `stack_yaml_sha256`. **Central thesis manifestation at the data-model level.**

### Cost transparency — absent (validates POLLMEVALS contribution)

No cost or token reporting required. $4/instance cap in SWE-agent paper was **agent-level methodology**, not harness gate. Leaderboard displays no cost figures. SWE-bench-Live added 2M/20M token limits (not back-ported to Verified).

Sources: <https://github.com/SWE-agent/SWE-agent>, <https://www.morphllm.com/swe-benchmark>.

POLLMEVALS direct contribution: SPEC-001 mandates `pricing_snapshot` + `stats.cost_usd` per eval. **Closes gap also seen in HELM/MTEB/lm-eval-harness.**

## Conclusions

- **Surviving hypothesis**: H2 (naming-convention attribution only, no schema field) — POLLMEVALS closes gap via `stack_pins[].stack_id`
- **Decision strength**: 89% (two 27/27 claims for load-bearing divergences)
- **POLLMEVALS implication**: Two structural divergences from SWE-bench made explicit at schema level — both stronger than the prior art. Borrow only the gold-test-Docker pattern for be_01 evaluator.
- **Follow-up evidence needed**: directly verify Docker tag-vs-digest claim by inspecting SWE-bench Verified docs (currently derived); confirm SWE-bench-Live token enforcement status (Verified back-port?)

## Sources

1. <https://www.swebench.com/SWE-bench/guides/evaluation/>
2. <https://www.swebench.com/sb-cli/submit-to-leaderboard/>
3. <https://github.com/SWE-bench/experiments>
4. <https://github.com/SWE-agent/SWE-agent>
5. <https://www.morphllm.com/swe-benchmark>
6. <https://www.swebench.com/SWE-bench/reference/harness/>

## Related Artifacts

- PRD-001 (informs — auto-linked)
- SPEC-001 (`stack_pins[].stack_id` first-class + `pricing_snapshot` mandatory)
- RFC-001 RR-4 (Docker digest pinning improvement)
- ADR-003 (5-model lineup uses Inspect AI's `provider/model-name`, not SWE-bench's free-text label)
- EVID-010 (Wave 1 infra — digest pinning verified with real SHA256 via `docker inspect`)
- Future ADR: harness-level cost ceiling vs agent-level enforcement
- NOTE-002 (Evidence Quality Standard — retrofit)

