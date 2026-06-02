import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildMatrix,
  frontierKeys,
  perTaskWinners,
  scaffoldingLift,
  bestCell,
  metricRange,
  type Board,
  type Cell,
} from "../src/lib/board.js";

function cell(
  model: string,
  stack: string,
  score: number | null,
  cost: number,
  perTask: Record<string, number | null> = {}
): Cell {
  return {
    model_id: model,
    stack_id: stack,
    mean_score: score,
    mean_cost_usd: cost,
    mean_latency_ms: 5000,
    pass_hat_k: score === null ? null : 0.8,
    quality_per_dollar: score === null || cost === 0 ? null : score / cost,
    per_task: Object.fromEntries(
      Object.entries(perTask).map(([t, s]) => [
        t,
        { score: s, cost_usd: cost, pass_hat_k: 0.8 },
      ])
    ),
    on_frontier: false,
  };
}

function board(cells: Cell[]): Board {
  return {
    run_hash: "x",
    run_type: "illustrative",
    methodology_version: "v0.1.0",
    region: "eu-central",
    scored: true,
    illustrative: true,
    solved_threshold: 6,
    harnesses: [
      {
        stack_id: "raw-llm",
        name: "Raw LLM",
        level: 0,
        family: "baseline",
        layers: [],
      },
      {
        stack_id: "forgeplan-framework",
        name: "ForgePlan",
        level: 8,
        family: "framework",
        layers: [],
      },
    ],
    models: [
      { model_id: "qwen", name: "Qwen", tier: "cheap" },
      { model_id: "sonnet", name: "Sonnet", tier: "frontier" },
    ],
    tasks: ["be_01", "fe_01"],
    cells,
  };
}

test("buildMatrix orders rows by level desc, cols by tier (cheap first)", () => {
  const b = board([
    cell("qwen", "raw-llm", 4, 0.01),
    cell("qwen", "forgeplan-framework", 8, 0.05),
    cell("sonnet", "raw-llm", 7, 0.04),
    cell("sonnet", "forgeplan-framework", 9, 0.7),
  ]);
  const m = buildMatrix(b);
  assert.equal(m.rows[0]?.stack_id, "forgeplan-framework"); // deepest first
  assert.equal(m.rows[1]?.stack_id, "raw-llm");
  assert.equal(m.cols[0]?.model_id, "qwen"); // cheap first
  assert.equal(m.cols[1]?.model_id, "sonnet");
  assert.equal(m.cellAt(m.rows[0]!, m.cols[0]!)?.mean_score, 8);
});

test("frontierKeys: cheap-scaffold and dear-bare can both be on the frontier", () => {
  // qwen+forgeplan (8 @ 0.05) and sonnet+raw (7 @ 0.04): neither dominates
  // (qwen better but dearer). sonnet+forgeplan (9 @ 0.7) on frontier (best quality).
  const b = board([
    cell("qwen", "raw-llm", 4, 0.01),
    cell("qwen", "forgeplan-framework", 8, 0.05),
    cell("sonnet", "raw-llm", 7, 0.04),
    cell("sonnet", "forgeplan-framework", 9, 0.7),
  ]);
  const f = frontierKeys(b);
  assert.equal(f.has("qwen::forgeplan-framework"), true);
  assert.equal(f.has("sonnet::raw-llm"), true);
  assert.equal(f.has("sonnet::forgeplan-framework"), true);
  // qwen+raw (4 @ 0.01) is cheapest — also frontier (nothing cheaper).
  assert.equal(f.has("qwen::raw-llm"), true);
});

test("frontierKeys excludes a dominated stack", () => {
  // mid (6 @ 0.10) is dominated by good (8 @ 0.05): cheaper AND better.
  const b = board([
    cell("good", "forgeplan-framework", 8, 0.05),
    cell("mid", "raw-llm", 6, 0.1),
  ]);
  const f = frontierKeys(b);
  assert.equal(f.has("good::forgeplan-framework"), true);
  assert.equal(f.has("mid::raw-llm"), false);
});

test("perTaskWinners: different tasks, different winners", () => {
  const b = board([
    cell("qwen", "forgeplan-framework", 8, 0.05, { be_01: 9, fe_01: 6 }), // wins backend
    cell("sonnet", "raw-llm", 7, 0.04, { be_01: 6, fe_01: 9 }), // wins frontend
  ]);
  const w = perTaskWinners(b);
  const be = w.find((x) => x.task === "be_01");
  const fe = w.find((x) => x.task === "fe_01");
  assert.equal(be?.cell.model_id, "qwen");
  assert.equal(fe?.cell.model_id, "sonnet");
});

test("scaffoldingLift: per model, points ordered L0 → L8", () => {
  const b = board([
    cell("qwen", "raw-llm", 4, 0.01),
    cell("qwen", "forgeplan-framework", 8, 0.05),
    cell("sonnet", "raw-llm", 7, 0.04),
    cell("sonnet", "forgeplan-framework", 9, 0.7),
  ]);
  const lift = scaffoldingLift(b);
  const qwen = lift.find((s) => s.model.model_id === "qwen");
  assert.equal(qwen?.points[0]?.harness.level, 0); // L0 first
  assert.equal(qwen?.points[1]?.harness.level, 8);
  // the climb: 4 → 8 (+4 for the weak model)
  assert.equal(qwen?.points[0]?.cell.mean_score, 4);
  assert.equal(qwen?.points[1]?.cell.mean_score, 8);
});

test("bestCell + metricRange", () => {
  const b = board([
    cell("qwen", "forgeplan-framework", 8, 0.05),
    cell("sonnet", "raw-llm", 7, 0.04),
  ]);
  assert.equal(bestCell(b, "mean_score")?.model_id, "qwen"); // 8 > 7
  assert.equal(bestCell(b, "mean_cost_usd")?.model_id, "sonnet"); // cheapest
  const r = metricRange(b, "mean_score");
  assert.equal(r.min, 7);
  assert.equal(r.max, 8);
});
