# 01 — Product requirements

## Personas

| Persona | Need | Product surface |
|---|---|---|
| Engineering lead | Choose LLM stack for team | leaderboard, compare, methodology, runs |
| Indie founder | Find cheap but effective stack | free leaderboard, blog, reproducible examples |
| Researcher / analyst | Raw data and reproducibility | datasets, API, run manifests |
| Model creator | Honest public evaluation | model page, disclosure, sponsored fast-track later |

## MVP scope

### v0.1 smoke

- 3 tasks: `be_01`, `fe_01`, `doc_01`.
- 5 models.
- 3 seeds.
- Automatic metrics only in first smoke.
- Local artifacts.
- No public site dependency.

### v0.2 first publishable run

- Judge panel enabled.
- Calibration enabled.
- Public methodology page.
- `/runs/[hash]` equivalent data available.
- First blog post.

### v0.3 scaffolding ablation

- 2 hard tasks.
- Stack adapter contract.
- L0 → L7 ablation.
- Cost and latency overhead per layer.

## Hard requirements

1. Every completed run is immutable.
2. Every task is versioned.
3. Every public score has traceable evidence.
4. Every judge run has self-judging disabled.
5. Every public result includes cost, token usage and version snapshot.
6. Every task in active pool has calibration examples.
7. Every evaluator executes in a sandbox.
8. Every methodology change creates a new methodology version.
