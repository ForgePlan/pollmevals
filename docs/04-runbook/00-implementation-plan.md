# 05 — Implementation plan

## Phase 0 — Repository and local demo

1. Install Python eval-core package.
2. Run local demo without external LLM calls.
3. Validate JSON schemas.
4. Generate first local run manifest.

## Phase 1 — Real model calls

1. Start LiteLLM with local config.
2. Add one cloud model and one local Ollama model.
3. Replace deterministic demo output with LiteLLM calls.
4. Persist raw model outputs.

## Phase 2 — Evaluator sandbox

1. Build evaluator Docker image.
2. Add evaluator command execution.
3. Capture stdout/stderr/exit code/timeouts.
4. Score `be_01` with tests, typecheck and lint.

## Phase 3 — Judge panel

1. Normalize outputs.
2. Disable self-judging.
3. Run 3 judges first, then 5.
4. Add calibration samples.
5. Publish judge agreement metrics.

## Phase 4 — Public result surfaces

1. API reads completed run manifest.
2. Site renders run page.
3. Site renders leaderboard.
4. Blog post links to immutable run.

## Phase 5 — Scaffolding ablation

1. Implement stack adapter spec.
2. Run L0 → L7 on hard task.
3. Publish quality lift and cost overhead.
