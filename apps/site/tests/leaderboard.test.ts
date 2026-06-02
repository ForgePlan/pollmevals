import { test } from "node:test";
import assert from "node:assert/strict";
import { computeFrontier, type Leaderboard } from "../src/lib/leaderboard.js";
import {
  formatUsd,
  formatLatency,
  formatPct,
  formatScore,
  shortHash,
} from "../src/lib/format.js";

function entry(
  model: string,
  cost: string,
  latency: number,
  score: number | null
) {
  return {
    model_id: model,
    stack_id: "raw-llm",
    n_evals: 9,
    n_scored: 9,
    n_failed: 0,
    n_tasks: 3,
    n_seeds: 3,
    total_cost_usd: cost,
    mean_cost_usd: cost,
    total_tokens_in: 100,
    total_tokens_out: 500,
    mean_latency_ms: latency,
    p50_latency_ms: latency,
    mean_score: score,
    pass_at_1: score === null ? null : score >= 6 ? 1 : 0,
    pass_at_k: score === null ? null : 1,
    pass_hat_k: score === null ? null : 1,
    flaky: score === null ? null : 0,
  };
}

function lb(scored: boolean, entries: ReturnType<typeof entry>[]): Leaderboard {
  return {
    run_hash: "sha256:" + "a".repeat(64),
    run_type: "smoke",
    methodology_version: "v0.1.0",
    region: "eu-central",
    scored,
    solved_threshold: 6,
    n_models: entries.length,
    n_stacks: 1,
    n_tasks: 3,
    entries,
  };
}

test("computeFrontier (scored): cheaper-and-better dominates", () => {
  // A: cheap + high quality (should be frontier); B: dear + low (dominated)
  const board = lb(true, [
    entry("A", "0.10", 1000, 9),
    entry("B", "0.50", 1000, 4),
  ]);
  const pts = computeFrontier(board);
  const a = pts.find((p) => p.entry.model_id === "A");
  const b = pts.find((p) => p.entry.model_id === "B");
  assert.equal(a?.onFrontier, true);
  assert.equal(b?.onFrontier, false);
});

test("computeFrontier (scored): cheap-low and dear-high both on frontier (tradeoff)", () => {
  const board = lb(true, [
    entry("cheap", "0.10", 1000, 5),
    entry("dear", "0.50", 1000, 9),
  ]);
  const pts = computeFrontier(board);
  assert.equal(
    pts.every((p) => p.onFrontier),
    true
  ); // neither dominates the other
});

test("computeFrontier (unscored): lower cost AND lower latency dominates", () => {
  const board = lb(false, [
    entry("fast", "0.10", 1000, null),
    entry("slow", "0.10", 5000, null),
  ]);
  const pts = computeFrontier(board);
  assert.equal(pts.find((p) => p.entry.model_id === "fast")?.onFrontier, true);
  assert.equal(pts.find((p) => p.entry.model_id === "slow")?.onFrontier, false);
});

test("format helpers", () => {
  assert.equal(formatUsd("0"), "$0");
  assert.equal(formatUsd("0.0067"), "$0.0067");
  assert.equal(formatUsd("2.5"), "$2.50");
  assert.equal(formatLatency(3320), "3.3s");
  assert.equal(formatLatency(847), "847ms");
  assert.equal(formatPct(0.358), "36%");
  assert.equal(formatPct(null), "—");
  assert.equal(formatScore(null), "—");
  assert.equal(formatScore(7.25), "7.3");
  // shortHash: strip "sha256:", then first8…last5 of the body
  assert.equal(shortHash("sha256:abcdef0123456789xyz"), "abcdef01…89xyz");
});
