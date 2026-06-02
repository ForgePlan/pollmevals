/**
 * TypeScript mirror of the Python `Leaderboard` contract
 * (apps/eval-core-py/src/leaderboard/aggregate.py). The site renders a frozen
 * leaderboard.json produced by `scripts/build_leaderboard.py`.
 *
 * Honesty invariant (mirrors the Python side): cost/latency/token fields are
 * always present; quality fields (meanScore, passAt1, passAtK, passHatK, flaky)
 * are `null` until a run carries real scores — the UI must render that absence
 * truthfully, never as a zero or a fake bar.
 */

export interface LeaderboardEntry {
  model_id: string;
  stack_id: string;
  n_evals: number;
  n_scored: number;
  n_failed: number;
  n_tasks: number;
  n_seeds: number;
  total_cost_usd: string; // Decimal serialized as string
  mean_cost_usd: string;
  total_tokens_in: number;
  total_tokens_out: number;
  mean_latency_ms: number;
  p50_latency_ms: number;
  mean_score: number | null;
  pass_at_1: number | null;
  pass_at_k: number | null;
  pass_hat_k: number | null;
  flaky: number | null;
}

export interface Leaderboard {
  run_hash: string;
  run_type: string;
  methodology_version: string;
  region: string;
  scored: boolean;
  solved_threshold: number;
  n_models: number;
  n_stacks: number;
  n_tasks: number;
  entries: LeaderboardEntry[];
}

/** A point for the cost-vs-(quality|latency) Pareto scatter. */
export interface FrontierPoint {
  entry: LeaderboardEntry;
  x: number; // cost (USD) — lower is better
  y: number; // quality (0-10, scored) or latency-seconds (unscored)
  onFrontier: boolean;
}

/**
 * Compute the Pareto frontier.
 *
 * Scored runs: maximize quality (y), minimize cost (x) → a point is dominated
 * if another is cheaper-or-equal AND higher-or-equal quality.
 * Unscored runs: minimize latency (y) AND cost (x) → both axes "lower is better".
 *
 * Returns points in input order with `onFrontier` flagged.
 */
export function computeFrontier(lb: Leaderboard): FrontierPoint[] {
  const points: FrontierPoint[] = lb.entries.map((entry) => ({
    entry,
    x: Number(entry.mean_cost_usd),
    y: lb.scored ? entry.mean_score ?? 0 : entry.mean_latency_ms / 1000,
    onFrontier: false,
  }));

  for (const p of points) {
    p.onFrontier = !points.some((q) => q !== p && dominates(q, p, lb.scored));
  }
  return points;
}

function dominates(
  a: FrontierPoint,
  b: FrontierPoint,
  scored: boolean
): boolean {
  if (scored) {
    // a dominates b if a is cheaper-or-equal AND higher-quality-or-equal, strictly better on one.
    const cheaper = a.x <= b.x;
    const better = a.y >= b.y;
    const strict = a.x < b.x || a.y > b.y;
    return cheaper && better && strict;
  }
  // unscored: both lower-is-better (cost, latency)
  const cheaper = a.x <= b.x;
  const faster = a.y <= b.y;
  const strict = a.x < b.x || a.y < b.y;
  return cheaper && faster && strict;
}
