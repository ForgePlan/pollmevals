/**
 * The "Board" — the rich, harness-centric data model the public site renders.
 *
 * POLLMEVALS evaluates STACKS = (model × harness/scaffolding), not bare models.
 * The board is shaped so the central question — *which harness, with which model,
 * is best, and for which task* — is answerable at a glance:
 *
 *   harnesses  → rows of the matrix (ordered L0 → L8 by scaffolding depth)
 *   models     → columns (ordered cheap → expensive)
 *   cells      → one (model × harness) stack, with per-task breakdown
 *
 * Honesty: `illustrative: true` marks a preview dataset built to demonstrate the
 * design before real multi-harness scored runs exist (the executor that runs
 * non-raw harnesses is a separate, cost-gated build). Real runs replace it.
 */

export interface Harness {
  stack_id: string;
  name: string; // display, e.g. "ForgePlan Framework"
  /** Max scaffolding level present (0-8) — drives row order. */
  level: number;
  /** Active L-layers, e.g. ["L1_system_prompt","L2_tools"]. */
  layers: string[];
  /** baseline | agnostic | vendor | framework — for grouping/legend. */
  family: "baseline" | "agnostic" | "vendor" | "framework";
}

export interface ModelRef {
  model_id: string;
  name: string;
  /** cheap | mid | frontier — drives column order (cheap left). */
  tier: "cheap" | "mid" | "frontier";
}

export interface TaskScore {
  score: number | null; // 0-10
  cost_usd: number;
  pass_hat_k: number | null;
}

export interface Cell {
  model_id: string;
  stack_id: string;
  /** Overall mean across tasks (null on unscored). */
  mean_score: number | null;
  mean_cost_usd: number;
  mean_latency_ms: number;
  pass_hat_k: number | null;
  /** quality ÷ cost — the thesis metric (null when unscored or cost 0). */
  quality_per_dollar: number | null;
  per_task: Record<string, TaskScore>;
  on_frontier: boolean;
}

export interface Board {
  run_hash: string;
  run_type: string;
  methodology_version: string;
  region: string;
  scored: boolean;
  illustrative: boolean;
  solved_threshold: number;
  harnesses: Harness[];
  models: ModelRef[];
  tasks: string[];
  cells: Cell[];
}

// ---------------------------------------------------------------------------
// Lookups + derivations
// ---------------------------------------------------------------------------

const key = (modelId: string, stackId: string) => `${modelId}::${stackId}`;

export function cellMap(board: Board): Map<string, Cell> {
  return new Map(board.cells.map((c) => [key(c.model_id, c.stack_id), c]));
}

/** A matrix in render order: rows = harnesses (deepest scaffold first), cols = models (cheap first). */
export interface MatrixView {
  rows: Harness[]; // ordered: highest level first (so scaffold climbs downward visually = top)
  cols: ModelRef[]; // ordered: cheapest first
  cellAt: (h: Harness, m: ModelRef) => Cell | undefined;
}

export function buildMatrix(board: Board): MatrixView {
  const rows = [...board.harnesses].sort((a, b) => b.level - a.level);
  const tierRank = { cheap: 0, mid: 1, frontier: 2 } as const;
  const cols = [...board.models].sort(
    (a, b) => tierRank[a.tier] - tierRank[b.tier]
  );
  const map = cellMap(board);
  return {
    rows,
    cols,
    cellAt: (h, m) => map.get(key(m.model_id, h.stack_id)),
  };
}

/** What a matrix cell is colored by. */
export type Metric = "quality_per_dollar" | "mean_score" | "mean_cost_usd";

export function metricValue(cell: Cell, metric: Metric): number | null {
  if (metric === "mean_cost_usd") return cell.mean_cost_usd;
  return cell[metric];
}

/** The single best stack under a metric (max, or min for cost). */
export function bestCell(board: Board, metric: Metric): Cell | null {
  const valued = board.cells
    .map((c) => ({ c, v: metricValue(c, metric) }))
    .filter((x): x is { c: Cell; v: number } => x.v !== null);
  if (valued.length === 0) return null;
  const pick =
    metric === "mean_cost_usd"
      ? valued.reduce((a, b) => (b.v < a.v ? b : a))
      : valued.reduce((a, b) => (b.v > a.v ? b : a));
  return pick.c;
}

/** Min/max of a metric across scored cells — for the heatmap color scale. */
export function metricRange(
  board: Board,
  metric: Metric
): { min: number; max: number } {
  const vals = board.cells
    .map((c) => metricValue(c, metric))
    .filter((v): v is number => v !== null);
  if (vals.length === 0) return { min: 0, max: 1 };
  return { min: Math.min(...vals), max: Math.max(...vals) };
}

/**
 * Pareto frontier over cells: maximize quality, minimize cost. Unscored cells
 * (no mean_score) are excluded — there's no quality axis to be on the frontier of.
 * Mutates nothing; returns the set of frontier keys.
 */
export function frontierKeys(board: Board): Set<string> {
  const scored = board.cells.filter((c) => c.mean_score !== null);
  const out = new Set<string>();
  for (const c of scored) {
    const dominated = scored.some(
      (q) =>
        q !== c &&
        q.mean_cost_usd <= c.mean_cost_usd &&
        (q.mean_score ?? 0) >= (c.mean_score ?? 0) &&
        (q.mean_cost_usd < c.mean_cost_usd ||
          (q.mean_score ?? 0) > (c.mean_score ?? 0))
    );
    if (!dominated) out.add(key(c.model_id, c.stack_id));
  }
  return out;
}

/** Per task: the highest-scoring stack (cell) — different tasks, different winners. */
export interface TaskWinner {
  task: string;
  cell: Cell;
  score: number;
}

export function perTaskWinners(board: Board): TaskWinner[] {
  return board.tasks
    .map((task) => {
      let best: { cell: Cell; score: number } | null = null;
      for (const c of board.cells) {
        const s = c.per_task[task]?.score;
        if (
          s !== null &&
          s !== undefined &&
          (best === null || s > best.score)
        ) {
          best = { cell: c, score: s };
        }
      }
      return best ? { task, cell: best.cell, score: best.score } : null;
    })
    .filter((w): w is TaskWinner => w !== null);
}

/**
 * Scaffolding-lift series: for each model, its cells ordered by harness level —
 * the climb from L0 (bare) up the ladder. Powers the per-model ablation view.
 */
export interface LiftPoint {
  harness: Harness;
  cell: Cell;
}
export interface LiftSeries {
  model: ModelRef;
  points: LiftPoint[]; // ordered by harness level ascending (L0 first)
}

export function scaffoldingLift(board: Board): LiftSeries[] {
  const map = cellMap(board);
  const byLevel = [...board.harnesses].sort((a, b) => a.level - b.level);
  return board.models.map((model) => ({
    model,
    points: byLevel
      .map((harness) => {
        const cell = map.get(key(model.model_id, harness.stack_id));
        return cell ? { harness, cell } : null;
      })
      .filter((p): p is LiftPoint => p !== null),
  }));
}
