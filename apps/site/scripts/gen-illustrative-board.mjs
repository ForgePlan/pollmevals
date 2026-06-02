/**
 * Generate the ILLUSTRATIVE board dataset (public/board.illustrative.json).
 *
 * Not real run data — a preview built from explicit, reviewable assumptions so
 * the harness × model × task design can be evaluated before the executor
 * produces real multi-harness scored runs. Every number below encodes a stated
 * belief about how scaffolding interacts with model strength; tune the tables,
 * re-run, the JSON regenerates deterministically.
 *
 *   node apps/site/scripts/gen-illustrative-board.mjs
 *
 * The THESIS this dataset must make legible:
 *  - scaffolding lifts WEAK models more than strong ones (diminishing returns at the top);
 *  - a cheap model + deep scaffold reaches — and on quality-per-$ beats — an expensive bare model;
 *  - different task types have different winners (backend rewards validator loops,
 *    frontend rewards a strong base model, docs compress the field).
 */

import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "public", "board.illustrative.json");

// ── Models (cheap → expensive) ──────────────────────────────────────────────
const MODELS = [
  {
    model_id: "qwen-3-14b",
    name: "Qwen 3 14B",
    tier: "cheap",
    base: 4.3,
    ppm: 0.12,
  },
  {
    model_id: "llama-3-3-70b",
    name: "Llama 3.3 70B",
    tier: "cheap",
    base: 4.8,
    ppm: 0.32,
  },
  {
    model_id: "gemini-3-flash",
    name: "Gemini 3 Flash",
    tier: "mid",
    base: 5.4,
    ppm: 0.42,
  },
  {
    model_id: "gpt-5-mini",
    name: "GPT-5 mini",
    tier: "mid",
    base: 6.1,
    ppm: 0.6,
  },
  {
    model_id: "claude-sonnet-4-6",
    name: "Claude Sonnet 4.6",
    tier: "frontier",
    base: 6.9,
    ppm: 4.5,
  },
];

// ── Harnesses (L0 → deep). `lift` = quality added at a NEUTRAL base; `weakBonus`
//    = extra lift that decays as the base model gets stronger (scaffolding helps
//    weak models more). `calls` ≈ model invocations (cost multiplier); `judge`
//    = flat judge-panel cost added when scored. `compat` lets a vendor harness
//    penalise foreign models (claude-code on qwen broke in our real spikes). ──
const HARNESSES = [
  {
    stack_id: "raw-llm",
    name: "Raw LLM",
    level: 0,
    family: "baseline",
    layers: ["L0_bare_llm"],
    lift: 0,
    weakBonus: 0,
    calls: 1,
    judge: 0.0,
    compat: {},
  },
  {
    stack_id: "aider",
    name: "Aider",
    level: 2,
    family: "agnostic",
    layers: ["L1_system_prompt", "L2_tools", "L4_file_memory"],
    lift: 1.5,
    weakBonus: 0.9,
    calls: 6,
    judge: 0.04,
    compat: {},
  },
  {
    stack_id: "claude-code-basic",
    name: "Claude Code Basic",
    level: 2,
    family: "vendor",
    layers: ["L1_system_prompt", "L2_tools"],
    lift: 1.8,
    weakBonus: 0.6,
    calls: 8,
    judge: 0.04,
    // vendor-tuned: native models gain, foreign models suffer (translation).
    compat: {
      "qwen-3-14b": -2.6,
      "llama-3-3-70b": -0.8,
      "claude-sonnet-4-6": 0.6,
    },
  },
  {
    stack_id: "forgeplan-framework",
    name: "ForgePlan Framework",
    level: 8,
    family: "framework",
    layers: [
      "L3_skills",
      "L4_file_memory",
      "L6_subagents",
      "L7_validator",
      "L8_framework",
    ],
    lift: 2.6,
    weakBonus: 1.5,
    calls: 15,
    judge: 0.04,
    compat: {},
  },
];

// ── Per-task character: how each task reweights scaffold vs base strength. ────
//   scaffoldMul scales the harness lift; baseMul scales how much raw base ability
//   matters; spread compresses (docs) or widens the field.
const TASKS = {
  be_01_jwt_auth: { scaffoldMul: 1.2, baseMul: 0.9, jitter: 0.15 }, // backend: validator loops pay off
  fe_01_multistep_form: { scaffoldMul: 0.8, baseMul: 1.25, jitter: 0.2 }, // frontend: strong base wins
  doc_01_cli_readme: { scaffoldMul: 0.7, baseMul: 0.8, jitter: 0.1 }, // docs: compressed field
};

const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const round = (x, d = 2) => Math.round(x * 10 ** d) / 10 ** d;
// deterministic pseudo-jitter from a string seed (no Math.random — reproducible)
function seeded(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  // map to [-1, 1]
  return ((h >>> 0) / 4294967295) * 2 - 1;
}

function baseQuality(model, harness) {
  // weakBonus decays with base strength: full at base=4, ~0 at base=8.
  const weakness = clamp((8 - model.base) / 4, 0, 1);
  const compat = harness.compat[model.model_id] ?? 0;
  const q = model.base + harness.lift + harness.weakBonus * weakness + compat;
  return clamp(q, 0, 10);
}

function taskScore(model, harness, taskId) {
  const t = TASKS[taskId];
  const weakness = clamp((8 - model.base) / 4, 0, 1);
  const scaffold =
    harness.lift * t.scaffoldMul + harness.weakBonus * weakness * t.scaffoldMul;
  const compat = harness.compat[model.model_id] ?? 0;
  const q =
    (model.base - 5) * t.baseMul +
    5 +
    scaffold +
    compat +
    seeded(`${model.model_id}|${harness.stack_id}|${taskId}`) * t.jitter;
  return clamp(round(q, 1), 0, 10);
}

function cellCost(model, harness, taskId) {
  // tokens-per-task ~ constant; cost ≈ ppm × calls × ~12k tok/Mtok + judge.
  const tokFactor = 0.012; // ~12k tokens per call in M-tokens
  const jit =
    1 + seeded(`cost|${model.model_id}|${harness.stack_id}|${taskId}`) * 0.08;
  const cost = model.ppm * harness.calls * tokFactor * jit + harness.judge;
  return round(cost, 4);
}

function passHatK(model, harness) {
  // reliability rises with quality; broken vendor pairings are flaky.
  const q = baseQuality(model, harness);
  const compatPenalty = (harness.compat[model.model_id] ?? 0) < -1 ? 0.4 : 0;
  return clamp(round((q - 3) / 7 - compatPenalty, 2), 0, 1);
}

const taskIds = Object.keys(TASKS);

const cells = [];
for (const harness of HARNESSES) {
  for (const model of MODELS) {
    const per_task = {};
    for (const taskId of taskIds) {
      per_task[taskId] = {
        score: taskScore(model, harness, taskId),
        cost_usd: cellCost(model, harness, taskId),
        pass_hat_k: passHatK(model, harness),
      };
    }
    const scores = taskIds.map((t) => per_task[t].score);
    const costs = taskIds.map((t) => per_task[t].cost_usd);
    const mean_score = round(
      scores.reduce((a, b) => a + b, 0) / scores.length,
      1
    );
    const mean_cost = round(costs.reduce((a, b) => a + b, 0) / costs.length, 4);
    cells.push({
      model_id: model.model_id,
      stack_id: harness.stack_id,
      mean_score,
      mean_cost_usd: mean_cost,
      mean_latency_ms: Math.round(
        2000 +
          harness.calls * 900 +
          seeded(`lat|${model.model_id}|${harness.stack_id}`) * 600
      ),
      pass_hat_k: passHatK(model, harness),
      quality_per_dollar:
        mean_cost > 0 ? round(mean_score / mean_cost, 1) : null,
      per_task,
      on_frontier: false, // computed client-side (frontierKeys)
    });
  }
}

const board = {
  run_hash: "sha256:illustrative-preview-not-a-real-run",
  run_type: "illustrative",
  methodology_version: "v0.1.0",
  region: "eu-central",
  scored: true,
  illustrative: true,
  solved_threshold: 6.0,
  harnesses: HARNESSES.map(({ stack_id, name, level, family, layers }) => ({
    stack_id,
    name,
    level,
    family,
    layers,
  })),
  models: MODELS.map(({ model_id, name, tier }) => ({ model_id, name, tier })),
  tasks: taskIds,
  cells,
};

writeFileSync(OUT, JSON.stringify(board, null, 2) + "\n");

// quick sanity print of the thesis
const cheapScaffold = cells.find(
  (c) => c.model_id === "qwen-3-14b" && c.stack_id === "forgeplan-framework"
);
const dearBare = cells.find(
  (c) => c.model_id === "claude-sonnet-4-6" && c.stack_id === "raw-llm"
);
console.log(`Wrote ${OUT}`);
console.log(
  `  ${cells.length} cells (${HARNESSES.length} harnesses × ${MODELS.length} models)`
);
console.log(
  `  THESIS check — qwen+forgeplan: score ${cheapScaffold.mean_score} @ $${cheapScaffold.mean_cost_usd} (q/$ ${cheapScaffold.quality_per_dollar})`
);
console.log(
  `              vs sonnet+raw-llm: score ${dearBare.mean_score} @ $${dearBare.mean_cost_usd} (q/$ ${dearBare.quality_per_dollar})`
);
