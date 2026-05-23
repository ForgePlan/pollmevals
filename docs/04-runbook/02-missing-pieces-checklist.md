# 07 — Missing pieces checklist

This file tracks the parts that must be implemented before moving from a research scaffold to a reliable public product.

## P0 before first real smoke

- [ ] Real LiteLLM model call client.
- [ ] Model registry loader.
- [ ] Task registry validator.
- [ ] Artifact content hashing.
- [ ] Run manifest schema validation.
- [ ] Evaluator sandbox timeout.
- [ ] Error taxonomy.

## P0 before public methodology post

- [ ] Methodology version `v0.1.0` frozen.
- [ ] Scoring weights frozen.
- [ ] Judge policy frozen.
- [ ] Task lifecycle policy frozen.
- [ ] Conflict disclosure policy frozen.

## P1 before Phase 2 ablation

- [ ] Stack adapter spec implemented.
- [ ] CLI execution trace captured.
- [ ] Tool call and file mutation trace captured.
- [ ] Token/cost overhead per scaffolding layer.
- [ ] Same task budget policy.

## P2 before community submissions

- [ ] Task proposal validator.
- [ ] License/IP checklist.
- [ ] Contamination checker.
- [ ] gVisor or Firecracker sandbox.
- [ ] Maintainer review queue.
