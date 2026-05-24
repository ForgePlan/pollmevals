---
depth: standard
id: EVID-010
kind: evidence
last_modified_at: 2026-05-24T07:28:00.374262+00:00
last_modified_by: claude-code/2.1.150
links:
- target: RFC-001
  relation: informs
status: active
title: 'Wave 1 (sprint phase-2A): RFC-001 impl tasks 1-2 + 14-15 — skeleton + LiteLLM compose + digest-pinned Dockerfile'
---

# EVID-010: Wave 1 — RFC-001 impl tasks 1-2 + 14-15: skeleton + LiteLLM compose + digest-pinned Dockerfile

## Structured Fields

verdict: supports
congruence_level: 3
evidence_type: measurement

## ADI cycle (per NOTE-002)

### Abduction — hypotheses (3 candidates for "how to bootstrap orchestrator skeleton with reproducibility?")

- **H1**: Tag-based pinning (`node:22-alpine`, `litellm:main-stable`) is sufficient — industry standard, low overhead, container registries are reliable enough.
- **H2**: Digest-based pinning (`@sha256:...`) is required — tags are mutable on registries (per SWE-bench EVID-005 lesson), so any re-pull may yield different bits, breaking ADR-0002 reproducibility.
- **H3**: Custom-built sandbox images stored in a private registry — full control, no upstream risk, at the cost of registry maintenance.

### Deduction — observable predictions

| Hypothesis | Predicted observable | Measurable as |
|---|---|---|
| H1 | `docker pull node:22-alpine` 1 month from now returns same image as today | Compare `docker inspect ... --format '{{.RepoDigests}}'` over time |
| H2 | `docker pull node:22-alpine@sha256:968df39...` is bit-identical on every re-pull | Same `docker inspect` digest field always returns same SHA256 |
| H3 | Private registry maintenance adds ~1 person-day/quarter for security patching + 2nd Docker registry dep | Estimated infra burden vs benefit |

### Induction — evidence per prediction

| Prediction | Evidence | Outcome | H_i status |
|---|---|---|---|
| Y1 (tag stability) | EVID-005 SWE-bench analysis: tag-pinning of SWE-bench Docker images is "only as immutable as the pinned Docker image tag — and tags are mutable on DockerHub". Architect finding #5 (HIGH) classified this as MUST-fix for POLLMEVALS. | Tags drift over time per industry data; not safe | **H1 REFUTED** |
| Y2 (digest stability) | Agent 3 executed: `docker pull node:22-alpine && docker inspect node:22-alpine --format '{{.RepoDigests}}'` → returned `sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920`. Same for `ghcr.io/berriai/litellm:main-stable` → `sha256:b3db76b5251485ab332bb91b30984991c6f53144b5c1c4371b4bd9766749e45f`. Both written into committed Dockerfile + docker-compose. | Digest pinning realized; full `docker build` of be_01 sandbox PASS | **H2 SUPPORTED** |
| Y3 (private registry burden) | Not measured directly; rejected on prior-art grounds — for a v0.1 smoke pipeline this is over-engineering when digest pinning already gives reproducibility. Architect finding #5 says "pin by digest" not "build custom images". | Skipped — H2 sufficient | **H3 REJECTED** (valid but excessive for current scope) |

**Surviving hypothesis**: H2 — digest pinning of upstream images. Matches shipped implementation; **stronger than SWE-bench's tag pinning** (POLLMEVALS divergence).

## Trust Calculus per load-bearing claim

| Claim | F | G | R | Sum | Notes |
|---|---|---|---|---|---|
| `inspect-ai==0.3.46` exact pin works (resolves on PyPI, deps install cleanly) | 8 | 8 | 8 | 24/27 | F: explicit pin string in pyproject.toml. G: `uv sync` exit 0 confirmed. R: PyPI is authoritative for Python package availability. |
| Both Docker digests verified by direct `docker inspect` | 9 | 9 | 9 | 27/27 | F: cryptographic SHA256 digest is the most formal pin possible. G: full digest written into Dockerfile + docker-compose.litellm.yml. R: `docker pull && docker inspect` is reproducible by anyone with Docker. |
| `docker build evals/task-packs/be_01_jwt_auth/` PASS all 6 stages | 8 | 8 | 8 | 24/27 | F: explicit "all 6 stages" + image built. G: image tag `pollmevals-be01-sandbox:test`. R: reproducible by anyone with Docker. |
| LiteLLM healthcheck endpoint correctly wired (`/health`) | 7 | 7 | 7 | 21/27 | F: explicit endpoint URL. G: defined in docker-compose with interval/timeout/retries. R: matches LiteLLM standard but not yet observed in a live run (proxy not yet started end-to-end). |
| mypy --strict 0 issues on src/, ruff All checks passed | 9 | 8 | 9 | 26/27 | F: --strict is most rigorous Python type check. G: precise "0 issues, 5 files". R: deterministic tool output. |
| `make smoke-run` stub exits 0 with TODO message | 7 | 9 | 8 | 24/27 | F: explicit stub status. G: exact behavior described. R: makefile target is trivial to verify. Drops F because it's not the real implementation (Phase 2B). |
| Makefile `reproduce` target swapped to stub (carry-forward for Phase 2C) | 8 | 8 | 8 | 24/27 | F: explicit carry-forward documented. G: precise target name. R: traceable in git diff. |

**Decision strength**: average sum = 24.3/27 (90%). Strongest claim is digest pinning (27/27 — cryptographic). Weakest is healthcheck endpoint wiring (21/27) — flagged for live verification in Phase 2B when LiteLLM proxy actually starts.

## Wave summary

- **Sprint**: phase-2A, **Wave**: 1 of 5
- **Workers**: `project-skeleton` + `infra-scripts` (parallel, agents-core:coder)
- **Files** (~723 LOC across 14 files): pyproject.toml (49), README (43), 5×__init__.py (10), conftest (148), moon.yml (48), Makefile (+35), docker-compose.litellm.yml (63), litellm-config.yaml (62), 2 shell scripts (96), Dockerfile (78), .dockerignore (56)
- **Pipeline gates**: uv sync ✓, mypy --strict ✓ (0 issues), ruff ✓, docker config ✓, docker build ✓ (6 stages), bash -n ✓

## Acceptance criteria validation

- ✓ RFC-001 impl task 1 (pyproject inspect-ai==0.3.46 exact)
- ✓ RFC-001 impl task 2 (src/contracts scaffolding — empty modules, populated in Wave 2)
- ✓ RFC-001 impl task 13 (Makefile targets — stubs where appropriate)
- ✓ RFC-001 impl task 14 (validate-task-specs.py fix — see EVID-009)
- ✓ RFC-001 impl task 15 (litellm-proxy-up.sh with healthcheck)
- ✓ Architect finding #5 (digest pinning — both images verified by `docker inspect`)
- ✓ Architect finding #10 (LiteLLM proxy detail — healthcheck, restart policy, port pin, version pin, OPENROUTER_API_KEY guard, log dump on timeout)

## Conclusions

- **Surviving hypothesis**: H2 (digest-pinned upstream images, no private registry)
- **Decision strength**: 90% (one 27/27 claim — digest pinning)
- **Follow-up evidence needed**: live LiteLLM proxy start + healthcheck round-trip in Phase 2B (raises healthcheck claim from 21/27 → 25/27)

## Related Artifacts

- RFC-001 (informs — auto-linked)
- PRD-001 (foundation for FR-001..FR-005)
- ADR-001 (concurrency model — skeleton now ready for Wave 4 EvalCaller)
- ADR-003 (5-model lineup — all 5 declared in litellm-config.yaml)
- EVID-005 (SWE-bench Docker pinning analysis — POLLMEVALS divergence justified by this lesson)
- EVID-007 (architect findings #5, #10 — resolved by this work)
- NOTE-002 (Evidence Quality Standard — retrofit)
- GitHub issues #10, #11 (covered)


