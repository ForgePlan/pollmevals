# 04 — Stack Decision

## Decision

Use a hybrid stack:

| Layer | Stack |
|---|---|
| Site | Next.js 15 + Tailwind + shadcn/ui |
| Public API | TypeScript + Hono first, MoleculerJS optional |
| Eval plane | Python 3.12+ + MoleculerPy |
| Eval framework | Inspect AI |
| Inference gateway | LiteLLM proxy |
| Service bus | NATS |
| Queue/cache | Redis/BullMQ or NATS JetStream |
| Database | Postgres |
| Raw artifact storage | Cloudflare R2 / S3-compatible storage |
| Sandbox MVP | Docker rootless/no-network/read-only/tmpfs |
| Sandbox future | gVisor/Kata/Firecracker |
| Rust | Future specialized runtime modules only |

## Why not Rust first

Rust is valuable for hardened execution, not for early methodology iteration.

The first bottlenecks are:

- task quality;
- run reproducibility;
- judge calibration;
- stack adapter fairness;
- artifact schema;
- scoring validity;
- content contamination detection.

None of these are solved faster by making the orchestrator Rust-first.

## Where Rust belongs later

| Module | Trigger |
|---|---|
| `sandbox-runner` | community tasks or untrusted evaluators appear |
| `trace-normalizer` | agent CLI traces become large and heterogeneous |
| `artifact-hasher` | artifact volume becomes high |
| `firecracker-runner` | enterprise/security requirements appear |
| `worker-supervisor` | Python workers need hardened lifecycle management |

## Moleculer boundary

MoleculerPy should power internal eval execution services. Public API should not depend on MoleculerPy maturity during v0.1.

```text
Public product plane:
  Next.js / Hono / MoleculerJS / Postgres

Eval execution plane:
  MoleculerPy / Python / Inspect AI / LiteLLM / Docker sandbox
```

## Versioning rule

Pin everything:

- MoleculerPy version;
- MoleculerJS version if used;
- Inspect AI version;
- LiteLLM version;
- vLLM version;
- Node version;
- Python version;
- task version;
- stack adapter version;
- methodology version.
