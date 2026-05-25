---
depth: standard
id: NOTE-007
kind: note
last_modified_at: 2026-05-25T18:51:30.049815+00:00
last_modified_by: claude-code/2.1.150
links:
- target: PRD-001
  relation: informs
- target: RFC-001
  relation: informs
status: active
title: Evaluator architecture split — static (no sandbox) vs dynamic (Docker) on execution boundary
---

# NOTE-007: Evaluator architecture split — static (no sandbox) vs dynamic (Docker) on execution boundary

## Context

Phase 2D Slice 1 shipped 3 evaluators (lint, complexity, secret_scan) via the same straightforward pattern — `subprocess.run` (or library Python API) invoked **directly on the host** with the candidate's `raw_output` directory as input. No sandbox, no isolation. This worked because all three tools **only parse** the artifact:

| Slice 1 evaluator | Underlying tool | Action |
|---|---|---|
| `LintEvaluator` | `ruff` (Py) / `eslint` (TS) | static analysis — read code, emit findings, exit |
| `ComplexityEvaluator` | `lizard` Python API | AST walk — count branches, no execution |
| `SecretScanEvaluator` | `gitleaks dir` | regex scan over bytes |

None of them **runs** the candidate's code. Static analysis only.

Phase 2D Slice 2 was originally scoped as «3 more evaluators of the same shape» (correctness, coverage, type_safety) — but research during the Slice 2 autorun (2026-05-25) surfaced a structural difference: **two of those three metrics REQUIRE running the code**.

| Slice 2 candidate metric | Tool | Action | Sandbox? |
|---|---|---|---|
| `type_safety` | `tsc --noEmit --strict --pretty false` | type-check, no emit, no execution | **No** — pure static analysis |
| `correctness` | `vitest run --reporter=json` | **runs the test suite** against candidate code | **Yes** — arbitrary code execution |
| `coverage` | `vitest run --coverage` (built-in v8) | **runs tests AND instruments** them via v8 | **Yes** — arbitrary code execution |

The frozen security policy (`docs/02-methodology/security-sandbox.md` + `docs/04-runbook/09-sandbox-security.md`) says: «Community-submitted evaluators must never run directly on the host. They must pass static inspection and execute only inside sandbox.» Code-execution evaluators fall under this rule; static-analysis evaluators don't.

External validation (WebSearch 2026-05-25):

- **Inspect AI** (the framework POLLMEVALS uses for the candidate side) ships sandboxing for Docker / K8s / Proxmox — same architectural decision, same boundary.
- Industry warning (multiple 2025-2026 sources, e.g. arxiv 2603.02277, dev.to 2026 "4 ways to sandbox untrusted code"): **Docker alone is insufficient for hardened sandboxing of untrusted code.** Container escape from a compromised process gives host access. Production-grade isolation requires gVisor, Kata Containers, or Firecracker microVMs. Our roadmap (sandbox-security.md «v0.1 Docker rootless → v0.3 gVisor / Kata → v1.0 Firecracker») is aligned with this consensus.

## The rule

Every evaluator declares its **execution boundary** explicitly in its docstring or `Evaluator` metadata:

- **Static** — the evaluator only parses / analyses bytes. It MUST NOT shell out anything that runs code. `subprocess.run` is permitted for tools like `tsc`, `ruff`, `lizard`, `gitleaks`. Hosts the call directly; no sandbox.
- **Dynamic** — the evaluator must run the candidate's code (tests, instrumentation, type-check that triggers macro expansion, …). It MUST go through the `SandboxRun` helper (Slice 2+ work) which enforces the frozen policy: no network, read-only rootfs, tmpfs, memory/CPU/PID/file-size limits, `cap_drop ALL`, `no-new-privileges:true`, hard timeout.

When a future evaluator is uncertain (e.g. a plugin-mode linter that can execute custom plugins), default to **dynamic** — the sandbox path is safe for static workloads but the host path is unsafe for dynamic ones.

## Examples (current code)

Static evaluators (Slice 1 — already shipped):

- `apps/eval-core-py/src/evaluators/lint_evaluator.py` — invokes `ruff check --output-format json` / `eslint --format=json` directly on the host.
- `apps/eval-core-py/src/evaluators/complexity_evaluator.py` — calls `lizard.analyze_file()` Python API, no subprocess.
- `apps/eval-core-py/src/evaluators/secret_scan_evaluator.py` — invokes `gitleaks dir` subcommand.

Static evaluator (Slice 2 — TypeSafetyEvaluator, this PR):

- `apps/eval-core-py/src/evaluators/type_safety_evaluator.py` (planned) — invokes `tsc --noEmit --strict --pretty false` directly on the host. **No sandbox**, identical pattern to Slice 1.

Dynamic evaluators (Slice 2 — deferred to a dedicated Docker-setup session):

- `correctness_evaluator.py` — vitest. Must use SandboxRun.
- `coverage_evaluator.py` — vitest --coverage. Must use SandboxRun (shares vitest output via cache OR own invocation).

## Promotion criterion

This Note is a "captured pattern" for now. Promote to a full **ADR** when:

- A second confirming case lands beyond Slice 2 (e.g. Slice 3+ introduces a third evaluator and the static/dynamic boundary remains the load-bearing distinction).
- OR a contradicting case appears (a "static" evaluator turns out to need sandboxing, or a "dynamic" tool can be safely run on host — would force the rule to be refined).

Until then, the pattern is reversible: a single re-orgization can move all evaluators behind a uniform sandbox if needed.

## Related Artifacts

- `PRD-001` — smoke run that consumes all evaluators
- `RFC-001` — orchestrator implementation plan that defines the Evaluator Protocol
- `EVID-025` — RFC-002 Slice E integration tests (precedent for "single autorun ships scoped slice")
- `docs/02-methodology/security-sandbox.md` v0.1.0 frozen — sandbox policy
- `docs/04-runbook/09-sandbox-security.md` — sandbox runtime spec (Docker rootless v0.1 → gVisor/Kata v0.3 → Firecracker v1.0)
- Future ADR-007 (reserved if this Note graduates)





