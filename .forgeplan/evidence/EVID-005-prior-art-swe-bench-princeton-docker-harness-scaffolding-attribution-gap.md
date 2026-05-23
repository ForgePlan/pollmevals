---
depth: standard
id: EVID-005
kind: evidence
last_modified_at: 2026-05-23T19:30:35.800640+00:00
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

## Summary

External prior art review of SWE-bench (Jimenez et al. 2024, princeton-nlp + SWE-bench org). SWE-bench is the de-facto standard for LLM coding benchmarks 2024-2026. Validates POLLMEVALS's stronger content-addressing approach to immutability, confirms gold-test-Docker pattern for `be_01_jwt_auth`, and surfaces a structural gap (scaffolding attribution) that POLLMEVALS deliberately closes.

## Key Findings

### Submission format — minimal JSONL contract

Each prediction is one JSON object in JSONL with three required fields:

```json
{
  "instance_id": "django__django-12345",
  "model_name_or_path": "free-text label, no effect on scoring",
  "model_patch": "unified diff applied to repo's base commit"
}
```

The harness applies the patch, runs the repo's own test suite inside a Docker container per instance, and records pass/fail.

Sources: <https://www.swebench.com/SWE-bench/guides/evaluation/>, <https://www.swebench.com/SWE-bench/reference/harness/>.

### Docker pinning — by tag, not digest (POLLMEVALS DIVERGES)

Docker images are pre-built and pulled from DockerHub. Reproducibility is **only as immutable as the pinned Docker image tag** — and tags are mutable on DockerHub. SWE-bench docs reference DockerHub without specifying digest-based pinning.

**POLLMEVALS divergence (and improvement)**: SPEC-001 specifies SHA256 content-addressing for ALL artifacts (manifest, raw_output, evaluator_json) — content-addressed storage is stronger than tag-pinning. RR-4 risk in RFC-001 explicitly says "pin Docker image by digest (not tag)" for our `be_01_jwt_auth` sandbox.

### Scaffolding attribution — naming convention, not schema (POLLMEVALS CLOSES GAP)

SWE-bench does **not enforce a formal scaffold-vs-model separation** at the protocol level. The submission folder convention in `SWE-bench/experiments` is:

```
YYYYMMDD_<scaffold>_<model>/    # e.g. 20240415_sweagent_gpt4/
```

So attribution is carried in the **directory name by convention, not schema**. `metadata.yaml` requires only `name`, `oss` (bool), and `site` URL. The leaderboard renders entries inconsistently: some show "SWE-agent + GPT-4", others show only the model. There is **NO machine-readable field for `scaffold_name` separate from `model_name`**.

Sources: <https://www.swebench.com/sb-cli/submit-to-leaderboard/>, <https://github.com/SWE-bench/experiments>, <https://www.morphllm.com/swe-benchmark>.

**POLLMEVALS direct improvement**: SPEC-001 `stack_pins[].stack_id` is a first-class manifest field — machine-readable, content-addressed via `stack_yaml_sha256`. Every eval carries explicit scaffold attribution separate from model attribution. This is the value-add of POLLMEVALS's stack-evaluation thesis at the schema level.

### Cost transparency — absent (validates POLLMEVALS contribution)

**No cost or token reporting is required by the submission schema.** The $4/instance budget cap originated as a **methodology choice in the SWE-agent paper** (enforced by the agent scaffold, not by the harness). The SWE-bench leaderboard displays no cost figures.

Third-party commentary (morphllm.com) notes entries like "Agentless" are cheaper, but this is editorial, not mandatory metadata. Token limits were added only in specific controlled variants (SWE-bench-Live: 2M uncached + 20M cached tokens per run), **not the canonical SWE-bench Verified**.

Sources: <https://github.com/SWE-agent/SWE-agent>, <https://www.morphllm.com/swe-benchmark>.

**POLLMEVALS direct contribution**: SPEC-001 mandates `pricing_snapshot` and `stats.cost_usd` per eval. This closes another industry gap (HELM, MTEB, lm-eval-harness, SWE-bench all leave it open — see EVID-001..004).

## Implications for POLLMEVALS

1. **Adopt SWE-bench harness pattern for `be_01_jwt_auth`** — gold test suite + Docker isolation + unified-diff submission. Inspect AI's `sandbox` field gives this directly. **CAVEAT**: pin Docker image by digest (not tag) — improvement over SWE-bench's approach. Captured in RFC-001 RR-4.
2. **POLLMEVALS DIVERGES on scaffolding attribution** — `stack_id` is a first-class schema field, not a folder-name convention. This is **the central thesis manifestation** at the data-model level.
3. **POLLMEVALS DIVERGES on cost reporting** — mandatory per-eval `cost_usd` field. Closes gap that SWE-bench Verified leaves open.
4. **Borrow pattern**: per-instance Docker isolation for coding tasks. Don't borrow tag-based pinning.

## Sources

1. <https://www.swebench.com/SWE-bench/guides/evaluation/> — submission JSONL schema, Docker isolation model
2. <https://www.swebench.com/sb-cli/submit-to-leaderboard/> — metadata.yaml required fields, PR-based submission
3. <https://github.com/SWE-bench/experiments> — folder naming pattern `YYYYMMDD_<scaffold>_<model>`, no cost fields
4. <https://github.com/SWE-agent/SWE-agent> — $4/instance budget cap at agent level
5. <https://www.morphllm.com/swe-benchmark> — leaderboard inconsistency analysis
6. <https://www.swebench.com/SWE-bench/reference/harness/> — harness invocation, DockerHub pull

## Confidence

🟡 Medium — submission format and naming conventions are 🟢 (multiple corroborating sources including official harness docs). Cost transparency is 🟡 (absence of requirement confirmed across 3 sources, but no official policy document explicitly states "cost reporting is optional"). Scaffolding attribution nuances on rendered leaderboard are 🟡 (third-party analysis).

## Open Questions

- Does SWE-bench Verified pin Docker image tags by digest (content-addressed) or only by tag name? Critical for understanding immutability claims.
- SWE-bench-Live added token-budget enforcement (2M/20M). Is this being back-ported to Verified, or Live-specific?
- The "$4/instance" cap in SWE-agent paper was agent-level. Does POLLMEVALS want a harness-level cost ceiling for fair cross-stack comparisons? (Worth a future ADR after first weekly run.)

## Related Artifacts

- PRD-001 (informs — auto-linked)
- SPEC-001 (`stack_pins[].stack_id` first-class field, `pricing_snapshot` mandatory)
- RFC-001 RR-4 (Docker digest pinning improvement)
- ADR-003 (5-model lineup — provider_route format informed by Inspect AI, not SWE-bench)
- Future ADR: harness-level cost ceiling vs agent-level enforcement




